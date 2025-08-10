"""Main story generation service."""

import asyncio
from typing import Optional
from domain.entities.story import Story, StoryInfo, Outline, Chapter
from domain.value_objects.generation_settings import GenerationSettings
from domain.exceptions import StoryGenerationError
from domain.repositories.savepoint_repository import SavepointRepository
from ..interfaces.model_provider import ModelProvider
from ..interfaces.storage_provider import StorageProvider
from ..interfaces.story_strategy import StoryStrategy 

class StoryGenerationService:
    """Main service for orchestrating story generation using strategies."""
    
    def __init__(
        self,
        strategy: StoryStrategy,
        model_provider: ModelProvider,
        storage: StorageProvider,
        savepoint_repo: Optional[SavepointRepository] = None
    ):
        self.strategy = strategy
        self.model_provider = model_provider
        self.storage = storage
        self.savepoint_repo = savepoint_repo
    
    async def generate_story(
        self,
        prompt: str,
        settings: GenerationSettings,
        prompt_filename: Optional[str] = None
    ) -> Story:
        """Generate a complete story from a prompt using the selected strategy."""
        try:
            # Generate outline using strategy
            outline = await self.strategy.generate_outline(
                prompt=prompt,
                settings=settings,
                prompt_filename=prompt_filename
            )
            
            # Generate chapters using strategy
            chapters = await self.strategy.generate_chapters(
                outline=outline,
                settings=settings
            )
            
            # Generate story info using strategy
            story_info = await self.strategy.generate_story_info(
                outline=outline,
                chapters=chapters,
                settings=settings
            )
            
            # Create story
            story = Story(
                info=story_info,
                outline=outline,
                chapters=chapters,
                prompt=prompt,
                settings=settings.to_dict()
            )
            
            return story
            
        except Exception as e:
            raise StoryGenerationError(f"Failed to generate story: {e}") from e
    
    async def save_story(self, story: Story, output_path: Optional[str] = None) -> str:
        """Save a story to storage."""
        try:
            # Generate filename if not provided
            if not output_path:
                safe_title = story.info.title.replace(" ", "_").replace("/", "_")
                output_path = f"Story_{safe_title}"
            
            # Save markdown version
            markdown_content = self._format_story_markdown(story)
            markdown_path = f"{output_path}.md"
            await self.storage.save_file(markdown_path, markdown_content)
            
            # Save JSON version
            json_path = f"{output_path}.json"
            await self.storage.save_json(json_path, story.to_dict())
            
            return output_path
            
        except Exception as e:
            raise StoryGenerationError(f"Failed to save story: {e}") from e
    
    def _format_story_markdown(self, story: Story) -> str:
        """Format story as markdown."""
        # Create statistics section
        stats = self._generate_statistics(story)
        
        # Create markdown content
        content = f"""# {story.info.title}

## Summary
{story.info.summary}

## Tags
{', '.join(story.info.tags)}

## Statistics
{stats}

---

{story.get_full_content()}

---

## Outline
```
{story.outline.content}
```
"""
        return content
    
    def _generate_statistics(self, story: Story) -> str:
        """Generate statistics for the story."""
        total_words = story.info.word_count
        total_chapters = story.info.chapter_count
        
        stats = f"""
- **Total Words**: {total_words:,}
- **Total Chapters**: {total_chapters}
- **Average Words per Chapter**: {total_words // total_chapters if total_chapters > 0 else 0}
- **Generation Date**: {story.info.generation_date.strftime('%Y-%m-%d %H:%M:%S') if story.info.generation_date else 'Unknown'}
- **Strategy Used**: {self.strategy.get_strategy_name()} v{self.strategy.get_strategy_version()}
"""
        return stats
    
    async def generate_story_with_savepoints(
        self,
        prompt: str,
        settings: GenerationSettings,
        prompt_filename: str
    ) -> Story:
        """Generate story with savepoint support."""
        if not self.savepoint_repo:
            raise StoryGenerationError("Savepoint repository not configured")
        
        return await self.generate_story(prompt, settings, prompt_filename) 