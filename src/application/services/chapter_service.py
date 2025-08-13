"""Chapter generation service."""

from typing import List, Optional
from domain.entities.story import Chapter, Outline
from domain.value_objects.generation_settings import GenerationSettings
from domain.exceptions import StoryGenerationError
from config.settings import AppConfig
from ..interfaces.model_provider import ModelProvider
from infrastructure.prompts.prompt_loader import PromptLoader


class ChapterService:
    """Service for generating story chapters."""
    
    def __init__(self, model_provider: ModelProvider, config: AppConfig, prompt_loader: PromptLoader):
        self.model_provider = model_provider
        self.config = config
        self.prompt_loader = prompt_loader 