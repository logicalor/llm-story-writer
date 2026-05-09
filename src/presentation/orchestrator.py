"""Python pipeline orchestrator for headless story generation.

Top-level entry point for the Python-native story generation pipeline.
Drives phases sequentially with injected async primitives, supporting
both TUI and headless operation without code changes.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from application.interfaces.model_provider import ModelProvider
from application.pipeline.handoffs import (
    ArcAnalysisResult,
    ChapterDraft,
    OutlineResult,
    PipelineState,
)
from config.config_loader import ConfigLoader
from domain.exceptions import StoryGenerationError
from domain.value_objects.generation_settings import GenerationSettings
from presentation.agents.chapter_writer import ChapterWriterAgent
from presentation.agents.consistency_checker import ConsistencyCheckerAgent
from presentation.agents.final_editor import FinalEditorAgent
from presentation.agents.outline_critic import OutlineCriticAgent
from presentation.agents.outline_planner import OutlinePlannerAgent
from presentation.agents.story_foundation import StoryFoundationAgent
from presentation.agents.story_metadata import StoryMetadataAgent
from presentation.agents.story_planner import StoryPlannerAgent
from presentation.agents.wiki_maintainer import WikiMaintainerAgent
from presentation.pipeline_primitives import (
    ApprovalGate,
    NullApprovalGate,
    NullStatusBus,
    StatusBus,
    StatusEvent,
    TokenStreamBus,
    WikiContextBus,
    WikiContextEvent,
)
from tools import recap_index, wiki_generation
from tools._io import STORIES_DIR, _atomic_write, _validate_story_name
from tools._persist import persist_markdown, read_markdown_ref
from tools._wiki import find_pages, get_wiki_dir, slugify as wiki_slugify
from tools.wiki_extract import _bootstrap_single_wiki_entity, _list_wiki_entities
from tools.wiki_init import _init_wiki_for_story
from tools.wiki_update import run_batch as wiki_update_run_batch


def _savepoint_path(story_name: str) -> Path:
    """Return path to the pipeline state savepoint file."""
    return STORIES_DIR / story_name / "savepoints" / "pipeline_state.json"


async def _write_savepoint(state: PipelineState) -> None:
    """Write PipelineState to disk as JSON savepoint (atomic)."""
    path = _savepoint_path(state.story_name)
    _atomic_write(path, state.to_json())


def _coerce_event_list(value: Any) -> list[dict[str, Any]]:
    """Parse recap event output into a list of event objects."""
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []

        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", stripped)
        candidate = fence_match.group(1).strip() if fence_match else stripped

        try:
            return _coerce_event_list(json.loads(candidate))
        except json.JSONDecodeError:
            raise ValueError(f"unparseable event list: {value[:120]!r}") from None

    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]

    if isinstance(value, dict):
        nested = value.get("events")
        if isinstance(nested, list):
            return [item for item in nested if isinstance(item, dict)]

    return []


def _coerce_string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if not isinstance(value, list):
        return []

    values: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        stripped = item.strip()
        if stripped and stripped not in values:
            values.append(stripped)
    return values


def _importance_to_impact(value: str) -> str:
    return {"high": "major", "medium": "moderate", "low": "minor"}.get(
        value,
        "moderate",
    )


def _build_recap_event_detail_levels(
    event: dict[str, Any], title: str
) -> dict[str, str]:
    summary = str(event.get("summary") or event.get("description") or title).strip()
    impact_text = str(event.get("impact") or "").strip()
    timestamp = str(
        event.get("timestamp")
        or event.get("date_start")
        or event.get("date")
        or event.get("time")
        or ""
    ).strip()
    key_events = _coerce_string_list(event.get("key_events"))
    locations = _coerce_string_list(event.get("locations"))
    character_development = _coerce_string_list(event.get("character_development"))

    l1 = summary or title

    l2_parts = [part for part in (summary, impact_text) if part]
    if timestamp:
        l2_parts.append(f"Timestamp: {timestamp}")
    l2 = " ".join(l2_parts) or title

    l3_parts = [f"Summary: {summary or title}"]
    if timestamp:
        l3_parts.append(f"Timestamp: {timestamp}")
    if key_events:
        l3_parts.append("Key events: " + "; ".join(key_events))
    if character_development:
        l3_parts.append("Character development: " + "; ".join(character_development))
    if locations:
        l3_parts.append("Locations: " + ", ".join(locations))
    if impact_text:
        l3_parts.append(f"Impact: {impact_text}")

    return {
        "L1": l1,
        "L2": l2,
        "L3": "\n\n".join(l3_parts),
    }


def _sync_recap_events_to_wiki(
    story_name: str,
    chapter_number: int,
    recap_events: Any,
) -> dict[str, Any]:
    """Create or update wiki event pages from recap output."""
    events = _coerce_event_list(recap_events)
    if not events:
        return {"created": 0, "updated": 0, "timeline_events": 0, "entity_counts": {}}

    story_dir = _validate_story_name(story_name)
    wiki_dir = get_wiki_dir(story_dir)
    creates: list[dict[str, Any]] = []
    updates: list[dict[str, Any]] = []

    for index, event in enumerate(events, start=1):
        title = str(
            event.get("name")
            or event.get("title")
            or event.get("summary")
            or event.get("description")
            or f"Chapter {chapter_number} Event {index}"
        ).strip()
        if not title:
            continue

        slug = wiki_slugify(title)
        if not slug:
            continue

        importance = str(event.get("importance") or "medium").strip().lower()
        if importance not in {"high", "medium", "low"}:
            importance = "medium"

        timestamp = str(
            event.get("timestamp")
            or event.get("date_start")
            or event.get("date")
            or event.get("time")
            or ""
        ).strip()
        participant_names = _coerce_string_list(
            event.get("participants")
            or event.get("characters")
            or event.get("key_characters")
        )
        participants = [wiki_slugify(name) for name in participant_names if name]
        emotional_state = str(
            event.get("emotional_state")
            or event.get("emotion")
            or event.get("mood")
            or ""
        ).strip()
        causal_context = str(
            event.get("causal_context") or event.get("cause") or ""
        ).strip()
        detail_levels = _build_recap_event_detail_levels(event, title)
        body = detail_levels["L3"]

        payload_item = {
            "slug": slug,
            "page_type": "event",
            "page_name": title,
            "confidence": "verified",
            "first_appearance": chapter_number,
            "chapter": chapter_number,
            "impact": _importance_to_impact(importance),
            "detail_levels": detail_levels,
            "body": body,
            "frontmatter": {
                "name": title,
                "confidence": "verified",
                "chapter": chapter_number,
                "impact": _importance_to_impact(importance),
                "timestamp": timestamp,
                "participants": participants,
                "importance": importance,
                "emotional_state": emotional_state,
                "causal_context": causal_context,
                "chapter_provenance": chapter_number,
            },
        }

        if find_pages(wiki_dir, slug=slug):
            updates.append(payload_item)
        else:
            creates.append(payload_item)

    if not creates and not updates:
        return {"created": 0, "updated": 0, "timeline_events": 0, "entity_counts": {}}

    return wiki_update_run_batch(
        story_name,
        {
            "creates": creates,
            "updates": updates,
            "timeline_events": [],
        },
    )


def _work_item_done(state: PipelineState, phase: str, item_id: str) -> bool:
    return item_id in state.completed_work_items.get(phase, [])


async def _mark_work_item_done(state: PipelineState, phase: str, item_id: str) -> None:
    state.completed_work_items.setdefault(phase, [])
    if item_id not in state.completed_work_items[phase]:
        state.completed_work_items[phase].append(item_id)
    await _write_savepoint(state)


async def _load_savepoint(story_name: str) -> PipelineState | None:
    """Load a PipelineState from disk. Returns None if no savepoint exists."""
    path = _savepoint_path(story_name)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return PipelineState.from_dict(data)


def _create_provider(config: dict[str, Any]) -> ModelProvider:
    from infrastructure.providers.openai_async_provider import OpenAIAsyncProvider

    return OpenAIAsyncProvider(
        base_url=config.get("model_api_base"),
        context_length=config.get("context_length", 16384),
        randomize_seed=config.get("randomize_seed", True),
        timeout=float(config.get("request_timeout", 600.0)),
    )


def _load_story_prompt(story_name: str, story_root: Path) -> str:
    story_state_path = story_root / "state.json"
    if not story_state_path.exists():
        return ""

    data = json.loads(story_state_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return ""

    for key in ("story_prompt", "prompt", "initial_prompt"):
        value = data.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return read_markdown_ref(story_root, value)
    return ""


def _load_settings(config: dict[str, Any]) -> GenerationSettings:
    generation_config = config.get("generation", {})
    if not isinstance(generation_config, dict):
        generation_config = {}
    return GenerationSettings.from_dict(generation_config)


async def _mark_phase_complete(
    state: PipelineState, phase_name: str, savepoint_name: str
) -> None:
    if phase_name not in state.completed_phases:
        state.completed_phases.append(phase_name)
    state.savepoint_id = savepoint_name
    state.current_phase = phase_name
    if savepoint_name not in state.savepoints:
        state.savepoints.append(savepoint_name)
    await _write_savepoint(state)


def _write_chapter_file(story_dir: Path, chapter_number: int, content: str) -> None:
    """Write an approved chapter's content to disk."""
    chapters_dir = story_dir / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    (chapters_dir / f"chapter_{chapter_number}.md").write_text(
        content, encoding="utf-8"
    )


def _edited_chapter_path(story_name: str, chapter_number: int) -> Path:
    """Return path for a per-chapter final-edit output."""
    return STORIES_DIR / story_name / "chapters" / f"chapter_{chapter_number}_edited.md"


def _write_story_metadata(
    story_dir: Path, title: str, summary: str, tags: list[str]
) -> None:
    """Write story metadata to disk."""
    metadata = {
        "title": title,
        "summary": summary,
        "tags": tags,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    metadata_path = story_dir / "metadata.json"
    _atomic_write(metadata_path, json.dumps(metadata, indent=2, ensure_ascii=False))


def _backfill_missing_chapter_files(
    story_dir: Path, approved_chapters: list[ChapterDraft]
) -> None:
    """Write persisted approved chapters that are absent from disk."""
    chapters_dir = story_dir / "chapters"
    for draft in approved_chapters:
        chapter_path = chapters_dir / f"chapter_{draft.chapter_number}.md"
        if chapter_path.exists():
            continue
        _write_chapter_file(story_dir, draft.chapter_number, draft.content)


def _chapter_numbers(
    outline_result: OutlineResult | None, settings: GenerationSettings
) -> list[int]:
    if outline_result is not None and outline_result.chapter_outlines:
        return list(range(1, len(outline_result.chapter_outlines) + 1))
    return list(range(1, min(settings.wanted_chapters, 3) + 1))


async def _await_outline_approval(
    state: PipelineState,
    gate: ApprovalGate,
    agent: OutlinePlannerAgent,
    story_name: str,
    story_prompt: str,
    settings: GenerationSettings,
    base_context: str = "",
    story_elements: str = "",
    provider: ModelProvider | None = None,
    config: dict[str, Any] | None = None,
    bus: TokenStreamBus | None = None,
    wiki_bus: WikiContextBus | None = None,
    sbus: StatusBus | None = None,
) -> PipelineState:
    while True:
        decision = await gate.await_decision()
        if decision.approved:
            return state
        if decision.feedback is None:
            state.status = "rejected"
            await _write_savepoint(state)
            return state

        critic_parts: list[str] = []
        if state.critic_summary:
            critic_parts.append(f"### Arc & Synthesis Summary\n{state.critic_summary}")
        if state.arc_distribution:
            critic_parts.append(f"### Arc Distribution\n{state.arc_distribution}")
        if state.promise_payoff:
            critic_parts.append(
                f"### Promise / Payoff Analysis\n{state.promise_payoff}"
            )
        critic_context = "\n\n".join(critic_parts)

        state.outline_result = await agent.run(
            story_name,
            story_prompt,
            settings,
            feedback=decision.feedback,
            base_context=base_context,
            story_elements=story_elements,
            critic_context=critic_context,
        )

        state.critic_summary = ""
        state.arc_distribution = ""
        state.promise_payoff = ""
        if "outline-critique" in state.completed_phases:
            state.completed_phases.remove("outline-critique")
        outline_items = state.completed_work_items.get("outline", [])
        if "outline/critique" in outline_items:
            outline_items.remove("outline/critique")

        if (
            settings.enable_outline_critique
            and provider is not None
            and config is not None
            and bus is not None
            and wiki_bus is not None
        ):
            _sbus = sbus if sbus is not None else NullStatusBus()
            await _emit_status(
                _sbus,
                "outline-critique",
                "Re-running outline critics after revision",
                kind="phase_start",
            )
            await bus.emit(
                "\n=== outline-critique: Re-running outline critics after revision ===\n"
            )
            critic_agent = OutlineCriticAgent(provider, config, bus, wiki_bus)
            state = await critic_agent.run(state, settings)
            await _mark_work_item_done(state, "outline", "outline/critique")
        else:
            await _write_savepoint(state)


def _scene_tag(issue: dict[str, Any]) -> str:
    scene_num = issue.get("scene_number")
    return f" [Scene {scene_num}]" if scene_num is not None else ""


async def _emit_consistency_results(
    bus: TokenStreamBus,
    chapter_number: int,
    consistency_result: dict[str, Any],
) -> None:
    """Emit consistency check findings to the token bus."""
    if not consistency_result["passed"]:
        await bus.emit(f"\n[Consistency] Chapter {chapter_number} — issues found:\n")
        for issue in consistency_result["issues"]:
            tag = _scene_tag(issue)
            await bus.emit(
                f"  [{issue['severity'].upper()}]{tag} {issue['description']}\n"
            )
    elif consistency_result["issues"]:
        await bus.emit(
            f"\n[Consistency] Chapter {chapter_number} — warnings/info found:\n"
        )
        for issue in consistency_result["issues"]:
            tag = _scene_tag(issue)
            await bus.emit(
                f"  [{issue['severity'].upper()}]{tag} {issue['description']}\n"
            )


def _format_consistency_results(
    chapter_number: int, consistency_result: dict[str, Any]
) -> str:
    """Format consistency check findings as text for injection into revision feedback."""
    issues = consistency_result.get("issues", [])
    if not issues:
        return ""
    lines = [f"## Consistency Check Findings — Chapter {chapter_number}"]
    for issue in issues:
        severity = issue.get("severity", "info").upper()
        description = issue.get("description", "")
        tag = _scene_tag(issue)
        lines.append(f"- [{severity}]{tag} {description}")
    return "\n".join(lines)


async def _generate_chapter_with_gate(
    state: PipelineState,
    gate: ApprovalGate,
    agent: ChapterWriterAgent,
    story_name: str,
    chapter_number: int,
    outline_result: OutlineResult,
    settings: GenerationSettings,
    consistency_agent: ConsistencyCheckerAgent | None = None,
    bus: TokenStreamBus | None = None,
) -> ChapterDraft | None:
    draft = await agent.run(
        story_name,
        chapter_number,
        outline_result,
        settings,
        recaps=state.recaps,
        state=state,
    )
    consistency_result: dict[str, Any] | None = None
    last_consistency_text = ""
    if consistency_agent is not None and bus is not None:
        try:
            consistency_result = await consistency_agent.run(
                story_name,
                chapter_number,
                draft.content,
                outline_result=outline_result,
            )
            await _emit_consistency_results(bus, chapter_number, consistency_result)
            last_consistency_text = _format_consistency_results(
                chapter_number, consistency_result
            )
            await _mark_work_item_done(
                state,
                f"chapter-{chapter_number}",
                f"chapter-{chapter_number}/consistency-check",
            )
        except Exception as exc:
            await bus.emit(
                f"\n[Consistency] Chapter {chapter_number} check failed "
                f"({type(exc).__name__}: {exc})\n"
            )

    while True:
        decision = await gate.await_decision()
        if decision.approved:
            if (
                decision.auto_approved
                and settings.enable_consistency_revision_loop
                and consistency_agent is not None
                and bus is not None
            ):
                for _cr_iter in range(settings.consistency_max_iterations):
                    if consistency_result is None:
                        break
                    _has_critical = any(
                        issue.get("severity") == "critical"
                        for issue in consistency_result.get("issues", [])
                    )
                    if not _has_critical:
                        break
                    _cr_feedback = _format_consistency_results(
                        chapter_number, consistency_result
                    )
                    if draft.content:
                        _cr_feedback = f"{_cr_feedback}\n\n## Current Chapter Draft\n{draft.content}"
                    draft = await agent.run(
                        story_name,
                        chapter_number,
                        outline_result,
                        settings,
                        feedback=_cr_feedback,
                        recaps=state.recaps,
                        state=state,
                    )
                    await _mark_work_item_done(
                        state,
                        f"chapter-{chapter_number}",
                        f"chapter-{chapter_number}/consistency-revision-{_cr_iter + 1}",
                    )
                    await _write_savepoint(state)
                    try:
                        consistency_result = await consistency_agent.run(
                            story_name,
                            chapter_number,
                            draft.content,
                            outline_result=outline_result,
                        )
                        await _emit_consistency_results(
                            bus, chapter_number, consistency_result
                        )
                    except Exception as exc:
                        await bus.emit(f"\n[Consistency] Revision check error: {exc}\n")
                        break
                else:
                    if consistency_result is not None:
                        _residual = [
                            i
                            for i in consistency_result.get("issues", [])
                            if i.get("severity") in ("warning", "info")
                        ]
                        if _residual:
                            await bus.emit(
                                f"\n[Consistency] {len(_residual)} advisory issue(s) remain after max iterations.\n"
                            )
            return draft
        if decision.feedback is None:
            state.status = "rejected"
            await _write_savepoint(state)
            return None

        combined_feedback = decision.feedback
        if last_consistency_text:
            combined_feedback = f"{combined_feedback}\n\n{last_consistency_text}"
        if draft.content:
            combined_feedback = (
                f"{combined_feedback}\n\n## Current Chapter Draft\n{draft.content}"
            )
        last_consistency_text = ""
        draft = await agent.run(
            story_name,
            chapter_number,
            outline_result,
            settings,
            feedback=combined_feedback,
            recaps=state.recaps,
            state=state,
        )
        if consistency_agent is not None and bus is not None:
            try:
                consistency_result = await consistency_agent.run(
                    story_name,
                    chapter_number,
                    draft.content,
                    outline_result=outline_result,
                )
                await _emit_consistency_results(bus, chapter_number, consistency_result)
                last_consistency_text = _format_consistency_results(
                    chapter_number, consistency_result
                )
                await _mark_work_item_done(
                    state,
                    f"chapter-{chapter_number}",
                    f"chapter-{chapter_number}/consistency-check",
                )
            except Exception as exc:
                await bus.emit(
                    f"\n[Consistency] Chapter {chapter_number} check failed "
                    f"({type(exc).__name__}: {exc})\n"
                )
        await _write_savepoint(state)


def _build_story_elements(outline_result: OutlineResult, story_root: Path) -> str:
    """Build story_elements string from OutlineResult for prompt injection."""
    _summary = outline_result.summary
    resolved_summary = (
        read_markdown_ref(story_root, _summary)
        if isinstance(_summary, dict)
        else (_summary or "")
    )
    parts = [resolved_summary]
    if outline_result.chapter_outlines:
        resolved_outlines: list[dict[str, Any]] = []
        for chapter in outline_result.chapter_outlines:
            chapter_copy = dict(chapter)
            summary = chapter_copy.get("summary")
            if isinstance(summary, dict):
                chapter_copy["summary"] = read_markdown_ref(story_root, summary)
            elif isinstance(summary, str):
                chapter_copy["summary"] = summary
            resolved_outlines.append(chapter_copy)
        parts.append(json.dumps(resolved_outlines, ensure_ascii=False))
    return "\n\n".join(parts)


async def _run_story_foundation(
    story_name: str,
    story_prompt: str,
    provider: ModelProvider,
    config: dict[str, Any],
    bus: TokenStreamBus,
    wiki_bus: WikiContextBus,
    settings: GenerationSettings,
) -> OutlineResult:
    """Run the Story Foundation phase to extract base_context, story_start_date, story_elements."""
    agent = StoryFoundationAgent(provider, config, bus, wiki_bus)
    return await agent.run(story_name, story_prompt, settings)


async def _emit_status(
    status_bus: StatusBus,
    phase: str,
    message: str,
    kind: str = "info",
    detail: str = "",
) -> None:
    """Emit a status event, also mirroring a banner line into the token bus is
    handled by callers when desired. Safe with NullStatusBus."""
    await status_bus.emit(
        StatusEvent(phase=phase, message=message, kind=kind, detail=detail)
    )


def _write_quality_report(
    state: PipelineState,
    story_dir: Path,
    config: dict[str, Any],
) -> None:
    """Append a quality-telemetry entry to stories/{name}/quality_report.json."""
    report_path = story_dir / "quality_report.json"
    try:
        existing: list[dict[str, Any]] = (
            json.loads(report_path.read_text(encoding="utf-8"))
            if report_path.exists()
            else []
        )
    except (json.JSONDecodeError, OSError):
        existing = []

    model_name = (
        config.get("models", {}).get("chapter_writer")
        or config.get("models", {}).get("default")
        or "unknown"
    )
    generation = config.get("generation", {}) or {}
    settings_snapshot = {
        k: generation.get(k)
        for k in (
            "seed",
            "wanted_chapters",
            "min_scene_score",
            "max_critique_iterations",
        )
        if generation.get(k) is not None
    }

    entry: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model_name,
        "settings_snapshot": settings_snapshot,
        "chapters": state.quality_telemetry,
    }
    existing.append(entry)
    report_path.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8"
    )


async def _continue_pipeline(
    state: PipelineState,
    gate: ApprovalGate,
    bus: TokenStreamBus,
    wiki_bus: WikiContextBus,
    config: dict[str, Any] | None,
    provider: ModelProvider | None,
    status_bus: StatusBus | None = None,
) -> PipelineState:
    resolved_config = config if config is not None else ConfigLoader().load_config()
    resolved_provider = provider or _create_provider(resolved_config)
    settings = _load_settings(resolved_config)
    sbus = status_bus if status_bus is not None else NullStatusBus()

    story_dir = STORIES_DIR / state.story_name
    (story_dir / "savepoints").mkdir(parents=True, exist_ok=True)
    story_prompt = _load_story_prompt(state.story_name, story_dir)

    async def _banner(phase: str, message: str) -> None:
        """Emit a status event AND a visible banner line into the token log."""
        await _emit_status(sbus, phase, message, kind="phase_start")
        await bus.emit(f"\n=== {phase}: {message} ===\n")

    try:
        if state.completed_work_items:
            for completed_phase in state.completed_phases:
                await _emit_status(sbus, completed_phase, "(resumed)", "phase_end")

            for phase, items in state.completed_work_items.items():
                if phase not in state.completed_phases and items:
                    last_done = items[-1]
                    await _emit_status(
                        sbus,
                        phase,
                        f"Resuming at: next step after {last_done}",
                        "step",
                    )

        if "story-foundation" not in state.completed_phases:
            state.current_phase = "story-foundation"
            await _banner(
                "story-foundation",
                "Extracting base context, story start date, and core elements",
            )
            foundation_result = await _run_story_foundation(
                state.story_name,
                story_prompt,
                resolved_provider,
                resolved_config,
                bus,
                wiki_bus,
                settings,
            )
            if state.outline_result is None:
                state.outline_result = foundation_result
            else:
                state.outline_result.story_start_date = (
                    foundation_result.story_start_date
                )
            if (
                isinstance(foundation_result.base_context, str)
                and foundation_result.base_context
            ):
                state.outline_result.base_context = persist_markdown(
                    story_dir,
                    "outline/base_context.md",
                    foundation_result.base_context,
                )
            elif isinstance(foundation_result.base_context, dict):
                state.outline_result.base_context = foundation_result.base_context
            if (
                isinstance(foundation_result.story_elements, str)
                and foundation_result.story_elements
            ):
                state.outline_result.story_elements = persist_markdown(
                    story_dir,
                    "outline/story_elements.md",
                    foundation_result.story_elements,
                )
            elif isinstance(foundation_result.story_elements, dict):
                state.outline_result.story_elements = foundation_result.story_elements
            if (
                isinstance(foundation_result.style_guide, str)
                and foundation_result.style_guide
            ):
                persist_markdown(
                    story_dir,
                    "style_guide.md",
                    foundation_result.style_guide,
                )
                state.style_guide = foundation_result.style_guide
            await _mark_phase_complete(
                state,
                "story-foundation",
                "story_foundation_complete",
            )
            await _emit_status(
                sbus,
                "story-foundation",
                "Foundation complete",
                kind="phase_end",
            )

        if "outline" not in state.completed_phases:
            state.current_phase = "outline"
            await _banner("outline", "Generating chapter outline")
            outline_phase = "outline"
            outline_agent = OutlinePlannerAgent(
                resolved_provider, resolved_config, bus, wiki_bus
            )
            _raw_bc = (
                state.outline_result.base_context
                if state.outline_result is not None
                else ""
            )
            _foundation_base_context = (
                read_markdown_ref(story_dir, _raw_bc)
                if isinstance(_raw_bc, dict)
                else (_raw_bc or "")
            )
            _foundation_story_start_date = (
                state.outline_result.story_start_date
                if state.outline_result is not None
                else ""
            )
            _raw_se = (
                state.outline_result.story_elements
                if state.outline_result is not None
                else ""
            )
            _foundation_story_elements = (
                read_markdown_ref(story_dir, _raw_se)
                if isinstance(_raw_se, dict)
                else (_raw_se or "")
            )
            if not _work_item_done(state, outline_phase, "outline/draft"):
                state.outline_result = await outline_agent.run(
                    state.story_name,
                    story_prompt,
                    settings,
                    base_context=_foundation_base_context,
                    story_elements=_foundation_story_elements,
                )
                for index, chapter in enumerate(
                    state.outline_result.chapter_outlines,
                    start=1,
                ):
                    summary = chapter.get("summary")
                    if isinstance(summary, str) and summary:
                        chapter["summary"] = persist_markdown(
                            story_dir,
                            f"outline/chapter_{index}_summary.md",
                            summary,
                        )
                enrichment_suggestions = state.outline_result.enrichment_suggestions
                if (
                    isinstance(enrichment_suggestions, str)
                    and enrichment_suggestions.strip()
                ):
                    match = re.search(
                        r"```json\s*(.*?)\s*```",
                        enrichment_suggestions,
                        re.DOTALL,
                    )
                    enrichment_text = (
                        match.group(1) if match else enrichment_suggestions.strip()
                    )
                    try:
                        parsed_enrichment = (
                            json.loads(enrichment_text) if enrichment_text else {}
                        )
                    except json.JSONDecodeError:
                        parsed_enrichment = {}
                    if not isinstance(parsed_enrichment, dict):
                        parsed_enrichment = {}
                    _atomic_write(
                        story_dir / "outline" / "enrichment_suggestions.json",
                        json.dumps(
                            parsed_enrichment,
                            indent=2,
                            ensure_ascii=False,
                        ),
                    )
                    state.outline_result.enrichment_suggestions = {
                        "$ref": "outline/enrichment_suggestions.json"
                    }
                if not state.outline_result.base_context and _foundation_base_context:
                    state.outline_result.base_context = persist_markdown(
                        story_dir,
                        "outline/base_context.md",
                        _foundation_base_context,
                    )
                if not state.outline_result.story_start_date:
                    state.outline_result.story_start_date = _foundation_story_start_date
                if (
                    not state.outline_result.story_elements
                    and _foundation_story_elements
                ):
                    state.outline_result.story_elements = persist_markdown(
                        story_dir,
                        "outline/story_elements.md",
                        _foundation_story_elements,
                    )
                # Persist generated outline before approval so a crash mid-gate
                # preserves it. The phase is only marked complete on approval.
                state.savepoint_id = "outline"
                await _write_savepoint(state)
                await _mark_work_item_done(state, outline_phase, "outline/draft")

            if (
                settings.enable_outline_critique
                and "outline-critique" not in state.completed_phases
                and not _work_item_done(state, outline_phase, "outline/critique")
            ):
                await _banner(
                    "outline-critique",
                    "Running outline critic passes",
                )
                critic_agent = OutlineCriticAgent(
                    resolved_provider,
                    resolved_config,
                    bus,
                    wiki_bus,
                )
                state = await critic_agent.run(state, settings)
                await _write_savepoint(state)
                await _mark_work_item_done(state, outline_phase, "outline/critique")

            await _emit_status(
                sbus,
                "outline",
                "Awaiting outline approval",
                kind="awaiting",
            )
            state = await _await_outline_approval(
                state,
                gate,
                outline_agent,
                state.story_name,
                story_prompt,
                settings,
                base_context=_foundation_base_context,
                story_elements=_foundation_story_elements,
                provider=resolved_provider,
                config=resolved_config,
                bus=bus,
                wiki_bus=wiki_bus,
                sbus=sbus,
            )
            if state.status == "rejected":
                return state
            await _mark_phase_complete(state, "outline", "outline")
            await _emit_status(sbus, "outline", "Outline approved", kind="phase_end")

        if "metadata-outline" not in state.completed_phases:
            state.current_phase = "metadata-outline"
            await _banner("metadata-outline", "Generating story title and tags")
            if state.outline_result is not None:
                try:
                    metadata_agent = StoryMetadataAgent(
                        resolved_provider, resolved_config, bus, wiki_bus
                    )
                    outline_text = _build_story_elements(
                        state.outline_result, story_dir
                    )
                    metadata_result = await metadata_agent.run(
                        state.story_name,
                        outline_text,
                        "",
                        settings,
                    )
                    state.outline_result.title = metadata_result.title
                    state.outline_result.tags = metadata_result.tags
                    _write_story_metadata(
                        story_dir,
                        metadata_result.title,
                        metadata_result.summary,
                        metadata_result.tags,
                    )
                    await _write_savepoint(state)
                except Exception as exc:
                    await bus.emit(
                        f"\n[Metadata] outline metadata skipped ({type(exc).__name__}: {exc})\n"
                    )
            await _mark_phase_complete(
                state,
                "metadata-outline",
                "metadata_outline_complete",
            )

        if "narrative-arc" not in state.completed_phases:
            state.current_phase = "narrative-arc"
            await _banner("narrative-arc", "Analysing narrative arc")
            if state.outline_result is not None:
                arc_agent = StoryPlannerAgent(
                    resolved_provider, resolved_config, bus, wiki_bus
                )
                try:
                    arc_result: ArcAnalysisResult = await arc_agent.run(state, settings)
                    state.arc_result = arc_result
                    await bus.emit(
                        f"\n[Narrative Arc] {arc_result.verdict_code}: "
                        f"{arc_result.arc_assessment[:200]}\n"
                    )
                except Exception as exc:
                    await bus.emit(
                        f"\n[Narrative Arc] arc analysis skipped ({type(exc).__name__}: {exc})\n"
                    )
            await _mark_phase_complete(state, "narrative-arc", "arc_analysis_complete")

        # Ensure wiki is initialized before any chapter wiki maintenance
        wiki_init_result = _init_wiki_for_story(state.story_name, STORIES_DIR)
        if "error" in wiki_init_result:
            raise StoryGenerationError(
                f"Wiki initialization failed for story '{state.story_name}': "
                f"{wiki_init_result['error']}"
            )

        if "wiki-generation" not in state.completed_phases:
            state.current_phase = "wiki-generation"
            await _banner("wiki-generation", "Generating wiki pages from outline")
            await wiki_bus.emit(
                WikiContextEvent(
                    phase="wiki-generation",
                    event_type="entity_match",
                    content=f"Generating planned wiki pages for: {state.story_name}",
                )
            )
            if state.outline_result is not None:
                char_result = await asyncio.to_thread(
                    wiki_generation.generate_character_pages,
                    state.story_name,
                    state.outline_result,
                    resolved_provider,
                    resolved_config,
                    story_dir.parent,
                )
                loc_result = await asyncio.to_thread(
                    wiki_generation.generate_location_pages,
                    state.story_name,
                    state.outline_result,
                    resolved_provider,
                    resolved_config,
                    story_dir.parent,
                )
                entity_result = await asyncio.to_thread(
                    wiki_generation.generate_outline_entity_pages,
                    state.story_name,
                    state.outline_result,
                    resolved_provider,
                    resolved_config,
                    story_dir.parent,
                )
                total_generated = (
                    char_result["generated"]
                    + loc_result["generated"]
                    + entity_result["generated"]
                )
                if (
                    total_generated == 0
                    and char_result["skipped"] == 0
                    and loc_result["skipped"] == 0
                    and entity_result["skipped"] == 0
                ):
                    await _write_savepoint(state)
                    raise StoryGenerationError("wiki-generation produced no pages")
            await _mark_phase_complete(
                state,
                "wiki-generation",
                "wiki_pages_generated",
            )

        if "wiki-bootstrap" not in state.completed_phases:
            state.current_phase = "wiki-bootstrap"
            await _banner("wiki-bootstrap", "Seeding wiki from outline entities")
            models = resolved_config.get("models", {})
            wiki_model: str | None = models.get("chapter_writer")
            await bus.emit("\n[Wiki Bootstrap] Seeding wiki from outline entities...\n")
            bootstrap_ok = False
            try:
                entities = await asyncio.to_thread(
                    _list_wiki_entities,
                    state.story_name,
                    model=wiki_model,
                )
                phase = "wiki-bootstrap"
                created = 0
                skipped = 0
                wiki_dir = STORIES_DIR / state.story_name / "wiki"
                for entity in entities:
                    slug = wiki_slugify(entity.get("name", ""))
                    if not slug:
                        continue
                    item_id = f"wiki-bootstrap/{slug}"
                    if _work_item_done(state, phase, item_id):
                        skipped += 1
                        await _emit_status(
                            sbus,
                            phase,
                            f"Skipped: {slug} (already done)",
                            "step",
                        )
                        continue
                    await asyncio.to_thread(
                        _bootstrap_single_wiki_entity,
                        state.story_name,
                        entity,
                        model=wiki_model,
                        wiki_dir=wiki_dir,
                    )
                    await _mark_work_item_done(state, phase, item_id)
                    await _emit_status(
                        sbus,
                        phase,
                        f"Wiki page created: {slug}",
                        "step",
                    )
                    created += 1
                await bus.emit(
                    f"[Wiki Bootstrap] Created {created} pages, "
                    f"skipped {skipped} existing.\n"
                )
                bootstrap_ok = bool(entities)
                if not bootstrap_ok:
                    # No outline/sheet entities to seed from — but the wiki
                    # may already have been populated by an earlier phase
                    # (e.g. wiki-generation). If so, treat bootstrap as a
                    # no-op success rather than blocking forever.
                    existing_pages = (
                        sum(1 for _ in wiki_dir.rglob("*.md") if _.parent != wiki_dir)
                        if wiki_dir.exists()
                        else 0
                    )
                    if existing_pages > 0:
                        bootstrap_ok = True
                        await bus.emit(
                            f"[Wiki Bootstrap] Wiki already populated "
                            f"({existing_pages} pages) — nothing to seed.\n"
                        )
                    else:
                        await _emit_status(
                            sbus,
                            "wiki-bootstrap",
                            "Bootstrap returned 0 pages — phase will retry on next run",
                            kind="warn",
                        )
            except Exception as exc:
                await bus.emit(
                    f"[Wiki Bootstrap] FAILED ({type(exc).__name__}: {exc})\n"
                )
                await _emit_status(
                    sbus,
                    "wiki-bootstrap",
                    f"bootstrap failed ({type(exc).__name__}: {exc})",
                    kind="error",
                )
            if bootstrap_ok:
                await _mark_phase_complete(state, "wiki-bootstrap", "wiki_populated")
            else:
                # Persist current state but do not mark phase complete, so
                # resume will retry. Surface the issue prominently.
                await bus.emit(
                    "[Wiki Bootstrap] Phase NOT marked complete — resume will "
                    "retry. Check provider/timeout settings.\n"
                )
                await _write_savepoint(state)

        outline_result = state.outline_result
        if outline_result is None:
            raise StoryGenerationError(
                "Outline phase did not produce an outline result"
            )

        chapter_numbers = _chapter_numbers(outline_result, settings)
        _backfill_missing_chapter_files(story_dir, state.approved_chapters)
        if "chapter-loop" not in state.completed_phases:
            chapter_agent = ChapterWriterAgent(
                resolved_provider, resolved_config, bus, wiki_bus, sbus
            )
            wiki_agent = WikiMaintainerAgent(
                resolved_provider, resolved_config, bus, wiki_bus
            )
            consistency_agent = ConsistencyCheckerAgent(
                resolved_provider,
                resolved_config,
                bus,
                wiki_bus,
            )

            for chapter_number in chapter_numbers:
                phase = f"chapter-{chapter_number}"
                if phase in state.completed_phases:
                    continue
                state.current_phase = phase
                total = len(chapter_numbers)
                await _banner(
                    phase,
                    f"Drafting chapter {chapter_number} of {total}",
                )
                draft_item_id = f"chapter-{chapter_number}/draft"
                if not _work_item_done(state, phase, draft_item_id):
                    if chapter_number <= len(state.approved_chapters):
                        await _mark_work_item_done(state, phase, draft_item_id)
                        draft = state.approved_chapters[chapter_number - 1]
                    else:
                        generated_draft = await _generate_chapter_with_gate(
                            state,
                            gate,
                            chapter_agent,
                            state.story_name,
                            chapter_number,
                            outline_result,
                            settings,
                            consistency_agent=consistency_agent,
                            bus=bus,
                        )
                        if generated_draft is None:
                            return state
                        draft = generated_draft
                        state.approved_chapters.append(draft)
                        _write_chapter_file(story_dir, chapter_number, draft.content)
                        await _mark_work_item_done(state, phase, draft_item_id)
                else:
                    draft = state.approved_chapters[chapter_number - 1]

                consistency_meta: dict[str, Any] = {
                    "passed": True,
                    "critical_count": 0,
                    "warning_count": 0,
                }
                consistency_item_id = f"chapter-{chapter_number}/consistency-check"
                if not _work_item_done(state, phase, consistency_item_id):
                    if consistency_agent is not None and bus is not None:
                        try:
                            consistency_result = await consistency_agent.run(
                                state.story_name,
                                chapter_number,
                                draft.content,
                                outline_result=outline_result,
                            )
                            await _emit_consistency_results(
                                bus, chapter_number, consistency_result
                            )
                            draft.consistency_findings = consistency_result.get(
                                "issues", []
                            )
                            _issues = consistency_result.get("issues", [])
                            _critical = sum(
                                1 for i in _issues if i.get("severity") == "critical"
                            )
                            _warnings = sum(
                                1
                                for i in _issues
                                if i.get("severity") in ("warning", "info")
                            )
                            consistency_meta = {
                                "passed": consistency_result.get("passed", True),
                                "critical_count": _critical,
                                "warning_count": _warnings,
                            }
                        except Exception as exc:
                            await bus.emit(
                                f"\n[Consistency] Chapter {chapter_number} check failed "
                                f"({type(exc).__name__}: {exc})\n"
                            )
                    await _mark_work_item_done(state, phase, consistency_item_id)

                wiki_item_id = f"chapter-{chapter_number}/wiki-update"
                if not _work_item_done(state, phase, wiki_item_id):
                    await _emit_status(
                        sbus,
                        phase,
                        f"Updating wiki for chapter {chapter_number}",
                        kind="step",
                    )
                    try:
                        wiki_batch = await wiki_agent.run(
                            state.story_name, chapter_number, draft.content
                        )
                        state.wiki_batches.append(wiki_batch)
                        await _mark_work_item_done(state, phase, wiki_item_id)
                    except Exception as exc:
                        await bus.emit(
                            f"\n[Wiki] chapter {chapter_number} wiki update skipped "
                            f"({type(exc).__name__}: {exc})\n"
                        )

                recap_item_id = f"chapter-{chapter_number}/recap"
                if not _work_item_done(state, phase, recap_item_id):
                    try:
                        from presentation.agents.recap_writer import (
                            RecapWriterAgent,
                        )

                        recap_agent = RecapWriterAgent(
                            resolved_provider, resolved_config, bus, wiki_bus
                        )
                        previous_recap_data = state.recaps.get(
                            str(chapter_number - 1),
                            "",
                        )
                        if isinstance(previous_recap_data, dict):
                            previous_recap = (
                                (
                                    read_markdown_ref(story_dir, _r)
                                    if isinstance(
                                        _r := previous_recap_data.get("sanitised"),
                                        dict,
                                    )
                                    else (_r or "")
                                )
                                or (
                                    read_markdown_ref(story_dir, _r)
                                    if isinstance(
                                        _r := previous_recap_data.get("compact"), dict
                                    )
                                    else (_r or "")
                                )
                                or (
                                    read_markdown_ref(story_dir, _r)
                                    if isinstance(
                                        _r := previous_recap_data.get("events"), dict
                                    )
                                    else (_r or "")
                                )
                                or ""
                            )
                        elif isinstance(previous_recap_data, str):
                            previous_recap = previous_recap_data
                        else:
                            previous_recap = str(previous_recap_data)
                        story_start_date = (
                            state.outline_result.story_start_date
                            if state.outline_result is not None
                            else ""
                        )
                        recap_result = await recap_agent.run(
                            story_name=state.story_name,
                            chapter_number=chapter_number,
                            chapter_content=draft.content,
                            previous_recap=previous_recap,
                            story_start_date=story_start_date,
                            settings=settings,
                        )
                        recap_pointers = {
                            field: persist_markdown(
                                story_dir,
                                f"chapters/chapter_{chapter_number}/recap_{field}.md",
                                str(recap_result.get(field, "") or ""),
                            )
                            for field in ("events", "compact", "sanitised")
                        }
                        state.recaps[str(chapter_number)] = recap_pointers
                        recap_path = (
                            story_dir
                            / "chapters"
                            / f"chapter_{chapter_number}_recap.json"
                        )
                        _atomic_write(
                            recap_path,
                            json.dumps(
                                recap_pointers,
                                indent=2,
                                ensure_ascii=False,
                            ),
                        )
                        # --- recap index upsert ---
                        try:
                            _parsed_events: list[dict] = (
                                recap_result["events"]
                                if isinstance(recap_result.get("events"), list)
                                else []
                            )
                            await asyncio.to_thread(
                                recap_index.delete_chapter_events,
                                state.story_name,
                                chapter_number,
                            )
                            await asyncio.to_thread(
                                recap_index.upsert_recap_events,
                                state.story_name,
                                chapter_number,
                                _parsed_events,
                            )
                            await bus.emit(
                                f"[Recap] indexed chapter {chapter_number} "
                                f"({len(_parsed_events)} events)\n"
                            )
                        except Exception as _exc:  # noqa: BLE001
                            await bus.emit(f"[Recap] index upsert failed: {_exc}\n")
                        # --- end recap index upsert ---
                        if recap_result.get("events"):
                            try:
                                wiki_event_result = await asyncio.to_thread(
                                    _sync_recap_events_to_wiki,
                                    state.story_name,
                                    chapter_number,
                                    recap_result.get("events"),
                                )
                            except ValueError as exc:
                                await bus.emit(f"[Recap] event parse failed: {exc}\n")
                            else:
                                await bus.emit(
                                    "[Recap] Wiki events synced — "
                                    f"created {wiki_event_result['created']}, "
                                    f"updated {wiki_event_result['updated']}\n"
                                )
                        await _mark_work_item_done(state, phase, recap_item_id)
                    except Exception as exc:
                        await bus.emit(
                            f"\n[Recap] chapter {chapter_number} recap skipped "
                            f"({type(exc).__name__}: {exc})\n"
                        )
                style_notes_item_id = f"chapter-{chapter_number}/style-notes"
                if settings.enable_critique_learning and not _work_item_done(
                    state, phase, style_notes_item_id
                ):
                    try:
                        from tools import wiki_style_notes as _wiki_style_notes

                        sn_result = await asyncio.to_thread(
                            _wiki_style_notes.promote_findings,
                            state.story_name,
                            chapter_number,
                        )
                        if (
                            sn_result.get("written")
                            and state.style_notes_first_chapter is None
                        ):
                            state.style_notes_first_chapter = chapter_number
                        if sn_result["written"]:
                            await bus.emit(
                                f"[StyleNotes] Promoted {len(sn_result['promoted'])} "
                                "finding(s) to wiki/style-notes.md\n"
                            )
                        await _mark_work_item_done(state, phase, style_notes_item_id)
                    except Exception as exc:  # noqa: BLE001
                        await bus.emit(
                            f"\n[StyleNotes] chapter {chapter_number} style-notes "
                            f"skipped ({type(exc).__name__}: {exc})\n"
                        )
                if (
                    chapter_number == 1
                    and "metadata-chapter-1" not in state.completed_phases
                    and not _work_item_done(
                        state, phase, f"chapter-{chapter_number}/metadata"
                    )
                ):
                    if state.outline_result is not None:
                        try:
                            metadata_agent_ch1 = StoryMetadataAgent(
                                resolved_provider, resolved_config, bus, wiki_bus
                            )
                            outline_text_ch1 = _build_story_elements(
                                state.outline_result,
                                story_dir,
                            )
                            metadata_result_ch1 = await metadata_agent_ch1.run(
                                state.story_name,
                                outline_text_ch1,
                                draft.content,
                                settings,
                            )
                            state.outline_result.title = metadata_result_ch1.title
                            state.outline_result.tags = metadata_result_ch1.tags
                            _write_story_metadata(
                                story_dir,
                                metadata_result_ch1.title,
                                metadata_result_ch1.summary,
                                metadata_result_ch1.tags,
                            )
                            state.completed_phases.append("metadata-chapter-1")
                            await _write_savepoint(state)
                            await _mark_work_item_done(
                                state,
                                phase,
                                f"chapter-{chapter_number}/metadata",
                            )
                        except Exception as exc:
                            await bus.emit(
                                f"\n[Metadata] chapter-1 metadata skipped ({type(exc).__name__}: {exc})\n"
                            )
                state.quality_telemetry.append(
                    {
                        "chapter_number": chapter_number,
                        "scenes": draft.critic_findings or [],
                        "consistency": {
                            "passed": consistency_meta.get("passed", True),
                            "iteration_count": 0,
                            "critical_count": consistency_meta.get("critical_count", 0),
                            "warning_count": consistency_meta.get("warning_count", 0),
                            "final_status": "passed"
                            if consistency_meta.get("passed", True)
                            else "failed",
                        },
                    }
                )
                await _mark_phase_complete(
                    state,
                    f"chapter-{chapter_number}",
                    f"chapter-{chapter_number}",
                )
                await _emit_status(
                    sbus,
                    f"chapter-{chapter_number}",
                    f"Chapter {chapter_number} complete",
                    kind="phase_end",
                )

            await _mark_phase_complete(state, "chapter-loop", "chapter-loop")

        if "final-edit" not in state.completed_phases:
            state.current_phase = "final-edit"
            await _banner("final-edit", "Running final editor pass")
            generation_config = resolved_config.get("generation", {})
            enable_final_edit = (
                generation_config.get("enable_final_edit", True)
                if isinstance(generation_config, dict)
                else True
            )
            if enable_final_edit and state.approved_chapters:
                final_editor = FinalEditorAgent(
                    resolved_provider, resolved_config, bus, wiki_bus
                )
                try:
                    prior_summaries = final_editor.build_prior_summaries(
                        state.approved_chapters
                    )
                    edited_chapters = list(state.approved_chapters)
                    for index, draft in enumerate(state.approved_chapters):
                        chapter_number = (
                            draft.chapter_number
                            if hasattr(draft, "chapter_number")
                            else index + 1
                        )
                        item_id = f"final-edit/chapter:{chapter_number}"
                        edited_path = _edited_chapter_path(
                            state.story_name, chapter_number
                        )
                        if _work_item_done(state, "final-edit", item_id):
                            if edited_path.exists():
                                edited_content = edited_path.read_text(encoding="utf-8")
                                edited_chapters[index] = replace(
                                    draft,
                                    content=edited_content,
                                    word_count=len(edited_content.split()),
                                )
                                continue

                        edited = await final_editor.edit_single_chapter(
                            draft,
                            prior_summaries[index],
                            chapter_number,
                            settings,
                        )
                        _atomic_write(edited_path, edited.content)
                        edited_chapters[index] = edited
                        await _mark_work_item_done(state, "final-edit", item_id)

                    state.approved_chapters = edited_chapters
                    edited_path = story_dir / "output" / "story_edited.md"
                    edited_path.parent.mkdir(parents=True, exist_ok=True)
                    edited_parts = [
                        ch.content.rstrip()
                        for ch in state.approved_chapters
                        if ch.content.strip()
                    ]
                    if edited_parts:
                        edited_path.write_text(
                            "\n\n".join(edited_parts) + "\n", encoding="utf-8"
                        )
                except Exception as exc:
                    await bus.emit(
                        f"\n[Final Edit] final edit skipped ({type(exc).__name__}: {exc})\n"
                    )
            await _mark_phase_complete(state, "final-edit", "final_edit_complete")

        if "metadata-final" not in state.completed_phases:
            state.current_phase = "metadata-final"
            await _banner("metadata-final", "Refreshing story metadata")
            if state.outline_result is not None and state.approved_chapters:
                try:
                    metadata_agent_final = StoryMetadataAgent(
                        resolved_provider, resolved_config, bus, wiki_bus
                    )
                    outline_text_final = _build_story_elements(
                        state.outline_result,
                        story_dir,
                    )
                    chapter_1_final = next(
                        (
                            chapter.content
                            for chapter in state.approved_chapters
                            if chapter.chapter_number == 1
                        ),
                        "",
                    )
                    metadata_result_final = await metadata_agent_final.run(
                        state.story_name,
                        outline_text_final,
                        chapter_1_final,
                        settings,
                    )
                    state.outline_result.title = metadata_result_final.title
                    state.outline_result.tags = metadata_result_final.tags
                    _write_story_metadata(
                        story_dir,
                        metadata_result_final.title,
                        metadata_result_final.summary,
                        metadata_result_final.tags,
                    )
                except Exception as exc:
                    await bus.emit(
                        f"\n[Metadata] final metadata skipped ({type(exc).__name__}: {exc})\n"
                    )
            await _mark_phase_complete(
                state,
                "metadata-final",
                "metadata_final_complete",
            )

        state.current_phase = "assembly"
        if "assembly" not in state.completed_phases:
            await _banner("assembly", "Assembling final story file")
            output_path = story_dir / "output" / "story.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            parts = [
                ch.content.rstrip()
                for ch in state.approved_chapters
                if ch.content.strip()
            ]
            if not parts:
                raise StoryGenerationError(
                    "Assembly failed: no approved chapter content to assemble"
                )
            try:
                output_path.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
            except OSError as exc:
                raise StoryGenerationError(
                    f"Assembly failed: could not write output file: {exc}"
                ) from exc
            await _mark_phase_complete(state, "assembly", "assembly")

        state.current_phase = "complete"
        state.status = "complete"
        state.savepoint_id = "complete"
        if "complete" not in state.savepoints:
            state.savepoints.append("complete")
        try:
            _write_quality_report(state, story_dir, resolved_config)
        except Exception as exc:
            await bus.emit(
                f"\n[Quality Report] Failed to write quality report: {exc}\n"
            )
        await _write_savepoint(state)
        await _emit_status(sbus, "complete", "Pipeline complete", kind="phase_end")
        return state
    except Exception as exc:
        await _emit_status(
            sbus,
            state.current_phase,
            f"Pipeline error: {type(exc).__name__}: {exc}",
            kind="error",
        )
        raise
    finally:
        bus.close()
        wiki_bus.close()
        sbus.close()


async def run_pipeline(
    story_name: str,
    gate: ApprovalGate,
    bus: TokenStreamBus,
    wiki_bus: WikiContextBus,
    config: dict[str, Any] | None = None,
    provider: ModelProvider | None = None,
    status_bus: StatusBus | None = None,
) -> PipelineState:
    """Execute the full story generation pipeline.

    Phases:
        Init → Outline → [Outline ApprovalGate] → Wiki Generation → Wiki Bootstrap
        → Chapter Loop (generate → [Chapter ApprovalGate] → revise if needed)
        → Final Edit → Assembly

    Each phase writes a savepoint on successful completion.
    """
    resolved_config = config if config is not None else ConfigLoader().load_config()
    _validate_story_name(story_name, STORIES_DIR)
    state = PipelineState(
        story_name=story_name,
        current_phase="init",
        batch_mode=isinstance(gate, NullApprovalGate),
        status="running",
    )

    story_dir = STORIES_DIR / story_name / "savepoints"
    story_dir.mkdir(parents=True, exist_ok=True)
    await _mark_phase_complete(state, "init", "init")

    return await _continue_pipeline(
        state, gate, bus, wiki_bus, resolved_config, provider, status_bus
    )


async def resume_pipeline(
    story_name: str,
    savepoint_name: str | None,
    gate: ApprovalGate,
    bus: TokenStreamBus,
    wiki_bus: WikiContextBus,
    config: dict[str, Any] | None = None,
    provider: ModelProvider | None = None,
    status_bus: StatusBus | None = None,
) -> PipelineState:
    """Resume a pipeline from the latest persisted savepoint.

    The ``savepoint_name`` parameter is validated for presence in the story's
    savepoint history but does not alter the resume point; execution always
    continues from the single latest ``pipeline_state.json`` snapshot.
    """
    _validate_story_name(story_name, STORIES_DIR)
    state = await _load_savepoint(story_name)
    if state is None:
        raise StoryGenerationError(
            f"No savepoint found for story '{story_name}'. "
            "Run run_pipeline() first to start the pipeline."
        )

    if savepoint_name is not None and savepoint_name not in state.savepoints:
        raise StoryGenerationError(
            f"Savepoint '{savepoint_name}' not found in story '{story_name}'. "
            f"Available savepoints: {state.savepoints}"
        )

    _backfill_missing_chapter_files(
        STORIES_DIR / state.story_name, state.approved_chapters
    )

    if state.status == "complete":
        bus.close()
        wiki_bus.close()
        if status_bus is not None:
            status_bus.close()
        return state

    return await _continue_pipeline(
        state, gate, bus, wiki_bus, config, provider, status_bus
    )
