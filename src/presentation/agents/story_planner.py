"""Story Planner agent - narrative arc analysis on finalised outline."""

from __future__ import annotations

import json
import re
from typing import Any, AsyncIterator, cast

from application.interfaces.model_provider import ModelProvider
from application.pipeline.handoffs import ArcAnalysisResult, OutlineResult
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


def _parse_verdict(text: str) -> str:
    """Extract verdict_code from arc assessment text."""
    lowered = text.lower()
    sig_match = re.search(
        r"\bsignificant\s+(?:issues?|problems?|flaws?|concerns?)\b", lowered
    )
    if sig_match:
        window_start = max(0, sig_match.start() - 25)
        preceding = lowered[window_start : sig_match.start()]
        if not re.search(r"\b(?:no|not|without|few|minimal|any)\b", preceding):
            return "significant_issues"
    if re.search(r"\bminor\b|\bconcerns?\b", lowered):
        return "minor_concerns"
    return "strong"


class StoryPlannerAgent:
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
        outline_result: OutlineResult,
        settings: GenerationSettings,
    ) -> ArcAnalysisResult:
        """Analyse narrative arc quality of the finalised outline.

        This phase is advisory - callers must catch exceptions and continue.
        """
        await self.wiki_bus.emit(
            WikiContextEvent(
                phase="narrative-arc",
                event_type="entity_match",
                content=f"Running narrative arc analysis for: {story_name}",
            )
        )

        outline_text = outline_result.summary
        if outline_result.chapter_outlines:
            outline_text += "\n\n" + json.dumps(
                outline_result.chapter_outlines, ensure_ascii=False, indent=2
            )

        loader = self._loader
        system_prompt = loader.load_prompt(
            "outline/arc_assessment_direct",
            variables={
                "outline": outline_text,
                "critic_summary": "",
                "arc_distribution": "",
                "promise_payoff": "",
            },
        )

        model_config = _build_model_config(
            self.config, "initial_outline_writer", "openai-compat://default"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Provide your assessment."},
        ]

        full_text = ""
        stream = cast(
            AsyncIterator[str],
            self.provider.stream_text(messages, model_config, seed=settings.seed),
        )
        async for token in stream:
            await self.bus.emit(token)
            full_text += token

        return ArcAnalysisResult(
            story_name=story_name,
            arc_assessment=full_text,
            verdict_code=_parse_verdict(full_text),
            overall_score=0.0,
        )
