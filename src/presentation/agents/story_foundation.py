"""Story Foundation agent - extracts early prompt context before outlining."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from application.interfaces.model_provider import ModelProvider
from application.pipeline.handoffs import OutlineResult
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


class StoryFoundationAgent:
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

    async def _generate_section(
        self,
        prompt_name: str,
        story_prompt: str,
        model_config: ModelConfig,
        settings: GenerationSettings,
    ) -> str:
        try:
            prompt = self._loader.load_prompt(prompt_name, {"prompt": story_prompt})
            response = await self.provider.generate_text(
                [{"role": "user", "content": prompt}],
                model_config,
                seed=settings.seed,
            )
        except Exception:
            return ""

        if response:
            await self.bus.emit(response)
        return response

    async def run(
        self,
        story_name: str,
        story_prompt: str,
        settings: GenerationSettings,
    ) -> OutlineResult:
        await self.bus.emit(
            f"\n[Foundation] Extracting story foundation for: {story_name}\n"
        )
        await self.wiki_bus.emit(
            WikiContextEvent(
                phase="story-foundation",
                event_type="entity_match",
                content=f"Extracting story foundation for: {story_name}",
            )
        )

        model_config = _build_model_config(
            self.config,
            "story_foundation",
            "openai-compat://default",
        )
        base_context = await self._generate_section(
            "extract_base_context",
            story_prompt,
            model_config,
            settings,
        )
        story_start_date = await self._generate_section(
            "extract_story_start_date",
            story_prompt,
            model_config,
            settings,
        )
        story_elements = await self._generate_section(
            "outline/create_elements",
            story_prompt,
            model_config,
            settings,
        )
        style_guide = await self._generate_section(
            "story/extract_style_guide",
            story_prompt,
            model_config,
            settings,
        )

        return OutlineResult(
            story_name=story_name,
            chapter_outlines=[],
            summary="",
            genre="",
            themes=[],
            base_context=base_context,
            story_start_date=story_start_date,
            story_elements=story_elements,
            style_guide=style_guide,
        )
