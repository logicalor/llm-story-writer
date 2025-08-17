"""Outline generation functionality for the outline-chapter strategy."""

from typing import List, Optional, Dict, Any
from domain.entities.story import Outline
from domain.value_objects.generation_settings import GenerationSettings
from domain.value_objects.model_config import ModelConfig
from domain.exceptions import StoryGenerationError

from application.interfaces.model_provider import ModelProvider
from infrastructure.prompts.prompt_handler import PromptHandler
from infrastructure.prompts.prompt_wrapper import execute_messages_with_savepoint, execute_prompt_with_savepoint, extract_boxed_solution
from infrastructure.savepoints import SavepointManager
from .character_manager import CharacterManager
from .setting_manager import SettingManager
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
        
        # Initialize RAG integration if service is provided
        self.rag_integration = None
        if self.rag_service:
            content_chunker = ContentChunker(
                max_chunk_size=self.config.get("max_chunk_size", 1000),
                overlap_size=self.config.get("overlap_size", 200)
            )
            self.rag_integration = RAGIntegrationService(self.rag_service, content_chunker)
        
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

            response = await execute_messages_with_savepoint(
                handler=self.prompt_handler,
                conversation_history=conversation_history,
                model_config=model_config,
                debug=settings.debug,
                savepoint_id="understand_prompt",
                stream=True,
                use_boxed_solution=True
            )

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
            
            await self._generate_stripped_story_elements(story_elements, settings)
            
            # Generate initial outline (this now includes critique refinement)
            # Use stripped story elements for outline generation to avoid character/setting duplication
            stripped_story_elements = story_elements
            final_outline = await self._generate_initial_outline(
                prompt, stripped_story_elements, base_context, settings
            )
            
            # Get the initial outline from savepoint if available
            initial_outline = None
            if self.savepoint_manager:
                try:
                    initial_outline = await self.savepoint_manager.load_step("initial_outline")
                except:
                    initial_outline = final_outline  # Fallback to final outline if initial not found
            
            # Generate detailed chapter list (now handled by chapter generator)
            # For both single-pass and chunked generation, use the chapter generator
            chapter_list = await self.chapter_generator.generate_chapter_synopses(
                final_outline, base_context, stripped_story_elements, settings
            )
            
            return Outline(
                content=chapter_list,
                story_elements=story_elements,
                chapter_list=chapter_list,
                base_context=base_context,
                story_start_date=start_date,
                initial_outline=initial_outline,
                final_outline=final_outline
            )
            
        except Exception as e:
            raise StoryGenerationError(f"Failed to generate outline: {e}") from e
    
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
            
            # Generate each type of story analysis chunk
            chunks = {}
            chunks["core_story_foundation"] = await self._generate_core_story_foundation_chunk(prompt, settings, conversation_history)
            chunks["character_foundation"] = await self._generate_character_foundation_chunk(prompt, settings, conversation_history)
            chunks["setting_foundation"] = await self._generate_setting_foundation_chunk(prompt, settings, conversation_history)
            chunks["plot_structure"] = await self._generate_plot_structure_chunk(prompt, settings, conversation_history)
            chunks["theme_message"] = await self._generate_theme_message_chunk(prompt, settings, conversation_history)
            chunks["tone_style"] = await self._generate_tone_style_chunk(prompt, settings, conversation_history)
            chunks["conflict_stakes"] = await self._generate_conflict_stakes_chunk(prompt, settings, conversation_history)
            chunks["world_rules_logic"] = await self._generate_world_rules_logic_chunk(prompt, settings, conversation_history)
            
            # Index all chunks in RAG if available
            if self.rag_integration:
                await self._index_story_analysis_chunks(chunks, settings)
            
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
        """Generate core story foundation chunk."""
        try:
            model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
            
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="multistep/outline/create_core_story_foundation_chunk",
                variables={
                    "prompt": prompt,
                    "base_context": "",
                    "story_elements": ""
                },
                savepoint_id="story_analysis/core_story_foundation_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                log_prompt_inputs=settings.log_prompt_inputs,
                system_message=self.system_message
            )
            
            if settings.debug:
                print(f"[STORY ANALYSIS] Generated core story foundation chunk")
            
            return response.content.strip()
                
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
        """Generate character foundation chunk."""
        try:
            model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
            
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="multistep/outline/create_character_foundation_chunk",
                variables={
                    "prompt": prompt,
                    "base_context": "",
                    "story_elements": ""
                },
                savepoint_id="story_analysis/character_foundation_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                log_prompt_inputs=settings.log_prompt_inputs,
                system_message=self.system_message
            )
            
            if settings.debug:
                print(f"[STORY ANALYSIS] Generated character foundation chunk")
            
            return response.content.strip()
                
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
        """Generate setting foundation chunk."""
        try:
            model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
            
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="multistep/outline/create_setting_foundation_chunk",
                variables={
                    "prompt": prompt,
                    "base_context": "",
                    "story_elements": ""
                },
                savepoint_id="story_analysis/setting_foundation_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                log_prompt_inputs=settings.log_prompt_inputs,
                system_message=self.system_message
            )
            
            if settings.debug:
                print(f"[STORY ANALYSIS] Generated setting foundation chunk")
            
            return response.content.strip()
                
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
        """Generate plot structure chunk."""
        try:
            model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
            
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="multistep/outline/create_plot_structure_chunk",
                variables={
                    "prompt": prompt,
                    "base_context": "",
                    "story_elements": ""
                },
                savepoint_id="story_analysis/plot_structure_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                log_prompt_inputs=settings.log_prompt_inputs,
                system_message=self.system_message
            )
            
            if settings.debug:
                print(f"[STORY ANALYSIS] Generated plot structure chunk")
            
            return response.content.strip()
                
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
        """Generate theme and message chunk."""
        try:
            model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
            
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="multistep/outline/create_theme_message_chunk",
                variables={
                    "prompt": prompt,
                    "base_context": "",
                    "story_elements": ""
                },
                savepoint_id="story_analysis/theme_message_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                log_prompt_inputs=settings.log_prompt_inputs,
                system_message=self.system_message
            )
            
            if settings.debug:
                print(f"[STORY ANALYSIS] Generated theme message chunk")
            
            return response.content.strip()
                
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
        """Generate tone and style chunk."""
        try:
            model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
            
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="multistep/outline/create_tone_style_chunk",
                variables={
                    "prompt": prompt,
                    "base_context": "",
                    "story_elements": ""
                },
                savepoint_id="story_analysis/tone_style_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                log_prompt_inputs=settings.log_prompt_inputs,
                system_message=self.system_message
            )
            
            if settings.debug:
                print(f"[STORY ANALYSIS] Generated tone style chunk")
            
            return response.content.strip()
                
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
        """Generate conflict and stakes chunk."""
        try:
            model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
            
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="multistep/outline/create_conflict_stakes_chunk",
                variables={
                    "prompt": prompt,
                    "base_context": "",
                    "story_elements": ""
                },
                savepoint_id="story_analysis/conflict_stakes_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                log_prompt_inputs=settings.log_prompt_inputs,
                system_message=self.system_message
            )
            
            if settings.debug:
                print(f"[STORY ANALYSIS] Generated conflict stakes chunk")
            
            return response.content.strip()
                
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
        """Generate world rules and logic chunk."""
        try:
            model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
            
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="multistep/outline/create_world_rules_logic_chunk",
                variables={
                    "prompt": prompt,
                    "base_context": "",
                    "story_elements": ""
                },
                savepoint_id="story_analysis/world_rules_logic_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                log_prompt_inputs=settings.log_prompt_inputs,
                system_message=self.system_message
            )
            
            if settings.debug:
                print(f"[STORY ANALYSIS] Generated world rules logic chunk")
            
            return response.content.strip()
                
        except Exception as e:
            if settings.debug:
                print(f"[STORY ANALYSIS] Error generating world rules logic chunk: {e}")
            return ""
    
    async def _index_story_analysis_chunks(
        self,
        chunks: Dict[str, str],
        settings: GenerationSettings
    ) -> None:
        """Index all story analysis chunks in RAG."""
        if not self.rag_integration:
            return
        
        try:
            for chunk_type, chunk_content in chunks.items():
                if chunk_content:
                    await self.rag_integration.index_outline(
                        outline_content=chunk_content,
                        metadata={
                            "content_type": "story_analysis_chunk",
                            "chunk_type": chunk_type,
                            "generation_stage": "story_analysis"
                        }
                    )
            
            if settings.debug:
                print(f"[RAG STORY ANALYSIS] Indexed {len(chunks)} story analysis chunks")
        
        except Exception as e:
            if settings.debug:
                print(f"[RAG STORY ANALYSIS] Error indexing story analysis chunks: {e}")
    
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

    async def _generate_stripped_story_elements(self, story_elements: str, settings: GenerationSettings) -> str:
        """Generate a version of story elements with characters and specific settings removed."""
        model_config = ModelConfig.from_string(self.config["models"]["logical_model"])
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="outline/strip_elements",
            variables={"story_elements": story_elements},
            savepoint_id="story_elements_stripped",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        return response.content.strip()

    async def _generate_initial_outline(
        self,
        prompt: str,
        story_elements: str,
        base_context: str,
        settings: GenerationSettings
    ) -> str:
        """Generate initial story outline with optional chunked generation."""
        # Choose generation method based on settings
        if settings.debug:
            print(f"[OUTLINE GENERATION] use_chunked_outline_generation: {settings.use_chunked_outline_generation}")
            print(f"[OUTLINE GENERATION] wanted_chapters: {settings.wanted_chapters}")
            print(f"[OUTLINE GENERATION] outline_chunk_size: {settings.outline_chunk_size}")
        
        print(f"[OUTLINE GENERATION] Using chunked generation approach")
        return await self._generate_initial_outline_chunked(prompt, story_elements, base_context, settings)
    
    async def _generate_initial_outline_chunked(
        self,
        prompt: str,
        story_elements: str,
        base_context: str,
        settings: GenerationSettings
    ) -> str:
        """Generate initial story outline using chunked approach to handle long chapter lists."""
        if settings.debug:
            print(f"[CHUNKED OUTLINE] Starting chunked skeleton generation for {settings.wanted_chapters} chapters")
        
        # Step 2: Generate chunked outline
        chunked_outline = await self._generate_chunked_outline(
            prompt, story_elements, base_context, settings
        )
        
        # Save the chunked outline as both initial and final if critique is disabled
        if self.savepoint_manager:
            await self.savepoint_manager.save_step("initial_outline", chunked_outline)
            await self.savepoint_manager.save_step("final_outline", chunked_outline)
        
        return chunked_outline
    
    async def _generate_chunked_outline(
        self,
        prompt: str,
        story_elements: str,
        base_context: str,
        settings: GenerationSettings
    ) -> str:
        """Generate chunked outline by processing chapters in manageable chunks."""
        if settings.debug:
            print(f"[CHUNKED OUTLINE] Generating chunked outline for {settings.wanted_chapters} chapters")
        
        # Determine chunk size (process 5-10 chapters at a time)
        chunk_size = min(10, max(5, settings.wanted_chapters // 4))
        total_chunks = (settings.wanted_chapters + chunk_size - 1) // chunk_size
        
        if settings.debug:
            print(f"[CHUNKED OUTLINE] Using chunk size {chunk_size}, total chunks: {total_chunks}")
        
        # Generate outline chunks
        outline_chunks = []
        previous_chunks = ""
        continuity_summary = ""
        
        for chunk_num in range(total_chunks):
            chunk_start = chunk_num * chunk_size + 1
            chunk_end = min((chunk_num + 1) * chunk_size, settings.wanted_chapters)
            
            if settings.debug:
                print(f"[CHUNKED OUTLINE] Processing chunk {chunk_num + 1}/{total_chunks}: chapters {chunk_start}-{chunk_end}")
            
            # Generate chunk outline
            chunk_outline = await self._generate_outline_chunk(
                story_elements, base_context, chunk_start, chunk_end, 
                settings.wanted_chapters, previous_chunks, continuity_summary, 
                settings
            )
            
            outline_chunks.append(chunk_outline)
            previous_chunks += f"\n\n{chunk_outline}"
            
            # Update continuity summary for next chunk
            continuity_summary = await self._analyze_chunk_continuity(
                chunk_outline, previous_chunks, settings
            )
        
        # Combine all chunks into final outline
        final_outline = "\n\n".join(outline_chunks)
        
        if settings.debug:
            print(f"[CHUNKED OUTLINE] Completed chunked outline generation")
        
        return final_outline
    
    async def _generate_outline_chunk(
        self,
        story_elements: str,
        base_context: str,
        chunk_start: int,
        chunk_end: int,
        total_chapters: int,
        previous_chunks: str,
        continuity_summary: str,
        settings: GenerationSettings
    ) -> str:
        """Generate outline for a specific chunk of chapters."""
        model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="outline/create_chunk",
            variables={
                "story_elements": story_elements,
                "base_context": base_context,
                "chunk_start": chunk_start,
                "chunk_end": chunk_end,
                "total_chapters": total_chapters,
                "previous_chunks": previous_chunks,
                "continuity_summary": continuity_summary
            },
            savepoint_id=f"outline_chunk_{chunk_start}_{chunk_end}",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def _analyze_chunk_continuity(
        self,
        chunk_outline: str,
        previous_chunks: str,
        settings: GenerationSettings
    ) -> str:
        """Analyze continuity between chunks to maintain story flow."""
        model_config = ModelConfig.from_string(self.config["models"]["logical_model"])
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="outline/analyze_continuity",
            variables={
                "chunk_outline": chunk_outline,
                "previous_chunks": previous_chunks
            },
            savepoint_id=f"chunk_continuity_analysis",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        return response.content.strip()
