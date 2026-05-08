"""Chapter Outline Expander agent - expands a skeleton chapter into a detailed outline."""

from __future__ import annotations

from typing import Any, AsyncIterator, cast

from application.interfaces.model_provider import ModelProvider
from domain.value_objects.model_config import ModelConfig
from infrastructure.prompts.prompt_loader import PromptLoader
from presentation.pipeline_primitives import (
    TokenStreamBus,
    WikiContextBus,
    WikiContextEvent,
)
from tools.context_assembly import assemble_context, render_recap_as_markdown


def _build_model_config(config: dict[str, Any], role: str, default: str) -> ModelConfig:
    models = config.get("models", {})
    model_name = models.get(role, default)
    return ModelConfig.from_string(model_name)


class ChapterOutlineExpanderAgent:
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
        chapter_outline: str,
        story_elements: str = "",
        previous_chunks: str = "",
        continuity_summary: str = "",
        total_chapters: int = 0,
        protagonist: str | None = None,
    ) -> str:
        """Expand a skeleton chapter outline into a detailed chapter outline.

        Returns the expanded detail text as a string.
        """
        await self.wiki_bus.emit(
            WikiContextEvent(
                phase="outline-expansion",
                event_type="entity_match",
                content=f"Expanding chapter {chapter_number} outline",
            )
        )

        try:
            ctx = assemble_context(
                story_name,
                scope="outline",
                focus=chapter_outline[:500],
                chapter=chapter_number,
                pov_character=protagonist,
                recap_window=("character", 3),
            )
            wiki_context: str = ctx["wiki_snapshot"]
            recap_context: str = render_recap_as_markdown(ctx["recap_snippets"])
        except Exception as exc:  # noqa: BLE001
            await self.wiki_bus.emit(
                WikiContextEvent(
                    phase="outline-expansion",
                    event_type="retrieval_error",
                    content=f"Context retrieval failed: {exc}",
                )
            )
            wiki_context = ""
            recap_context = ""

        loader = self._loader
        system_prompt = loader.load_prompt(
            "outline/expand_chapter_detail",
            variables={
                "story_elements": story_elements,
                "base_context": "",
                "previous_chunks": previous_chunks,
                "continuity_summary": continuity_summary,
                "chunk_start": str(chapter_number),
                "total_chapters": str(total_chapters or chapter_number),
                "wiki_context": wiki_context,
                "recap_context": recap_context,
            },
        )

        model_config = _build_model_config(
            self.config,
            "initial_outline_writer",
            "openai-compat://default",
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Please expand chapter {chapter_number}.",
            },
        ]

        full_text = ""
        stream = cast(
            AsyncIterator[str],
            self.provider.stream_text(messages, model_config),
        )
        async for token in stream:
            await self.bus.emit(token)
            full_text += token

        return full_text
