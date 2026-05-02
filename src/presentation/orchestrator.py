"""Python pipeline orchestrator for headless story generation.

Top-level entry point for the Python-native story generation pipeline.
Drives phases sequentially with injected async primitives, supporting
both TUI and headless operation without code changes.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from application.interfaces.model_provider import ModelProvider
from application.pipeline.handoffs import (
    ArcAnalysisResult,
    ChapterDraft,
    FinalEditResult,
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
    TokenStreamBus,
    WikiContextBus,
    WikiContextEvent,
)
from tools._io import STORIES_DIR, _atomic_write, _validate_story_name
from tools.wiki_extract import bootstrap_wiki_from_story
from tools.wiki_init import _init_wiki_for_story


def _savepoint_path(story_name: str) -> Path:
    """Return path to the pipeline state savepoint file."""
    return STORIES_DIR / story_name / "savepoints" / "pipeline_state.json"


async def _write_savepoint(state: PipelineState) -> None:
    """Write PipelineState to disk as JSON savepoint."""
    path = _savepoint_path(state.story_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(state.to_json(), encoding="utf-8")


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
    )


def _load_story_prompt(story_name: str) -> str:
    story_state_path = STORIES_DIR / story_name / "state.json"
    if not story_state_path.exists():
        return ""

    data = json.loads(story_state_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return ""

    for key in ("story_prompt", "prompt", "initial_prompt"):
        value = data.get(key)
        if isinstance(value, str):
            return value
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


async def _generate_chapter_with_gate(
    state: PipelineState,
    gate: ApprovalGate,
    agent: ChapterWriterAgent,
    story_name: str,
    chapter_number: int,
    outline_result: OutlineResult,
    settings: GenerationSettings,
) -> ChapterDraft | None:
    draft = await agent.run(
        story_name,
        chapter_number,
        outline_result,
        settings,
        recaps=state.recaps,
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
        )
        await _write_savepoint(state)


def _slugify_name(name: str) -> str:
    """Convert a name to a filesystem-safe slug."""
    slug = name.lower().replace(" ", "-")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def _build_story_elements(outline_result: OutlineResult) -> str:
    """Build story_elements string from OutlineResult for prompt injection."""
    parts = [outline_result.summary]
    if outline_result.chapter_outlines:
        parts.append(json.dumps(outline_result.chapter_outlines, ensure_ascii=False))
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
    outline_result: OutlineResult,
    provider: ModelProvider,
    config: dict[str, Any],
    stories_dir: Path,
) -> list[Path]:
    """Generate character sheets from outline and write to disk."""
    project_root = Path(__file__).resolve().parents[2]
    loader = PromptLoader(prompts_dir=str(project_root / "prompts"))
    models = config.get("models", {})
    model_name = models.get("chapter_writer", "openai-compat://default")
    model_config = ModelConfig.from_string(model_name)
    story_elements = _build_story_elements(outline_result)

    extract_prompt = loader.load_prompt(
        "characters/extract_names", {"story_elements": story_elements}
    )
    messages = [{"role": "user", "content": extract_prompt}]
    try:
        names_raw = await provider.generate_text(messages, model_config)
        names = _parse_name_list(names_raw)
    except Exception:
        names = []

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

    for character_name in names:
        if not character_name.strip():
            continue
        slug = _slugify_name(character_name)
        if not slug:
            continue
        try:
            create_prompt = loader.load_prompt(
                "characters/create",
                {
                    "story_elements": story_elements,
                    "character_name": character_name,
                },
            )
            sheet_messages = [{"role": "user", "content": create_prompt}]
            sheet_text = await provider.generate_text(sheet_messages, model_config)
        except Exception:
            continue

        sheet_data = {
            "name": character_name,
            "sheet": sheet_text,
            "chunks": {},
            "summary": "",
            "abridged": "",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        char_path = characters_dir / f"{slug}.json"
        _atomic_write(char_path, json.dumps(sheet_data, indent=2, ensure_ascii=False))

        try:
            sheet_json_text = char_path.read_text(encoding="utf-8")
            chunk_results: dict[str, str] = {}
            for chunk_key, prompt_name in chunk_prompts.items():
                chunk_prompt = loader.load_prompt(
                    prompt_name,
                    {"character_name": character_name},
                )
                chunk_results[chunk_key] = await provider.generate_text(
                    [{"role": "user", "content": chunk_prompt}],
                    model_config,
                )

            abridged_prompt = loader.load_prompt(
                "characters/create_abridged",
                {
                    "story_elements": outline_result.story_elements,
                    "character_name": character_name,
                },
            )
            abridged_text = await provider.generate_text(
                [{"role": "user", "content": abridged_prompt}],
                model_config,
            )

            summary_prompt = loader.load_prompt(
                "characters/create_summary",
                {
                    "character_name": character_name,
                    "character_info": sheet_json_text,
                },
            )
            summary_text = await provider.generate_text(
                [{"role": "user", "content": summary_prompt}],
                model_config,
            )

            enriched_data = json.loads(sheet_json_text)
            if not isinstance(enriched_data, dict):
                enriched_data = sheet_data.copy()
            enriched_data["chunks"] = chunk_results
            enriched_data["abridged"] = abridged_text
            enriched_data["summary"] = summary_text
            enriched_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            _atomic_write(
                char_path,
                json.dumps(enriched_data, indent=2, ensure_ascii=False),
            )
        except Exception:
            pass

        written.append(char_path)

    return written


async def _generate_setting_sheets(
    story_name: str,
    outline_result: OutlineResult,
    provider: ModelProvider,
    config: dict[str, Any],
    stories_dir: Path,
) -> list[Path]:
    """Generate setting sheets from outline and write to disk."""
    project_root = Path(__file__).resolve().parents[2]
    loader = PromptLoader(prompts_dir=str(project_root / "prompts"))
    models = config.get("models", {})
    model_name = models.get("chapter_writer", "openai-compat://default")
    model_config = ModelConfig.from_string(model_name)
    story_elements = _build_story_elements(outline_result)

    extract_prompt = loader.load_prompt(
        "settings/extract_names", {"story_elements": story_elements}
    )
    messages = [{"role": "user", "content": extract_prompt}]
    try:
        names_raw = await provider.generate_text(messages, model_config)
        names = _parse_name_list(names_raw)
    except Exception:
        names = []

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

    for setting_name in names:
        if not setting_name.strip():
            continue
        slug = _slugify_name(setting_name)
        if not slug:
            continue
        try:
            create_prompt = loader.load_prompt(
                "settings/create",
                {
                    "story_elements": story_elements,
                    "setting_name": setting_name,
                },
            )
            sheet_messages = [{"role": "user", "content": create_prompt}]
            sheet_text = await provider.generate_text(sheet_messages, model_config)
        except Exception:
            continue

        sheet_data = {
            "name": setting_name,
            "sheet": sheet_text,
            "chunks": {},
            "summary": "",
            "abridged": "",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        setting_path = settings_dir / f"{slug}.json"
        _atomic_write(
            setting_path,
            json.dumps(sheet_data, indent=2, ensure_ascii=False),
        )

        try:
            sheet_json_text = setting_path.read_text(encoding="utf-8")
            chunk_results: dict[str, str] = {}
            for chunk_key, prompt_name in chunk_prompts.items():
                chunk_prompt = loader.load_prompt(
                    prompt_name,
                    {"setting_name": setting_name},
                )
                chunk_results[chunk_key] = await provider.generate_text(
                    [{"role": "user", "content": chunk_prompt}],
                    model_config,
                )

            abridged_prompt = loader.load_prompt(
                "settings/create_abridged",
                {
                    "story_elements": outline_result.story_elements,
                    "setting_name": setting_name,
                },
            )
            abridged_text = await provider.generate_text(
                [{"role": "user", "content": abridged_prompt}],
                model_config,
            )

            summary_prompt = loader.load_prompt(
                "settings/create_summary",
                {
                    "setting_name": setting_name,
                    "setting_info": sheet_json_text,
                },
            )
            summary_text = await provider.generate_text(
                [{"role": "user", "content": summary_prompt}],
                model_config,
            )

            enriched_data = json.loads(sheet_json_text)
            if not isinstance(enriched_data, dict):
                enriched_data = sheet_data.copy()
            enriched_data["chunks"] = chunk_results
            enriched_data["abridged"] = abridged_text
            enriched_data["summary"] = summary_text
            enriched_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            _atomic_write(
                setting_path,
                json.dumps(enriched_data, indent=2, ensure_ascii=False),
            )
        except Exception:
            pass

        written.append(setting_path)

    return written


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


async def _continue_pipeline(
    state: PipelineState,
    gate: ApprovalGate,
    bus: TokenStreamBus,
    wiki_bus: WikiContextBus,
    config: dict[str, Any] | None,
    provider: ModelProvider | None,
) -> PipelineState:
    resolved_config = config if config is not None else ConfigLoader().load_config()
    resolved_provider = provider or _create_provider(resolved_config)
    settings = _load_settings(resolved_config)

    story_dir = STORIES_DIR / state.story_name
    (story_dir / "savepoints").mkdir(parents=True, exist_ok=True)
    story_prompt = _load_story_prompt(state.story_name)

    try:
        if "story-foundation" not in state.completed_phases:
            state.current_phase = "story-foundation"
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
                state.outline_result.base_context = foundation_result.base_context
                state.outline_result.story_start_date = (
                    foundation_result.story_start_date
                )
                state.outline_result.story_elements = foundation_result.story_elements
            await _mark_phase_complete(
                state,
                "story-foundation",
                "story_foundation_complete",
            )

        if "outline" not in state.completed_phases:
            state.current_phase = "outline"
            outline_agent = OutlinePlannerAgent(
                resolved_provider, resolved_config, bus, wiki_bus
            )
            _foundation_base_context = (
                state.outline_result.base_context
                if state.outline_result is not None
                else ""
            )
            _foundation_story_start_date = (
                state.outline_result.story_start_date
                if state.outline_result is not None
                else ""
            )
            _foundation_story_elements = (
                state.outline_result.story_elements
                if state.outline_result is not None
                else ""
            )
            state.outline_result = await outline_agent.run(
                state.story_name,
                story_prompt,
                settings,
                base_context=_foundation_base_context,
                story_elements=_foundation_story_elements,
            )
            if not state.outline_result.base_context:
                state.outline_result.base_context = _foundation_base_context
            if not state.outline_result.story_start_date:
                state.outline_result.story_start_date = _foundation_story_start_date
            if not state.outline_result.story_elements:
                state.outline_result.story_elements = _foundation_story_elements
            # Persist generated outline before approval so a crash mid-gate
            # preserves it. The phase is only marked complete on approval.
            state.savepoint_id = "outline"
            await _write_savepoint(state)

            if (
                settings.enable_outline_critique
                and "outline-critique" not in state.completed_phases
            ):
                critic_agent = OutlineCriticAgent(
                    resolved_provider,
                    resolved_config,
                    bus,
                    wiki_bus,
                )
                state = await critic_agent.run(state, settings)
                await _write_savepoint(state)

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

        if "metadata-outline" not in state.completed_phases:
            state.current_phase = "metadata-outline"
            if state.outline_result is not None:
                try:
                    metadata_agent = StoryMetadataAgent(
                        resolved_provider, resolved_config, bus, wiki_bus
                    )
                    outline_text = _build_story_elements(state.outline_result)
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
            await wiki_bus.emit(
                WikiContextEvent(
                    phase="characters",
                    event_type="entity_match",
                    content=f"Generating character sheets for: {state.story_name}",
                )
            )
            if state.outline_result is not None:
                await _generate_character_sheets(
                    state.story_name,
                    state.outline_result,
                    resolved_provider,
                    resolved_config,
                    story_dir.parent,
                )
            await _mark_phase_complete(state, "characters", "characters")

        if "settings" not in state.completed_phases:
            state.current_phase = "settings"
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
                    state.outline_result,
                    resolved_provider,
                    resolved_config,
                    story_dir.parent,
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
            models = resolved_config.get("models", {})
            wiki_model: str | None = models.get("chapter_writer")
            await bus.emit(
                "\n[Wiki Bootstrap] Seeding wiki from outline and sheets...\n"
            )
            try:
                bootstrap_summary = await asyncio.to_thread(
                    bootstrap_wiki_from_story,
                    state.story_name,
                    model=wiki_model,
                )
                await bus.emit(
                    f"[Wiki Bootstrap] Created {bootstrap_summary['created']} pages"
                    f", skipped {bootstrap_summary['skipped']} existing.\n"
                )
            except Exception as exc:
                await bus.emit(
                    f"[Wiki Bootstrap] bootstrap skipped ({type(exc).__name__}: {exc})\n"
                )
            await _mark_phase_complete(state, "wiki-bootstrap", "wiki_populated")

        outline_result = state.outline_result
        if outline_result is None:
            raise StoryGenerationError(
                "Outline phase did not produce an outline result"
            )

        chapter_numbers = _chapter_numbers(outline_result, settings)
        _backfill_missing_chapter_files(story_dir, state.approved_chapters)
        next_chapter = len(state.approved_chapters) + 1
        if "chapter-loop" not in state.completed_phases:
            chapter_agent = ChapterWriterAgent(
                resolved_provider, resolved_config, bus, wiki_bus
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
                if chapter_number < next_chapter:
                    continue
                state.current_phase = f"chapter-{chapter_number}"
                draft = await _generate_chapter_with_gate(
                    state,
                    gate,
                    chapter_agent,
                    state.story_name,
                    chapter_number,
                    outline_result,
                    settings,
                )
                if draft is None:
                    return state

                consistency_result = await consistency_agent.run(
                    state.story_name,
                    chapter_number,
                    draft.content,
                    outline_result=outline_result,
                )
                if not consistency_result["passed"]:
                    await bus.emit(
                        f"\n[Consistency] Chapter {chapter_number} — issues found:\n"
                    )
                    for issue in consistency_result["issues"]:
                        await bus.emit(
                            f"  [{issue['severity'].upper()}] {issue['description']}\n"
                        )
                elif consistency_result["issues"]:
                    await bus.emit(
                        f"\n[Consistency] Chapter {chapter_number} — warnings/info found:\n"
                    )
                    for issue in consistency_result["issues"]:
                        await bus.emit(
                            f"  [{issue['severity'].upper()}] {issue['description']}\n"
                        )
                state.approved_chapters.append(draft)
                _write_chapter_file(story_dir, chapter_number, draft.content)
                try:
                    wiki_batch = await wiki_agent.run(
                        state.story_name, chapter_number, draft.content
                    )
                    state.wiki_batches.append(wiki_batch)
                except Exception as exc:
                    # Wiki updates are advisory; a failure must not lose the
                    # approved chapter or block the loop. Persist the chapter
                    # savepoint and continue so the run can complete.
                    await bus.emit(
                        f"\n[Wiki] chapter {chapter_number} wiki update skipped "
                        f"({type(exc).__name__}: {exc})\n"
                    )
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
                    if char_changes or setting_changes:
                        state.evolved_sheets[str(chapter_number)] = {
                            "characters": char_changes,
                            "settings": setting_changes,
                        }
                        await _write_savepoint(state)
                except Exception as exc:
                    await bus.emit(
                        f"\n[Sheet Evolution] chapter {chapter_number} skipped "
                        f"({type(exc).__name__}: {exc})\n"
                    )
                # Recap generation is advisory; failure must not block the loop
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
                            previous_recap_data.get("sanitised")
                            or previous_recap_data.get("compact")
                            or previous_recap_data.get("events")
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
                        state.recaps[str(chapter_number)] = recap_result
                        recap_path = (
                            story_dir
                            / "chapters"
                            / f"chapter_{chapter_number}_recap.json"
                        )
                        _atomic_write(
                            recap_path,
                            json.dumps(recap_result, indent=2, ensure_ascii=False),
                        )
                except Exception as exc:
                    await bus.emit(
                        f"\n[Recap] chapter {chapter_number} recap skipped "
                        f"({type(exc).__name__}: {exc})\n"
                    )
                if (
                    chapter_number == 1
                    and "metadata-chapter-1" not in state.completed_phases
                ):
                    if state.outline_result is not None:
                        try:
                            metadata_agent_ch1 = StoryMetadataAgent(
                                resolved_provider, resolved_config, bus, wiki_bus
                            )
                            outline_text_ch1 = _build_story_elements(
                                state.outline_result
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
                        except Exception as exc:
                            await bus.emit(
                                f"\n[Metadata] chapter-1 metadata skipped ({type(exc).__name__}: {exc})\n"
                            )
                await _mark_phase_complete(
                    state,
                    f"chapter-{chapter_number}",
                    f"chapter-{chapter_number}",
                )

            await _mark_phase_complete(state, "chapter-loop", "chapter-loop")

        if "final-edit" not in state.completed_phases:
            state.current_phase = "final-edit"
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
                    final_edit_result: FinalEditResult = await final_editor.run(
                        state.story_name, state.approved_chapters, settings
                    )
                    state.approved_chapters = final_edit_result.edited_chapters
                    edited_path = story_dir / "output" / "story_edited.md"
                    edited_path.parent.mkdir(parents=True, exist_ok=True)
                    edited_parts = [
                        ch.content.rstrip()
                        for ch in final_edit_result.edited_chapters
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
            if state.outline_result is not None and state.approved_chapters:
                try:
                    metadata_agent_final = StoryMetadataAgent(
                        resolved_provider, resolved_config, bus, wiki_bus
                    )
                    outline_text_final = _build_story_elements(state.outline_result)
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
        return state
    finally:
        bus.close()
        wiki_bus.close()


async def run_pipeline(
    story_name: str,
    gate: ApprovalGate,
    bus: TokenStreamBus,
    wiki_bus: WikiContextBus,
    config: dict[str, Any] | None = None,
    provider: ModelProvider | None = None,
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
        state, gate, bus, wiki_bus, resolved_config, provider
    )


async def resume_pipeline(
    story_name: str,
    savepoint_name: str | None,
    gate: ApprovalGate,
    bus: TokenStreamBus,
    wiki_bus: WikiContextBus,
    config: dict[str, Any] | None = None,
    provider: ModelProvider | None = None,
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
        return state

    return await _continue_pipeline(state, gate, bus, wiki_bus, config, provider)
