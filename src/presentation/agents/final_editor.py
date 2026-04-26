"""Final Editor agent - post-assembly prose pass for voice and pacing."""

from __future__ import annotations

from typing import Any, AsyncIterator, cast

from application.interfaces.model_provider import ModelProvider
from application.pipeline.handoffs import ChapterDraft, FinalEditResult
from domain.value_objects.generation_settings import GenerationSettings
from domain.value_objects.model_config import ModelConfig
from infrastructure.prompts.agent_prompt_loader import load_agent_prompt
from presentation.pipeline_primitives import (
    TokenStreamBus,
    WikiContextBus,
    WikiContextEvent,
)


def _build_model_config(config: dict[str, Any], role: str, default: str) -> ModelConfig:
    models = config.get("models", {})
    model_name = models.get(role, default)
    return ModelConfig.from_string(model_name)


class FinalEditorAgent:
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
            self._system_prompt = load_agent_prompt("final-editor")
        return self._system_prompt

    async def run(
        self,
        story_name: str,
        approved_chapters: list[ChapterDraft],
        settings: GenerationSettings,
    ) -> FinalEditResult:
        """Perform a prose editing pass over each approved chapter.

        Each chapter is passed individually to the LLM with the final-editor
        system prompt. The returned text replaces the chapter content. If the
        LLM returns an empty response, the original content is preserved.
        """
        model_config = _build_model_config(
            self.config, "chapter_writer", "openai-compat://default"
        )
        system_prompt = self._get_system_prompt()
        edited_chapters: list[ChapterDraft] = []

        for draft in approved_chapters:
            await self.wiki_bus.emit(
                WikiContextEvent(
                    phase="final-edit",
                    event_type="entity_match",
                    content=f"Final editing chapter {draft.chapter_number} of {story_name}",
                )
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"## Chapter {draft.chapter_number}: {draft.title}\n\n"
                        f"{draft.content}"
                    ),
                },
            ]

            full_text = ""
            stream = cast(
                AsyncIterator[str],
                self.provider.stream_text(messages, model_config, seed=settings.seed),
            )
            async for token in stream:
                await self.bus.emit(token)
                full_text += token

            edited_content = full_text.strip() if full_text.strip() else draft.content
            edited_chapters.append(
                ChapterDraft(
                    story_name=draft.story_name,
                    chapter_number=draft.chapter_number,
                    title=draft.title,
                    content=edited_content,
                    word_count=len(edited_content.split()),
                )
            )

        return FinalEditResult(
            story_name=story_name,
            chapters_processed=len(edited_chapters),
            total_issues_found=0,
            total_revisions_made=len(edited_chapters),
            edited_chapters=edited_chapters,
        )
