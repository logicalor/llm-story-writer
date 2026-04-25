"""Chapter Writer agent — generates chapter content scene by scene."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, cast

from application.interfaces.model_provider import ModelProvider
from application.pipeline.handoffs import ChapterDraft, OutlineResult
from domain.value_objects.generation_settings import GenerationSettings
from domain.value_objects.model_config import ModelConfig
from infrastructure.prompts.agent_prompt_loader import load_agent_prompt
from presentation.pipeline_primitives import (
    TokenStreamBus,
    WikiContextBus,
    WikiContextEvent,
)
from tools._io import STORIES_DIR


def _build_model_config(config: dict[str, Any], role: str, default: str) -> ModelConfig:
    models = config.get("models", {})
    model_name = models.get(role, default)
    return ModelConfig.from_string(model_name)


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
        self._system_prompt: str | None = None

    def _get_system_prompt(self) -> str:
        if self._system_prompt is None:
            self._system_prompt = load_agent_prompt("chapter-writer")
        return self._system_prompt

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

        prompt = (
            f"Story: {story_name}\n"
            f"Chapter Number: {chapter_number}\n"
            f"Chapter Title: {title}\n"
            f"Outline Summary:\n{chapter_summary}"
        )
        if feedback:
            prompt = f"{prompt}\n\n## Revision Feedback\n{feedback}"

        # Guard against path traversal
        if ".." in story_name or "/" in story_name or "\\" in story_name:
            raise ValueError(f"Invalid story_name: {story_name!r}")

        context_parts: list[str] = []
        story_dir = STORIES_DIR / story_name
        for entity_type, label in (
            ("characters", "Character"),
            ("settings", "Setting"),
        ):
            entity_dir = story_dir / entity_type
            if not entity_dir.exists():
                continue
            sheets: list[str] = []
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
                    sheets.append(f"- {name}: {summary}")

            if sheets:
                context_parts.append(f"## {label}s\n" + "\n".join(sheets))

        if context_parts:
            prompt = prompt + "\n\n" + "\n\n".join(context_parts)

        await self.wiki_bus.emit(
            WikiContextEvent(
                phase="chapter",
                event_type="entity_match",
                content=f"Assembling chapter {chapter_number} context",
            )
        )

        model_config = _build_model_config(
            self.config,
            "chapter_writer",
            "openai-compat://default",
        )
        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": prompt},
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

        return ChapterDraft(
            story_name=story_name,
            chapter_number=chapter_number,
            title=title,
            content=full_text,
            word_count=len(full_text.split()),
        )
