"""Wiki Maintainer agent — updates wiki pages after chapter completion."""

from __future__ import annotations

from typing import Any, AsyncIterator, cast

from application.interfaces.model_provider import ModelProvider
from application.pipeline.handoffs import WikiUpdateBatch
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


class WikiMaintainerAgent:
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
            self._system_prompt = load_agent_prompt("wiki-maintainer")
        return self._system_prompt

    async def run(
        self,
        story_name: str,
        chapter_number: int,
        chapter_content: str,
    ) -> WikiUpdateBatch:
        await self.wiki_bus.emit(
            WikiContextEvent(
                phase="wiki",
                event_type="wikilink_traversal",
                content=f"Processing chapter {chapter_number} wiki updates",
            )
        )

        model_config = _build_model_config(
            self.config,
            "eval_model",
            "openai-compat://default",
        )
        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {
                "role": "user",
                "content": (
                    f"Story: {story_name}\nChapter: {chapter_number}\n"
                    f"Chapter Content:\n{chapter_content[:4000]}"
                ),
            },
        ]

        stream = cast(
            AsyncIterator[str],
            self.provider.stream_text(messages, model_config),
        )
        async for token in stream:
            await self.bus.emit(token)

        return WikiUpdateBatch(
            story_name=story_name,
            chapter_number=chapter_number,
            updated_pages=[],
            new_pages=[],
            savepoint_id=None,
        )
