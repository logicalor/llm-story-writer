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

            # Extract story start date
            start_date = await self._extract_story_start_date(prompt, settings, conversation_history)
            
            # Extract base context
            base_context = await self._extract_base_context(prompt, settings, conversation_history)
            
            # Generate story elements
            story_elements = await self._generate_story_elements(prompt, base_context, settings, conversation_history)

            await self.character_manager.generate_character_sheets(story_elements, base_context, settings)
            await self.setting_manager.generate_setting_sheets(story_elements, base_context, settings)
            await self._generate_stripped_story_elements(story_elements, settings)

            enrichment_suggestions = await self._analyze_story_enrichment(
                prompt, story_elements, base_context, settings
            )
            
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
            
            # Generate detailed chapter list (now handled in chunked generation)
            # For single-pass generation, we still need to generate the chapter list
            if not settings.use_chunked_outline_generation:
                chapter_list = await self._generate_chapter_list(
                    final_outline, base_context, stripped_story_elements, settings
                )
            else:
                # For chunked generation, we need to extract chapters and generate synopses
                # This will return a formatted chapter list string
                chapter_list = await self._generate_chapter_synopses(
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
    
    async def _extract_story_start_date(self, prompt: str, settings: GenerationSettings, conversation_history: list) -> str:
        """Extract story start date from prompt."""
        model_config = ModelConfig.from_string(self.config["models"]["creative_model"])

        story_start_date_prompt = self.prompt_handler.prompt_loader.load_prompt("multistep/outline/story_start_date")
        conversation_history.append({"role": "user", "content": story_start_date_prompt})

        response = await execute_messages_with_savepoint(
            handler=self.prompt_handler,
            conversation_history=conversation_history,
            savepoint_id="story_start_date",
            model_config=model_config,
            debug=settings.debug,
            stream=True,
            use_boxed_solution=True
        )
        
        conversation_history.append({"role": "assistant", "content": response.content.strip()})

        return response.content.strip()
    
    async def _extract_base_context(self, prompt: str, settings: GenerationSettings, conversation_history: list) -> str:
        """Extract important base context from prompt."""
        model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])

        base_context_prompt = self.prompt_handler.prompt_loader.load_prompt("multistep/outline/base_context", {
            "prompt": prompt,
        })
        conversation_history.append({"role": "user", "content": base_context_prompt})
        
        
        response = await execute_messages_with_savepoint(
            handler=self.prompt_handler,
            conversation_history=conversation_history,
            savepoint_id="base_context",
            model_config=model_config,
            debug=settings.debug,
            stream=True,
            use_boxed_solution=True
        )
        
        conversation_history.append({"role": "assistant", "content": response.content.strip()})

        return response.content.strip()
    
    async def _generate_story_elements(self, prompt: str, base_context: str, settings: GenerationSettings, conversation_history: list) -> str:
        """Generate story elements from prompt."""
        model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
        
        elements_prompt = self.prompt_handler.prompt_loader.load_prompt("multistep/outline/story_elements", {
            "prompt": prompt,
            "base_context": base_context,
        })
        conversation_history.append({"role": "user", "content": elements_prompt})

        response = await execute_messages_with_savepoint(
            handler=self.prompt_handler,
            conversation_history=conversation_history,
            savepoint_id="story_elements",
            model_config=model_config,
            debug=settings.debug,
            stream=True,
            use_boxed_solution=True
        )
        
        conversation_history.append({"role": "assistant", "content": response.content.strip()})

        story_elements = response.content.strip()

        return story_elements
    
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
    
    async def _get_story_elements_for_prompts(self) -> str:
        """Get the stripped story elements for use in prompts (without characters/settings)."""
        if self.savepoint_manager and await self.savepoint_manager.has_step("story_elements_stripped"):
            return await self.savepoint_manager.load_step("story_elements_stripped")
        else:
            # Fallback to original story elements if stripped version doesn't exist
            return await self.savepoint_manager.load_step("story_elements")
    

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
        
        # Step 1: Analyze story enrichment opportunities
        enrichment_suggestions = await self._analyze_story_enrichment(
            prompt, story_elements, base_context, settings
        )
        
        # Step 2: Generate chunked outline
        chunked_outline = await self._generate_chunked_outline(
            prompt, story_elements, base_context, enrichment_suggestions, settings
        )
        
        # Apply iterative critique refinement if enabled
        if settings.enable_outline_critique:
            from application.services.critique_service import CritiqueService
            critique_service = CritiqueService(self.model_provider, self.config, self.prompt_handler.prompt_loader)
            
            # Save the initial outline
            if self.savepoint_manager:
                await self.savepoint_manager.save_step("initial_outline", chunked_outline)
            
            refined_outline = await critique_service.refine_outline_iteratively(
                initial_outline=chunked_outline,
                story_elements=story_elements,
                base_context=base_context,
                prompt=prompt,
                settings=settings,
                max_iterations=settings.outline_critique_iterations,
                savepoint_manager=self.savepoint_manager
            )
            
            # Save the final refined outline
            if self.savepoint_manager:
                await self.savepoint_manager.save_step("final_outline", refined_outline)
            
            return refined_outline
        else:
            # Save the chunked outline as both initial and final if critique is disabled
            if self.savepoint_manager:
                await self.savepoint_manager.save_step("initial_outline", chunked_outline)
                await self.savepoint_manager.save_step("final_outline", chunked_outline)
            
            return chunked_outline
    
    async def _analyze_story_enrichment(
        self,
        prompt: str,
        story_elements: str,
        base_context: str,
        settings: GenerationSettings
    ) -> str:
        """Analyze opportunities to enrich the story using a multistep approach."""
        model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])

        # First extract the characters and setting names from the story elements
        characters = await self.character_manager.extract_character_names(story_elements, settings)
        setting_names = await self.setting_manager.extract_setting_names(story_elements, settings)

        # Then get character summaries
        character_summaries = await self.character_manager.get_character_summaries(characters, settings)

        # Then get setting summaries
        setting_summaries = await self.setting_manager.get_setting_summaries(setting_names, settings)
        
        # Build conversation history through multistep approach
        conversation_history = []
        
        # Step 1: Understand story elements
        story_elements_prompt = self.prompt_handler.prompt_loader.load_prompt(
            "multistep/outline/enrichment/understand_story_elements",
            {"story_elements": story_elements}
        )
        conversation_history.append({"role": "user", "content": story_elements_prompt})
        
        response = await execute_messages_with_savepoint(
            handler=self.prompt_handler,
            conversation_history=conversation_history,
            savepoint_id="enrichment_step1_story_elements",
            model_config=model_config,
            debug=settings.debug,
            stream=settings.stream
        )
        conversation_history.append({"role": "assistant", "content": response.content.strip()})
        
        # Step 2: Understand base context
        base_context_prompt = self.prompt_handler.prompt_loader.load_prompt(
            "multistep/outline/enrichment/understand_base_context",
            {"base_context": base_context}
        )
        conversation_history.append({"role": "user", "content": base_context_prompt})
        
        response = await execute_messages_with_savepoint(
            handler=self.prompt_handler,
            conversation_history=conversation_history,
            savepoint_id="enrichment_step2_base_context",
            model_config=model_config,
            debug=settings.debug,
            stream=settings.stream
        )
        conversation_history.append({"role": "assistant", "content": response.content.strip()})
        
        # Step 3: Understand character summaries
        character_summaries_prompt = self.prompt_handler.prompt_loader.load_prompt(
            "multistep/outline/enrichment/understand_character_summaries",
            {"character_summaries": character_summaries}
        )
        conversation_history.append({"role": "user", "content": character_summaries_prompt})
        
        response = await execute_messages_with_savepoint(
            handler=self.prompt_handler,
            conversation_history=conversation_history,
            savepoint_id="enrichment_step3_character_summaries",
            model_config=model_config,
            debug=settings.debug,
            stream=settings.stream
        )
        conversation_history.append({"role": "assistant", "content": response.content.strip()})
        
        # Step 4: Understand setting summaries
        setting_summaries_prompt = self.prompt_handler.prompt_loader.load_prompt(
            "multistep/outline/enrichment/understand_setting_summaries",
            {"setting_summaries": setting_summaries}
        )
        conversation_history.append({"role": "user", "content": setting_summaries_prompt})
        
        response = await execute_messages_with_savepoint(
            handler=self.prompt_handler,
            conversation_history=conversation_history,
            savepoint_id="enrichment_step4_setting_summaries",
            model_config=model_config,
            debug=settings.debug,
            stream=settings.stream
        )
        conversation_history.append({"role": "assistant", "content": response.content.strip()})
        
        # Step 5: Analyze enrichment opportunities
        analyze_enrichment_prompt = self.prompt_handler.prompt_loader.load_prompt(
            "multistep/outline/enrichment/analyze_enrichment",
            {"desired_chapters": settings.wanted_chapters}
        )
        conversation_history.append({"role": "user", "content": analyze_enrichment_prompt})
        
        response = await execute_messages_with_savepoint(
            handler=self.prompt_handler,
            conversation_history=conversation_history,
            savepoint_id="enrichment_suggestions",
            model_config=model_config,
            debug=settings.debug,
            stream=settings.stream
        )
        
        return response.content.strip()
    
    async def _generate_outline_skeleton(
        self,
        prompt: str,
        story_elements: str,
        base_context: str,
        enrichment_suggestions: str,
        settings: GenerationSettings
    ) -> str:
        """Generate the main outline skeleton."""
        model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="outline/create_skeleton",
            variables={
                "prompt": prompt,
                "story_elements": story_elements,
                "base_context": base_context,
                "enrichment_suggestions": enrichment_suggestions,
                "desired_chapters": settings.wanted_chapters
            },
            savepoint_id="outline_skeleton",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message,
            min_word_count=500
        )
        
        return response.content.strip()
    
    async def _generate_chunked_outline(
        self,
        prompt: str,
        story_elements: str,
        base_context: str,
        enrichment_suggestions: str,
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
                enrichment_suggestions, settings
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
        enrichment_suggestions: str,
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
                "continuity_summary": continuity_summary,
                "enrichment_suggestions": enrichment_suggestions
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
    

    
    async def _generate_chapter_synopses(
        self,
        combined_outline: str,
        base_context: str,
        story_elements: str,
        settings: GenerationSettings
    ) -> str:
        """Extract chapters from combined outline and generate synopses for each."""
        if settings.debug:
            print(f"[CHAPTER SYNOPSES] Generating synopses for chapters from combined outline")
        
        # Step 1: Extract chapters as JSON list from the combined outline
        chapter_list = await self._extract_chapters_from_outline(
            combined_outline, base_context, story_elements, settings
        )
        
        # Step 2: Generate synopsis for each chapter
        synopses = []
        for chapter_data in chapter_list:
            chapter_num = chapter_data.get("number", len(synopses) + 1)
            chapter_title = chapter_data.get("title", f"Chapter {chapter_num}")
            chapter_description = chapter_data.get("description", "")
            
            if settings.debug:
                print(f"[CHAPTER SYNOPSES] Generating synopsis for Chapter {chapter_num}: {chapter_title}")
            
            # Generate synopsis for this chapter
            synopsis = await self._generate_single_chapter_synopsis(
                chapter_num, chapter_title, chapter_description,
                combined_outline, base_context, story_elements, settings
            )
            
            synopses.append(synopsis)
            
            # Save synopsis to savepoint
            if self.savepoint_manager:
                await self.savepoint_manager.save_step(f"chapter_{chapter_num}/synopsis", synopsis)
        
        if settings.debug:
            print(f"[CHAPTER SYNOPSES] Completed generating {len(synopses)} chapter synopses")
        
        # Return a formatted chapter list string for the main method to use
        chapter_list_text = []
        for chapter_data in chapter_list:
            chapter_num = chapter_data.get("number", 0)
            chapter_title = chapter_data.get("title", f"Chapter {chapter_num}")
            chapter_description = chapter_data.get("description", "")
            chapter_list_text.append(f"## Chapter {chapter_num}: {chapter_title}\n{chapter_description}")
        
        return "\n\n".join(chapter_list_text)
    
    async def _extract_chapters_from_outline(
        self,
        combined_outline: str,
        base_context: str,
        story_elements: str,
        settings: GenerationSettings
    ) -> List[Dict[str, Any]]:
        """Extract chapters from combined outline as a structured list."""
        model_config = ModelConfig.from_string(self.config["models"]["creative_model"])
        
        # Define JSON schema for chapter list
        CHAPTER_LIST_SCHEMA = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "number": {"type": "integer"},
                    "title": {"type": "string"},
                    "description": {"type": "string"}
                },
                "required": ["number", "title", "description"]
            }
        }
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="chapters/extract_list",
            variables={
                "outline": combined_outline,
                "base_context": base_context,
                "story_elements": story_elements
            },
            savepoint_id="extracted_chapters",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message,
            expect_json=True,
            json_schema=CHAPTER_LIST_SCHEMA
        )
        
        # Parse the response using the new JSON integration
        if response.json_parsed:
            # llm-output-parser has already successfully parsed the JSON
            # The content should now be a clean JSON string that we can parse
            try:
                # Validate the parsed JSON
                chapter_list = json.loads(response.content.strip())
                if not isinstance(chapter_list, list):
                    raise ValueError("Response is not a list")
                
                if settings.debug:
                    print(f"[CHAPTER SYNOPSES] Successfully parsed {len(chapter_list)} chapters from JSON")
                return chapter_list
                
            except (json.JSONDecodeError, ValueError) as e:
                if settings.debug:
                    print(f"[CHAPTER SYNOPSES] JSON validation failed: {e}")
                    print(f"[CHAPTER SYNOPSES] Raw response: {response.content}")
                
                # Fallback: create a simple list from the outline
                return self._fallback_chapter_extraction(combined_outline)
        else:
            if settings.debug:
                print(f"[CHAPTER SYNOPSES] JSON parsing failed: {response.json_errors}")
                print(f"[CHAPTER SYNOPSES] Raw response preview: {response.content[:200]}...")
            
            # Fallback: create a simple list from the outline
            return self._fallback_chapter_extraction(combined_outline)
    
    async def _generate_single_chapter_synopsis(
        self,
        chapter_num: int,
        chapter_title: str,
        chapter_description: str,
        combined_outline: str,
        base_context: str,
        story_elements: str,
        settings: GenerationSettings
    ) -> str:
        """Generate synopsis for a single chapter using a multistep approach."""
        model_config = ModelConfig.from_string(self.config["models"]["chapter_outline_writer"])
        
        # Get previous chapter synopsis if this is not the first chapter
        previous_chapter = ""
        if chapter_num > 1 and self.savepoint_manager:
            try:
                previous_chapter = await self.savepoint_manager.load_step(f"chapter_{chapter_num-1}/synopsis")
            except:
                if settings.debug:
                    print(f"[CHAPTER SYNOPSES] Could not load previous chapter synopsis for chapter {chapter_num}")
                previous_chapter = ""
        
        # Build conversation history through multistep approach
        conversation_history = []
        
        # Step 1: Understand storyline
        storyline_prompt = self.prompt_handler.prompt_loader.load_prompt(
            "multistep/chapter/enrichment/understand_storyline",
            {"story_elements": story_elements}
        )
        conversation_history.append({"role": "user", "content": storyline_prompt})
        
        response = await execute_messages_with_savepoint(
            handler=self.prompt_handler,
            conversation_history=conversation_history,
            savepoint_id=f"chapter_{chapter_num}_step1_storyline",
            model_config=model_config,
            debug=settings.debug,
            stream=settings.stream
        )
        conversation_history.append({"role": "assistant", "content": response.content.strip()})
        
        # Step 2: Understand base context
        base_context_prompt = self.prompt_handler.prompt_loader.load_prompt(
            "multistep/chapter/enrichment/understand_base_context",
            {"base_context": base_context}
        )
        conversation_history.append({"role": "user", "content": base_context_prompt})
        
        response = await execute_messages_with_savepoint(
            handler=self.prompt_handler,
            conversation_history=conversation_history,
            model_config=model_config,
            debug=settings.debug,
            stream=settings.stream
        )
        conversation_history.append({"role": "assistant", "content": response.content.strip()})
        
        # Step 3: Understand combined outline
        outline_prompt = self.prompt_handler.prompt_loader.load_prompt(
            "multistep/chapter/enrichment/understand_outline",
            {"outline": combined_outline}
        )
        conversation_history.append({"role": "user", "content": outline_prompt})
        
        response = await execute_messages_with_savepoint(
            handler=self.prompt_handler,
            conversation_history=conversation_history,
            model_config=model_config,
            debug=settings.debug,
            stream=settings.stream
        )
        conversation_history.append({"role": "assistant", "content": response.content.strip()})
        
        # Step 4: Understand characters (combined abridged characters)
        characters = await self.character_manager.extract_character_names(story_elements, settings)
        character_summaries = await self.character_manager.get_character_summaries(characters, settings)
        character_prompt = self.prompt_handler.prompt_loader.load_prompt(
            "multistep/chapter/enrichment/understand_characters",
            {"character_summaries": character_summaries}
        )
        conversation_history.append({"role": "user", "content": character_prompt})
        
        response = await execute_messages_with_savepoint(
            handler=self.prompt_handler,
            conversation_history=conversation_history,
            model_config=model_config,
            debug=settings.debug,
            stream=settings.stream
        )
        conversation_history.append({"role": "assistant", "content": response.content.strip()})
        
        # Step 5: Understand settings (combined abridged settings)
        setting_names = await self.setting_manager.extract_setting_names(story_elements, settings)
        setting_summaries = await self.setting_manager.get_setting_summaries(setting_names, settings)
        setting_prompt = self.prompt_handler.prompt_loader.load_prompt(
            "multistep/chapter/enrichment/understand_settings",
            {"setting_summaries": setting_summaries}
        )
        conversation_history.append({"role": "user", "content": setting_prompt})
        
        response = await execute_messages_with_savepoint(
            handler=self.prompt_handler,
            conversation_history=conversation_history,
            model_config=model_config,
            debug=settings.debug,
            stream=settings.stream
        )
        conversation_history.append({"role": "assistant", "content": response.content.strip()})
        
        # Step 6: Understand previous chapter synopsis (if chapter > 1)
        if chapter_num > 1 and previous_chapter:
            previous_chapter_prompt = self.prompt_handler.prompt_loader.load_prompt(
                "multistep/chapter/enrichment/understand_previous_chapter",
                {"previous_chapter": previous_chapter}
            )
            conversation_history.append({"role": "user", "content": previous_chapter_prompt})
            
            response = await execute_messages_with_savepoint(
                handler=self.prompt_handler,
                conversation_history=conversation_history,
                model_config=model_config,
                debug=settings.debug,
                stream=settings.stream
            )
            conversation_history.append({"role": "assistant", "content": response.content.strip()})
        
        # Step 7: Generate the chapter synopsis
        synopsis_prompt = self.prompt_handler.prompt_loader.load_prompt(
            "multistep/chapter/create_synopsis",
            {
                "chapter_number": chapter_num,
                "chapter_title": chapter_title,
                "chapter_description": chapter_description,
            }
        )
        conversation_history.append({"role": "user", "content": synopsis_prompt})
        
        response = await execute_messages_with_savepoint(
            handler=self.prompt_handler,
            conversation_history=conversation_history,
            savepoint_id=f"chapter_{chapter_num}/synopsis",
            model_config=model_config,
            debug=settings.debug,
            stream=settings.stream
        )
        
        return response.content.strip()
    
    def _fallback_chapter_extraction(self, combined_outline: str) -> List[Dict[str, Any]]:
        """Fallback method to extract chapters when JSON parsing fails."""
        chapters = []
        lines = combined_outline.split('\n')
        current_chapter = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('## Chapter') or line.startswith('Chapter'):
                # Extract chapter number and title
                parts = line.split(':', 1)
                if len(parts) == 2:
                    chapter_title = parts[1].strip()
                else:
                    chapter_title = line
                
                current_chapter = {
                    "number": len(chapters) + 1,
                    "title": chapter_title,
                    "description": ""
                }
                chapters.append(current_chapter)
            elif current_chapter and line:
                # Add description lines to current chapter
                if current_chapter["description"]:
                    current_chapter["description"] += " " + line
                else:
                    current_chapter["description"] = line
        
        return chapters
    
    async def _generate_chapter_list(
        self,
        final_outline: str,
        base_context: str,
        story_elements: str,
        settings: GenerationSettings
    ) -> str:
        """Generate detailed chapter list from outline (for single-pass generation)."""
        model_config = ModelConfig.from_string(self.config["models"]["chapter_outline_writer"])
        
        # Define JSON schema for chapter list
        CHAPTER_LIST_SCHEMA = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "number": {"type": "integer"},
                    "title": {"type": "string"},
                    "description": {"type": "string"}
                },
                "required": ["number", "title", "description"]
            }
        }

        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="chapters/create_list",
            variables={
                "combined_outline": final_outline,
                "base_context": base_context,
                "story_elements": story_elements
            },
            savepoint_id="chapter_list",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message,
            expect_json=True,
            json_schema=CHAPTER_LIST_SCHEMA
        )
        
        # Parse the response using the new JSON integration
        if response.json_parsed:
            # llm-output-parser has already successfully parsed the JSON
            # The content should now be a clean JSON string that we can parse
            try:
                # Validate the parsed JSON
                chapter_list = json.loads(response.content.strip())
                if not isinstance(chapter_list, list):
                    raise ValueError("Response is not a list")
                
                if settings.debug:
                    print(f"[CHAPTER SYNOPSES] Successfully parsed {len(chapter_list)} chapters from JSON")
                return chapter_list
                
            except (json.JSONDecodeError, ValueError) as e:
                if settings.debug:
                    print(f"[CHAPTER SYNOPSES] JSON validation failed: {e}")
                    print(f"[CHAPTER SYNOPSES] Raw response: {response.content}")
                
                # Fallback: create a simple list from the outline
                return self._fallback_chapter_extraction(final_outline)
        else:
            if settings.debug:
                print(f"[CHAPTER SYNOPSES] JSON parsing failed: {response.json_errors}")
            
            # Fallback: create a simple list from the outline
            return self._fallback_chapter_extraction(final_outline)