"""Outline-Chapter story writing strategy."""

from typing import List, Optional, Dict, Any
from domain.entities.story import Story, Outline, Chapter, StoryInfo
from domain.value_objects.generation_settings import GenerationSettings
from domain.value_objects.model_config import ModelConfig
from domain.exceptions import StoryGenerationError
from domain.repositories.savepoint_repository import SavepointRepository
from application.interfaces.story_strategy import StoryStrategy
from application.interfaces.model_provider import ModelProvider
from infrastructure.prompts.prompt_loader import PromptLoader
from infrastructure.prompts.prompt_handler import PromptHandler
from infrastructure.prompts.prompt_wrapper import execute_prompt_with_savepoint
from infrastructure.savepoints import SavepointManager
from .outline_generator import OutlineGenerator
from .chapter_generator import ChapterGenerator


class OutlineChapterStrategy(StoryStrategy):
    """Story writing strategy that generates outline first, then chapters."""
    
    def __init__(
        self, 
        model_provider: ModelProvider, 
        config: Dict[str, Any], 
        prompt_loader: PromptLoader,
        savepoint_repo: Optional[SavepointRepository] = None
    ):
        super().__init__(model_provider)
        self.config = config
        self.prompt_loader = prompt_loader
        self.savepoint_repo = savepoint_repo
        self.savepoint_manager: Optional[SavepointManager] = None
        
        # Create the prompt handler
        self.prompt_handler = PromptHandler(
            model_provider=model_provider,
            prompt_loader=prompt_loader,
            savepoint_repo=savepoint_repo
        )
        
        # System message for consistent context and role signaling
        self.system_message = """You are an expert creative writer and storyteller specializing in novel writing. Your role is to help create compelling, well-structured stories with rich characters, engaging plots, and vivid descriptions.

When responding to prompts:
- Maintain consistency with the established story elements and context
- Provide detailed, creative responses that advance the narrative
- Consider character development, plot progression, and thematic elements
- Write in a clear, engaging style appropriate for the target audience
- Follow any specific formatting or structural requirements given in the prompt
- Ensure your responses contribute to a cohesive overall story arc

You have deep knowledge of storytelling techniques, character development, plot structure, and creative writing principles. Use this expertise to create high-quality story content."""
        
        # Initialize generators
        self.outline_generator = OutlineGenerator(
            model_provider=model_provider,
            config=config,
            prompt_handler=self.prompt_handler,
            system_message=self.system_message,
            savepoint_manager=self.savepoint_manager
        )
        
        self.chapter_generator = ChapterGenerator(
            model_provider=model_provider,
            config=config,
            prompt_handler=self.prompt_handler,
            system_message=self.system_message,
            savepoint_manager=self.savepoint_manager
        )
    
    def _setup_savepoints(self, prompt_filename: str) -> None:
        """Setup savepoint manager for the current story."""
        if self.savepoint_repo:
            self.savepoint_manager = SavepointManager(self.savepoint_repo, prompt_filename)
            # Also set up the prompt handler with the story directory
            self.prompt_handler.set_story_directory(prompt_filename)
            
            # Update generators with the new savepoint manager
            self.outline_generator.savepoint_manager = self.savepoint_manager
            self.chapter_generator.savepoint_manager = self.savepoint_manager
            
            # Update managers in generators
            self.outline_generator.character_manager.savepoint_manager = self.savepoint_manager
            self.outline_generator.setting_manager.savepoint_manager = self.savepoint_manager
            self.chapter_generator.character_manager.savepoint_manager = self.savepoint_manager
            self.chapter_generator.setting_manager.savepoint_manager = self.savepoint_manager
            self.chapter_generator.recap_manager.savepoint_manager = self.savepoint_manager
            self.chapter_generator.scene_generator.savepoint_manager = self.savepoint_manager
    
    def _create_messages_with_system(self, user_content: str) -> List[Dict[str, str]]:
        """Create messages list with system message included."""
        return [
            {"role": "user", "content": self.system_message + "\n\n" + user_content}
        ]
    
    def get_system_message(self) -> str:
        """Get the current system message."""
        return self.system_message
    
    def set_system_message(self, system_message: str) -> None:
        """Set a custom system message."""
        self.system_message = system_message
    
    def get_default_system_message(self) -> str:
        """Get the default system message."""
        return """You are an expert creative writer and storyteller specializing in novel writing. Your role is to help create compelling, well-structured stories with rich characters, engaging plots, and vivid descriptions.

When responding to prompts:
- Maintain consistency with the established story elements and context
- Provide detailed, creative responses that advance the narrative
- Consider character development, plot progression, and thematic elements
- Write in a clear, engaging style appropriate for the target audience
- Follow any specific formatting or structural requirements given in the prompt
- Ensure your responses contribute to a cohesive overall story arc

You have deep knowledge of storytelling techniques, character development, plot structure, and creative writing principles. Use this expertise to create high-quality story content."""
    
    def reset_system_message(self) -> None:
        """Reset the system message to the default."""
        self.system_message = self.get_default_system_message()
    
    async def generate_outline(self, prompt: str, settings: GenerationSettings, prompt_filename: Optional[str] = None) -> Outline:
        """Generate story outline from prompt."""
        try:
            # Setup savepoints if available
            if prompt_filename and self.savepoint_repo:
                self._setup_savepoints(prompt_filename)
            
            # Delegate to outline generator
            return await self.outline_generator.generate_outline(prompt, settings)
            
        except Exception as e:
            raise StoryGenerationError(f"Failed to generate outline: {e}") from e
    
    async def generate_chapters(self, outline: Outline, settings: GenerationSettings) -> List[Chapter]:
        """Generate chapters from outline."""
        try:
            # Delegate to chapter generator
            return await self.chapter_generator.generate_chapters(outline, settings)
            
        except Exception as e:
            raise StoryGenerationError(f"Failed to generate chapters: {e}") from e
    
    async def generate_story_info(self, outline: Outline, chapters: List[Chapter], settings: GenerationSettings) -> StoryInfo:
        """Generate story metadata."""
        try:
            # Generate title
            title = await self._generate_title(outline, chapters, settings)
            
            # Generate summary
            summary = await self._generate_summary(outline, chapters, settings)
            
            # Generate tags
            tags = await self._generate_tags(outline, chapters, settings)
            
            # Calculate word count
            word_count = sum(len(chapter.content.split()) for chapter in chapters)
            
            return StoryInfo(
                title=title,
                summary=summary,
                tags=tags,
                chapter_count=len(chapters),
                word_count=word_count
            )
            
        except Exception as e:
            raise StoryGenerationError(f"Failed to generate story info: {e}") from e
    
    def get_strategy_name(self) -> str:
        """Get the name of this strategy."""
        return "outline-chapter"
    
    def get_strategy_version(self) -> str:
        """Get the version of this strategy."""
        return "1.0.0"
    
    def get_strategy_description(self) -> str:
        """Get a description of this strategy."""
        return "Generates a detailed outline first, then writes chapters based on the outline structure."
    
    def get_required_models(self) -> List[str]:
        """Get list of required model names for this strategy."""
        return [
            "sanity_model",
            "initial_outline_writer",
            "chapter_outline_writer",
            "logical_model",
            "scene_writer",
            "info_model"
        ]
    
    def get_prompt_directory(self) -> str:
        """Get the directory containing prompts for this strategy."""
        return "src/application/strategies/outline_chapter/prompts"
    
    # Story info generation methods
    async def _generate_title(self, outline: Outline, chapters: List[Chapter], settings: GenerationSettings) -> str:
        """Generate story title."""
        model_config = ModelConfig.from_string(self.config["models"]["info_model"])
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="outline/create_title",
            variables={
                "outline": outline.content,
                "chapters": [chapter.content for chapter in chapters]
            },
            savepoint_id="story_title",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def _generate_summary(self, outline: Outline, chapters: List[Chapter], settings: GenerationSettings) -> str:
        """Generate story summary."""
        model_config = ModelConfig.from_string(self.config["models"]["info_model"])
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="outline/create_summary",
            variables={
                "outline": outline.content,
                "chapters": [chapter.content for chapter in chapters]
            },
            savepoint_id="story_summary",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def _generate_tags(self, outline: Outline, chapters: List[Chapter], settings: GenerationSettings) -> List[str]:
        """Generate story tags."""
        model_config = ModelConfig.from_string(self.config["models"]["info_model"])
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="outline/create_tags",
            variables={
                "outline": outline.content,
                "chapters": [chapter.content for chapter in chapters]
            },
            savepoint_id="story_tags",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        return response.content.strip()
    