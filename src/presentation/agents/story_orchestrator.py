"""Story Orchestrator agent — thin coordinator (largely vestigial)."""

from __future__ import annotations

from typing import Any

from application.interfaces.model_provider import ModelProvider
from presentation.pipeline_primitives import TokenStreamBus, WikiContextBus


class StoryOrchestratorAgent:
    """Thin coordinator agent — largely vestigial in the Python-native architecture.

    In the OpenCode architecture, this was the top-level Markdown agent that
    dispatched other agents via task(). In the Python-native architecture,
    orchestration is handled by the pipeline orchestrator directly. This class
    is retained for API completeness and future extensibility.
    """

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

    async def run(
        self,
        story_name: str,
        story_prompt: str,
    ) -> dict[str, Any]:
        """Return a pipeline execution plan."""
        return {
            "story_name": story_name,
            "prompt_length": len(story_prompt),
            "phases": [
                "init",
                "outline",
                "characters",
                "settings",
                "chapter-loop",
                "final-edit",
                "assembly",
            ],
        }
