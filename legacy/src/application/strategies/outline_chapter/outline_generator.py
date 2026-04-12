"""Outline generation functionality for the outline-chapter strategy."""

import logging
from typing import List, Optional, Dict, Any
from domain.entities.story import Outline
from domain.value_objects.generation_settings import GenerationSettings
from domain.value_objects.model_config import ModelConfig
from domain.exceptions import StoryGenerationError

logger = logging.getLogger(__name__)

from application.interfaces.model_provider import ModelProvider
from infrastructure.prompts.prompt_handler import PromptHandler
from infrastructure.prompts.prompt_wrapper import execute_messages_with_savepoint, execute_prompt_with_savepoint, extract_boxed_solution
from infrastructure.savepoints import SavepointManager
from .character_manager import CharacterManager
from .setting_manager import SettingManager
from .chapter_generator import ChapterGenerator
from .story_state_manager import StoryStateManager
from application.services.rag_service import RAGService
from application.services.rag_integration_service import RAGIntegrationService
from application.services.content_chunker import ContentChunker
import json


class OutlineGenerator:
    """Handles outline generation functionality."""
    
    def __init__(
        self,
        model_provider: ModelProvider,
        config: Dict[str, Any],
        prompt_handler: PromptHandler,
        system_message: str,
        savepoint_manager: Optional[SavepointManager] = None,
        rag_service: Optional[RAGService] = None
    ):
        self.model_provider = model_provider
        self.config = config
        self.prompt_handler = prompt_handler
        self.system_message = system_message
        self.savepoint_manager = savepoint_manager
        self.rag_service = rag_service
        
        # RAG integration service will be set by the strategy after story initialization
        self.rag_integration = None
        
        # Initialize managers
        self.character_manager = CharacterManager(
            model_provider=model_provider,
            config=config,
            prompt_handler=prompt_handler,
            system_message=system_message,
            savepoint_manager=savepoint_manager,
            rag_service=rag_service
        )
        
        self.setting_manager = SettingManager(
            model_provider=model_provider,
            config=config,
            prompt_handler=prompt_handler,
            system_message=system_message,
            savepoint_manager=savepoint_manager,
            rag_service=rag_service
        )

        self.chapter_generator = ChapterGenerator(
            model_provider=model_provider,
            config=config,
            prompt_handler=prompt_handler,
            system_message=system_message,
            savepoint_manager=savepoint_manager,
            rag_service=rag_service
        )
        
        # Initialize story state manager for progressive planning
        self.story_state_manager = StoryStateManager(
            model_provider=model_provider,
            config=config,
            prompt_handler=prompt_handler,
            system_message=system_message,
            savepoint_manager=savepoint_manager,
            rag_service=rag_service
        )
    
    async def generate_outline(
        self, 
        prompt: str, 
        settings: GenerationSettings
    ) -> Outline:
        """Generate story outline from prompt."""
        try:
            conversation_history = []
            model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])

            prompt_prompt = self.prompt_handler.prompt_loader.load_prompt("multistep/outline/understand_prompt", {
                "prompt": prompt,
            })
            conversation_history.append({"role": "user", "content": prompt_prompt})

            response =await execute_messages_with_savepoint(
                handler=self.prompt_handler,
                conversation_history=conversation_history,
                model_config=model_config,
                debug=settings.debug,
                savepoint_id="understand_prompt",
                stream=True,
                use_boxed_solution=True,
            )

            conversation_history.append({"role": "assistant", "content": response.content})

            # Generate story analysis chunks for optimal RAG indexing
            story_analysis = await self._generate_story_analysis_chunks(prompt, settings, conversation_history)
            
            # Extract story start date from core foundation chunk
            start_date = await self._extract_story_start_date_from_chunks(story_analysis, settings)
            
            # Extract base context from core foundation chunk
            base_context = await self._extract_base_context_from_chunks(story_analysis, settings)
            
            # Generate story elements from all chunks
            story_elements = await self._generate_story_elements_from_chunks(story_analysis, settings)

            # Generate character sheets with RAG integration
            await self.character_manager.generate_character_sheets(story_elements, base_context, settings)
            
            # Generate setting sheets with RAG integration
            await self.setting_manager.generate_setting_sheets(story_elements, base_context, settings)
            
            return Outline(
                story_elements=story_elements,
                base_context=base_context,
                story_start_date=start_date,
                initial_outline=initial_outline
            )
            
        except Exception as e:
            raise StoryGenerationError(f"Failed to generate outline: {e}") from e
    
    async def initialize_progressive_outline(
        self, 
        prompt: str, 
        settings: GenerationSettings
    ) -> Dict[str, Any]:
        """Initialize the progressive outline system with story context."""
        try:
            if settings.debug:
                print(f"[PROGRESSIVE PLANNING] Initializing progressive outline system...")
            
            # Initialize story context using story state manager
            story_context = await self.story_state_manager.initialize_story_context(prompt, settings)
            
            if settings.debug:
                print(f"[PROGRESSIVE PLANNING] Story context initialized: {story_context.story_direction}")
            
            # Generate initial story analysis chunks for RAG indexing
            story_chunks = await self._generate_story_analysis_chunks(prompt, settings, [])
            
            # Return initialization data
            return {
                "story_context": story_context,
                "story_chunks": story_chunks,
                "status": "initialized",
                "message": "Progressive outline system ready for chapter planning"
            }
            
        except Exception as e:
            raise StoryGenerationError(f"Failed to initialize progressive outline: {e}") from e
    
    async def _index_story_analysis_chunk(self, content: str, chunk_type: str, settings: GenerationSettings) -> None:
        """Index a story analysis chunk in RAG."""
        await self.rag_integration.index_outline(
            outline_content=content,
            metadata={
                "content_type": "story_analysis_chunk",
                "chunk_type": chunk_type,
                "generation_stage": "story_analysis"
            }
        )
        if settings.debug:
            print(f"[RAG STORY ANALYSIS] Indexed {chunk_type} chunk")

    async def _generate_story_analysis_chunks(
        self,
        prompt: str,
        settings: GenerationSettings,
        conversation_history: list
    ) -> Dict[str, str]:
        """Generate focused story analysis chunks for optimal RAG indexing."""
        try:
            if settings.debug:
                print(f"[STORY ANALYSIS] Generating story analysis chunks")
            
            # Initialize base conversation for understanding the story prompt
            base_conversation = conversation_history
            
            # Generate each type of story analysis chunk
            chunks = {}
            chunks["core_story_foundation"] = await self._generate_core_story_foundation_chunk(prompt, settings, base_conversation)
            chunks["character_foundation"] = await self._generate_character_foundation_chunk(prompt, settings, base_conversation)
            chunks["setting_foundation"] = await self._generate_setting_foundation_chunk(prompt, settings, base_conversation)
            chunks["plot_structure"] = await self._generate_plot_structure_chunk(prompt, settings, base_conversation)
            chunks["theme_message"] = await self._generate_theme_message_chunk(prompt, settings, base_conversation)
            chunks["tone_style"] = await self._generate_tone_style_chunk(prompt, settings, base_conversation)
            chunks["conflict_stakes"] = await self._generate_conflict_stakes_chunk(prompt, settings, base_conversation)
            chunks["world_rules_logic"] = await self._generate_world_rules_logic_chunk(prompt, settings, base_conversation)
            
            # Individual chunk methods now handle their own indexing
            
            if settings.debug:
                print(f"[STORY ANALYSIS] Generated all {len(chunks)} story analysis chunks")
            
            return chunks
                
        except Exception as e:
            if settings.debug:
                print(f"[STORY ANALYSIS] Error generating story analysis chunks: {e}")
            # Return empty dict as fallback
            return {}
    
    async def _generate_core_story_foundation_chunk(
        self,
        prompt: str,
        settings: GenerationSettings,
        conversation_history: list
    ) -> str:
        """Generate core story foundation chunk using multistep conversation."""
        try:
            model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
            
            # Add the specific chunk generation prompt to the base conversation
            messages = conversation_history + [
                {
                    "role": "user",
                    "content": f"Based on your understanding of the story prompt, please generate a core story foundation chunk. Use this prompt:\n\n{self.prompt_handler.prompt_loader.load_prompt('multistep/outline/create_core_story_foundation_chunk')}\n\nStory prompt: {prompt}"
                }
            ]
            
            response = await execute_messages_with_savepoint(
                handler=self.prompt_handler,
                conversation_history=messages,
                savepoint_id="story_analysis/core_story_foundation_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream
            )
            
            content = response.content.strip()
            if settings.debug:
                print(f"[STORY ANALYSIS] Generated core story foundation chunk")
            
            # Index this chunk immediately
            await self._index_story_analysis_chunk(content, "core_story_foundation", settings)
            
            return content
                
        except Exception as e:
            if settings.debug:
                print(f"[STORY ANALYSIS] Error generating core story foundation chunk: {e}")
            return ""
    
    async def _generate_character_foundation_chunk(
        self,
        prompt: str,
        settings: GenerationSettings,
        conversation_history: list
    ) -> str:
        """Generate character foundation chunk using multistep conversation."""
        try:
            model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
            
            # Add the specific chunk generation prompt to the base conversation
            messages = conversation_history + [
                {
                    "role": "user",
                    "content": f"Based on your understanding of the story prompt, please generate a character foundation chunk. Use this prompt:\n\n{self.prompt_handler.prompt_loader.load_prompt('multistep/outline/create_character_foundation_chunk')}\n\nStory prompt: {prompt}"
                }
            ]
            
            response = await execute_messages_with_savepoint(
                handler=self.prompt_handler,
                conversation_history=messages,
                savepoint_id="story_analysis/character_foundation_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream
            )
            
            content = response.content.strip()
            if settings.debug:
                print(f"[STORY ANALYSIS] Generated character foundation chunk")
            
            # Index this chunk immediately
            await self._index_story_analysis_chunk(content, "character_foundation", settings)
            
            return content
                
        except Exception as e:
            if settings.debug:
                print(f"[STORY ANALYSIS] Error generating character foundation chunk: {e}")
            return ""
    
    async def _generate_setting_foundation_chunk(
        self,
        prompt: str,
        settings: GenerationSettings,
        conversation_history: list
    ) -> str:
        """Generate setting foundation chunk using multistep conversation."""
        try:
            model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
            
            # Add the specific chunk generation prompt to the base conversation
            messages = conversation_history + [
                {
                    "role": "user",
                    "content": f"Based on your understanding of the story prompt, please generate a setting foundation chunk. Use this prompt:\n\n{self.prompt_handler.prompt_loader.load_prompt('multistep/outline/create_setting_foundation_chunk')}\n\nStory prompt: {prompt}"
                }
            ]
            
            response = await execute_messages_with_savepoint(
                handler=self.prompt_handler,
                conversation_history=messages,
                savepoint_id="story_analysis/setting_foundation_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream
            )
            
            content = response.content.strip()
            if settings.debug:
                print(f"[STORY ANALYSIS] Generated setting foundation chunk")
            
            # Index this chunk immediately
            await self._index_story_analysis_chunk(content, "setting_foundation", settings)
            
            return content
                
        except Exception as e:
            if settings.debug:
                print(f"[STORY ANALYSIS] Error generating setting foundation chunk: {e}")
            return ""
    
    async def _generate_plot_structure_chunk(
        self,
        prompt: str,
        settings: GenerationSettings,
        conversation_history: list
    ) -> str:
        """Generate plot structure chunk using multistep conversation."""
        try:
            model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
            
            # Add the specific chunk generation prompt to the base conversation
            messages = conversation_history + [
                {
                    "role": "user",
                    "content": f"Based on your understanding of the story prompt, please generate a plot structure chunk. Use this prompt:\n\n{self.prompt_handler.prompt_loader.load_prompt('multistep/outline/create_plot_structure_chunk')}\n\nStory prompt: {prompt}"
                }
            ]
            
            response = await execute_messages_with_savepoint(
                handler=self.prompt_handler,
                conversation_history=messages,
                savepoint_id="story_analysis/plot_structure_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream
            )
            
            content = response.content.strip()
            if settings.debug:
                print(f"[STORY ANALYSIS] Generated plot structure chunk")
            
            # Index this chunk immediately
            await self._index_story_analysis_chunk(content, "plot_structure", settings)
            
            return content
                
        except Exception as e:
            if settings.debug:
                print(f"[STORY ANALYSIS] Error generating plot structure chunk: {e}")
            return ""
    
    async def _generate_theme_message_chunk(
        self,
        prompt: str,
        settings: GenerationSettings,
        conversation_history: list
    ) -> str:
        """Generate theme and message chunk using multistep conversation."""
        try:
            model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
            
            # Add the specific chunk generation prompt to the base conversation
            messages = conversation_history + [
                {
                    "role": "user",
                    "content": f"Based on your understanding of the story prompt, please generate a theme and message chunk. Use this prompt:\n\n{self.prompt_handler.prompt_loader.load_prompt('multistep/outline/create_theme_message_chunk')}\n\nStory prompt: {prompt}"
                }
            ]
            
            response = await execute_messages_with_savepoint(
                handler=self.prompt_handler,
                conversation_history=messages,
                savepoint_id="story_analysis/theme_message_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream
            )
            
            content = response.content.strip()
            if settings.debug:
                print(f"[STORY ANALYSIS] Generated theme message chunk")
            
            # Index this chunk immediately
            await self._index_story_analysis_chunk(content, "theme_message", settings)
            
            return content
                
        except Exception as e:
            if settings.debug:
                print(f"[STORY ANALYSIS] Error generating theme message chunk: {e}")
            return ""
    
    async def _generate_tone_style_chunk(
        self,
        prompt: str,
        settings: GenerationSettings,
        conversation_history: list
    ) -> str:
        """Generate tone and style chunk using multistep conversation."""
        try:
            model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
            
            # Add the specific chunk generation prompt to the base conversation
            messages = conversation_history + [
                {
                    "role": "user",
                    "content": f"Based on your understanding of the story prompt, please generate a tone and style chunk. Use this prompt:\n\n{self.prompt_handler.prompt_loader.load_prompt('multistep/outline/create_tone_style_chunk')}\n\nStory prompt: {prompt}"
                }
            ]
            
            response = await execute_messages_with_savepoint(
                handler=self.prompt_handler,
                conversation_history=messages,
                savepoint_id="story_analysis/tone_style_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream
            )
            
            content = response.content.strip()
            if settings.debug:
                print(f"[STORY ANALYSIS] Generated tone style chunk")
            
            # Index this chunk immediately
            await self._index_story_analysis_chunk(content, "tone_style", settings)
            
            return content
                
        except Exception as e:
            if settings.debug:
                print(f"[STORY ANALYSIS] Error generating tone style chunk: {e}")
            return ""
    
    async def _generate_conflict_stakes_chunk(
        self,
        prompt: str,
        settings: GenerationSettings,
        conversation_history: list
    ) -> str:
        """Generate conflict and stakes chunk using multistep conversation."""
        try:
            model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
            
            # Add the specific chunk generation prompt to the base conversation
            messages = conversation_history + [
                {
                    "role": "user",
                    "content": f"Based on your understanding of the story prompt, please generate a conflict and stakes chunk. Use this prompt:\n\n{self.prompt_handler.prompt_loader.load_prompt('multistep/outline/create_conflict_stakes_chunk')}\n\nStory prompt: {prompt}"
                }
            ]
            
            response = await execute_messages_with_savepoint(
                handler=self.prompt_handler,
                conversation_history=messages,
                savepoint_id="story_analysis/conflict_stakes_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream
            )
            
            content = response.content.strip()
            if settings.debug:
                print(f"[STORY ANALYSIS] Generated conflict stakes chunk")
            
            # Index this chunk immediately
            await self._index_story_analysis_chunk(content, "conflict_stakes", settings)
            
            return content
                
        except Exception as e:
            if settings.debug:
                print(f"[STORY ANALYSIS] Error generating conflict stakes chunk: {e}")
            return ""
    
    async def _generate_world_rules_logic_chunk(
        self,
        prompt: str,
        settings: GenerationSettings,
        conversation_history: list
    ) -> str:
        """Generate world rules and logic chunk using multistep conversation."""
        try:
            model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
            
            # Add the specific chunk generation prompt to the base conversation
            messages = conversation_history + [
                {
                    "role": "user",
                    "content": f"Based on your understanding of the story prompt, please generate a world rules and logic chunk. Use this prompt:\n\n{self.prompt_handler.prompt_loader.load_prompt('multistep/outline/create_world_rules_logic_chunk')}\n\nStory prompt: {prompt}"
                }
            ]
            
            response = await execute_messages_with_savepoint(
                handler=self.prompt_handler,
                conversation_history=messages,
                savepoint_id="story_analysis/world_rules_logic_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream
            )
            
            content = response.content.strip()
            if settings.debug:
                print(f"[STORY ANALYSIS] Generated world rules logic chunk")
            
            # Index this chunk immediately
            await self._index_story_analysis_chunk(content, "world_rules_logic", settings)
            
            return content
                
        except Exception as e:
            if settings.debug:
                print(f"[STORY ANALYSIS] Error generating world rules logic chunk: {e}")
            return ""
    
    async def _extract_story_start_date_from_chunks(
        self,
        story_analysis: Dict[str, str],
        settings: GenerationSettings
    ) -> str:
        """Extract story start date from core story foundation chunk."""
        try:
            # Use core story foundation chunk to extract start date
            core_foundation = story_analysis.get("core_story_foundation", "")
            if not core_foundation:
                return "Present day"  # Default fallback
            
            model_config = ModelConfig.from_string(self.config["models"]["creative_model"])
            
            # Extract start date from the core foundation content
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="multistep/outline/story_start_date",
                variables={"prompt": core_foundation},
                savepoint_id="story_start_date",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                log_prompt_inputs=settings.log_prompt_inputs,
                system_message=self.system_message
            )
            
            return response.content.strip()
                
        except Exception as e:
            if settings.debug:
                print(f"[STORY START DATE] Error extracting start date from chunks: {e}")
            return "Present day"  # Default fallback
    
    async def _extract_base_context_from_chunks(
        self,
        story_analysis: Dict[str, str],
        settings: GenerationSettings
    ) -> str:
        """Extract base context from core story foundation chunk."""
        try:
            # Use core story foundation chunk as base context
            core_foundation = story_analysis.get("core_story_foundation", "")
            if not core_foundation:
                return "Story development in progress"  # Default fallback
            
            # The core foundation chunk serves as the base context
            return core_foundation
                
        except Exception as e:
            if settings.debug:
                print(f"[BASE CONTEXT] Error extracting base context from chunks: {e}")
            return "Story development in progress"  # Default fallback
    
    async def _generate_story_elements_from_chunks(
        self,
        story_analysis: Dict[str, str],
        settings: GenerationSettings
    ) -> str:
        """Generate story elements from all analysis chunks."""
        try:
            # Combine all chunks into comprehensive story elements
            combined_chunks = []
            for chunk_type, chunk_content in story_analysis.items():
                if chunk_content:
                    combined_chunks.append(f"=== {chunk_type.replace('_', ' ').title()} ===\n{chunk_content}")
            
            if not combined_chunks:
                return "Story elements generation in progress"  # Default fallback
            
            story_elements = "\n\n".join(combined_chunks)
            
            # Save the combined story elements
            if self.savepoint_manager:
                await self.savepoint_manager.save_step("story_elements", story_elements)
            
            return story_elements
                
        except Exception as e:
            if settings.debug:
                print(f"[STORY ELEMENTS] Error generating story elements from chunks: {e}")
            return "Story elements generation in progress"  # Default fallback


    

