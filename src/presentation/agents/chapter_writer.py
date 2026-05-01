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
import re
from typing import Any, AsyncIterator, cast

from application.interfaces.model_provider import ModelProvider
from application.pipeline.handoffs import ChapterDraft, OutlineResult
from domain.value_objects.generation_settings import GenerationSettings
from domain.value_objects.model_config import ModelConfig
from infrastructure.prompts.prompt_loader import PromptLoader
from presentation.pipeline_primitives import (
    TokenStreamBus,
    WikiContextBus,
    WikiContextEvent,
)
from tools._io import STORIES_DIR, _validate_story_name


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
    ) -> None:
        self.provider = provider
        self.config = config
        self.bus = bus
        self.wiki_bus = wiki_bus
        self._loader = PromptLoader(prompts_dir="prompts")

    async def run(
        self,
        story_name: str,
        chapter_number: int,
        outline_result: OutlineResult,
        settings: GenerationSettings,
        feedback: str | None = None,
    ) -> ChapterDraft:
        chapter_outline = None
        if 0 < chapter_number <= len(outline_result.chapter_outlines):
            chapter_outline = outline_result.chapter_outlines[chapter_number - 1]

        title = f"Chapter {chapter_number}"
        chapter_summary = outline_result.summary
        if isinstance(chapter_outline, dict):
            chapter_summary = str(
                chapter_outline.get("summary")
                or chapter_outline.get("content")
                or chapter_summary
            )
            title = str(chapter_outline.get("title") or title)

        _validate_story_name(story_name)
        base_context, character_context, setting_context = self._build_entity_context(
            story_name
        )

        previous_chapter_summary = ""
        if chapter_number > 1 and outline_result.chapter_outlines:
            prev_outline = outline_result.chapter_outlines[chapter_number - 2]
            if isinstance(prev_outline, dict):
                previous_chapter_summary = str(
                    prev_outline.get("summary") or prev_outline.get("content") or ""
                )

        next_chapter_summary = ""
        if chapter_number < len(outline_result.chapter_outlines):
            next_outline = outline_result.chapter_outlines[chapter_number]
            if isinstance(next_outline, dict):
                next_chapter_summary = str(
                    next_outline.get("summary") or next_outline.get("content") or ""
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
                base_context=base_context,
                previous_chapter_summary=previous_chapter_summary,
                next_chapter_summary=next_chapter_summary,
                settings=settings,
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

        # Direct (single-shot) path: used for revisions, when the scene
        # pipeline is disabled, or as a fallback when scene drafting
        # produced no usable prose.
        full_text = await self._draft_direct(
            story_name=story_name,
            chapter_number=chapter_number,
            title=title,
            chapter_summary=chapter_summary,
            base_context=base_context,
            previous_chapter_summary=previous_chapter_summary,
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

    def _build_entity_context(self, story_name: str) -> tuple[str, str, str]:
        """Read character/setting sheets from disk into prompt-ready strings.

        Returns (base_context, character_context, setting_context).
        """
        character_context_parts: list[str] = []
        setting_context_parts: list[str] = []
        story_dir = STORIES_DIR / story_name
        for entity_type, _label, target_list in (
            ("characters", "Character", character_context_parts),
            ("settings", "Setting", setting_context_parts),
        ):
            entity_dir = story_dir / entity_type
            if not entity_dir.exists():
                continue
            for sheet_path in sorted(entity_dir.glob("*.json")):
                try:
                    data = json.loads(sheet_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    continue

                if not isinstance(data, dict):
                    continue

                name = data.get("name", sheet_path.stem)
                summary = data.get("summary") or ""
                if not summary:
                    sheet_text = data.get("sheet", "")
                    summary = sheet_text[:300].strip() if sheet_text else ""
                if summary:
                    target_list.append(f"- {name}: {summary}")

        base_context_parts: list[str] = []
        if character_context_parts:
            base_context_parts.append(
                "## Characters\n" + "\n".join(character_context_parts)
            )
        if setting_context_parts:
            base_context_parts.append(
                "## Settings\n" + "\n".join(setting_context_parts)
            )
        base_context = "\n\n".join(base_context_parts)
        return (
            base_context,
            "\n".join(character_context_parts),
            "\n".join(setting_context_parts),
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
        base_context: str,
        previous_chapter_summary: str,
        next_chapter_summary: str,
        settings: GenerationSettings,
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

        # Stage 1: synopsis expansion.
        await self.bus.emit(
            f"\n[Chapter {chapter_number}] Expanding chapter synopsis...\n"
        )
        synopsis_prompt = loader.load_prompt(
            "chapters/create_synopsis",
            variables={
                "chapter_number": str(chapter_number),
                "outline": chapter_summary,
                "story_elements": "",
                "base_context": base_context,
                "previous_chapter": previous_chapter_summary,
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

        # Stage 2: scene decomposition.
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
                "previous_chapter_recap": previous_chapter_summary,
                "next_chapter_synopsis": next_chapter_summary,
                "story_elements": "",
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

        # Persist scene definitions for downstream tooling and resumability.
        try:
            scenes_dir = STORIES_DIR / story_name / "chapters"
            scenes_dir.mkdir(parents=True, exist_ok=True)
            (scenes_dir / f"chapter_{chapter_number}_scenes.json").write_text(
                json.dumps(scenes, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            await self.bus.emit(
                f"\n[Chapter {chapter_number}] could not persist scene "
                f"definitions ({type(exc).__name__}: {exc}); continuing.\n"
            )

        # Stage 3: per-scene drafting.
        scene_prose: list[str] = []
        previous_scene_tail = ""
        for index, scene in enumerate(scenes, start=1):
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

            scene_prompt = loader.load_prompt(
                "scenes/create_content",
                variables={
                    "scene_num": str(index),
                    "chapter_num": str(chapter_number),
                    "scene_definition": json.dumps(scene, ensure_ascii=False),
                    "base_context": base_context,
                    "chapter_outline": synopsis_text,
                    "story_elements": "",
                    "previous_scene": previous_scene_tail,
                    "next_chapter_synopsis": next_chapter_summary,
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
            # Carry forward the last 500 chars of the prior scene as
            # continuity context, keeping the prompt budget bounded.
            previous_scene_tail = scene_text[-500:]

        if not scene_prose:
            return ""

        chapter_body = f"# {chapter_title}\n\n" + "\n\n".join(scene_prose)
        return chapter_body

    async def _draft_direct(
        self,
        story_name: str,
        chapter_number: int,
        title: str,
        chapter_summary: str,
        base_context: str,
        previous_chapter_summary: str,
        next_chapter_summary: str,
        character_context: str,
        setting_context: str,
        settings: GenerationSettings,
        feedback: str | None,
    ) -> str:
        loader = self._loader
        system_prompt = loader.load_prompt(
            "chapters/write_chapter_direct",
            variables={
                "chapter_number": str(chapter_number),
                "chapter_title": title,
                "chapter_summary": chapter_summary,
                "story_name": story_name,
                "base_context": base_context,
                "story_elements": "",
                "previous_chapter_summary": previous_chapter_summary,
                "next_chapter_summary": next_chapter_summary,
                "character_context": character_context,
                "setting_context": setting_context,
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
