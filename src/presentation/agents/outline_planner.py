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

    async def _run_chunked(
        self,
        story_name: str,
        prompt: str,
        settings: GenerationSettings,
        base_context: str,
        story_elements: str,
        feedback: str = "",
        critic_context: str = "",
    ) -> OutlineResult:
        story_dir = _validate_story_name(story_name, STORIES_DIR)
        outline_dir = story_dir / "outline"
        chunks_dir = outline_dir / "chunks"
        continuity_dir = outline_dir / "continuity"
        chunks_dir.mkdir(parents=True, exist_ok=True)
        continuity_dir.mkdir(parents=True, exist_ok=True)

        desired_chapters = settings.wanted_chapters
        chunk_size = settings.outline_chunk_size
        loader = self._loader
        accumulated_chunks: list[str] = []
        continuity_summary = ""

        windows: list[tuple[int, int]] = []
        start = 1
        while start <= desired_chapters:
            end = min(start + chunk_size - 1, desired_chapters)
            windows.append((start, end))
            start = end + 1

        revision_context = ""
        if feedback or critic_context:
            parts: list[str] = []
            if feedback:
                parts.append(f"## Revision Feedback\n{feedback}")
            if critic_context:
                parts.append(f"## Critique Analysis\n{critic_context}")
            revision_context = "\n\n".join(parts)

        for i, (chunk_start, chunk_end) in enumerate(windows):
            previous_chunks_text = "\n\n".join(accumulated_chunks)
            chunk_prompt = loader.load_prompt(
                "outline/create_chunk",
                variables={
                    "story_elements": story_elements,
                    "base_context": base_context,
                    "chunk_start": str(chunk_start),
                    "chunk_end": str(chunk_end),
                    "total_chapters": str(desired_chapters),
                    "previous_chunks": previous_chunks_text,
                    "continuity_summary": continuity_summary,
                },
            )
            if revision_context:
                chunk_prompt = f"{chunk_prompt}\n\n{revision_context}"
            chunk_text = await self._stream_prompt(
                chunk_prompt,
                f"Please generate the outline for chapters {chunk_start} to {chunk_end}.",
                settings,
            )
            chunk_file = chunks_dir / f"chunk_{chunk_start}_{chunk_end}.md"
            chunk_file.write_text(chunk_text, encoding="utf-8")
            accumulated_chunks.append(chunk_text)

            if i < len(windows) - 1:
                next_start, next_end = windows[i + 1]
                continuity_prompt = loader.load_prompt(
                    "outline/analyze_continuity",
                    variables={
                        "story_elements": story_elements,
                        "base_context": base_context,
                        "enrichment_suggestions": "",
                        "previous_chunks": "\n\n".join(accumulated_chunks),
                        "chunk_start": str(next_start),
                        "chunk_end": str(next_end),
                        "total_chapters": str(desired_chapters),
                        "last_chapter_in_previous": str(chunk_end),
                    },
                )
                continuity_text = await self._stream_prompt(
                    continuity_prompt,
                    f"Please analyze continuity before chapter {next_start}.",
                    settings,
                )
                continuity_file = (
                    continuity_dir / f"continuity_{chunk_start}_{chunk_end}.md"
                )
                continuity_file.write_text(continuity_text, encoding="utf-8")
                continuity_summary = continuity_text
                await self.bus.emit(
                    f"\n\n## Continuity Analysis (after chapter {chunk_end})\n\n{continuity_text}"
                )

        current_scope = "\n\n".join(accumulated_chunks)
        enrichment_prompt = loader.load_prompt(
            "outline/analyze_enrichment",
            variables={
                "story_elements": story_elements,
                "base_context": base_context,
                "character_context": "",
                "setting_context": "",
                "wanted_chapters": str(desired_chapters),
                "current_scope": current_scope,
            },
        )
        if revision_context:
            enrichment_prompt = f"{enrichment_prompt}\n\n{revision_context}"
        enrichment_text = await self._stream_prompt(
            enrichment_prompt,
            "Please analyze enrichment opportunities.",
            settings,
        )
        (outline_dir / "enrichment.md").write_text(enrichment_text, encoding="utf-8")

        chapter_outlines = _parse_chapter_outlines(current_scope, desired_chapters)
        return OutlineResult(
            story_name=story_name,
            chapter_outlines=chapter_outlines,
            summary=current_scope,
            genre=_extract_genre(current_scope),
            themes=_extract_themes(current_scope),
            base_context=base_context,
            story_elements=story_elements,
            enrichment_suggestions=enrichment_text,
        )

    async def run(
        self,
        story_name: str,
        story_prompt: str,
        settings: GenerationSettings,
        feedback: str | None = None,
        base_context: str = "",
        story_elements: str = "",
        critic_context: str = "",
    ) -> OutlineResult:
        """Generate outline for the story.

        If feedback is provided (REVISE scenario), append it to the prompt
        before calling the generator. critic_context (formatted critique output
        from OutlineCriticAgent) is injected alongside the feedback so the LLM
        understands *why* the revision is requested.
        """
        prompt = story_prompt
        if feedback or critic_context:
            parts: list[str] = [story_prompt]
            if feedback:
                parts.append(f"## Revision Feedback\n{feedback}")
            if critic_context:
                parts.append(f"## Critique Analysis\n{critic_context}")
            prompt = "\n\n".join(parts)

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

        if (
            settings.use_chunked_outline_generation
            and settings.wanted_chapters > settings.outline_chunk_size
        ):
            return await self._run_chunked(
                story_name,
                prompt,
                settings,
                base_context,
                story_elements,
                feedback=feedback or "",
                critic_context=critic_context,
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
