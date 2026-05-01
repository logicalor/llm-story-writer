"""Outline Planner agent — transforms story prompt into structured outline."""

from __future__ import annotations

import json
import re
from typing import Any, AsyncIterator, cast

from application.interfaces.model_provider import ModelProvider
from application.pipeline.handoffs import OutlineResult
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


def _build_outline_pacing_variables(desired_chapters: int) -> dict[str, str]:
    early_chapters = max(1, int(desired_chapters * 0.25))
    rising_start = early_chapters + 1
    rising_end = max(rising_start, int(desired_chapters * 0.75))
    climax_start = max(rising_end + 1, int(desired_chapters * 0.75) + 1)
    climax_end = max(climax_start, int(desired_chapters * 0.90))
    resolution_start = climax_end + 1
    return {
        "desired_chapters": str(desired_chapters),
        "early_chapters": str(early_chapters),
        "rising_start": str(rising_start),
        "rising_end": str(rising_end),
        "climax_start": str(climax_start),
        "climax_end": str(climax_end),
        "resolution_start": str(resolution_start),
    }


def _parse_chapter_outlines(text: str, wanted_chapters: int) -> list[dict[str, Any]]:
    stripped = text.strip()
    if not stripped:
        return []

    if stripped.startswith("{") or stripped.startswith("["):
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            payload = None
        else:
            if isinstance(payload, dict):
                parsed_chapter_outlines = payload.get("chapter_outlines", [])
                if isinstance(parsed_chapter_outlines, list):
                    return [
                        entry
                        for entry in parsed_chapter_outlines
                        if isinstance(entry, dict)
                    ]
            if isinstance(payload, list):
                return [entry for entry in payload if isinstance(entry, dict)]

    chapter_outlines: list[dict[str, Any]] = []
    # Match headings like "### Chapter 3: Linguistic Shadows", "## Chapter 3 - Title",
    # "Chapter 3: Title", or bold "**Chapter 3:**" forms.
    heading_re = re.compile(
        r"^\s*(?:#{1,6}\s*|\*{1,3}\s*)?chapter\s+(\d+)\b\s*[:\-\u2013\u2014.)]?\s*(.*?)(?:\*{1,3})?\s*$",
        re.IGNORECASE,
    )

    current: dict[str, Any] | None = None
    body_lines: list[str] = []

    def _flush() -> None:
        if current is None:
            return
        summary = "\n".join(body_lines).strip()
        if summary:
            current["summary"] = summary
        chapter_outlines.append(current)

    for line in text.splitlines():
        match = heading_re.match(line)
        if match:
            _flush()
            number = int(match.group(1))
            title_part = match.group(2).strip().rstrip("*").strip()
            title = (
                f"Chapter {number}: {title_part}" if title_part else f"Chapter {number}"
            )
            current = {
                "chapter_number": number,
                "title": title,
                "summary": "",
            }
            body_lines = []
            continue
        if current is not None:
            body_lines.append(line)

    _flush()

    if chapter_outlines:
        # Trim to wanted_chapters when the model produced more than requested.
        if len(chapter_outlines) > wanted_chapters:
            chapter_outlines = chapter_outlines[:wanted_chapters]
        return chapter_outlines

    summary = stripped[:500]
    return [
        {
            "chapter_number": 1,
            "title": "Chapter 1",
            "summary": summary,
        }
    ]


def _extract_genre(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            return "unknown"
        genre = payload.get("genre") if isinstance(payload, dict) else None
        return genre if isinstance(genre, str) and genre else "unknown"
    return "unknown"


def _extract_themes(text: str) -> list[str]:
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            return []
        themes = payload.get("themes") if isinstance(payload, dict) else None
        if isinstance(themes, list):
            return [theme for theme in themes if isinstance(theme, str)]
    return []


class OutlinePlannerAgent:
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

    async def _stream_prompt(
        self,
        system_prompt: str,
        user_message: str,
        settings: GenerationSettings,
    ) -> str:
        model_config = _build_model_config(
            self.config,
            "initial_outline_writer",
            "openai-compat://default",
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        full_text = ""
        stream = cast(
            AsyncIterator[str],
            self.provider.stream_text(
                messages,
                model_config,
                seed=settings.seed,
            ),
        )
        async for token in stream:
            await self.bus.emit(token)
            full_text += token
        return full_text

    async def run(
        self,
        story_name: str,
        story_prompt: str,
        settings: GenerationSettings,
        feedback: str | None = None,
        base_context: str = "",
        story_elements: str = "",
    ) -> OutlineResult:
        """Generate outline for the story.

        If feedback is provided (REVISE scenario), append it to the prompt
        before calling the generator.
        """
        prompt = story_prompt
        if feedback:
            prompt = f"{story_prompt}\n\n## Revision Feedback\n{feedback}"

        await self.wiki_bus.emit(
            WikiContextEvent(
                phase="outline",
                event_type="entity_match",
                content=f"Assembling outline context for: {story_name}",
            )
        )

        desired_chapters = settings.wanted_chapters
        pacing_variables = _build_outline_pacing_variables(desired_chapters)

        loader = self._loader
        if not settings.expand_outline:
            system_prompt = loader.load_prompt(
                "outline/create_direct",
                variables={
                    "prompt": prompt,
                    "story_elements": story_elements,
                    "base_context": base_context,
                    **pacing_variables,
                },
            )
            full_text = await self._stream_prompt(
                system_prompt,
                "Please generate the complete outline.",
                settings,
            )
            chapter_outlines = _parse_chapter_outlines(
                full_text, settings.wanted_chapters
            )
            return OutlineResult(
                story_name=story_name,
                chapter_outlines=chapter_outlines,
                summary=full_text,
                genre=_extract_genre(full_text),
                themes=_extract_themes(full_text),
                base_context=base_context,
                story_elements=story_elements,
            )

        story_dir = _validate_story_name(story_name, STORIES_DIR)
        outline_dir = story_dir / "outline"
        outline_dir.mkdir(parents=True, exist_ok=True)

        skeleton_prompt = loader.load_prompt(
            "outline/create_skeleton",
            variables={
                "prompt": prompt,
                "story_elements": story_elements,
                "base_context": base_context,
                **pacing_variables,
            },
        )
        skeleton_text = await self._stream_prompt(
            skeleton_prompt,
            "Please generate the complete outline.",
            settings,
        )
        (outline_dir / "skeleton.md").write_text(skeleton_text, encoding="utf-8")

        chapter_outlines = _parse_chapter_outlines(
            skeleton_text, settings.wanted_chapters
        )
        chapter_skeletons = list(chapter_outlines)

        details_dir = outline_dir / "details"
        details_dir.mkdir(parents=True, exist_ok=True)
        chapter_details: list[dict[str, Any]] = []

        for chapter_number in range(1, settings.wanted_chapters + 1):
            detail_file = details_dir / f"chapter_{chapter_number}.md"
            if detail_file.exists():
                detail_text = detail_file.read_text(encoding="utf-8")
                chapter_details.append(
                    {"chapter_number": chapter_number, "detail": detail_text}
                )
                continue

            previous_detail = chapter_details[-1]["detail"] if chapter_details else ""
            detail_prompt = loader.load_prompt(
                "outline/expand_chapter_detail",
                variables={
                    "story_elements": story_elements,
                    "base_context": base_context,
                    "previous_chunks": skeleton_text,
                    "continuity_summary": previous_detail,
                    "chunk_start": str(chapter_number),
                    "total_chapters": str(settings.wanted_chapters),
                },
            )
            detail_text = await self._stream_prompt(
                detail_prompt,
                f"Please expand chapter {chapter_number}.",
                settings,
            )
            detail_file.write_text(detail_text, encoding="utf-8")
            chapter_details.append(
                {"chapter_number": chapter_number, "detail": detail_text}
            )

        strip_prompt = loader.load_prompt(
            "outline/strip_elements",
            variables={"story_elements": skeleton_text},
        )
        stripped_text = await self._stream_prompt(
            strip_prompt,
            "Please strip the outline elements.",
            settings,
        )

        return OutlineResult(
            story_name=story_name,
            chapter_outlines=chapter_outlines,
            summary=skeleton_text,
            genre=_extract_genre(skeleton_text),
            themes=_extract_themes(skeleton_text),
            base_context=base_context,
            story_elements=story_elements,
            chapter_skeletons=chapter_skeletons,
            chapter_details=chapter_details,
            enrichment_suggestions=stripped_text,
        )
