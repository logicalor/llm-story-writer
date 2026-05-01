"""Chapter Writer agent — generates chapter content scene by scene."""

from __future__ import annotations

import json
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

        character_context_parts: list[str] = []
        setting_context_parts: list[str] = []
        story_dir = STORIES_DIR / story_name
        for entity_type, label, target_list in (
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
                "character_context": "\n".join(character_context_parts),
                "setting_context": "\n".join(setting_context_parts),
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
