"""Recap writer agent - generates chapter recap artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from application.interfaces.model_provider import ModelProvider
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


class RecapWriterAgent:
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

    async def _run_stage(
        self,
        prompt_name: str,
        variables: dict[str, Any],
        model_config: ModelConfig,
        settings: GenerationSettings,
    ) -> str:
        try:
            prompt = self._loader.load_prompt(prompt_name, variables)
            response = await self.provider.generate_text(
                [{"role": "user", "content": prompt}],
                model_config,
                seed=settings.seed,
            )
        except Exception:
            return ""

        if isinstance(response, str):
            output = response
        else:
            output = json.dumps(response, ensure_ascii=False)

        if output:
            await self.bus.emit(output)
        return output

    async def _emit_stage(self, chapter_number: int, stage_name: str) -> None:
        await self.bus.emit(f"\n[Recap] Chapter {chapter_number} — {stage_name}\n")

    async def run(
        self,
        story_name: str,
        chapter_number: int,
        chapter_content: str,
        previous_recap: str,
        story_start_date: str,
        settings: GenerationSettings,
    ) -> dict[str, Any]:
        await self.wiki_bus.emit(
            WikiContextEvent(
                phase="recap",
                event_type="entity_match",
                content=(f"Generating recap for {story_name} chapter {chapter_number}"),
            )
        )

        model_config = _build_model_config(
            self.config,
            "recap_writer",
            "openai-compat://default",
        )

        await self._emit_stage(chapter_number, "extract chapter events")
        events = await self._run_stage(
            "extract_chapter_events",
            {
                "chapter_content": chapter_content,
                "previous_chapter_recap": previous_recap,
            },
            model_config,
            settings,
        )
        if not events:
            return {"events": "", "compact": "", "sanitised": ""}

        if not settings.use_multi_stage_recap_sanitizer:
            await self._emit_stage(chapter_number, "format json")
            compact = await self._run_stage(
                "recap/format_json",
                {"enriched_events": events},
                model_config,
                settings,
            )
            return {
                "events": events,
                "compact": compact,
                "sanitised": compact,
            }

        await self._emit_stage(chapter_number, "assign event timing")
        timed_events = await self._run_stage(
            "recap/assign_event_timing",
            {
                "events": events,
                "story_start_date": story_start_date,
                "previous_chapter_recap": previous_recap,
            },
            model_config,
            settings,
        )

        await self._emit_stage(chapter_number, "enrich event details")
        enriched_events = await self._run_stage(
            "recap/enrich_event_details",
            {"timed_events": timed_events},
            model_config,
            settings,
        )

        await self._emit_stage(chapter_number, "format json")
        formatted = await self._run_stage(
            "recap/format_json",
            {"enriched_events": enriched_events},
            model_config,
            settings,
        )

        await self._emit_stage(chapter_number, "compact events")
        compact = await self._run_stage(
            "recap/compact_events",
            {"events_json": formatted},
            model_config,
            settings,
        )

        sanitised = compact
        if settings.use_improved_recap_sanitizer:
            await self._emit_stage(chapter_number, "sanitize")
            sanitised = await self._run_stage(
                "recap/sanitize",
                {
                    "recap": compact,
                    "story_start_date": story_start_date,
                    "previous_chapter_recap": previous_recap,
                },
                model_config,
                settings,
            )

        return {
            "events": events,
            "compact": compact,
            "sanitised": sanitised,
        }
