"""Stream of Consciousness story writing strategy."""

from typing import List, Dict, Any
from domain.entities.story import Story, Outline, Chapter, StoryInfo
from domain.value_objects.generation_settings import GenerationSettings
from domain.value_objects.model_config import ModelConfig
from domain.exceptions import StoryGenerationError

from application.interfaces.story_strategy import StoryStrategy
from application.interfaces.model_provider import ModelProvider


class StreamOfConsciousnessStrategy(StoryStrategy):
    """Story writing strategy that generates content in a stream-of-consciousness style."""
    
    def __init__(self, model_provider: ModelProvider, config: Dict[str, Any] = None):
        super().__init__(model_provider)
        self.config = config
        # Create strategy-specific prompt loader
        from infrastructure.prompts.prompt_loader import PromptLoader
        self.prompt_loader = PromptLoader(prompts_dir=self.get_prompt_directory())
    
    async def generate_outline(self, prompt: str, settings: GenerationSettings) -> Outline:
        """Generate a minimal outline for stream-of-consciousness writing."""
        # Load outline prompt
        outline_prompt = self.prompt_loader.load_prompt(
            "outline",
            variables={"prompt": prompt}
        )
        
        messages = [{"role": "user", "content": outline_prompt}]
        
        response = await self.model_provider.generate_text(
            messages=messages,
            model_config=ModelConfig.from_string(self.config["models"]["initial_outline_writer"]) if self.config else None,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream
        )
        
        outline_content = response.strip()
        
        return Outline(
            story_elements="Stream of consciousness narrative",
            base_context=prompt,
            story_start_date="Now"
        )
    
    async def generate_chapters(self, outline: Outline, settings: GenerationSettings) -> List[Chapter]:
        """Generate chapters in a stream-of-consciousness style."""
        # Load content prompt
        content_prompt = self.prompt_loader.load_prompt(
            "content",
            variables={"prompt": outline.base_context}
        )
        
        messages = [{"role": "user", "content": content_prompt}]
        
        response = await self.model_provider.generate_text(
            messages=messages,
            model_config=ModelConfig.from_string(self.config["models"]["initial_outline_writer"]) if self.config else None,
            seed=settings.seed,
            min_word_count=2000,
            debug=settings.debug,
            stream=settings.stream
        )
        
        # Split into "chapters" based on natural breaks
        sections = response.split('\n\n')
        chapters = []
        
        for i, section in enumerate(sections, 1):
            if section.strip():
                chapter = Chapter(
                    number=i,
                    title=f"Flow {i}",
                    content=section.strip(),
                    outline=f"Natural flow section {i}"
                )
                chapters.append(chapter)
        
        return chapters
    
    async def generate_story_info(self, outline: Outline, chapters: List[Chapter], settings: GenerationSettings) -> StoryInfo:
        """Generate story metadata for stream-of-consciousness story."""
        # Use first chapter content for context
        first_chapter_content = chapters[0].content if chapters else ""
        
        # Load metadata prompt
        metadata_prompt = self.prompt_loader.load_prompt(
            "metadata",
            variables={"content": first_chapter_content[:1000] + "..."}
        )
        
        messages = [{"role": "user", "content": metadata_prompt}]
        
        title_response = await self.model_provider.generate_text(
            messages=messages,
            model_config=ModelConfig.from_string(self.config["models"]["info_model"]) if self.config else None,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream
        )
        
        title = title_response.strip().strip('"').strip("'")
        
        # Generate summary
        summary = "A stream-of-consciousness narrative that flows through thoughts, memories, and associations."
        
        # Generate tags
        tags = ["stream-of-consciousness", "experimental", "literary", "introspective"]
        
        # Calculate word count
        word_count = sum(len(chapter.content.split()) for chapter in chapters)
        
        return StoryInfo(
            title=title,
            summary=summary,
            tags=tags,
            chapter_count=len(chapters),
            word_count=word_count
        )
    
    def get_strategy_name(self) -> str:
        """Get the name of this strategy."""
        return "stream-of-consciousness"
    
    def get_strategy_version(self) -> str:
        """Get the version of this strategy."""
        return "1.0.0"
    
    def get_strategy_description(self) -> str:
        """Get a description of this strategy."""
        return "Generates stories in a stream-of-consciousness style with flowing, associative narrative."
    
    def get_required_models(self) -> List[str]:
        """Get list of required model names for this strategy."""
        return ["initial_outline_writer"]  # Only needs one model
    
    def get_prompt_directory(self) -> str:
        """Get the directory containing prompts for this strategy."""
        return "src/application/strategies/stream_of_consciousness/prompts" 