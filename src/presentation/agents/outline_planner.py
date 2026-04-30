"""Outline Planner agent — transforms story prompt into structured outline."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, cast

from application.interfaces.model_provider import ModelProvider
from application.pipeline.handoffs import OutlineResult
from domain.value_objects.generation_settings import GenerationSettings
from domain.value_objects.model_config import ModelConfig
from infrastructure.prompts.agent_prompt_loader import load_agent_prompt  # noqa: F401
from infrastructure.prompts.prompt_loader import PromptLoader
from presentation.pipeline_primitives import (
    TokenStreamBus,
    WikiContextBus,
    WikiContextEvent,
)


def _build_model_config(config: dict[str, Any], role: str, default: str) -> ModelConfig:
    models = config.get("models", {})
    model_name = models.get(role, default)
    return ModelConfig.from_string(model_name)


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
    for index, line in enumerate(text.splitlines(), start=1):
        normalized = line.strip()
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered.startswith("chapter"):
            title = normalized.split(":", 1)[0].strip()
            summary = (
                normalized.split(":", 1)[1].strip() if ":" in normalized else normalized
            )
            chapter_outlines.append(
                {
                    "chapter_number": index,
                    "title": title,
                    "summary": summary,
                }
            )
        if len(chapter_outlines) >= wanted_chapters:
            break

    if chapter_outlines:
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
        self._system_prompt: str | None = None

    def _get_system_prompt(self) -> str:
        if self._system_prompt is None:
            loader = PromptLoader(prompts_dir="prompts")
            self._system_prompt = loader.load_prompt("outline/create_direct")
        return self._system_prompt

    async def run(
        self,
        story_name: str,
        story_prompt: str,
        settings: GenerationSettings,
        feedback: str | None = None,
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
        early_chapters = max(1, int(desired_chapters * 0.25))
        rising_start = early_chapters + 1
        rising_end = max(rising_start, int(desired_chapters * 0.75))
        climax_start = max(rising_end + 1, int(desired_chapters * 0.75) + 1)
        climax_end = max(climax_start, int(desired_chapters * 0.90))
        resolution_start = climax_end + 1

        loader = PromptLoader(prompts_dir="prompts")
        system_prompt = loader.load_prompt(
            "outline/create_direct",
            variables={
                "prompt": prompt,
                "desired_chapters": str(desired_chapters),
                "story_elements": "",
                "base_context": "",
                "early_chapters": str(early_chapters),
                "rising_start": str(rising_start),
                "rising_end": str(rising_end),
                "climax_start": str(climax_start),
                "climax_end": str(climax_end),
                "resolution_start": str(resolution_start),
            },
        )

        model_config = _build_model_config(
            self.config,
            "initial_outline_writer",
            "openai-compat://default",
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Please generate the complete outline."},
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

        chapter_outlines = _parse_chapter_outlines(full_text, settings.wanted_chapters)

        return OutlineResult(
            story_name=story_name,
            chapter_outlines=chapter_outlines,
            summary=full_text[:1000],
            genre=_extract_genre(full_text),
            themes=_extract_themes(full_text),
        )
