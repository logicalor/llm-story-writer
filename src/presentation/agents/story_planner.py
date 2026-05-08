"""Story Planner agent - narrative arc analysis on finalised outline."""

from __future__ import annotations

import json
import re
from typing import Any, AsyncIterator, cast

from application.interfaces.model_provider import ModelProvider
from application.pipeline.handoffs import ArcAnalysisResult, PipelineState
from domain.value_objects.generation_settings import GenerationSettings
from domain.value_objects.model_config import ModelConfig
from infrastructure.prompts.prompt_loader import PromptLoader
from presentation.pipeline_primitives import (
    TokenStreamBus,
    WikiContextBus,
    WikiContextEvent,
)
from tools._io import STORIES_DIR
from tools._persist import read_markdown_ref
from tools.context_assembly import assemble_context, render_recap_as_markdown


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
        state: PipelineState,
        settings: GenerationSettings,
    ) -> ArcAnalysisResult:
        """Analyse narrative arc quality of the finalised outline.

        This phase is advisory - callers must catch exceptions and continue.
        """
        outline_result = state.outline_result
        if outline_result is None:
            raise ValueError("StoryPlannerAgent requires state.outline_result")

        await self.wiki_bus.emit(
            WikiContextEvent(
                phase="narrative-arc",
                event_type="entity_match",
                content=f"Running narrative arc analysis for: {state.story_name}",
            )
        )

        _raw_summary = outline_result.summary
        story_root = STORIES_DIR / state.story_name
        outline_text = (
            read_markdown_ref(story_root, _raw_summary)
            if isinstance(_raw_summary, dict)
            else (_raw_summary or "")
        )
        if outline_result.chapter_outlines:
            outline_text += "\n\n" + json.dumps(
                outline_result.chapter_outlines, ensure_ascii=False, indent=2
            )

        if state.approved_chapters:
            try:
                ctx = assemble_context(
                    state.story_name,
                    scope="outline",
                    focus=outline_text[:800],
                    recap_window=("chapter", 5),
                )
                wiki_context: str = ctx["wiki_snapshot"]
                recap_context: str = render_recap_as_markdown(ctx["recap_snippets"])
            except Exception as exc:  # noqa: BLE001
                await self.wiki_bus.emit(
                    WikiContextEvent(
                        phase="narrative-arc",
                        event_type="retrieval_error",
                        content=f"Context retrieval failed: {exc}",
                    )
                )
                wiki_context = ""
                recap_context = ""
        else:
            wiki_context = ""
            recap_context = ""

        loader = self._loader
        system_prompt = loader.load_prompt(
            "outline/arc_assessment_direct",
            variables={
                "outline": outline_text,
                "critic_summary": state.critic_summary,
                "arc_distribution": state.arc_distribution,
                "promise_payoff": state.promise_payoff,
                "wiki_context": wiki_context,
                "recap_context": recap_context,
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
            story_name=state.story_name,
            arc_assessment=full_text,
            verdict_code=_parse_verdict(full_text),
            overall_score=0.0,
        )
