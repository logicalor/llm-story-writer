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
    
    async def generate_chapters(
        self,
        outline: Outline,
        settings: GenerationSettings,
        savepoint_name: Optional[str] = None
    ) -> List[Chapter]:
        """Generate all chapters for a story."""
        try:
            # Determine number of chapters
            num_chapters = await self._count_chapters(outline.content, settings)
            
            chapters = []
            for chapter_num in range(1, num_chapters + 1):
                chapter = await self._generate_chapter(
                    chapter_num=chapter_num,
                    total_chapters=num_chapters,
                    outline=outline,
                    previous_chapters=chapters,
                    settings=settings,
                    savepoint_name=savepoint_name
                )
                chapters.append(chapter)
            
            return chapters
            
        except Exception as e:
            raise StoryGenerationError(f"Failed to generate chapters: {e}") from e
    
    async def _count_chapters(self, outline: str, settings: GenerationSettings) -> int:
        """Count the number of chapters in the outline."""
        prompt_content = self.prompt_loader.load_prompt(
            "outline-chapter/count_chapters",
            variables={"outline": outline}
        )
        
        messages = [{"role": "user", "content": prompt_content}]
        
        model_config = self.config.get_model("logical_model")
        response = await self.model_provider.generate_json(
            messages=messages,
            model_config=model_config,
            required_attributes=["TotalChapters"],
            seed=settings.seed
        )
        
        # Handle both JSON object and direct integer responses
        if isinstance(response, dict) and "TotalChapters" in response:
            return response["TotalChapters"]
        elif isinstance(response, int):
            return response
        else:
            # Try to parse as integer if it's a string
            try:
                return int(str(response))
            except (ValueError, TypeError):
                raise StoryGenerationError(f"Invalid response format for chapter count: {response}")
    

    
    async def _generate_chapter(
        self,
        chapter_num: int,
        total_chapters: int,
        outline: Outline,
        previous_chapters: List[Chapter],
        settings: GenerationSettings,
        savepoint_name: Optional[str] = None
    ) -> Chapter:
        """Generate a single chapter."""
        try:
            # Get chapter outline
            chapter_outline = await self._get_chapter_outline(
                chapter_num, outline.content, settings
            )
            
            # Get previous chapter recap
            previous_recap = await self._get_previous_chapter_recap(
                chapter_num, previous_chapters, outline, settings
            )
            
            # Get next chapter outline
            next_chapter_outline = await self._get_next_chapter_outline(
                chapter_num, total_chapters, outline, settings
            )
            
            # Generate chapter content
            content = await self._generate_chapter_content(
                chapter_num=chapter_num,
                total_chapters=total_chapters,
                chapter_outline=chapter_outline,
                previous_recap=previous_recap,
                next_chapter_outline=next_chapter_outline,
                outline=outline,
                settings=settings
            )
            
            # Generate chapter title
            title = await self._generate_chapter_title(
                chapter_num, content, chapter_outline, settings
            )
            
            # Create chapter entity
            chapter = Chapter(
                number=chapter_num,
                title=title,
                content=content,
                outline=chapter_outline
            )
            
            return chapter
            
        except Exception as e:
            raise StoryGenerationError(f"Failed to generate chapter {chapter_num}: {e}") from e
    
    async def _get_chapter_outline(
        self,
        chapter_num: int,
        outline: str,
        settings: GenerationSettings
    ) -> str:
        """Get outline for specific chapter."""
        prompt_content = self.prompt_loader.load_prompt(
            "outline-chapter/get_chapter_outline",
            variables={
                "chapter_num": chapter_num,
                "outline": outline
            }
        )
        
        messages = [{"role": "user", "content": prompt_content}]
        
        model_config = self.config.get_model("chapter_outline_writer")
        response = await self.model_provider.generate_text(
            messages=messages,
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream
        )
        
        return response.strip()
    
    async def _get_previous_chapter_recap(
        self,
        chapter_num: int,
        previous_chapters: List[Chapter],
        outline: Outline,
        settings: GenerationSettings
    ) -> str:
        """Generate recap of previous chapter."""
        if chapter_num <= 1 or not previous_chapters:
            return ""
        
        last_chapter = previous_chapters[-1]
        
        prompt_content = self.prompt_loader.load_prompt(
            "outline-chapter/get_previous_chapter_recap",
            variables={
                "chapter_num": chapter_num,
                "outline": outline.content,
                "previous_chapter": last_chapter.content
            }
        )
        
        messages = [{"role": "user", "content": prompt_content}]
        
        model_config = self.config.get_model("chapter_outline_writer")
        response = await self.model_provider.generate_text(
            messages=messages,
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream
        )
        
        return response.strip()
    
    async def _get_next_chapter_outline(
        self,
        chapter_num: int,
        total_chapters: int,
        outline: Outline,
        settings: GenerationSettings
    ) -> str:
        """Get outline for next chapter."""
        if chapter_num >= total_chapters:
            return ""
        
        return await self._get_chapter_outline(chapter_num + 1, outline.content, settings)
    
    async def _generate_chapter_content(
        self,
        chapter_num: int,
        total_chapters: int,
        chapter_outline: str,
        previous_recap: str,
        next_chapter_outline: str,
        outline: Outline,
        settings: GenerationSettings
    ) -> str:
        """Generate the actual chapter content."""
        prompt_content = self.prompt_loader.load_prompt(
            "outline-chapter/generate_chapter_content",
            variables={
                "chapter_num": chapter_num,
                "total_chapters": total_chapters,
                "outline": outline.content,
                "chapter_outline": chapter_outline,
                "previous_recap": previous_recap,
                "next_chapter_outline": next_chapter_outline
            }
        )
        
        messages = [{"role": "user", "content": prompt_content}]
        
        model_config = self.config.get_model("chapter_stage1_writer")
        response = await self.model_provider.generate_text(
            messages=messages,
            model_config=model_config,
            seed=settings.seed + chapter_num,
            min_word_count=1000,
            debug=settings.debug,
            stream=settings.stream
        )
        
        return response.strip()
    
    async def _generate_chapter_title(
        self,
        chapter_num: int,
        content: str,
        chapter_outline: str,
        settings: GenerationSettings
    ) -> str:
        """Generate a title for the chapter."""
        prompt_content = self.prompt_loader.load_prompt(
            "outline-chapter/generate_chapter_title",
            variables={
                "chapter_outline": chapter_outline,
                "chapter_content": content[:500] + "..."
            }
        )
        
        messages = [{"role": "user", "content": prompt_content}]
        
        model_config = self.config.get_model("chapter_outline_writer")
        response = await self.model_provider.generate_text(
            messages=messages,
            model_config=model_config,
            seed=settings.seed + chapter_num,
            debug=settings.debug,
            stream=settings.stream
        )
        
        return response.strip() 