"""Final Editor agent - post-assembly prose pass for voice and pacing."""

from __future__ import annotations

from typing import Any, AsyncIterator, cast

from application.interfaces.model_provider import ModelProvider
from application.pipeline.handoffs import ChapterDraft, FinalEditResult
from domain.value_objects.generation_settings import GenerationSettings
from domain.value_objects.model_config import ModelConfig
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
        self._loader = PromptLoader(prompts_dir="prompts")

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
        edited_chapters: list[ChapterDraft] = []
        loader = self._loader

        # Pre-build a per-chapter prior summary so chapter N only sees
        # chapters 1..N-1 (no leakage of later chapters into the edit pass).
        per_chapter_prior_summary: dict[int, str] = {}
        running_summaries: list[str] = []
        for draft in approved_chapters:
            per_chapter_prior_summary[draft.chapter_number] = "\n".join(
                running_summaries
            )
            running_summaries.append(
                f"Chapter {draft.chapter_number}: {draft.title} — "
                f"{draft.content[:200].replace(chr(10), ' ')}..."
            )

        for draft in approved_chapters:
            await self.wiki_bus.emit(
                WikiContextEvent(
                    phase="final-edit",
                    event_type="entity_match",
                    content=f"Final editing chapter {draft.chapter_number} of {story_name}",
                )
            )

            prior_chapters_summary = per_chapter_prior_summary.get(
                draft.chapter_number, ""
            )

            system_prompt = loader.load_prompt(
                "final_edit/edit_chapter_direct",
                variables={
                    "chapter_text": draft.content,
                    "chapter_number": str(draft.chapter_number),
                    "chapter_title": draft.title,
                    "prior_chapters_summary": prior_chapters_summary,
                },
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Return the polished chapter."},
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
