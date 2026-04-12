"""Abstract story writing strategy interface."""

from abc import ABC, abstractmethod
from typing import List, Optional
from domain.entities.story import Story, Outline, Chapter, StoryInfo
from domain.value_objects.generation_settings import GenerationSettings
from ..interfaces.model_provider import ModelProvider


class StoryStrategy(ABC):
    """Abstract interface for story writing strategies."""
    
    def __init__(self, model_provider: ModelProvider):
        self.model_provider = model_provider
    
    @abstractmethod
    async def generate_outline(self, prompt: str, settings: GenerationSettings) -> Outline:
        """Generate story outline from prompt."""
        pass
    
    @abstractmethod
    async def generate_chapters(self, outline: Outline, settings: GenerationSettings) -> List[Chapter]:
        """Generate chapters from outline."""
        pass
    
    @abstractmethod
    async def generate_story_info(self, outline: Outline, chapters: List[Chapter], settings: GenerationSettings) -> StoryInfo:
        """Generate story metadata."""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get the name of this strategy."""
        pass
    
    @abstractmethod
    def get_strategy_version(self) -> str:
        """Get the version of this strategy."""
        pass
    
    @abstractmethod
    def get_strategy_description(self) -> str:
        """Get a description of this strategy."""
        pass
    
    @abstractmethod
    def get_required_models(self) -> List[str]:
        """Get list of required model names for this strategy."""
        pass
    
    @abstractmethod
    def get_prompt_directory(self) -> str:
        """Get the directory containing prompts for this strategy."""
        pass 