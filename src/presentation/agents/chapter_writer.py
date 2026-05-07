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
from tools._llm import extract_paragraph_tail
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


def _extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()

    fence = re.search(r"```(?:json)?\s*(.*?)```", stripped, re.DOTALL)
    if fence:
        stripped = fence.group(1).strip()

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            return parsed

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


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
            recap_window=("chapter", 5),
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
        style_guide: str = state.style_guide if state is not None else ""
        if isinstance(style_guide, dict):
            style_guide = ""

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
            scenes_min = settings.scenes_per_chapter_min
            scenes_max = settings.scenes_per_chapter_max
            scenes_prompt = loader.load_prompt(
                "chapters/expand_to_scenes",
                variables={
                    "chapter_synopsis": synopsis_text,
                    "scenes_min": str(scenes_min),
                    "scenes_max": str(scenes_max),
                    "previous_chapter_recap": previous_chapter_recap,
                    "next_chapter_synopsis": next_chapter_summary,
                    "story_elements": story_elements,
                    "base_context": base_context,
                },
            )

            scenes = []
            last_count: int | None = None
            for attempt in range(2):
                user_msg = "Return the JSON array of scenes."
                if attempt > 0 and last_count is not None:
                    user_msg = (
                        f"Your previous response contained {last_count} scenes, which "
                        f"is outside the required range [{scenes_min}, {scenes_max}]. "
                        f"Decompose the synopsis again into at least {scenes_min} and "
                        f"at most {scenes_max} scenes. Return ONLY the JSON array."
                    )
                try:
                    scenes_raw = await self._stream_to_bus(
                        [
                            {"role": "system", "content": scenes_prompt},
                            {"role": "user", "content": user_msg},
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

                candidate = _extract_json_array(scenes_raw)
                if not candidate:
                    # Unparseable: don't waste a retry on the same prompt.
                    break
                last_count = len(candidate)
                if scenes_min <= last_count <= scenes_max:
                    scenes = candidate
                    break
                await self.bus.emit(
                    f"\n[Chapter {chapter_number}] scene decomposition produced "
                    f"{last_count} scenes (need {scenes_min}-{scenes_max}); retrying.\n"
                )
                scenes = candidate  # keep last as fallback

            if not scenes:
                await self.bus.emit(
                    f"\n[Chapter {chapter_number}] scene decomposition returned no "
                    "parsable scenes; falling back to direct drafting.\n"
                )
                return ""

            if not (scenes_min <= len(scenes) <= scenes_max):
                await self.bus.emit(
                    f"\n[Chapter {chapter_number}] scene count {len(scenes)} still "
                    f"outside [{scenes_min}, {scenes_max}] after retry; proceeding anyway.\n"
                )

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

            if settings.enable_decomposition_critique:
                try:
                    known_character_slugs: list[str] = []
                    known_location_slugs: list[str] = []
                    wiki_index_path = STORIES_DIR / story_name / "wiki" / "index.md"
                    if wiki_index_path.exists():
                        try:
                            for raw_line in wiki_index_path.read_text(
                                encoding="utf-8"
                            ).splitlines():
                                line = raw_line.strip()
                                if not line:
                                    continue
                                parts = [part.strip() for part in line.split("|")]
                                if len(parts) != 5:
                                    raise ValueError(
                                        f"Malformed wiki index line: {raw_line}"
                                    )
                                slug, entry_type, _name, _aliases, entry_path = parts
                                if entry_type == "character":
                                    known_character_slugs.append(slug)
                                if entry_path.startswith("locations/"):
                                    known_location_slugs.append(slug)
                        except (OSError, ValueError) as exc:
                            known_character_slugs = []
                            known_location_slugs = []
                            await self.bus.emit(
                                f"\n[Chapter {chapter_number}] Decomposition critic "
                                f"wiki index unavailable ({type(exc).__name__}: {exc}); "
                                "using empty slug hints.\n"
                            )

                    critic_prompt = loader.load_prompt(
                        "chapters/critique_scene_decomposition",
                        variables={
                            "scene_array_json": json.dumps(
                                scenes, indent=2, ensure_ascii=False
                            ),
                            "chapter_synopsis": synopsis_text,
                            "known_character_slugs": ", ".join(known_character_slugs),
                            "known_location_slugs": ", ".join(known_location_slugs),
                        },
                    )
                    critic_raw = await self._stream_to_bus(
                        [
                            {"role": "system", "content": critic_prompt},
                            {
                                "role": "user",
                                "content": "Return the JSON findings object.",
                            },
                        ],
                        synopsis_model,
                        settings.seed,
                    )
                    findings = _extract_json_object(critic_raw)
                    has_findings = any(key != "summary" for key in findings)

                    if has_findings:
                        await self.bus.emit(
                            f"\n[Chapter {chapter_number}] Decomposition critic found issues; regenerating scenes.\n"
                        )
                        await self.status_bus.emit(
                            StatusEvent(
                                phase=phase,
                                message=(
                                    f"Ch {chapter_number}: regenerating scenes "
                                    "(critic feedback)"
                                ),
                                kind="step",
                            )
                        )
                        feedback_msg = (
                            "The previous scene decomposition had the following "
                            "structural issues:\n\n"
                            + json.dumps(findings, indent=2, ensure_ascii=False)
                            + "\n\nPlease regenerate the scene array, fixing all "
                            "listed issues. Return ONLY the JSON array of scenes."
                        )
                        retry_raw = await self._stream_to_bus(
                            [
                                {"role": "system", "content": scenes_prompt},
                                {"role": "user", "content": feedback_msg},
                            ],
                            synopsis_model,
                            settings.seed,
                        )
                        retry_scenes = _extract_json_array(retry_raw)
                        if (
                            retry_scenes
                            and scenes_min <= len(retry_scenes) <= scenes_max
                        ):
                            scenes = retry_scenes
                            try:
                                _atomic_write(
                                    scenes_json_path,
                                    json.dumps(scenes, indent=2, ensure_ascii=False),
                                )
                            except OSError as exc:
                                await self.bus.emit(
                                    f"\n[Chapter {chapter_number}] could not persist "
                                    "critic-regenerated scenes "
                                    f"({type(exc).__name__}: {exc}); continuing.\n"
                                )
                        else:
                            retry_count = len(retry_scenes) if retry_scenes else 0
                            await self.bus.emit(
                                f"\n[Chapter {chapter_number}] Decomposition critic "
                                "retry produced invalid scene output "
                                f"({retry_count} scenes); proceeding with original decomposition.\n"
                            )
                    else:
                        await self.bus.emit(
                            f"\n[Chapter {chapter_number}] Decomposition critic: no issues found.\n"
                        )
                except Exception as exc:
                    await self.bus.emit(
                        f"\n[Chapter {chapter_number}] Decomposition critic failed "
                        f"({type(exc).__name__}: {exc}); proceeding.\n"
                    )

        # Stage 3: per-scene drafting.
        scene_prose: list[str] = []
        scenes_completed_meta: list[dict[str, Any]] = []
        actual_recaps: dict[int, str] = {}
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
                recap_cache_file = scenes_dir / f"scene_{index}_actual_recap.txt"
                if recap_cache_file.exists():
                    actual_recaps[index] = recap_cache_file.read_text(
                        encoding="utf-8"
                    ).strip()
                continue

            if index == 1:
                scene_prompt_key = "multistep/scene/create_content_first"
            elif index == total_scenes:
                scene_prompt_key = "multistep/scene/create_content_final"
            else:
                scene_prompt_key = "multistep/scene/create_content_middle"

            # Continuity context: tail of previous scene's prose + summary
            # of all scenes already drafted, so the model does not retread.
            prev_tail = (
                extract_paragraph_tail(scene_prose[-1].strip()) if scene_prose else ""
            )

            if scenes_completed_meta:
                completed_lines = []
                for done_idx, done_scene in enumerate(scenes_completed_meta, start=1):
                    title = done_scene.get("title", "") or f"scene {done_idx}"
                    desc = actual_recaps.get(done_idx) or (
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
                    recap_window=("chapter", 3),
                )
                if _scene_ctx["wiki_snapshot"]:
                    scene_base_context = _scene_ctx["wiki_snapshot"]
                if _scene_ctx["recap_snippets"]:
                    scene_recap_context = "\n\n".join(_scene_ctx["recap_snippets"])
            except Exception:
                pass

            if index < total_scenes:
                next_scene_summary = json.dumps(scenes[index], ensure_ascii=False)
            else:
                next_scene_summary = "(none — this is the final scene of the chapter)"

            _key_events = scene.get("key_events", []) if isinstance(scene, dict) else []
            _description = (
                scene.get("description", "") if isinstance(scene, dict) else ""
            )
            scene_word_target = settings.scene_word_target_floor
            scene_word_target += 150 * len(_key_events)
            if len(_description) > 200:
                scene_word_target += 100
            scene_word_target = min(
                scene_word_target, settings.scene_word_target_ceiling
            )

            _raw_devices = (
                scene.get("literary_devices", []) if isinstance(scene, dict) else []
            )
            if isinstance(_raw_devices, list):
                literary_devices_str = "\n".join(f"- {d}" for d in _raw_devices)
            elif isinstance(_raw_devices, str) and _raw_devices:
                literary_devices_str = f"- {_raw_devices}"
            else:
                literary_devices_str = ""

            scene_for_summary = (
                {k: v for k, v in scene.items() if k != "literary_devices"}
                if isinstance(scene, dict)
                else scene
            )

            scene_prompt = loader.load_prompt(
                scene_prompt_key,
                variables={
                    "current_scene_summary": json.dumps(
                        scene_for_summary, ensure_ascii=False
                    ),
                    "next_scene_summary": next_scene_summary,
                    "base_context": scene_base_context,
                    "story_elements": story_elements,
                    "chapter_number": str(chapter_number),
                    "chapter_title": chapter_title,
                    "chapter_summary": chapter_summary,
                    "next_chapter_summary": next_chapter_summary
                    or "(none — this is the final chapter)",
                    "scene_index": str(index),
                    "scene_total": str(total_scenes),
                    "previous_scene_tail": prev_tail,
                    "scenes_completed_summary": scenes_completed_summary,
                    "scene_recap_context": scene_recap_context,
                    "scene_word_target": str(scene_word_target),
                    "style_guide": style_guide,
                    "literary_devices": literary_devices_str,
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

            if settings.enable_scene_critique:
                await self.status_bus.emit(
                    StatusEvent(
                        phase=phase,
                        message=(
                            f"Ch {chapter_number}: critiquing scene "
                            f"{index}/{total_scenes}"
                        ),
                        kind="step",
                    )
                )
                await self.bus.emit(
                    f"\n[Chapter {chapter_number}] Critiquing scene {index}...\n"
                )
                critique_prompt = loader.load_prompt(
                    "scenes/critique_draft",
                    variables={
                        "chapter_num": str(chapter_number),
                        "scene_num": str(index),
                        "scene_content": scene_text,
                        "scene_definition": json.dumps(scene, ensure_ascii=False),
                        "chapter_outline": chapter_summary,
                        "previous_scene": prev_tail,
                    },
                )
                try:
                    critique_text = await self._stream_to_bus(
                        [
                            {"role": "system", "content": critique_prompt},
                            {"role": "user", "content": "Critique the scene now."},
                        ],
                        scene_model,
                        settings.seed,
                    )
                    critique_text = critique_text.strip()
                    if critique_text and critique_text != "{}":
                        # Non-empty findings — run one revision pass
                        await self.status_bus.emit(
                            StatusEvent(
                                phase=phase,
                                message=(
                                    f"Ch {chapter_number}: revising scene "
                                    f"{index}/{total_scenes}"
                                ),
                                kind="step",
                            )
                        )
                        await self.bus.emit(
                            f"\n[Chapter {chapter_number}] Revising scene {index}...\n"
                        )
                        revise_prompt = loader.load_prompt(
                            "scenes/revise_content",
                            variables={
                                "chapter_num": str(chapter_number),
                                "scene_num": str(index),
                                "scene_content": scene_text,
                                "feedback": critique_text,
                                "scene_definition": json.dumps(
                                    scene, ensure_ascii=False
                                ),
                                "chapter_outline": chapter_summary,
                                "previous_scene": prev_tail,
                                "next_chapter_synopsis": (
                                    next_chapter_summary
                                    if index == total_scenes
                                    else ""
                                ),
                            },
                        )
                        try:
                            revised = await self._stream_to_bus(
                                [
                                    {"role": "system", "content": revise_prompt},
                                    {
                                        "role": "user",
                                        "content": "Revise the scene now.",
                                    },
                                ],
                                scene_model,
                                settings.seed,
                            )
                            revised = revised.strip()
                            if revised:
                                scene_text = revised
                        except Exception as exc:
                            await self.bus.emit(
                                f"\n[Chapter {chapter_number}] scene {index} revision "
                                f"failed ({type(exc).__name__}: {exc}); using draft.\n"
                            )
                except Exception as exc:
                    await self.bus.emit(
                        f"\n[Chapter {chapter_number}] scene {index} critique "
                        f"failed ({type(exc).__name__}: {exc}); skipping critique.\n"
                    )

            if settings.enable_scrubbing:
                await self.status_bus.emit(
                    StatusEvent(
                        phase=phase,
                        message=(
                            f"Ch {chapter_number}: scrubbing scene "
                            f"{index}/{total_scenes}"
                        ),
                        kind="step",
                    )
                )
                await self.bus.emit(
                    f"\n[Chapter {chapter_number}] Scrubbing scene {index}...\n"
                )
                scrub_prompt = loader.load_prompt(
                    "scenes/scrub_content",
                    variables={
                        "chapter_num": str(chapter_number),
                        "scene_num": str(index),
                        "scene_content": scene_text,
                        "scene_definition": json.dumps(scene, ensure_ascii=False),
                    },
                )
                try:
                    scrubbed = await self._stream_to_bus(
                        [
                            {"role": "system", "content": scrub_prompt},
                            {
                                "role": "user",
                                "content": "Return the corrected scene now.",
                            },
                        ],
                        scene_model,
                        settings.seed,
                    )
                    scrubbed = scrubbed.strip()
                    if scrubbed:
                        scene_text = scrubbed
                except Exception as exc:
                    await self.bus.emit(
                        f"\n[Chapter {chapter_number}] scene {index} scrub "
                        f"failed ({type(exc).__name__}: {exc}); using raw draft.\n"
                    )

            # Generate and cache an actual-prose recap for continuity.
            prose_excerpt = scene_text[-500:].strip()
            recap_prompt = loader.load_prompt(
                "scenes/summarise_for_continuity",
                variables={"prose_excerpt": prose_excerpt},
            )
            try:
                recap_text = await self._stream_to_bus(
                    [
                        {"role": "system", "content": recap_prompt},
                        {"role": "user", "content": "Summarise the scene ending now."},
                    ],
                    scene_model,
                    settings.seed,
                )
                recap_text = recap_text.strip()
                if recap_text:
                    actual_recaps[index] = recap_text
                    recap_cache_file = scenes_dir / f"scene_{index}_actual_recap.txt"
                    _atomic_write(recap_cache_file, recap_text)
            except Exception as exc:
                await self.bus.emit(
                    f"\n[Chapter {chapter_number}] scene {index} recap failed "
                    f"({type(exc).__name__}: {exc}); continuity will use predicted ending.\n"
                )

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
