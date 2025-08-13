"""Story info generation service."""

from typing import List
from domain.entities.story import StoryInfo, Outline, Chapter
from domain.value_objects.generation_settings import GenerationSettings
from domain.exceptions import StoryGenerationError
from config.settings import AppConfig
from ..interfaces.model_provider import ModelProvider
from infrastructure.prompts.prompt_loader import PromptLoader


class StoryInfoService:
    """Service for generating story metadata."""
    
    def __init__(self, model_provider: ModelProvider, config: AppConfig, prompt_loader: PromptLoader):
        self.model_provider = model_provider
        self.config = config
        self.prompt_loader = prompt_loader
    
    async def generate_story_info(
        self,
        outline: Outline,
        chapters: List[Chapter],
        settings: GenerationSettings
    ) -> StoryInfo:
        """Generate story metadata."""
        try:
            # Generate title
            title = await self._generate_title(outline, chapters, settings)
            
            # Generate summary
            summary = await self._generate_summary(outline, chapters, settings)
            
            # Generate tags
            tags = await self._generate_tags(outline, chapters, settings)
            
            # Create story info
            story_info = StoryInfo(
                title=title,
                summary=summary,
                tags=tags
            )
            
            return story_info
            
        except Exception as e:
            raise StoryGenerationError(f"Failed to generate story info: {e}") from e
    
    async def _generate_title(
        self,
        outline: Outline,
        chapters: List[Chapter],
        settings: GenerationSettings
    ) -> str:
        """Generate a title for the story."""
        # Use first chapter content for context
        first_chapter_content = chapters[0].content if chapters else ""
        
        prompt_content = self.prompt_loader.load_prompt(
            "outline-chapter/outline/create_title",
            variables={
                "outline": outline.content,
                "first_chapter": first_chapter_content[:1000] + "..."
            }
        )
        
        messages = [{"role": "user", "content": prompt_content}]
        
        model_config = self.config.get_model("info_model")
        response = await self.model_provider.generate_text(
            messages=messages,
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream
        )
        
        return response.strip()
    
    async def _generate_summary(
        self,
        outline: Outline,
        chapters: List[Chapter],
        settings: GenerationSettings
    ) -> str:
        """Generate a summary for the story."""
        # Use first few chapters for context
        chapter_content = "\n\n".join([ch.content[:500] for ch in chapters[:3]])
        
        prompt_content = self.prompt_loader.load_prompt(
            "outline-chapter/outline/create_summary",
            variables={
                "outline": outline.content,
                "chapter_content": chapter_content
            }
        )
        
        messages = [{"role": "user", "content": prompt_content}]
        
        model_config = self.config.get_model("info_model")
        response = await self.model_provider.generate_text(
            messages=messages,
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream
        )
        
        return response.strip()
    
    async def _generate_tags(
        self,
        outline: Outline,
        chapters: List[Chapter],
        settings: GenerationSettings
    ) -> List[str]:
        """Generate tags for the story."""
        # Use first chapter for context
        first_chapter_content = chapters[0].content if chapters else ""
        
        prompt_content = self.prompt_loader.load_prompt(
            "outline-chapter/outline/create_tags",
            variables={
                "outline": outline.content,
                "first_chapter": first_chapter_content[:1000] + "..."
            }
        )
        
        messages = [{"role": "user", "content": prompt_content}]
        
        model_config = self.config.get_model("info_model")
        response = await self.model_provider.generate_json(
            messages=messages,
            model_config=model_config,
            required_attributes=[],
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream
        )
        
        # Handle different response formats
        if isinstance(response, dict) and "tags" in response:
            tags = response["tags"]
        elif isinstance(response, list):
            tags = response
        else:
            # Fallback: extract tags from response
            tags = []
            if isinstance(response, dict):
                for key, value in response.items():
                    if isinstance(value, list):
                        tags.extend(value)
                    elif isinstance(value, str):
                        tags.append(value)
        
        # Ensure tags are strings and clean them up
        tags = [str(tag).strip().lower() for tag in tags if tag]
        return tags[:10]  # Limit to 10 tags 