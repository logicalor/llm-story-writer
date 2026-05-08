"""Quality Reviewer agent - runs multi-perspective chapter critiques."""

from __future__ import annotations

from typing import Any, AsyncIterator, cast

from application.interfaces.model_provider import ModelProvider
from application.pipeline.handoffs import OutlineResult
from domain.value_objects.model_config import ModelConfig
from infrastructure.prompts.prompt_loader import PromptLoader
from presentation.pipeline_primitives import (
    TokenStreamBus,
    WikiContextBus,
    WikiContextEvent,
)
from tools.context_assembly import assemble_context, render_recap_as_markdown


_CRITIQUE_PROMPTS: list[tuple[str, str]] = [
    ("commercial-fiction-editor", "chapter_review/commercial-fiction-editor"),
    ("chapter-pacing", "chapter_review/chapter-pacing"),
    (
        "chapter-character-consistency",
        "chapter_review/chapter-character-consistency",
    ),
    (
        "character-voice-consistency",
        "chapter_review/character-voice-consistency",
    ),
]


def _build_model_config(config: dict[str, Any], role: str, default: str) -> ModelConfig:
    models = config.get("models", {})
    model_name = models.get(role, default)
    return ModelConfig.from_string(model_name)


class QualityReviewerAgent:
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
        chapter_content: str,
        outline_result: OutlineResult | None = None,
    ) -> list[dict[str, Any]]:
        """Run multi-perspective quality review for a chapter.

        Returns a list of critique dicts, one per perspective.
        """
        _ = outline_result

        await self.wiki_bus.emit(
            WikiContextEvent(
                phase="quality-review",
                event_type="detail_level",
                content=f"Running quality review for chapter {chapter_number}",
            )
        )

        try:
            ctx = assemble_context(
                story_name,
                scope="consistency",
                focus=chapter_content[:500],
                chapter=chapter_number,
                recap_window=("chapter", 3),
            )
            wiki_context: str = ctx["wiki_snapshot"]
            recap_context: str = render_recap_as_markdown(ctx["recap_snippets"])
        except Exception as exc:  # noqa: BLE001
            await self.wiki_bus.emit(
                WikiContextEvent(
                    phase="quality-review",
                    event_type="retrieval_error",
                    content=f"Context retrieval failed: {exc}",
                )
            )
            wiki_context = ""
            recap_context = ""

        model_config = _build_model_config(
            self.config,
            "checker_model",
            "openai-compat://default",
        )
        loader = self._loader
        results: list[dict[str, Any]] = []

        for critique_type, prompt_key in _CRITIQUE_PROMPTS:
            system_prompt = loader.load_prompt(
                prompt_key,
                variables={
                    "outline": chapter_content,
                    "wiki_context": wiki_context,
                    "recap_context": recap_context,
                },
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Please provide your critique."},
            ]

            full_text = ""
            stream = cast(
                AsyncIterator[str],
                self.provider.stream_text(messages, model_config),
            )
            async for token in stream:
                await self.bus.emit(token)
                full_text += token

            results.append({"critique_type": critique_type, "text": full_text})

        return results
