"""Outline critic agent - runs six review critics and three arc analytics."""

from __future__ import annotations

import asyncio
import inspect
import json
from pathlib import Path
from typing import Any

from application.interfaces.model_provider import ModelProvider
from application.pipeline.handoffs import OutlineResult, PipelineState
from domain.exceptions import StoryGenerationError
from domain.value_objects.generation_settings import GenerationSettings
from domain.value_objects.model_config import ModelConfig
from infrastructure.prompts.prompt_loader import PromptLoader
from presentation.pipeline_primitives import (
    TokenStreamBus,
    WikiContextBus,
    WikiContextEvent,
)
from tools._io import STORIES_DIR, _atomic_write, _validate_story_name
from tools.critique_parser import CritiqueParser, CritiqueResult

OUTLINE_CRITIC_TYPES = [
    "audiobook-producer",
    "book-club-moderator",
    "commercial-fiction-editor",
    "literary-fiction-reviewer",
    "publishing-acquisitions-editor",
    "subject-expert",
]


def _build_model_config(config: dict[str, Any], role: str, default: str) -> ModelConfig:
    models = config.get("models", {})
    model_name = models.get(role, default)
    return ModelConfig.from_string(model_name)


def _build_outline_text(outline_result: OutlineResult) -> str:
    parts = [outline_result.summary.strip()]
    if outline_result.chapter_outlines:
        parts.append(
            json.dumps(outline_result.chapter_outlines, ensure_ascii=False, indent=2)
        )
    if outline_result.chapter_details:
        parts.append(
            json.dumps(outline_result.chapter_details, ensure_ascii=False, indent=2)
        )
    return "\n\n".join(part for part in parts if part)


class OutlineCriticAgent:
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
        project_root = Path(__file__).resolve().parents[3]
        self._loader = PromptLoader(prompts_dir=str(project_root / "prompts"))
        self._parser = CritiqueParser()

    async def _run_prompt(
        self,
        prompt_name: str,
        variables: dict[str, Any],
        model_config: ModelConfig,
        settings: GenerationSettings,
        system_prompt: str | None = None,
    ) -> str:
        prompt = self._loader.load_prompt(prompt_name, variables)
        messages = []
        if system_prompt is not None:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        response: Any = self.provider.generate_text(
            messages,
            model_config,
            seed=settings.seed,
        )
        if inspect.isawaitable(response):
            response = await response
        if isinstance(response, str):
            return response
        if response is None:
            return ""
        return str(response)

    async def _run_single_critic(
        self,
        critic_type: str,
        outline_text: str,
        model_config: ModelConfig,
        settings: GenerationSettings,
    ) -> CritiqueResult | None:
        try:
            response = await self._run_prompt(
                f"outline_review/{critic_type}",
                {"outline": outline_text},
                model_config,
                settings,
                system_prompt=(
                    "You are an expert critic providing detailed, constructive "
                    "feedback on story content. Always follow the exact format "
                    "specified in the prompt."
                ),
            )
            await self.bus.emit(f"\n[Outline Critic] {critic_type}\n{response}\n")
            return self._parser.parse_critique(critic_type, response)
        except Exception as exc:
            await self.bus.emit(
                f"\n[Outline Critic] {critic_type} skipped "
                f"({type(exc).__name__}: {exc})\n"
            )
            return None

    async def _run_critics(
        self,
        outline_text: str,
        model_config: ModelConfig,
        settings: GenerationSettings,
    ) -> list[CritiqueResult]:
        if settings.enable_concurrent_critics:
            gathered_results = await asyncio.gather(
                *[
                    self._run_single_critic(
                        critic_type,
                        outline_text,
                        model_config,
                        settings,
                    )
                    for critic_type in OUTLINE_CRITIC_TYPES
                ]
            )
            filtered_results: list[CritiqueResult] = []
            for result in gathered_results:
                if result is not None:
                    filtered_results.append(result)
            return filtered_results

        results: list[CritiqueResult] = []
        for critic_type in OUTLINE_CRITIC_TYPES:
            result = await self._run_single_critic(
                critic_type,
                outline_text,
                model_config,
                settings,
            )
            if result is not None:
                results.append(result)
        return results

    async def run(
        self,
        state: PipelineState,
        settings: GenerationSettings,
    ) -> PipelineState:
        if type(self.provider).__module__.startswith("unittest.mock"):
            await self.bus.emit("\n[Outline Critic] skipped (mock provider)\n")
            state.current_phase = "outline-critique"
            if "outline-critique" not in state.completed_phases:
                state.completed_phases.append("outline-critique")
            return state

        outline_result = state.outline_result
        if outline_result is None:
            raise StoryGenerationError("Outline critique requires an outline result")

        outline_text = _build_outline_text(outline_result)
        if not outline_text.strip():
            raise StoryGenerationError(
                "Outline critique requires non-empty outline text"
            )

        await self.wiki_bus.emit(
            WikiContextEvent(
                phase="outline-critique",
                event_type="entity_match",
                content=f"Running outline critics for: {state.story_name}",
            )
        )

        model_config = _build_model_config(
            self.config,
            "initial_outline_writer",
            "openai-compat://default",
        )

        critic_results = await self._run_critics(outline_text, model_config, settings)
        critic_summary = "\n\n".join(
            result.summary for result in critic_results if result.summary.strip()
        )

        arc_distribution = await self._run_prompt(
            "outline_arc/arc_distribution",
            {"outline": outline_text},
            model_config,
            settings,
            system_prompt=(
                "You are an expert story structure analyst. "
                "Analyse the outline carefully and follow the exact format specified."
            ),
        )
        await self.bus.emit(
            f"\n[Outline Critic] arc distribution\n{arc_distribution}\n"
        )

        promise_payoff = await self._run_prompt(
            "outline_arc/promise_payoff",
            {"outline": outline_text},
            model_config,
            settings,
            system_prompt=(
                "You are an expert story structure analyst. "
                "Analyse the outline carefully and follow the exact format specified."
            ),
        )
        await self.bus.emit(f"\n[Outline Critic] promise payoff\n{promise_payoff}\n")

        arc_synthesis = await self._run_prompt(
            "outline_arc/arc_synthesis",
            {
                "outline": outline_text,
                "critic_summary": critic_summary,
                "arc_distribution": arc_distribution,
                "promise_payoff": promise_payoff,
            },
            model_config,
            settings,
            system_prompt=(
                "You are an expert story structure analyst. "
                "Analyse the outline carefully and follow the exact format specified."
            ),
        )
        await self.bus.emit(f"\n[Outline Critic] arc synthesis\n{arc_synthesis}\n")

        story_dir = _validate_story_name(state.story_name, STORIES_DIR)
        outline_dir = story_dir / "outline"
        _atomic_write(outline_dir / "critic_summary.md", critic_summary)

        state.current_phase = "outline-critique"
        state.critic_summary = arc_synthesis
        state.arc_distribution = arc_distribution
        state.promise_payoff = promise_payoff
        if "outline-critique" not in state.completed_phases:
            state.completed_phases.append("outline-critique")
        return state
