"""Python pipeline orchestrator for headless story generation.

Top-level entry point for the Python-native story generation pipeline.
Drives phases sequentially with injected async primitives, supporting
both TUI and headless operation without code changes.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from application.interfaces.model_provider import ModelProvider
from application.pipeline.handoffs import ChapterDraft, OutlineResult, PipelineState
from config.config_loader import ConfigLoader
from domain.exceptions import StoryGenerationError
from domain.value_objects.generation_settings import GenerationSettings
from domain.value_objects.model_config import ModelConfig
from infrastructure.prompts.prompt_loader import PromptLoader
from presentation.agents.chapter_writer import ChapterWriterAgent
from presentation.agents.consistency_checker import ConsistencyCheckerAgent
from presentation.agents.outline_planner import OutlinePlannerAgent
from presentation.agents.wiki_maintainer import WikiMaintainerAgent
from presentation.pipeline_primitives import (
    ApprovalGate,
    NullApprovalGate,
    TokenStreamBus,
    WikiContextBus,
    WikiContextEvent,
)
from tools._io import STORIES_DIR, _atomic_write, _validate_story_name


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
    state.savepoints.append(savepoint_name)
    await _write_savepoint(state)


def _write_chapter_file(story_dir: Path, chapter_number: int, content: str) -> None:
    """Write an approved chapter's content to disk."""
    chapters_dir = story_dir / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    (chapters_dir / f"chapter_{chapter_number}.md").write_text(
        content, encoding="utf-8"
    )


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
        )
        state.savepoint_id = "outline"
        if "outline" not in state.savepoints:
            state.savepoints.append("outline")
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
    draft = await agent.run(story_name, chapter_number, outline_result, settings)
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
        )
        state.savepoint_id = f"chapter-{chapter_number}"
        if f"chapter-{chapter_number}" not in state.savepoints:
            state.savepoints.append(f"chapter-{chapter_number}")
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
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        char_path = characters_dir / f"{slug}.json"
        _atomic_write(char_path, json.dumps(sheet_data, indent=2, ensure_ascii=False))
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
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        setting_path = settings_dir / f"{slug}.json"
        _atomic_write(
            setting_path,
            json.dumps(sheet_data, indent=2, ensure_ascii=False),
        )
        written.append(setting_path)

    return written


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
        if "outline" not in state.completed_phases:
            state.current_phase = "outline"
            outline_agent = OutlinePlannerAgent(
                resolved_provider, resolved_config, bus, wiki_bus
            )
            state.outline_result = await outline_agent.run(
                state.story_name,
                story_prompt,
                settings,
            )
            await _mark_phase_complete(state, "outline", "outline")

            state = await _await_outline_approval(
                state,
                gate,
                outline_agent,
                state.story_name,
                story_prompt,
                settings,
            )
            if state.status == "rejected":
                return state

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

        outline_result = state.outline_result
        if outline_result is None:
            raise StoryGenerationError(
                "Outline phase did not produce an outline result"
            )

        chapter_numbers = _chapter_numbers(outline_result, settings)
        next_chapter = len(state.approved_chapters) + 1
        if "chapter-loop" not in state.completed_phases:
            chapter_agent = ChapterWriterAgent(
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

                await consistency_agent.run(
                    state.story_name, chapter_number, draft.content
                )
                state.approved_chapters.append(draft)
                _write_chapter_file(story_dir, chapter_number, draft.content)
                wiki_batch = await wiki_agent.run(
                    state.story_name, chapter_number, draft.content
                )
                state.wiki_batches.append(wiki_batch)
                await _mark_phase_complete(
                    state,
                    f"chapter-{chapter_number}",
                    f"chapter-{chapter_number}",
                )

            await _mark_phase_complete(state, "chapter-loop", "chapter-loop")

        if "final-edit" not in state.completed_phases:
            state.current_phase = "final-edit"
            await _mark_phase_complete(state, "final-edit", "final-edit")

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
    """Resume a pipeline from a named savepoint or the latest savepoint."""
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

    if state.status == "complete":
        bus.close()
        wiki_bus.close()
        return state

    return await _continue_pipeline(state, gate, bus, wiki_bus, config, provider)
