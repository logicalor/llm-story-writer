"""Outline generation service."""

from typing import Optional
from domain.entities.story import Outline
from domain.value_objects.generation_settings import GenerationSettings
from domain.exceptions import StoryGenerationError
from config.settings import AppConfig
from ..interfaces.model_provider import ModelProvider
from infrastructure.prompts.prompt_loader import PromptLoader


class OutlineService:
    """Service for generating story outlines."""
    
    def __init__(self, model_provider: ModelProvider, config: AppConfig, prompt_loader: PromptLoader):
        self.model_provider = model_provider
        self.config = config
        self.prompt_loader = prompt_loader
    
    async def generate_outline(
        self,
        prompt: str,
        settings: GenerationSettings,
        savepoint_name: Optional[str] = None
    ) -> Outline:
        """Generate a complete story outline."""
        try:
            # Extract story start date
            story_start_date = await self._extract_story_start_date(prompt, settings)
            
            # Extract base context
            base_context = await self._extract_base_context(prompt, settings)
            
            # Generate story elements
            story_elements = await self._generate_story_elements(prompt, settings)
            
            # Generate initial outline
            outline_content = await self._generate_initial_outline(
                prompt, story_elements, base_context, settings
            )
            
            # Generate chapter list
            chapter_list = await self._generate_chapter_list(
                outline_content, base_context, story_elements, settings
            )
            
            # Create outline entity
            outline = Outline(
                content=outline_content,
                story_elements=story_elements,
                chapter_list=chapter_list,
                base_context=base_context,
                story_start_date=story_start_date
            )
            
            return outline
            
        except Exception as e:
            raise StoryGenerationError(f"Failed to generate outline: {e}") from e
    
    async def _extract_story_start_date(self, prompt: str, settings: GenerationSettings) -> str:
        """Extract story start date from prompt."""
        prompt_content = self.prompt_loader.load_prompt(
            "outline/extract_story_start_date",
            variables={"prompt": prompt}
        )
        
        messages = [{"role": "user", "content": prompt_content}]
        
        model_config = self.config.get_model("sanity_model")
        response = await self.model_provider.generate_text(
            messages=messages,
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream
        )
        
        return response.strip()
    
    async def _extract_base_context(self, prompt: str, settings: GenerationSettings) -> str:
        """Extract important base context from prompt."""
        prompt_content = self.prompt_loader.load_prompt(
            "outline/extract_base_context",
            variables={"prompt": prompt}
        )
        
        messages = [{"role": "user", "content": prompt_content}]
        
        model_config = self.config.get_model("initial_outline_writer")
        response = await self.model_provider.generate_text(
            messages=messages,
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream
        )
        
        return response.strip()
    
    async def _generate_story_elements(self, prompt: str, settings: GenerationSettings) -> str:
        """Generate story elements from prompt."""
        prompt_content = self.prompt_loader.load_prompt(
            "outline/generate_story_elements",
            variables={"prompt": prompt}
        )
        
        messages = [{"role": "user", "content": prompt_content}]
        
        model_config = self.config.get_model("initial_outline_writer")
        response = await self.model_provider.generate_text(
            messages=messages,
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream
        )
        
        return response.strip()
    
    async def _generate_initial_outline(
        self,
        prompt: str,
        story_elements: str,
        base_context: str,
        settings: GenerationSettings
    ) -> str:
        """Generate initial story outline."""
        prompt_content = self.prompt_loader.load_prompt(
            "outline/generate_initial_outline",
            variables={
                "prompt": prompt,
                "story_elements": story_elements,
                "base_context": base_context
            }
        )
        
        messages = [{"role": "user", "content": prompt_content}]
        
        model_config = self.config.get_model("initial_outline_writer")
        response = await self.model_provider.generate_text(
            messages=messages,
            model_config=model_config,
            seed=settings.seed,
            min_word_count=500,
            debug=settings.debug,
            stream=settings.stream
        )
        
        return response.strip()
    
    async def _generate_chapter_list(
        self,
        outline: str,
        base_context: str,
        story_elements: str,
        settings: GenerationSettings
    ) -> str:
        """Generate detailed chapter list."""
        prompt_content = self.prompt_loader.load_prompt(
            "outline/generate_chapter_list",
            variables={
                "outline": outline,
                "base_context": base_context,
                "story_elements": story_elements
            }
        )
        
        messages = [{"role": "user", "content": prompt_content}]
        
        model_config = self.config.get_model("chapter_outline_writer")
        response = await self.model_provider.generate_text(
            messages=messages,
            model_config=model_config,
            seed=settings.seed,
            min_word_count=300,
            debug=settings.debug,
            stream=settings.stream
        )
        
        return response.strip() 