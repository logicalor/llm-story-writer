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
from typing import Any, cast

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
from domain.value_objects.model_config import ModelConfig
from infrastructure.prompts.prompt_loader import PromptLoader
from presentation.agents.character_evolver import CharacterEvolverAgent
from presentation.agents.chapter_writer import ChapterWriterAgent
from presentation.agents.consistency_checker import ConsistencyCheckerAgent
from presentation.agents.final_editor import FinalEditorAgent
from presentation.agents.outline_critic import OutlineCriticAgent
from presentation.agents.outline_planner import OutlinePlannerAgent
from presentation.agents.setting_evolver import SettingEvolverAgent
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
from tools._io import STORIES_DIR, _atomic_write, _validate_story_name
from tools._persist import persist_markdown, read_markdown_ref
from tools._wiki import slugify as wiki_slugify
from tools.wiki_extract import _bootstrap_single_wiki_entity, _list_wiki_entities
from tools.wiki_init import _init_wiki_for_story


def _savepoint_path(story_name: str) -> Path:
    """Return path to the pipeline state savepoint file."""
    return STORIES_DIR / story_name / "savepoints" / "pipeline_state.json"


async def _write_savepoint(state: PipelineState) -> None:
    """Write PipelineState to disk as JSON savepoint (atomic)."""
    path = _savepoint_path(state.story_name)
    _atomic_write(path, state.to_json())


def _work_item_done(state: PipelineState, phase: str, item_id: str) -> bool:
    """Return True if the given work item has already been completed."""
    return item_id in state.completed_work_items.get(phase, [])


async def _mark_work_item_done(state: PipelineState, phase: str, item_id: str) -> None:
    """Mark a work item as completed and atomically persist the savepoint."""
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
) -> PipelineState:
    while True:
        decision = await gate.await_decision()
        if decision.approved:
            return state
        if decision.feedback is None:
            state.status = "rejected"
            await _write_savepoint(state)
            return state
        state.outline_result = await agent.run(
            story_name,
            story_prompt,
            settings,
            feedback=decision.feedback,
            base_context=base_context,
            story_elements=story_elements,
        )
        await _write_savepoint(state)


async def _emit_consistency_results(
    bus: TokenStreamBus,
    chapter_number: int,
    consistency_result: dict[str, Any],
) -> None:
    """Emit consistency check findings to the token bus."""
    if not consistency_result["passed"]:
        await bus.emit(f"\n[Consistency] Chapter {chapter_number} — issues found:\n")
        for issue in consistency_result["issues"]:
            await bus.emit(f"  [{issue['severity'].upper()}] {issue['description']}\n")
    elif consistency_result["issues"]:
        await bus.emit(
            f"\n[Consistency] Chapter {chapter_number} — warnings/info found:\n"
        )
        for issue in consistency_result["issues"]:
            await bus.emit(f"  [{issue['severity'].upper()}] {issue['description']}\n")


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
    if consistency_agent is not None and bus is not None:
        try:
            consistency_result = await consistency_agent.run(
                story_name,
                chapter_number,
                draft.content,
                outline_result=outline_result,
            )
            await _emit_consistency_results(bus, chapter_number, consistency_result)
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
            return draft
        if decision.feedback is None:
            state.status = "rejected"
            await _write_savepoint(state)
            return None
        draft = await agent.run(
            story_name,
            chapter_number,
            outline_result,
            settings,
            feedback=decision.feedback,
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


def _slugify_name(name: str) -> str:
    """Convert a name to a filesystem-safe slug."""
    slug = name.lower().replace(" ", "-")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def _extract_output_content(text: str) -> str:
    """Extract content between <output>...</output> tags, or return text stripped."""
    match = re.search(r"<output>(.*?)</output>", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def _build_story_elements(outline_result: OutlineResult, story_root: Path) -> str:
    """Build story_elements string from OutlineResult for prompt injection."""
    parts = [outline_result.summary]
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


def _parse_name_list(names_raw: str) -> list[str]:
    names_text = names_raw.strip()
    if names_text.startswith("```"):
        names_lines = names_text.splitlines()
        if names_lines:
            names_lines = names_lines[1:]
        if names_lines and names_lines[-1].strip() == "```":
            names_lines = names_lines[:-1]
        names_text = "\n".join(names_lines).strip()

    parsed = json.loads(names_text)
    if not isinstance(parsed, list):
        return []
    return [name for name in parsed if isinstance(name, str)]


async def _generate_character_sheets(
    story_name: str,
    state: PipelineState,
    outline_result: OutlineResult,
    provider: ModelProvider,
    config: dict[str, Any],
    stories_dir: Path,
    bus: TokenStreamBus | None = None,
    status_bus: StatusBus | None = None,
) -> list[Path]:
    """Generate character sheets from outline and write to disk."""
    sbus = status_bus if status_bus is not None else NullStatusBus()
    story_root = stories_dir / story_name
    project_root = Path(__file__).resolve().parents[2]
    loader = PromptLoader(prompts_dir=str(project_root / "prompts"))
    models = config.get("models", {})
    model_name = models.get("chapter_writer", "openai-compat://default")
    model_config = ModelConfig.from_string(model_name)
    _se = outline_result.story_elements
    actual_story_elements = (
        read_markdown_ref(story_root, _se) if isinstance(_se, dict) else (_se or "")
    )
    _bc = outline_result.base_context
    actual_base_context = (
        read_markdown_ref(story_root, _bc) if isinstance(_bc, dict) else (_bc or "")
    )

    extract_prompt = loader.load_prompt(
        "characters/extract_names", {"story_elements": actual_story_elements}
    )
    messages = [{"role": "user", "content": extract_prompt}]
    names_cache_path = stories_dir / story_name / "characters" / "_names.json"
    if _work_item_done(state, "characters", "_extract_names"):
        names = json.loads(names_cache_path.read_text(encoding="utf-8"))
    else:
        try:
            names_raw = await provider.generate_text(messages, model_config)
            names = _parse_name_list(names_raw)
            if not names:
                return []
        except Exception as exc:
            if bus is not None:
                await bus.emit(
                    f"\n[Characters] name extraction failed ({type(exc).__name__}: {exc}) — no character sheets generated\n"
                )
            return []
        names_cache_path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(names_cache_path, json.dumps(names, ensure_ascii=False))
        await _mark_work_item_done(state, "characters", "_extract_names")

    if not names:
        if bus is not None:
            await bus.emit(
                "\n[Characters] extract_names returned an empty list — no character sheets generated\n"
            )
        return []

    characters_dir = stories_dir / story_name / "characters"
    characters_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    chunk_prompts = {
        "backstory": "characters/create_background_chunk",
        "personality": "characters/create_personality_chunk",
        "motivation": "characters/create_motivations_chunk",
        "relationships": "characters/create_relationships_chunk",
        "skills": "characters/create_skills_chunk",
        "arc": "characters/create_growth_arc_chunk",
        "current_state": "characters/create_current_state_chunk",
    }

    for idx, character_name in enumerate(names, start=1):
        if not character_name.strip():
            continue
        slug = _slugify_name(character_name)
        if not slug:
            continue
        char_path = characters_dir / f"{slug}.json"
        char_item_sheet = f"characters/{slug}/sheet"
        await _emit_status(
            sbus,
            "characters",
            f"[{idx}/{len(names)}] {character_name}: generating sheet",
            kind="step",
        )
        if _work_item_done(state, "characters", char_item_sheet):
            loaded_sheet = json.loads(char_path.read_text(encoding="utf-8"))
            if not isinstance(loaded_sheet, dict):
                raise ValueError(
                    f"Character sheet cache for {character_name!r} is not a JSON object"
                )
            sheet_data = dict(loaded_sheet)
            sheet_data.setdefault("name", character_name)
            sheet_data.setdefault("summary", "")
            sheet_data.setdefault("abridged", "")
            if not isinstance(sheet_data.get("chunks"), dict):
                sheet_data["chunks"] = {}
            sheet_text = (
                read_markdown_ref(story_root, _r)
                if isinstance(_r := sheet_data.get("sheet"), dict)
                else (_r or "")
            )
        else:
            try:
                create_prompt = loader.load_prompt(
                    "characters/create",
                    {
                        "story_elements": actual_story_elements,
                        "character_name": character_name,
                        "additional_context": actual_base_context,
                    },
                )
                sheet_messages = [{"role": "user", "content": create_prompt}]
                sheet_text = await provider.generate_text(sheet_messages, model_config)
            except Exception as exc:
                if bus is not None:
                    await bus.emit(
                        f"\n[Characters] sheet generation failed for {character_name!r} "
                        f"({type(exc).__name__}: {exc}) — skipping\n"
                    )
                continue

            sheet_data = {
                "name": character_name,
                "sheet": persist_markdown(
                    story_root, f"characters/{slug}/sheet.md", sheet_text
                ),
                "chunks": {},
                "summary": "",
                "abridged": "",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            _atomic_write(
                char_path,
                json.dumps(sheet_data, indent=2, ensure_ascii=False),
            )
            await _mark_work_item_done(state, "characters", char_item_sheet)

        chunk_results = dict(cast(dict[str, str], sheet_data.get("chunks", {})))
        abridged_text = (
            read_markdown_ref(story_root, _r)
            if isinstance(_r := sheet_data.get("abridged"), dict)
            else (_r or "")
        )
        summary_text = (
            read_markdown_ref(story_root, _r)
            if isinstance(_r := sheet_data.get("summary"), dict)
            else (_r or "")
        )

        try:
            chunk_items = list(chunk_prompts.items())
            for chunk_idx, (chunk_key, prompt_name) in enumerate(chunk_items, start=1):
                await _emit_status(
                    sbus,
                    "characters",
                    f"[{idx}/{len(names)}] {character_name}: chunk "
                    f"{chunk_idx}/{len(chunk_items)} ({chunk_key})",
                    kind="step",
                )
                chunk_item_id = f"characters/{slug}/chunk:{chunk_key}"
                if _work_item_done(state, "characters", chunk_item_id):
                    existing_chunks = sheet_data.get("chunks", {})
                    if isinstance(existing_chunks, dict):
                        chunk_results[chunk_key] = (
                            read_markdown_ref(story_root, _r)
                            if isinstance(_r := existing_chunks.get(chunk_key), dict)
                            else (_r or "")
                        )
                    else:
                        chunk_results[chunk_key] = ""
                    continue

                try:
                    chunk_prompt = loader.load_prompt(
                        prompt_name,
                        {
                            "character_name": character_name,
                            "character_sheet": sheet_text,
                            "story_elements": actual_story_elements,
                        },
                    )
                    raw_chunk = await provider.generate_text(
                        [{"role": "user", "content": chunk_prompt}],
                        model_config,
                    )
                    chunk_results[chunk_key] = _extract_output_content(raw_chunk)
                except Exception:
                    chunk_results[chunk_key] = ""
                    continue

                sheet_data["chunks"] = {
                    k: persist_markdown(
                        story_root, f"characters/{slug}/chunks/{k}.md", v
                    )
                    for k, v in chunk_results.items()
                }
                sheet_data["updated_at"] = datetime.now(timezone.utc).isoformat()
                _atomic_write(
                    char_path,
                    json.dumps(sheet_data, indent=2, ensure_ascii=False),
                )
                await _mark_work_item_done(state, "characters", chunk_item_id)

            await _emit_status(
                sbus,
                "characters",
                f"[{idx}/{len(names)}] {character_name}: abridged",
                kind="step",
            )
            abridged_item_id = f"characters/{slug}/abridged"
            if _work_item_done(state, "characters", abridged_item_id):
                abridged_text = (
                    read_markdown_ref(story_root, _r)
                    if isinstance(_r := sheet_data.get("abridged"), dict)
                    else (_r or "")
                )
            else:
                try:
                    abridged_prompt = loader.load_prompt(
                        "characters/create_abridged",
                        {
                            "story_elements": actual_story_elements,
                            "character_name": character_name,
                        },
                    )
                    abridged_raw = await provider.generate_text(
                        [{"role": "user", "content": abridged_prompt}],
                        model_config,
                    )
                    abridged_text = _extract_output_content(abridged_raw)
                except Exception:
                    abridged_text = ""

                sheet_data["abridged"] = persist_markdown(
                    story_root, f"characters/{slug}/abridged.md", abridged_text
                )
                sheet_data["updated_at"] = datetime.now(timezone.utc).isoformat()
                _atomic_write(
                    char_path,
                    json.dumps(sheet_data, indent=2, ensure_ascii=False),
                )
                await _mark_work_item_done(state, "characters", abridged_item_id)

            character_info = (
                "\n\n".join(
                    f"=== {key.replace('_', ' ').title()} ===\n{value}"
                    for key, value in chunk_results.items()
                    if value
                )
                or sheet_text
            )
            await _emit_status(
                sbus,
                "characters",
                f"[{idx}/{len(names)}] {character_name}: summary",
                kind="step",
            )
            summary_item_id = f"characters/{slug}/summary"
            if _work_item_done(state, "characters", summary_item_id):
                summary_text = (
                    read_markdown_ref(story_root, _r)
                    if isinstance(_r := sheet_data.get("summary"), dict)
                    else (_r or "")
                )
            else:
                try:
                    summary_prompt = loader.load_prompt(
                        "characters/create_summary",
                        {
                            "character_name": character_name,
                            "character_info": character_info,
                        },
                    )
                    summary_raw = await provider.generate_text(
                        [{"role": "user", "content": summary_prompt}],
                        model_config,
                    )
                    summary_text = _extract_output_content(summary_raw)
                except Exception:
                    summary_text = ""

                sheet_data["summary"] = persist_markdown(
                    story_root, f"characters/{slug}/summary.md", summary_text
                )
                sheet_data["updated_at"] = datetime.now(timezone.utc).isoformat()
                _atomic_write(
                    char_path,
                    json.dumps(sheet_data, indent=2, ensure_ascii=False),
                )
                await _mark_work_item_done(state, "characters", summary_item_id)
        except Exception as exc:
            if bus is not None:
                await bus.emit(
                    f"\n[Characters] enrichment failed for {character_name!r} "
                    f"({type(exc).__name__}: {exc}) — base sheet retained\n"
                )

        enriched_data = dict(sheet_data)
        enriched_data["chunks"] = {
            k: persist_markdown(story_root, f"characters/{slug}/chunks/{k}.md", v)
            for k, v in chunk_results.items()
        }
        enriched_data["abridged"] = persist_markdown(
            story_root, f"characters/{slug}/abridged.md", abridged_text
        )
        enriched_data["summary"] = persist_markdown(
            story_root, f"characters/{slug}/summary.md", summary_text
        )
        enriched_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        _atomic_write(
            char_path,
            json.dumps(enriched_data, indent=2, ensure_ascii=False),
        )

        await _emit_status(
            sbus,
            "characters",
            f"[{idx}/{len(names)}] {character_name}: saved",
            kind="step",
        )
        written.append(char_path)

    return [path for path in written if path != names_cache_path]


async def _generate_setting_sheets(
    story_name: str,
    state: PipelineState,
    outline_result: OutlineResult,
    provider: ModelProvider,
    config: dict[str, Any],
    stories_dir: Path,
    bus: TokenStreamBus | None = None,
    status_bus: StatusBus | None = None,
) -> list[Path]:
    """Generate setting sheets from outline and write to disk."""
    sbus = status_bus if status_bus is not None else NullStatusBus()
    story_root = stories_dir / story_name
    project_root = Path(__file__).resolve().parents[2]
    loader = PromptLoader(prompts_dir=str(project_root / "prompts"))
    models = config.get("models", {})
    model_name = models.get("chapter_writer", "openai-compat://default")
    model_config = ModelConfig.from_string(model_name)
    _se = outline_result.story_elements
    actual_story_elements = (
        read_markdown_ref(story_root, _se) if isinstance(_se, dict) else (_se or "")
    )
    _bc = outline_result.base_context
    actual_base_context = (
        read_markdown_ref(story_root, _bc) if isinstance(_bc, dict) else (_bc or "")
    )

    extract_prompt = loader.load_prompt(
        "settings/extract_names", {"story_elements": actual_story_elements}
    )
    messages = [{"role": "user", "content": extract_prompt}]
    names_cache_path = stories_dir / story_name / "settings" / "_names.json"
    if _work_item_done(state, "settings", "_extract_locations"):
        names = json.loads(names_cache_path.read_text(encoding="utf-8"))
    else:
        try:
            names_raw = await provider.generate_text(messages, model_config)
            names = _parse_name_list(names_raw)
            if not names:
                return []
        except Exception as exc:
            if bus is not None:
                await bus.emit(
                    f"\n[Settings] name extraction failed ({type(exc).__name__}: {exc}) — no setting sheets generated\n"
                )
            return []
        names_cache_path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(names_cache_path, json.dumps(names, ensure_ascii=False))
        await _mark_work_item_done(state, "settings", "_extract_locations")

    if not names:
        if bus is not None:
            await bus.emit(
                "\n[Settings] extract_names returned an empty list — no setting sheets generated\n"
            )
        return []

    settings_dir = stories_dir / story_name / "settings"
    settings_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    chunk_prompts = {
        "physical_description": "settings/create_physical_description_chunk",
        "atmosphere_mood": "settings/create_atmosphere_mood_chunk",
        "function_purpose": "settings/create_function_purpose_chunk",
        "history_background": "settings/create_history_background_chunk",
        "connections_relationships": "settings/create_connections_relationships_chunk",
        "rules_constraints": "settings/create_rules_constraints_chunk",
    }

    for idx, setting_name in enumerate(names, start=1):
        if not setting_name.strip():
            continue
        slug = _slugify_name(setting_name)
        if not slug:
            continue
        setting_path = settings_dir / f"{slug}.json"
        setting_item_sheet = f"settings/{slug}/sheet"
        await _emit_status(
            sbus,
            "settings",
            f"[{idx}/{len(names)}] {setting_name}: generating sheet",
            kind="step",
        )
        if _work_item_done(state, "settings", setting_item_sheet):
            loaded_sheet = json.loads(setting_path.read_text(encoding="utf-8"))
            if not isinstance(loaded_sheet, dict):
                raise ValueError(
                    f"Setting sheet cache for {setting_name!r} is not a JSON object"
                )
            sheet_data = dict(loaded_sheet)
            sheet_data.setdefault("name", setting_name)
            sheet_data.setdefault("summary", "")
            sheet_data.setdefault("abridged", "")
            if not isinstance(sheet_data.get("chunks"), dict):
                sheet_data["chunks"] = {}
            sheet_text = (
                read_markdown_ref(story_root, _r)
                if isinstance(_r := sheet_data.get("sheet"), dict)
                else (_r or "")
            )
        else:
            try:
                create_prompt = loader.load_prompt(
                    "settings/create",
                    {
                        "story_elements": actual_story_elements,
                        "setting_name": setting_name,
                        "additional_context": actual_base_context,
                    },
                )
                sheet_messages = [{"role": "user", "content": create_prompt}]
                sheet_text = await provider.generate_text(sheet_messages, model_config)
            except Exception as exc:
                if bus is not None:
                    await bus.emit(
                        f"\n[Settings] sheet generation failed for {setting_name!r} "
                        f"({type(exc).__name__}: {exc}) — skipping\n"
                    )
                continue

            sheet_data = {
                "name": setting_name,
                "sheet": persist_markdown(
                    story_root, f"settings/{slug}/sheet.md", sheet_text
                ),
                "chunks": {},
                "summary": "",
                "abridged": "",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            _atomic_write(
                setting_path,
                json.dumps(sheet_data, indent=2, ensure_ascii=False),
            )
            await _mark_work_item_done(state, "settings", setting_item_sheet)

        chunk_results = dict(cast(dict[str, str], sheet_data.get("chunks", {})))
        abridged_text = (
            read_markdown_ref(story_root, _r)
            if isinstance(_r := sheet_data.get("abridged"), dict)
            else (_r or "")
        )
        summary_text = (
            read_markdown_ref(story_root, _r)
            if isinstance(_r := sheet_data.get("summary"), dict)
            else (_r or "")
        )

        try:
            chunk_items = list(chunk_prompts.items())
            for chunk_idx, (chunk_key, prompt_name) in enumerate(chunk_items, start=1):
                await _emit_status(
                    sbus,
                    "settings",
                    f"[{idx}/{len(names)}] {setting_name}: chunk "
                    f"{chunk_idx}/{len(chunk_items)} ({chunk_key})",
                    kind="step",
                )
                chunk_item_id = f"settings/{slug}/chunk:{chunk_key}"
                if _work_item_done(state, "settings", chunk_item_id):
                    existing_chunks = sheet_data.get("chunks", {})
                    if isinstance(existing_chunks, dict):
                        chunk_results[chunk_key] = (
                            read_markdown_ref(story_root, _r)
                            if isinstance(_r := existing_chunks.get(chunk_key), dict)
                            else (_r or "")
                        )
                    else:
                        chunk_results[chunk_key] = ""
                    continue

                try:
                    chunk_prompt = loader.load_prompt(
                        prompt_name,
                        {
                            "setting_name": setting_name,
                            "setting_sheet": sheet_text,
                            "story_elements": actual_story_elements,
                        },
                    )
                    raw_chunk = await provider.generate_text(
                        [{"role": "user", "content": chunk_prompt}],
                        model_config,
                    )
                    chunk_results[chunk_key] = _extract_output_content(raw_chunk)
                except Exception:
                    chunk_results[chunk_key] = ""
                    continue

                sheet_data["chunks"] = {
                    k: persist_markdown(story_root, f"settings/{slug}/chunks/{k}.md", v)
                    for k, v in chunk_results.items()
                }
                sheet_data["updated_at"] = datetime.now(timezone.utc).isoformat()
                _atomic_write(
                    setting_path,
                    json.dumps(sheet_data, indent=2, ensure_ascii=False),
                )
                await _mark_work_item_done(state, "settings", chunk_item_id)

            await _emit_status(
                sbus,
                "settings",
                f"[{idx}/{len(names)}] {setting_name}: abridged",
                kind="step",
            )
            abridged_item_id = f"settings/{slug}/abridged"
            if _work_item_done(state, "settings", abridged_item_id):
                abridged_text = (
                    read_markdown_ref(story_root, _r)
                    if isinstance(_r := sheet_data.get("abridged"), dict)
                    else (_r or "")
                )
            else:
                try:
                    abridged_prompt = loader.load_prompt(
                        "settings/create_abridged",
                        {
                            "story_elements": actual_story_elements,
                            "setting_name": setting_name,
                        },
                    )
                    abridged_raw = await provider.generate_text(
                        [{"role": "user", "content": abridged_prompt}],
                        model_config,
                    )
                    abridged_text = _extract_output_content(abridged_raw)
                except Exception:
                    abridged_text = ""

                sheet_data["abridged"] = persist_markdown(
                    story_root, f"settings/{slug}/abridged.md", abridged_text
                )
                sheet_data["updated_at"] = datetime.now(timezone.utc).isoformat()
                _atomic_write(
                    setting_path,
                    json.dumps(sheet_data, indent=2, ensure_ascii=False),
                )
                await _mark_work_item_done(state, "settings", abridged_item_id)

            setting_info = (
                "\n\n".join(
                    f"=== {key.replace('_', ' ').title()} ===\n{value}"
                    for key, value in chunk_results.items()
                    if value
                )
                or sheet_text
            )
            await _emit_status(
                sbus,
                "settings",
                f"[{idx}/{len(names)}] {setting_name}: summary",
                kind="step",
            )
            summary_item_id = f"settings/{slug}/summary"
            if _work_item_done(state, "settings", summary_item_id):
                summary_text = (
                    read_markdown_ref(story_root, _r)
                    if isinstance(_r := sheet_data.get("summary"), dict)
                    else (_r or "")
                )
            else:
                try:
                    summary_prompt = loader.load_prompt(
                        "settings/create_summary",
                        {
                            "setting_name": setting_name,
                            "setting_info": setting_info,
                        },
                    )
                    summary_raw = await provider.generate_text(
                        [{"role": "user", "content": summary_prompt}],
                        model_config,
                    )
                    summary_text = _extract_output_content(summary_raw)
                except Exception:
                    summary_text = ""

                sheet_data["summary"] = persist_markdown(
                    story_root, f"settings/{slug}/summary.md", summary_text
                )
                sheet_data["updated_at"] = datetime.now(timezone.utc).isoformat()
                _atomic_write(
                    setting_path,
                    json.dumps(sheet_data, indent=2, ensure_ascii=False),
                )
                await _mark_work_item_done(state, "settings", summary_item_id)
        except Exception as exc:
            if bus is not None:
                await bus.emit(
                    f"\n[Settings] enrichment failed for {setting_name!r} "
                    f"({type(exc).__name__}: {exc}) — base sheet retained\n"
                )

        enriched_data = dict(sheet_data)
        enriched_data["chunks"] = {
            k: persist_markdown(story_root, f"settings/{slug}/chunks/{k}.md", v)
            for k, v in chunk_results.items()
        }
        enriched_data["abridged"] = persist_markdown(
            story_root, f"settings/{slug}/abridged.md", abridged_text
        )
        enriched_data["summary"] = persist_markdown(
            story_root, f"settings/{slug}/summary.md", summary_text
        )
        enriched_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        _atomic_write(
            setting_path,
            json.dumps(enriched_data, indent=2, ensure_ascii=False),
        )

        await _emit_status(
            sbus,
            "settings",
            f"[{idx}/{len(names)}] {setting_name}: saved",
            kind="step",
        )
        written.append(setting_path)

    return [path for path in written if path != names_cache_path]


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

        if "characters" not in state.completed_phases:
            state.current_phase = "characters"
            await _banner("characters", "Generating character sheets")
            await wiki_bus.emit(
                WikiContextEvent(
                    phase="characters",
                    event_type="entity_match",
                    content=f"Generating character sheets for: {state.story_name}",
                )
            )
            if state.outline_result is not None:
                char_count = len(
                    await _generate_character_sheets(
                        state.story_name,
                        state,
                        state.outline_result,
                        resolved_provider,
                        resolved_config,
                        story_dir.parent,
                        bus,
                        sbus,
                    )
                )
                if char_count == 0:
                    await _emit_status(
                        sbus,
                        "characters",
                        "Characters phase produced no files — will retry on resume",
                        kind="warn",
                    )
                    # Do NOT mark phase complete so resume retries it.
                    await _write_savepoint(state)
                    raise StoryGenerationError(
                        "[Characters] No character sheets were generated. "
                        "Check extract_names prompt and LLM output."
                    )
            await _mark_phase_complete(state, "characters", "characters")

        if "settings" not in state.completed_phases:
            state.current_phase = "settings"
            await _banner("settings", "Generating setting sheets")
            await wiki_bus.emit(
                WikiContextEvent(
                    phase="settings",
                    event_type="detail_level",
                    content=f"Generating setting sheets for: {state.story_name}",
                )
            )
            if state.outline_result is not None:
                await _generate_setting_sheets(
                    state.story_name,
                    state,
                    state.outline_result,
                    resolved_provider,
                    resolved_config,
                    story_dir.parent,
                    bus,
                    sbus,
                )
            await _mark_phase_complete(state, "settings", "settings")

        # Ensure wiki is initialized before any chapter wiki maintenance
        wiki_init_result = _init_wiki_for_story(state.story_name, STORIES_DIR)
        if "error" in wiki_init_result:
            raise StoryGenerationError(
                f"Wiki initialization failed for story '{state.story_name}': "
                f"{wiki_init_result['error']}"
            )

        if "wiki-bootstrap" not in state.completed_phases:
            state.current_phase = "wiki-bootstrap"
            await _banner("wiki-bootstrap", "Seeding wiki from outline and sheets")
            models = resolved_config.get("models", {})
            wiki_model: str | None = models.get("chapter_writer")
            await bus.emit(
                "\n[Wiki Bootstrap] Seeding wiki from outline and sheets...\n"
            )
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
            char_evolver = CharacterEvolverAgent(
                resolved_provider, resolved_config, bus, wiki_bus
            )
            setting_evolver = SettingEvolverAgent(
                resolved_provider, resolved_config, bus, wiki_bus
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

                sheet_item_id = f"chapter-{chapter_number}/sheet-evolution"
                if not _work_item_done(state, phase, sheet_item_id):
                    try:
                        char_changes = await char_evolver.run(
                            state.story_name,
                            draft,
                            chapter_number,
                            settings,
                        )
                        setting_changes = await setting_evolver.run(
                            state.story_name,
                            draft,
                            chapter_number,
                            settings,
                        )
                        state.evolved_sheets[str(chapter_number)] = {
                            "characters": char_changes,
                            "settings": setting_changes,
                        }
                        await _write_savepoint(state)
                        await _mark_work_item_done(state, phase, sheet_item_id)
                    except Exception as exc:
                        await bus.emit(
                            f"\n[Sheet Evolution] chapter {chapter_number} skipped "
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
                        if recap_result.get("events"):
                            recap_pointers = {
                                field: persist_markdown(
                                    story_dir,
                                    f"chapters/chapter_{chapter_number}/recap_{field}.md",
                                    str(recap_result.get(field, "")),
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
                        await _mark_work_item_done(state, phase, recap_item_id)
                    except Exception as exc:
                        await bus.emit(
                            f"\n[Recap] chapter {chapter_number} recap skipped "
                            f"({type(exc).__name__}: {exc})\n"
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
        Init → Outline → [Outline ApprovalGate] → Characters → Settings
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
