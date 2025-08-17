"""Outline-Chapter story writing strategy."""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
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
from .story_state_manager import StoryStateManager
from application.services.rag_service import RAGService


class OutlineChapterStrategy(StoryStrategy):
    """Story writing strategy that generates outline first, then chapters."""
    
    def __init__(
        self, 
        model_provider: ModelProvider, 
        config: Dict[str, Any], 
        prompt_loader: PromptLoader,
        savepoint_repo: Optional[SavepointRepository] = None,
        rag_service: Optional['RAGService'] = None
    ):
        super().__init__(model_provider)
        self.config = config
        self.prompt_loader = prompt_loader
        self.savepoint_repo = savepoint_repo
        self.savepoint_manager: Optional[SavepointManager] = None
        self.rag_service = rag_service
        self._prompt_filename: Optional[str] = None
        self._rag_story_id: Optional[int] = None
        
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
            savepoint_manager=self.savepoint_manager,
            rag_service=self.rag_service
        )
        
        self.chapter_generator = ChapterGenerator(
            model_provider=model_provider,
            config=config,
            prompt_handler=self.prompt_handler,
            system_message=self.system_message,
            savepoint_manager=self.savepoint_manager,
            rag_service=self.rag_service
        )
        
        # Initialize story state manager
        self.story_state_manager = StoryStateManager(
            model_provider=model_provider,
            config=config,
            prompt_handler=self.prompt_handler,
            system_message=self.system_message,
            savepoint_manager=self.savepoint_manager,
            rag_service=self.rag_service
        )
    
    async def _setup_savepoints(self, prompt_filename: str) -> None:
        """Setup savepoint manager for the current story."""
        if self.savepoint_repo:
            # Store the prompt filename for RAG context
            self._prompt_filename = prompt_filename
            
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
            
            # Update story state manager
            self.story_state_manager.savepoint_manager = self.savepoint_manager
            self.story_state_manager.set_story_directory(prompt_filename)
            
            # Set the story identifier in RAG integration services for story isolation
            if self.rag_service and self.outline_generator.rag_integration:
                self.outline_generator.rag_integration.set_current_story_identifier(prompt_filename)
            if self.rag_service and self.chapter_generator.rag_integration:
                self.chapter_generator.rag_integration.set_current_story_identifier(prompt_filename)
            if self.rag_service and self.story_state_manager.rag_integration:
                self.story_state_manager.rag_integration.set_current_story_identifier(prompt_filename)
            
            # Initialize RAG story context for this prompt filename
            if self.rag_service:
                await self._initialize_rag_story(prompt_filename)
    
    async def _initialize_rag_story(self, prompt_filename: str) -> None:
        """Initialize RAG story context for the given prompt filename."""
        try:
            if not self.rag_service:
                return
            
            # Ensure RAG service is initialized before use
            if not hasattr(self.rag_service, '_initialized'):
                await self.rag_service.initialize()
                self.rag_service._initialized = True
            
            # Create or get story in RAG system using prompt filename as identifier
            story_id = await self.rag_service.create_story(
                story_name=prompt_filename,
                prompt_file_path=Path(prompt_filename)
            )
            
            # Store the story ID for future use
            self._rag_story_id = story_id
            
            print(f"✅ RAG story initialized for '{prompt_filename}' with ID: {story_id}")
            
        except Exception as e:
            print(f"⚠️ Warning: Could not initialize RAG story for '{prompt_filename}': {e}")
    
    def get_rag_story_id(self) -> Optional[int]:
        """Get the current RAG story ID for the active prompt filename."""
        return self._rag_story_id
    
    def has_rag_story(self) -> bool:
        """Check if a RAG story is currently active."""
        return self._rag_story_id is not None
    
    def get_current_prompt_filename(self) -> Optional[str]:
        """Get the current prompt filename for the active story."""
        return self._prompt_filename
    
    def get_rag_status(self) -> Dict[str, Any]:
        """Get comprehensive RAG status including story information."""
        status = {
            "rag_service_available": self.rag_service is not None,
            "prompt_filename": self._prompt_filename,
            "rag_story_active": self.has_rag_story(),
            "rag_story_id": self._rag_story_id
        }
        
        if self.rag_service:
            status["rag_service_type"] = type(self.rag_service).__name__
        
        return status
    
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
                await self._setup_savepoints(prompt_filename)
            
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
    
    async def generate_progressive_story(self, prompt: str, settings: GenerationSettings) -> List[Chapter]:
        """Generate story progressively, one chapter at a time."""
        try:
            # Initialize progressive outline system
            print("[PROGRESSIVE STORY] Initializing progressive outline system...")
            init_result = await self.outline_generator.initialize_progressive_outline(prompt, settings)
            print(f"[PROGRESSIVE STORY] Progressive outline initialized: {init_result['status']}")
            
            chapters = []
            chapter_count = 0
            
            # Generate chapters progressively
            while chapter_count < settings.wanted_chapters:
                chapter_count += 1
                print(f"[PROGRESSIVE STORY] Planning Chapter {chapter_count}...")
                
                # Use OutlineGenerator to coordinate chapter planning
                chapter_plan = await self.outline_generator.plan_next_chapter_progressive(settings)
                print(f"[PROGRESSIVE STORY] Chapter {chapter_count} planned: {chapter_plan['title']}")
                
                # Generate the chapter content using ChapterGenerator
                print(f"[PROGRESSIVE STORY] Generating Chapter {chapter_count} content...")
                chapter = await self._generate_chapter_from_plan(chapter_plan, settings)
                chapters.append(chapter)
                
                # Update story evolution
                print(f"[PROGRESSIVE STORY] Analyzing Chapter {chapter_count} evolution...")
                await self.story_state_manager.update_story_evolution(chapter_count, settings)
                
                # Check if we need to revise previous chapter plans
                if chapter_count > 1:
                    print(f"[PROGRESSIVE STORY] Checking if Chapter {chapter_count-1} needs revision...")
                    await self._check_and_revise_previous_chapters(chapter_count, settings)
                
                print(f"[PROGRESSIVE STORY] Chapter {chapter_count} completed. Story state updated.")
                print(f"[PROGRESSIVE STORY] Current story summary:\n{self.story_state_manager.get_story_summary()}")
            
            return chapters
            
        except Exception as e:
            raise StoryGenerationError(f"Failed to generate progressive story: {e}") from e
    
    async def get_progressive_outline_status(self, settings: GenerationSettings) -> Dict[str, Any]:
        """Get the current status of the progressive outline system."""
        try:
            if not self.story_state_manager.story_context:
                return {
                    "status": "not_initialized",
                    "message": "Progressive outline system not initialized"
                }
            
            # Get status information from StoryStateManager
            chapter_count = len(self.story_state_manager.chapters)
            planned_chapters = len([c for c in self.story_state_manager.chapters.values() if c.status == "planned"])
            completed_chapters = len([c for c in self.story_state_manager.chapters.values() if c.status == "completed"])
            revised_chapters = len([c for c in self.story_state_manager.chapters.values() if c.status == "revised"])
            
            # Get story context summary
            context = self.story_state_manager.story_context
            story_summary = {
                "direction": context.story_direction,
                "themes": context.current_themes,
                "tone": context.tone_style,
                "pacing": context.story_pacing,
                "tension": context.current_tension
            }
            
            return {
                "status": "active",
                "story_context": story_summary,
                "chapters": {
                    "planned": planned_chapters,
                    "completed": completed_chapters,
                    "revised": revised_chapters,
                    "total": chapter_count
                },
                "characters": len(self.story_state_manager.characters),
                "plot_threads": len([t for t in self.story_state_manager.plot_threads.values() if t.status == 'active']),
                "evolution_entries": len(self.story_state_manager.story_evolution)
            }
            
        except Exception as e:
            raise StoryGenerationError(f"Failed to get progressive outline status: {e}") from e
    
    async def plan_next_chapter_progressive(self, settings: GenerationSettings) -> Dict[str, Any]:
        """Manually plan the next chapter in the progressive story."""
        try:
            if not self.story_state_manager.story_context:
                raise StoryGenerationError("Progressive outline system not initialized. Call generate_progressive_story first.")
            
            # Use OutlineGenerator to coordinate chapter planning
            chapter_plan = await self.outline_generator.plan_next_chapter_progressive(settings)
            
            if settings.debug:
                print(f"[PROGRESSIVE PLANNING] Next chapter planned: {chapter_plan['title']}")
            
            return chapter_plan
            
        except Exception as e:
            raise StoryGenerationError(f"Failed to plan next chapter: {e}") from e
    
    async def _generate_chapter_from_plan(self, chapter_plan: Dict[str, Any], settings: GenerationSettings) -> Chapter:
        """Generate a chapter from a progressive chapter plan using ChapterGenerator."""
        try:
            # Create a Chapter entity with the planned content
            from domain.entities.story import Chapter
            chapter = Chapter(
                title=chapter_plan['title'],
                content=chapter_plan['planned_content'],
                chapter_number=chapter_plan['chapter_number']
            )
            
            # Use ChapterGenerator to enhance the chapter content if needed
            # This could involve scene generation, character development, etc.
            # For now, we'll use the planned content directly
            if settings.debug:
                print(f"[PROGRESSIVE STORY] Chapter {chapter.chapter_number} generated from plan")
                print(f"   Title: {chapter.title}")
                print(f"   Content length: {len(chapter.content)} characters")
            
            # Update the chapter state in StoryStateManager
            if chapter.chapter_number in self.story_state_manager.chapters:
                chapter_state = self.story_state_manager.chapters[chapter.chapter_number]
                chapter_state.actual_content = chapter.content
                chapter_state.status = "completed"
                chapter_state.updated_at = datetime.now()
                
                # Save the updated state
                self.story_state_manager._save_state()
            
            return chapter
            
        except Exception as e:
            raise StoryGenerationError(f"Failed to generate chapter from plan: {e}") from e
    
    async def _check_and_revise_previous_chapters(self, current_chapter: int, settings: GenerationSettings) -> None:
        """Check if previous chapters need revision based on story evolution."""
        try:
            # Check the previous chapter for potential revisions
            prev_chapter = current_chapter - 1
            if prev_chapter in self.story_state_manager.chapters:
                chapter_state = self.story_state_manager.chapters[prev_chapter]
                
                # Simple heuristic: if the chapter was planned more than 2 chapters ago, consider revision
                if current_chapter - chapter_state.chapter_number > 2:
                    print(f"[PROGRESSIVE STORY] Revising Chapter {prev_chapter} plan...")
                    # Use OutlineGenerator to coordinate revision
                    await self.outline_generator.revise_outline_progressive(prev_chapter, settings)
                    print(f"[PROGRESSIVE STORY] Chapter {prev_chapter} plan revised.")
                    
        except Exception as e:
            print(f"[PROGRESSIVE STORY] Warning: Could not check/revise previous chapters: {e}")
    
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
        return "Generates stories progressively, allowing organic development through iterative chapter planning and writing, or traditionally with upfront outline generation."
    
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
    