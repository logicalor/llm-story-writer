"""Chapter Writer agent — generates chapter content via synopsis → scenes → prose.

When `settings.scene_generation_pipeline` is True (the default), the agent
performs a three-stage pipeline:

1. **Synopsis expansion** — `chapters/create_synopsis` expands the bare
   chapter outline into a detailed multi-beat synopsis.
2. **Scene decomposition** — `chapters/expand_to_scenes` decomposes the
   synopsis into a JSON array of scene definitions, bounded by
   `scenes_per_chapter_min/max`.
3. **Per-scene drafting** — `scenes/create_content` writes prose for each
   scene sequentially, threading the prior scene tail as continuity.

When `scene_generation_pipeline` is False, or any pipeline step fails,
the agent falls back to single-shot generation via
`chapters/write_chapter_direct`. Revision feedback always uses the direct
path because revisions operate on whole-chapter prose.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, AsyncIterator, cast

from application.interfaces.model_provider import ModelProvider
from application.pipeline.handoffs import ChapterDraft, OutlineResult, PipelineState
from domain.value_objects.generation_settings import GenerationSettings
from domain.value_objects.model_config import ModelConfig
from infrastructure.prompts.prompt_loader import PromptLoader
from presentation.pipeline_primitives import (
    NullStatusBus,
    StatusBus,
    StatusEvent,
    TokenStreamBus,
    WikiContextBus,
    WikiContextEvent,
)
from tools._io import STORIES_DIR, _atomic_write, _validate_story_name
from tools._persist import read_markdown_ref
from tools.context_assembly import assemble_context


def _savepoint_path(story_name: str) -> Path:
    return STORIES_DIR / story_name / "savepoints" / "pipeline_state.json"


def _work_item_done(state: PipelineState, phase: str, item_id: str) -> bool:
    return item_id in state.completed_work_items.get(phase, [])


async def _mark_work_item_done(state: PipelineState, phase: str, item_id: str) -> None:
    state.completed_work_items.setdefault(phase, [])
    if item_id not in state.completed_work_items[phase]:
        state.completed_work_items[phase].append(item_id)
    _atomic_write(_savepoint_path(state.story_name), state.to_json())


def _build_model_config(config: dict[str, Any], role: str, default: str) -> ModelConfig:
    models = config.get("models", {})
    model_name = models.get(role, default)
    return ModelConfig.from_string(model_name)


def _extract_json_array(text: str) -> list[dict[str, Any]]:
    """Extract a JSON array of scene objects from an LLM response.

    Tolerates fenced code blocks and surrounding prose. Returns an empty
    list if no parsable array is found.
    """
    stripped = text.strip()

    # Strip ```json ... ``` or ``` ... ``` fences.
    fence = re.search(r"```(?:json)?\s*(.*?)```", stripped, re.DOTALL)
    if fence:
        stripped = fence.group(1).strip()

    # Find the first JSON array in the text.
    start = stripped.find("[")
    end = stripped.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return []

    try:
        parsed = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError:
        return []

    if not isinstance(parsed, list):
        return []
    return [scene for scene in parsed if isinstance(scene, dict)]


class ChapterWriterAgent:
    def __init__(
        self,
        provider: ModelProvider,
        config: dict[str, Any],
        bus: TokenStreamBus,
        wiki_bus: WikiContextBus,
        status_bus: StatusBus | None = None,
    ) -> None:
        self.provider = provider
        self.config = config
        self.bus = bus
        self.wiki_bus = wiki_bus
        self.status_bus: StatusBus = (
            status_bus if status_bus is not None else NullStatusBus()
        )
        self._loader = PromptLoader(prompts_dir="prompts")

    async def run(
        self,
        story_name: str,
        chapter_number: int,
        outline_result: OutlineResult,
        settings: GenerationSettings,
        feedback: str | None = None,
        recaps: dict[str, Any] | None = None,
        state: PipelineState | None = None,
    ) -> ChapterDraft:
        recaps = recaps or {}
        chapter_outline = None
        if 0 < chapter_number <= len(outline_result.chapter_outlines):
            chapter_outline = outline_result.chapter_outlines[chapter_number - 1]

        title = f"Chapter {chapter_number}"
        story_root = STORIES_DIR / story_name
        _raw_outline_summary = outline_result.summary
        chapter_summary: str = (
            read_markdown_ref(story_root, _raw_outline_summary)
            if isinstance(_raw_outline_summary, dict)
            else (_raw_outline_summary or "")
        )
        if isinstance(chapter_outline, dict):
            raw_summary = (
                chapter_outline.get("summary")
                or chapter_outline.get("content")
                or chapter_summary
            )
            chapter_summary = (
                read_markdown_ref(story_root, raw_summary)
                if isinstance(raw_summary, dict)
                else str(raw_summary)
            )
            title = str(chapter_outline.get("title") or title)

        if outline_result.chapter_details and chapter_number <= len(
            outline_result.chapter_details
        ):
            entry = outline_result.chapter_details[chapter_number - 1]
            raw_detail = entry.get("detail", "") if isinstance(entry, dict) else ""
            detail_block = (
                read_markdown_ref(story_root, raw_detail)
                if isinstance(raw_detail, dict)
                else (raw_detail or "")
            )
            if detail_block:
                chapter_summary = detail_block

        _validate_story_name(story_name)
        actual_story_elements = (
            read_markdown_ref(story_root, outline_result.story_elements)
            if isinstance(outline_result.story_elements, dict)
            else (outline_result.story_elements or "")
        )
        _pov_character: str | None = None
        _primary_location: str | None = None
        _chapter_characters: tuple[str, ...] = ()
        if isinstance(chapter_outline, dict):
            _ch_chars = chapter_outline.get("characters") or []
            if isinstance(_ch_chars, list) and _ch_chars:
                _pov_character = str(_ch_chars[0])
                _chapter_characters = tuple(str(c) for c in _ch_chars)
            _primary_location = (
                chapter_outline.get("primary_location")
                or chapter_outline.get("setting")
                or chapter_outline.get("location")
                or None
            )

        _chapter_ctx = assemble_context(
            story_name,
            scope="chapter",
            focus=chapter_summary,
            chapter=chapter_number,
            pov_character=_pov_character,
            primary_location=_primary_location,
            characters=_chapter_characters,
            recap_window=("character", 5),
        )
        base_context = _chapter_ctx["wiki_snapshot"]
        recap_context = (
            "\n\n".join(_chapter_ctx["recap_snippets"])
            if _chapter_ctx["recap_snippets"]
            else ""
        )
        character_context = ""
        setting_context = ""
        await self.wiki_bus.emit(
            WikiContextEvent(
                phase="chapter",
                event_type="semantic_search",
                content=f"Wiki snapshot assembled for chapter {chapter_number}",
            )
        )

        previous_chapter_recap = ""
        if chapter_number > 1:
            recap_entry = recaps.get(str(chapter_number - 1), {})
            if isinstance(recap_entry, dict):
                _raw_recap = (
                    recap_entry.get("compact")
                    or recap_entry.get("sanitised")
                    or recap_entry.get("events")
                    or ""
                )
                previous_chapter_recap = (
                    read_markdown_ref(story_root, _raw_recap)
                    if isinstance(_raw_recap, dict)
                    else str(_raw_recap)
                )

        next_chapter_summary = ""
        if chapter_number < len(outline_result.chapter_outlines):
            next_outline = outline_result.chapter_outlines[chapter_number]
            if isinstance(next_outline, dict):
                raw_next = (
                    next_outline.get("summary") or next_outline.get("content") or ""
                )
                next_chapter_summary = (
                    read_markdown_ref(story_root, raw_next)
                    if isinstance(raw_next, dict)
                    else str(raw_next)
                )

        await self.wiki_bus.emit(
            WikiContextEvent(
                phase="chapter",
                event_type="entity_match",
                content=f"Assembling chapter {chapter_number} context",
            )
        )

        # Multi-stage pipeline: synopsis → scenes → per-scene drafting.
        # Skipped on revisions (feedback path) and when disabled by settings.
        if feedback is None and settings.scene_generation_pipeline:
            multi_stage_text = await self._run_scene_pipeline(
                story_name=story_name,
                chapter_number=chapter_number,
                chapter_title=title,
                chapter_summary=chapter_summary,
                story_elements=actual_story_elements,
                base_context=base_context,
                recap_context=recap_context,
                previous_chapter_recap=previous_chapter_recap,
                next_chapter_summary=next_chapter_summary,
                settings=settings,
                state=state,
            )
            if multi_stage_text:
                return ChapterDraft(
                    story_name=story_name,
                    chapter_number=chapter_number,
                    title=title,
                    content=multi_stage_text,
                    word_count=len(multi_stage_text.split()),
                )
            await self.bus.emit(
                f"\n[Chapter {chapter_number}] scene pipeline empty — "
                "falling back to single-shot drafting.\n"
            )

        # Scene-by-scene revision: when feedback is set and saved scenes exist,
        # revise each scene individually rather than regenerating the whole chapter.
        if feedback is not None and settings.scene_generation_pipeline:
            revised_text = await self._revise_scene_pipeline(
                story_name=story_name,
                chapter_number=chapter_number,
                chapter_title=title,
                chapter_summary=chapter_summary,
                base_context=base_context,
                feedback=feedback,
                settings=settings,
                next_chapter_synopsis=next_chapter_summary,
            )
            if revised_text:
                return ChapterDraft(
                    story_name=story_name,
                    chapter_number=chapter_number,
                    title=title,
                    content=revised_text,
                    word_count=len(revised_text.split()),
                )
            await self.bus.emit(
                f"\n[Chapter {chapter_number}] scene revision pipeline unavailable "
                "(no saved scenes) — falling back to single-shot rewrite.\n"
            )

        # Direct (single-shot) path: used for revisions when no scenes JSON exists,
        # when the scene pipeline is disabled, or as a fallback when scene drafting
        # produced no usable prose.
        full_text = await self._draft_direct(
            story_name=story_name,
            chapter_number=chapter_number,
            title=title,
            chapter_summary=chapter_summary,
            story_elements=actual_story_elements,
            base_context=base_context,
            recap_context=recap_context,
            previous_chapter_summary=previous_chapter_recap,
            next_chapter_summary=next_chapter_summary,
            character_context=character_context,
            setting_context=setting_context,
            settings=settings,
            feedback=feedback,
        )

        return ChapterDraft(
            story_name=story_name,
            chapter_number=chapter_number,
            title=title,
            content=full_text,
            word_count=len(full_text.split()),
        )

    async def _stream_to_bus(
        self, messages: list[dict[str, str]], model_config: ModelConfig, seed: int
    ) -> str:
        """Stream tokens to the bus and return the accumulated text."""
        full_text = ""
        stream = cast(
            AsyncIterator[str],
            self.provider.stream_text(messages, model_config, seed=seed),
        )
        async for token in stream:
            await self.bus.emit(token)
            full_text += token
        return full_text

    async def _run_scene_pipeline(
        self,
        story_name: str,
        chapter_number: int,
        chapter_title: str,
        chapter_summary: str,
        story_elements: str,
        base_context: str,
        next_chapter_summary: str,
        settings: GenerationSettings,
        previous_chapter_recap: str = "",
        recap_context: str = "",
        state: PipelineState | None = None,
    ) -> str:
        """Run synopsis → scene-decomposition → per-scene drafting.

        Returns the concatenated chapter prose, or an empty string if any
        critical step fails so the caller can fall back to single-shot
        drafting.
        """
        loader = self._loader
        synopsis_model = _build_model_config(
            self.config, "chapter_outline_writer", "openai-compat://default"
        )
        scene_model = _build_model_config(
            self.config, "scene_writer", "openai-compat://default"
        )

        phase = f"chapter-{chapter_number}"
        scenes_json_path = (
            STORIES_DIR
            / story_name
            / "chapters"
            / f"chapter_{chapter_number}_scenes.json"
        )
        if state is not None and _work_item_done(state, phase, "scenes/decomposition"):
            loaded_scenes = json.loads(scenes_json_path.read_text(encoding="utf-8"))
            if not isinstance(loaded_scenes, list):
                raise ValueError(
                    f"Cached scenes for chapter {chapter_number} are not a JSON array"
                )
            scenes = [scene for scene in loaded_scenes if isinstance(scene, dict)]
        else:
            await self.status_bus.emit(
                StatusEvent(
                    phase=phase,
                    message=f"Ch {chapter_number}: expanding synopsis",
                    kind="step",
                )
            )
            await self.bus.emit(
                f"\n[Chapter {chapter_number}] Expanding chapter synopsis...\n"
            )
            synopsis_prompt = loader.load_prompt(
                "chapters/create_synopsis",
                variables={
                    "chapter_number": str(chapter_number),
                    "outline": chapter_summary,
                    "story_elements": story_elements,
                    "base_context": base_context,
                    "previous_chapter": previous_chapter_recap,
                    "recap_context": recap_context,
                },
            )
            try:
                synopsis_text = await self._stream_to_bus(
                    [
                        {"role": "system", "content": synopsis_prompt},
                        {"role": "user", "content": "Produce the expanded synopsis."},
                    ],
                    synopsis_model,
                    settings.seed,
                )
            except Exception as exc:
                await self.bus.emit(
                    f"\n[Chapter {chapter_number}] synopsis expansion failed "
                    f"({type(exc).__name__}: {exc}); using outline summary.\n"
                )
                synopsis_text = chapter_summary

            synopsis_text = synopsis_text.strip() or chapter_summary

            await self.status_bus.emit(
                StatusEvent(
                    phase=phase,
                    message=f"Ch {chapter_number}: decomposing into scenes",
                    kind="step",
                )
            )
            await self.bus.emit(
                f"\n[Chapter {chapter_number}] Decomposing synopsis into scenes "
                f"({settings.scenes_per_chapter_min}-"
                f"{settings.scenes_per_chapter_max})...\n"
            )
            scenes_prompt = loader.load_prompt(
                "chapters/expand_to_scenes",
                variables={
                    "chapter_synopsis": synopsis_text,
                    "scenes_min": str(settings.scenes_per_chapter_min),
                    "scenes_max": str(settings.scenes_per_chapter_max),
                    "previous_chapter_recap": previous_chapter_recap,
                    "next_chapter_synopsis": next_chapter_summary,
                    "story_elements": story_elements,
                    "base_context": base_context,
                },
            )
            try:
                scenes_raw = await self._stream_to_bus(
                    [
                        {"role": "system", "content": scenes_prompt},
                        {"role": "user", "content": "Return the JSON array of scenes."},
                    ],
                    synopsis_model,
                    settings.seed,
                )
            except Exception as exc:
                await self.bus.emit(
                    f"\n[Chapter {chapter_number}] scene decomposition failed "
                    f"({type(exc).__name__}: {exc}); falling back to direct drafting.\n"
                )
                return ""

            scenes = _extract_json_array(scenes_raw)
            if not scenes:
                await self.bus.emit(
                    f"\n[Chapter {chapter_number}] scene decomposition returned no "
                    "parsable scenes; falling back to direct drafting.\n"
                )
                return ""

            try:
                scenes_json_path.parent.mkdir(parents=True, exist_ok=True)
                _atomic_write(
                    scenes_json_path,
                    json.dumps(scenes, indent=2, ensure_ascii=False),
                )
                if state is not None:
                    await _mark_work_item_done(state, phase, "scenes/decomposition")
            except OSError as exc:
                await self.bus.emit(
                    f"\n[Chapter {chapter_number}] could not persist scene "
                    f"definitions ({type(exc).__name__}: {exc}); continuing.\n"
                )

        # Stage 3: per-scene drafting.
        scene_prose: list[str] = []
        scenes_completed_meta: list[dict[str, Any]] = []
        total_scenes = len(scenes)
        scenes_dir = STORIES_DIR / story_name / "chapters" / f"chapter_{chapter_number}"
        for index, scene in enumerate(scenes, start=1):
            scene_item_id = f"scene:{index}"
            scene_file = scenes_dir / f"scene_{index}.md"
            scene_title = scene.get("title", "") or f"scene {index}"
            await self.status_bus.emit(
                StatusEvent(
                    phase=phase,
                    message=(
                        f"Ch {chapter_number}: scene {index}/{total_scenes} — "
                        f"{scene_title}"
                    ),
                    kind="step",
                )
            )
            await self.wiki_bus.emit(
                WikiContextEvent(
                    phase="chapter",
                    event_type="detail_level",
                    content=(
                        f"Drafting chapter {chapter_number} scene {index}/"
                        f"{len(scenes)}: {scene.get('title', '')}"
                    ),
                )
            )
            await self.bus.emit(
                f"\n\n--- Chapter {chapter_number} Scene {index}/{len(scenes)}: "
                f"{scene.get('title', '')} ---\n"
            )

            if state is not None and _work_item_done(state, phase, scene_item_id):
                scene_text = scene_file.read_text(encoding="utf-8")
                scene_prose.append(scene_text)
                scenes_completed_meta.append(scene)
                continue

            if index == 1:
                scene_prompt_key = "multistep/scene/create_content_first"
            elif index == total_scenes:
                scene_prompt_key = "multistep/scene/create_content_final"
            else:
                scene_prompt_key = "multistep/scene/create_content_middle"

            # Continuity context: tail of previous scene's prose + summary
            # of all scenes already drafted, so the model does not retread.
            if scene_prose:
                prev_tail = scene_prose[-1].strip()
                if len(prev_tail) > 1200:
                    prev_tail = "…" + prev_tail[-1200:]
            else:
                prev_tail = ""

            if scenes_completed_meta:
                completed_lines = []
                for done_idx, done_scene in enumerate(scenes_completed_meta, start=1):
                    title = done_scene.get("title", "") or f"scene {done_idx}"
                    desc = (
                        done_scene.get("ending") or done_scene.get("description") or ""
                    )
                    completed_lines.append(f"{done_idx}. {title} — {desc}".strip())
                scenes_completed_summary = "\n".join(completed_lines)
            else:
                scenes_completed_summary = "(none yet — this is the opening scene)"

            scene_base_context = base_context
            scene_recap_context = recap_context
            _scene_pov = (
                scene.get("characters", [None])[0] if scene.get("characters") else None
            )
            _scene_chars = tuple(
                scene.get("characters", [])[1:] if scene.get("characters") else []
            )
            _scene_location = scene.get("setting") or scene.get("location") or None
            _scene_focus = (
                scene.get("description", "")
                or scene.get("summary", "")
                or chapter_summary
            )
            try:
                _scene_ctx = assemble_context(
                    story_name,
                    scope="scene",
                    focus=_scene_focus,
                    chapter=chapter_number,
                    scene=index,
                    pov_character=_scene_pov,
                    primary_location=_scene_location,
                    characters=_scene_chars,
                    recap_window=("character", 3),
                )
                if _scene_ctx["wiki_snapshot"]:
                    scene_base_context = _scene_ctx["wiki_snapshot"]
                if _scene_ctx["recap_snippets"]:
                    scene_recap_context = "\n\n".join(_scene_ctx["recap_snippets"])
            except Exception:
                pass

            scene_prompt = loader.load_prompt(
                scene_prompt_key,
                variables={
                    "current_scene_summary": json.dumps(scene, ensure_ascii=False),
                    "base_context": scene_base_context,
                    "scene_index": str(index),
                    "scene_total": str(total_scenes),
                    "previous_scene_tail": prev_tail,
                    "scenes_completed_summary": scenes_completed_summary,
                    "scene_recap_context": scene_recap_context,
                },
            )
            try:
                scene_text = await self._stream_to_bus(
                    [
                        {"role": "system", "content": scene_prompt},
                        {"role": "user", "content": "Write the scene now."},
                    ],
                    scene_model,
                    settings.seed,
                )
            except Exception as exc:
                await self.bus.emit(
                    f"\n[Chapter {chapter_number}] scene {index} drafting "
                    f"failed ({type(exc).__name__}: {exc}); continuing.\n"
                )
                continue

            scene_text = scene_text.strip()
            if not scene_text:
                continue

            scene_prose.append(scene_text)
            scenes_completed_meta.append(scene)
            if state is not None:
                scene_file.parent.mkdir(parents=True, exist_ok=True)
                _atomic_write(scene_file, scene_text)
                await _mark_work_item_done(state, phase, scene_item_id)

        if not scene_prose:
            return ""

        chapter_body = f"# {chapter_title}\n\n" + "\n\n".join(scene_prose)
        return chapter_body

    async def _revise_scene_pipeline(
        self,
        story_name: str,
        chapter_number: int,
        chapter_title: str,
        chapter_summary: str,
        base_context: str,
        feedback: str,
        settings: GenerationSettings,
        next_chapter_synopsis: str = "",
    ) -> str:
        """Revise a chapter scene-by-scene using saved scene definitions and prose.

        Loads chapter_N_scenes.json and per-scene scene_M.md files, runs the
        scenes/revise_content prompt for each scene individually, overwrites the
        per-scene files with revised prose, and reassembles the chapter.

        Returns the reassembled chapter text, or an empty string if no saved
        scenes exist (caller should fall back to _draft_direct).
        """
        loader = self._loader
        scene_model = _build_model_config(
            self.config, "scene_writer", "openai-compat://default"
        )
        phase = f"chapter-{chapter_number}"

        # Load saved scene definitions.
        scenes_json_path = (
            STORIES_DIR
            / story_name
            / "chapters"
            / f"chapter_{chapter_number}_scenes.json"
        )
        if not scenes_json_path.exists():
            return ""
        try:
            scenes = json.loads(scenes_json_path.read_text(encoding="utf-8"))
            if not isinstance(scenes, list) or not scenes:
                return ""
        except (json.JSONDecodeError, OSError):
            return ""

        # Strip the appended "## Current Chapter Draft" block from feedback — the
        # full draft is redundant here since each scene gets its own existing prose.
        draft_marker = "\n\n## Current Chapter Draft\n"
        scene_feedback = feedback
        if draft_marker in scene_feedback:
            scene_feedback = scene_feedback[: scene_feedback.index(draft_marker)]

        scenes_dir = STORIES_DIR / story_name / "chapters" / f"chapter_{chapter_number}"
        total_scenes = len(scenes)
        scene_prose: list[str] = []

        for index, scene in enumerate(scenes, start=1):
            scene_title = scene.get("title", "") or f"scene {index}"
            await self.status_bus.emit(
                StatusEvent(
                    phase=phase,
                    message=(
                        f"Ch {chapter_number}: revising scene {index}/{total_scenes}"
                        f" — {scene_title}"
                    ),
                    kind="step",
                )
            )
            await self.bus.emit(
                f"\n\n--- Revising Chapter {chapter_number} Scene "
                f"{index}/{total_scenes}: {scene_title} ---\n"
            )

            scene_file = scenes_dir / f"scene_{index}.md"
            existing_prose = (
                scene_file.read_text(encoding="utf-8") if scene_file.exists() else ""
            )

            previous_scene = scene_prose[-1] if scene_prose else ""
            revision_prompt = loader.load_prompt(
                "scenes/revise_content",
                variables={
                    "scene_content": existing_prose,
                    "feedback": scene_feedback,
                    "scene_definition": json.dumps(scene, ensure_ascii=False),
                    "chapter_outline": chapter_summary,
                    "previous_scene": previous_scene,
                    "next_chapter_synopsis": next_chapter_synopsis
                    if index == total_scenes
                    else "",
                    "scene_num": str(index),
                    "chapter_num": str(chapter_number),
                },
            )
            try:
                revised_text = await self._stream_to_bus(
                    [
                        {"role": "system", "content": revision_prompt},
                        {"role": "user", "content": "Revise the scene now."},
                    ],
                    scene_model,
                    settings.seed,
                )
            except Exception as exc:
                await self.bus.emit(
                    f"\n[Chapter {chapter_number}] scene {index} revision failed "
                    f"({type(exc).__name__}: {exc}); retaining original.\n"
                )
                revised_text = existing_prose

            revised_text = revised_text.strip() or existing_prose
            scene_prose.append(revised_text)

            # Overwrite per-scene file with revised prose.
            scene_file.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write(scene_file, revised_text)

        if not scene_prose:
            return ""

        return f"# {chapter_title}\n\n" + "\n\n".join(scene_prose)

    async def _draft_direct(
        self,
        story_name: str,
        chapter_number: int,
        title: str,
        chapter_summary: str,
        story_elements: str,
        base_context: str,
        previous_chapter_summary: str,
        next_chapter_summary: str,
        character_context: str,
        setting_context: str,
        settings: GenerationSettings,
        feedback: str | None,
        recap_context: str = "",
    ) -> str:
        loader = self._loader
        character_context_block = (
            f"<CHARACTER_CONTEXT>\n{character_context}\n</CHARACTER_CONTEXT>"
            if character_context
            else ""
        )
        setting_context_block = (
            f"<SETTING_CONTEXT>\n{setting_context}\n</SETTING_CONTEXT>"
            if setting_context
            else ""
        )
        system_prompt = loader.load_prompt(
            "chapters/write_chapter_direct",
            variables={
                "chapter_number": str(chapter_number),
                "chapter_title": title,
                "chapter_summary": chapter_summary,
                "story_name": story_name,
                "base_context": base_context,
                "story_elements": story_elements,
                "previous_chapter_summary": previous_chapter_summary,
                "next_chapter_summary": next_chapter_summary,
                "character_context_block": character_context_block,
                "setting_context_block": setting_context_block,
                "recap_context": recap_context,
            },
        )
        if feedback:
            system_prompt = f"{system_prompt}\n\n## Revision Feedback\n{feedback}"

        model_config = _build_model_config(
            self.config,
            "chapter_writer",
            "openai-compat://default",
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Write the chapter now."},
        ]
        return await self._stream_to_bus(messages, model_config, settings.seed)
