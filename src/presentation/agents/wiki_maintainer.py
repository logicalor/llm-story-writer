"""Wiki Maintainer agent — updates wiki pages after chapter completion."""

from __future__ import annotations

import asyncio

from typing import Any

from application.interfaces.model_provider import ModelProvider
from application.pipeline.handoffs import WikiUpdateBatch
from domain.value_objects.model_config import ModelConfig
from presentation.pipeline_primitives import (
    TokenStreamBus,
    WikiContextBus,
    WikiContextEvent,
)
from tools.wiki_extract import update_wiki_from_chapter


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
        # Retained for constructor interface compatibility with orchestrator; not active in run().
        self.provider = provider
        self.config = config
        # Retained for constructor interface compatibility with orchestrator; not active in run().
        self.bus = bus
        self.wiki_bus = wiki_bus

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
        base_url: str | None = (
            f"http://{model_config.host}/v1" if model_config.host else None
        )

        try:
            summary = await asyncio.to_thread(
                update_wiki_from_chapter,
                story_name,
                chapter_number,
                chapter_content,
                model=model_config.name,
                base_url=base_url,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Wiki update failed for story={story_name!r} chapter={chapter_number}: {exc}"
            ) from exc

        new_slugs: list[str] = summary.get("new_slugs", [])
        updated_slugs: list[str] = summary.get("updated_slugs", [])

        for slug in new_slugs:
            await self.wiki_bus.emit(
                WikiContextEvent(
                    phase="wiki",
                    event_type="entity_match",
                    content=f"Created wiki page: {slug}",
                    metadata={"slug": slug, "action": "create"},
                )
            )

        for slug in updated_slugs:
            await self.wiki_bus.emit(
                WikiContextEvent(
                    phase="wiki",
                    event_type="entity_match",
                    content=f"Updated wiki page: {slug}",
                    metadata={"slug": slug, "action": "update"},
                )
            )

        return WikiUpdateBatch(
            story_name=story_name,
            chapter_number=chapter_number,
            updated_pages=updated_slugs,
            new_pages=new_slugs,
            savepoint_id=None,
        )
