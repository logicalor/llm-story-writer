"""Character management functionality for the outline-chapter strategy."""

import json
from typing import List, Optional, Dict, Any
from domain.value_objects.generation_settings import GenerationSettings
from domain.value_objects.model_config import ModelConfig

from application.interfaces.model_provider import ModelProvider
from infrastructure.prompts.prompt_handler import PromptHandler
from infrastructure.prompts.prompt_wrapper import execute_prompt_with_savepoint, execute_messages_with_savepoint
from infrastructure.savepoints import SavepointManager
from application.services.rag_service import RAGService
from application.services.rag_integration_service import RAGIntegrationService


class CharacterManager:
    """Handles character generation, extraction, and management functionality."""
    
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
    
    async def generate_character_sheets(self, story_elements: str, additional_context: str, settings: GenerationSettings) -> None:
        """Generate character sheets for all characters identified in story elements."""
        try:
            # Extract character names from story elements
            character_names = await self.extract_character_names(story_elements, settings)
            
            if settings.debug:
                print(f"[CHARACTER SHEETS] Found {len(character_names)} characters: {character_names}")
            
            # Generate sheet for each character
            for character_name in character_names:
                if settings.debug:
                    print(f"[CHARACTER SHEETS] Generating sheet for: {character_name}")
                
                await self.generate_single_character_sheet(character_name, story_elements, additional_context, settings)
        
        except Exception as e:
            if settings.debug:
                print(f"[CHARACTER SHEETS] Error generating character sheets: {e}")
            # Don't fail the entire process if character sheet generation fails
            pass
    
    async def extract_character_names(self, story_elements: str, settings: GenerationSettings) -> List[str]:
        """Extract character names from story elements."""
        model_config = ModelConfig.from_string(self.config["models"]["logical_model"])
        
        # Define JSON schema for character names
        CHARACTER_NAMES_SCHEMA = {
            "type": "array",
            "items": {"type": "string"}
        }

        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="characters/extract_names",
            variables={"story_elements": story_elements},
            savepoint_id="character_names",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message,
            expect_json=True,
            json_schema=CHARACTER_NAMES_SCHEMA
        )
        
        # Parse the response using the new JSON integration
        names_text = response.content.strip()
        character_names = []
        
        if response.json_parsed:
            # llm-output-parser has already successfully parsed the JSON
            # The content should now be a clean JSON string that we can parse
            try:
                parsed_names = json.loads(names_text)
                if isinstance(parsed_names, list):
                    character_names = [str(name).strip() for name in parsed_names if name and str(name).strip()]
                    if settings.debug:
                        print(f"[CHARACTER NAMES] Successfully parsed JSON: {character_names}")
                else:
                    if settings.debug:
                        print(f"[CHARACTER NAMES] Expected list but got: {type(parsed_names)}")
            except (json.JSONDecodeError, AttributeError) as e:
                if settings.debug:
                    print(f"[CHARACTER NAMES] JSON parsing failed: {e}, falling back to line parsing")
                character_names = []
        else:
            if settings.debug:
                print(f"[CHARACTER NAMES] JSON parsing failed: {response.json_errors}, falling back to line parsing")
                print(f"[CHARACTER NAMES] Raw response preview: {names_text[:200]}...")
            character_names = []
        
        # Fallback to line-by-line parsing if JSON parsing failed
        if not character_names:
            # Since llm-output-parser handles markdown automatically, 
            # we can use simpler line parsing as fallback
            for line in names_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-') and not line.startswith('```'):
                    # Remove any bullet points, numbers, or other formatting
                    clean_name = line.replace('*', '').replace('-', '').replace('•', '')
                    clean_name = clean_name.strip()
                    if clean_name and len(clean_name) < 50:  # Reasonable name length
                        character_names.append(clean_name)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_names = []
        for name in character_names:
            if name.lower() not in seen:
                seen.add(name.lower())
                unique_names.append(name)
        
        return unique_names[:10]  # Limit to 10 characters max
    
    async def generate_single_character_sheet(self, character_name: str, story_elements: str, additional_context: str, settings: GenerationSettings) -> None:
        """Generate a character sheet for a single character using multistep conversation for optimal RAG indexing."""
        model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
        
        try:
            # Start the conversation with the character creation prompt
            character_creation_prompt = self.prompt_handler.prompt_loader.load_prompt("characters/create", {
                "character_name": character_name,
                "story_elements": story_elements,
                "additional_context": additional_context
            })
            
            conversation = [
                {
                    "role": "system",
                    "content": self.system_message
                },
                {
                    "role": "user", 
                    "content": character_creation_prompt
                }
            ]
            
            # Execute the initial character creation step
            response = await execute_messages_with_savepoint(
                handler=self.prompt_handler,
                conversation_history=conversation,
                savepoint_id=f"characters/{character_name}/sheet",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream
            )
            
            # Append the response to continue the conversation
            conversation.append({
                "role": "assistant",
                "content": response.content
            })
            
            if settings.debug:
                print(f"[CHARACTER SHEET] Generated initial sheet for {character_name}")
            
            # Generate chunked character information using the conversation
            await self._generate_character_chunks(character_name, conversation, settings)
            
            # Character chunks are now indexed individually after generation
                
        except Exception as e:
            if settings.debug:
                print(f"[CHARACTER SHEET] Error generating sheet for {character_name}: {e}")
    
    async def _generate_character_chunks(
        self, 
        character_name: str, 
        conversation: List[Dict[str, str]], 

        settings: GenerationSettings
    ) -> None:
        """Generate focused character chunks for optimal RAG indexing using conversation continuation."""
        try:
            # Generate each chunk using specialized prompts, passing a copy of the conversation
            await self._generate_personality_chunk(character_name, conversation.copy(), settings)
            await self._generate_background_chunk(character_name, conversation.copy(), settings)
            await self._generate_motivations_chunk(character_name, conversation.copy(), settings)
            await self._generate_relationships_chunk(character_name, conversation.copy(), settings)
            await self._generate_skills_chunk(character_name, conversation.copy(), settings)
            await self._generate_current_state_chunk(character_name, conversation.copy(), settings)
            await self._generate_growth_arc_chunk(character_name, conversation.copy(), settings)
            
            if settings.debug:
                print(f"[CHARACTER CHUNKS] Generated all chunks for {character_name}")
                
        except Exception as e:
            if settings.debug:
                print(f"[CHARACTER CHUNKS] Error generating chunks for {character_name}: {e}")
    
    async def _generate_personality_chunk(
        self, 
        character_name: str, 
        conversation: List[Dict[str, str]], 
        settings: GenerationSettings
    ) -> None:
        """Generate personality chunk focusing on core traits and behavioral patterns."""
        model_config = ModelConfig.from_string(self.config["models"]["logical_model"])
        
        try:
            # Continue the conversation with the personality chunk prompt
            personality_prompt = self.prompt_handler.prompt_loader.load_prompt("characters/create_personality_chunk", {
                "character_name": character_name,
            })
            
            conversation.append({
                "role": "user",
                "content": personality_prompt
            })
            
            response = await execute_messages_with_savepoint(
                handler=self.prompt_handler,
                conversation_history=conversation,
                savepoint_id=f"characters/{character_name}/personality_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream
            )
            
            if settings.debug:
                print(f"[CHARACTER CHUNK] Generated personality chunk for {character_name}")
            
            # Index this chunk immediately after generation
            await self._index_character_chunk(character_name, "personality_chunk", settings)
                
        except Exception as e:
            if settings.debug:
                print(f"[CHARACTER CHUNK] Error generating personality chunk for {character_name}: {e}")
    
    async def _index_character_chunk(self, character_name: str, chunk_type: str, settings: GenerationSettings) -> None:
        """Index a character chunk in RAG."""
        if not self.rag_integration or not self.savepoint_manager:
            return
            
        try:
            chunk_key = f"characters/{character_name}/{chunk_type}"
            chunk_content = await self.savepoint_manager.load_step(chunk_key)
            
            if chunk_content:
                # Index each chunk with appropriate metadata
                chunk_ids = await self.rag_integration.index_character(
                    character_content=chunk_content,
                    character_name=character_name,
                    metadata={
                        "character_name": character_name,
                        "content_type": "character_chunk",
                        "chunk_type": chunk_type.replace("_chunk", ""),
                        "generation_stage": "outline"
                    }
                )
                
                if settings.debug:
                    print(f"[RAG CHARACTER INDEXING] Indexed {len(chunk_ids)} chunks for {character_name} - {chunk_type}")
        except Exception as e:
            if settings.debug:
                print(f"[RAG CHARACTER INDEXING] Could not index {chunk_type} for {character_name}: {e}")

    async def _generate_background_chunk(
        self, 
        character_name: str, 
        conversation: List[Dict[str, str]], 
        settings: GenerationSettings
    ) -> None:
        """Generate background chunk focusing on history and formative experiences."""
        model_config = ModelConfig.from_string(self.config["models"]["logical_model"])
        
        try:
            # Continue the conversation with the background chunk prompt
            background_prompt = self.prompt_handler.prompt_loader.load_prompt("characters/create_background_chunk", {
                "character_name": character_name,
            })
            
            conversation.append({
                "role": "user",
                "content": background_prompt
            })
            
            response = await execute_messages_with_savepoint(
                handler=self.prompt_handler,
                conversation_history=conversation,
                savepoint_id=f"characters/{character_name}/background_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream
            )
            
            if settings.debug:
                print(f"[CHARACTER CHUNK] Generated background chunk for {character_name}")
            
            # Index this chunk immediately after generation
            await self._index_character_chunk(character_name, "background_chunk", settings)
                
        except Exception as e:
            if settings.debug:
                print(f"[CHARACTER CHUNK] Error generating background chunk for {character_name}: {e}")
    
    async def _generate_motivations_chunk(
        self, 
        character_name: str, 
        conversation: List[Dict[str, str]], 
        settings: GenerationSettings
    ) -> None:
        """Generate motivations chunk focusing on goals, driving forces, and values."""
        model_config = ModelConfig.from_string(self.config["models"]["logical_model"])
        
        try:
            # Continue the conversation with the motivations chunk prompt
            motivations_prompt = self.prompt_handler.prompt_loader.load_prompt("characters/create_motivations_chunk", {
                "character_name": character_name,
            })
            
            conversation.append({
                "role": "user",
                "content": motivations_prompt
            })
            
            response = await execute_messages_with_savepoint(
                handler=self.prompt_handler,
                conversation_history=conversation,
                savepoint_id=f"characters/{character_name}/motivations_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream
            )
            
            if settings.debug:
                print(f"[CHARACTER CHUNK] Generated motivations chunk for {character_name}")
            
            # Index this chunk immediately after generation
            await self._index_character_chunk(character_name, "motivations_chunk", settings)
                
        except Exception as e:
            if settings.debug:
                print(f"[CHARACTER CHUNK] Error generating motivations chunk for {character_name}: {e}")
    
    async def _generate_relationships_chunk(
        self, 
        character_name: str, 
        conversation: List[Dict[str, str]], 
        settings: GenerationSettings
    ) -> None:
        """Generate relationships chunk focusing on connections with other characters."""
        model_config = ModelConfig.from_string(self.config["models"]["logical_model"])
        
        try:
            # Continue the conversation with the relationships chunk prompt
            relationships_prompt = self.prompt_handler.prompt_loader.load_prompt("characters/create_relationships_chunk", {
                "character_name": character_name,
            })
            
            conversation.append({
                "role": "user",
                "content": relationships_prompt
            })
            
            response = await execute_messages_with_savepoint(
                handler=self.prompt_handler,
                conversation_history=conversation,
                savepoint_id=f"characters/{character_name}/relationships_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream
            )
            
            if settings.debug:
                print(f"[CHARACTER CHUNK] Generated relationships chunk for {character_name}")
            
            # Index this chunk immediately after generation
            await self._index_character_chunk(character_name, "relationships_chunk", settings)
                
        except Exception as e:
            if settings.debug:
                print(f"[CHARACTER CHUNK] Error generating relationships chunk for {character_name}: {e}")
    
    async def _generate_skills_chunk(
        self, 
        character_name: str, 
        conversation: List[Dict[str, str]], 
        settings: GenerationSettings
    ) -> None:
        """Generate skills chunk focusing on competencies, talents, and limitations."""
        model_config = ModelConfig.from_string(self.config["models"]["logical_model"])
        
        try:
            # Continue the conversation with the skills chunk prompt
            skills_prompt = self.prompt_handler.prompt_loader.load_prompt("characters/create_skills_chunk", {
                "character_name": character_name,
            })
            
            conversation.append({
                "role": "user",
                "content": skills_prompt
            })
            
            response = await execute_messages_with_savepoint(
                handler=self.prompt_handler,
                conversation_history=conversation,
                savepoint_id=f"characters/{character_name}/skills_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream
            )
            
            if settings.debug:
                print(f"[CHARACTER CHUNK] Generated skills chunk for {character_name}")
            
            # Index this chunk immediately after generation
            await self._index_character_chunk(character_name, "skills_chunk", settings)
                
        except Exception as e:
            if settings.debug:
                print(f"[CHARACTER CHUNK] Error generating skills chunk for {character_name}: {e}")
    
    async def _generate_current_state_chunk(
        self, 
        character_name: str, 
        conversation: List[Dict[str, str]], 
        settings: GenerationSettings
    ) -> None:
        """Generate current state chunk focusing on present circumstances and emotional state."""
        model_config = ModelConfig.from_string(self.config["models"]["logical_model"])
        
        try:
            # Continue the conversation with the current state chunk prompt
            current_state_prompt = self.prompt_handler.prompt_loader.load_prompt("characters/create_current_state_chunk", {
                "character_name": character_name,
            })
            
            conversation.append({
                "role": "user",
                "content": current_state_prompt
            })
            
            response = await execute_messages_with_savepoint(
                handler=self.prompt_handler,
                conversation_history=conversation,
                savepoint_id=f"characters/{character_name}/current_state_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream
            )
            
            if settings.debug:
                print(f"[CHARACTER CHUNK] Generated current state chunk for {character_name}")
            
            # Index this chunk immediately after generation
            await self._index_character_chunk(character_name, "current_state_chunk", settings)
                
        except Exception as e:
            if settings.debug:
                print(f"[CHARACTER CHUNK] Error generating current state chunk for {character_name}: {e}")
    
    async def _generate_growth_arc_chunk(
        self, 
        character_name: str, 
        conversation: List[Dict[str, str]], 
        settings: GenerationSettings
    ) -> None:
        """Generate growth arc chunk focusing on development patterns and character evolution."""
        model_config = ModelConfig.from_string(self.config["models"]["logical_model"])
        
        try:
            # Continue the conversation with the growth arc chunk prompt
            growth_arc_prompt = self.prompt_handler.prompt_loader.load_prompt("characters/create_growth_arc_chunk", {
                "character_name": character_name,
            })
            
            conversation.append({
                "role": "user",
                "content": growth_arc_prompt
            })
            
            response = await execute_messages_with_savepoint(
                handler=self.prompt_handler,
                conversation_history=conversation,
                savepoint_id=f"characters/{character_name}/growth_arc_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream
            )
            
            if settings.debug:
                print(f"[CHARACTER CHUNK] Generated growth arc chunk for {character_name}")
            
            # Index this chunk immediately after generation
            await self._index_character_chunk(character_name, "growth_arc_chunk", settings)
                
        except Exception as e:
            if settings.debug:
                print(f"[CHARACTER CHUNK] Error generating growth arc chunk for {character_name}: {e}")
    

    async def index_character_in_rag(
        self, 
        character_name: str, 
        settings: GenerationSettings
    ) -> None:
        """Index character content in RAG from savepoint manager. Can be called by other modules."""
        if not self.rag_integration or not self.savepoint_manager:
            return
        
        try:
            # Clean up existing character chunks before reindexing
            try:
                deleted_count = await self.rag_integration.cleanup_content_by_type_and_metadata(
                    content_type="character",
                    metadata_filters={
                        "character_name": character_name
                    }
                )
                if settings.debug:
                    print(f"[RAG CHARACTER INDEXING] Cleaned up {deleted_count} existing chunks for character '{character_name}' before reindexing")
            except Exception as e:
                if settings.debug:
                    print(f"[RAG CHARACTER INDEXING] Warning: Failed to cleanup existing chunks for '{character_name}': {e}")
                # Continue with indexing even if cleanup fails
            

            
            # Index all character chunks for optimal RAG retrieval
            chunk_types = [
                "personality_chunk",
                "background_chunk", 
                "motivations_chunk",
                "relationships_chunk",
                "skills_chunk",
                "current_state_chunk",
                "growth_arc_chunk"
            ]
            
            for chunk_type in chunk_types:
                try:
                    chunk_key = f"characters/{character_name}/{chunk_type}"
                    chunk_content = await self.savepoint_manager.load_step(chunk_key)
                    
                    if chunk_content:
                        # Index each chunk with appropriate metadata
                        chunk_ids = await self.rag_integration.index_character(
                            character_content=chunk_content,
                            character_name=character_name,
                            metadata={
                                "character_name": character_name,
                                "content_type": "character_chunk",
                                "chunk_type": chunk_type.replace("_chunk", ""),
                                "generation_stage": "outline"
                            }
                        )
                        
                        if settings.debug:
                            print(f"[RAG CHARACTER INDEXING] Indexed {len(chunk_ids)} chunks for {character_name} - {chunk_type}")
                
                except Exception as e:
                    if settings.debug:
                        print(f"[RAG CHARACTER INDEXING] Could not index {chunk_type} for {character_name}: {e}")
        
        except Exception as e:
            if settings.debug:
                print(f"[RAG CHARACTER INDEXING] Error indexing character '{character_name}' in RAG: {e}")
    

    
    async def extract_chapter_characters(self, chapter_synopsis: str, chapter_num: int, settings: GenerationSettings) -> List[str]:
        """Extract character names from chapter synopsis."""
        model_config = ModelConfig.from_string(self.config["models"]["logical_model"])
        
        try:
            # Define JSON schema for character names
            CHARACTER_NAMES_SCHEMA = {
                "type": "array",
                "items": {"type": "string"}
            }

            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="characters/extract_from_chapter",
                variables={
                    "chapter_synopsis": chapter_synopsis,
                    "chapter_num": chapter_num
                },
                savepoint_id=f"chapter_{chapter_num}/characters",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                log_prompt_inputs=settings.log_prompt_inputs,
                system_message=self.system_message,
                expect_json=True,
                json_schema=CHARACTER_NAMES_SCHEMA
            )
            
            # Parse the response using the new JSON integration
            names_text = response.content.strip()
            
            # First try to parse as JSON (the expected format)
            character_names = []
            if response.json_parsed:
                try:
                    parsed_names = json.loads(names_text)
                    if isinstance(parsed_names, list):
                        character_names = [str(name).strip() for name in parsed_names if name and str(name).strip()]
                        if settings.debug:
                            print(f"[CHARACTER EXTRACTION] Successfully parsed JSON: {character_names}")
                except (json.JSONDecodeError, AttributeError) as e:
                    if settings.debug:
                        print(f"[CHARACTER EXTRACTION] JSON parsing failed: {e}, falling back to line parsing")
                    character_names = []
            else:
                if settings.debug:
                    print(f"[CHARACTER EXTRACTION] JSON parsing failed: {response.json_errors}, falling back to line parsing")
                character_names = []
            
            # Fallback to line-by-line parsing if JSON parsing failed
            if not character_names:
                for line in names_text.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#') and not line.startswith('-'):
                        # Remove any bullet points, numbers, or other formatting
                        clean_name = line.replace('*', '').replace('-', '').replace('•', '')
                        clean_name = clean_name.strip()
                        if clean_name and len(clean_name) < 50:  # Reasonable name length
                            character_names.append(clean_name)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_names = []
            for name in character_names:
                if name.lower() not in seen:
                    seen.add(name.lower())
                    unique_names.append(name)
            
            return unique_names[:10]  # Limit to 10 characters max
            
        except Exception as e:
            if settings.debug:
                print(f"[CHAPTER CHARACTERS] Error extracting characters for chapter {chapter_num}: {e}")
            return []
    
    async def fetch_character_sheets_for_chapter(self, character_names: List[str], settings: GenerationSettings) -> str:
        """Fetch character sheets for the given character names."""
        if not character_names or not self.savepoint_manager:
            return ""
        
        character_sheets = []
        for character_name in character_names:
            try:
                sheet_key = f"characters/{character_name}/sheet"
                sheet_content = await self.savepoint_manager.load_step(sheet_key)
                character_sheets.append(f"=== {character_name} ===\n{sheet_content}")
            except:
                if settings.debug:
                    print(f"[CHARACTER SHEETS] Could not load sheet for {character_name}")
        
        return "\n\n".join(character_sheets)
    
    async def update_character_sheets(
        self,
        character_names: List[str],
        chapter_outline: str,
        chapter_num: int,
        settings: GenerationSettings
    ) -> None:
        """Update character sheets based on new information from chapter outline."""
        if not character_names or not self.savepoint_manager:
            return
        
        for character_name in character_names:
            try:
                # Check if character sheet exists
                sheet_key = f"characters/{character_name}/sheet"
                existing_sheet = ""
                try:
                    existing_sheet = await self.savepoint_manager.load_step(sheet_key)
                except:
                    if settings.debug:
                        print(f"[CHARACTER UPDATE] No existing sheet for {character_name}, trying personality chunk as fallback")
                        # Try to load personality chunk as fallback
                        try:
                            personality_key = f"characters/{character_name}/personality_chunk"
                            existing_sheet = await self.savepoint_manager.load_step(personality_key)
                            if settings.debug:
                                print(f"[CHARACTER UPDATE] Using personality chunk for {character_name}")
                        except:
                            if settings.debug:
                                print(f"[CHARACTER UPDATE] No personality chunk either for {character_name}")
                            continue
                
                # Generate updated character sheet
                model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
                
                response = await execute_prompt_with_savepoint(
                    handler=self.prompt_handler,
                    prompt_id="characters/update",
                    variables={
                        "character_name": character_name,
                        "existing_sheet": existing_sheet,
                        "chapter_outline": chapter_outline,
                        "chapter_num": chapter_num
                    },
                    savepoint_id=f"characters/{character_name}/sheet",
                    model_config=model_config,
                    seed=settings.seed,
                    debug=settings.debug,
                    stream=settings.stream,
                    log_prompt_inputs=settings.log_prompt_inputs,
                    system_message=self.system_message
                )
                
                if settings.debug:
                    print(f"[CHARACTER UPDATE] Updated sheet for {character_name} based on chapter {chapter_num}")
                    
            except Exception as e:
                if settings.debug:
                    print(f"[CHARACTER UPDATE] Error updating sheet for {character_name}: {e}")
    

    
    async def extract_chapter_characters_from_outline(self, chapter_outline: str, chapter_num: int, settings: GenerationSettings) -> List[str]:
        """Extract character names from chapter outline."""
        model_config = ModelConfig.from_string(self.config["models"]["logical_model"])
        
        try:
            # Define JSON schema for character names
            CHARACTER_NAMES_SCHEMA = {
                "type": "array",
                "items": {"type": "string"}
            }

            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="characters/extract_from_chapter",
                variables={
                    "chapter_outline": chapter_outline,
                    "chapter_num": chapter_num
                },
                savepoint_id=f"chapter_{chapter_num}/characters_from_outline",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                log_prompt_inputs=settings.log_prompt_inputs,
                system_message=self.system_message,
                expect_json=True,
                json_schema=CHARACTER_NAMES_SCHEMA
            )
            
            # Parse the response using the new JSON integration
            names_text = response.content.strip()
            
            # First try to parse as JSON (the expected format)
            character_names = []
            if response.json_parsed:
                try:
                    parsed_names = json.loads(names_text)
                    if isinstance(parsed_names, list):
                        character_names = [str(name).strip() for name in parsed_names if name and str(name).strip()]
                        if settings.debug:
                            print(f"[CHARACTER EXTRACTION] Successfully parsed JSON: {character_names}")
                except (json.JSONDecodeError, AttributeError) as e:
                    if settings.debug:
                        print(f"[CHARACTER EXTRACTION] JSON parsing failed: {e}, falling back to line parsing")
                    character_names = []
            else:
                if settings.debug:
                    print(f"[CHARACTER EXTRACTION] JSON parsing failed: {response.json_errors}, falling back to line parsing")
                print(f"[CHARACTER EXTRACTION] Raw response preview: {names_text[:200]}...")
                character_names = []
            
            # Fallback to line-by-line parsing if JSON parsing failed
            if not character_names:
                for line in names_text.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#') and not line.startswith('-'):
                        # Remove any bullet points, numbers, or other formatting
                        clean_name = line.replace('*', '').replace('-', '').replace('•', '')
                        clean_name = clean_name.strip()
                        if clean_name and len(clean_name) < 50:  # Reasonable name length
                            character_names.append(clean_name)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_names = []
            for name in character_names:
                if name.lower() not in seen:
                    seen.add(name.lower())
                    unique_names.append(name)
            
            return unique_names[:10]  # Limit to 10 characters max
            
        except Exception as e:
            if settings.debug:
                print(f"[CHAPTER CHARACTERS] Error extracting characters from outline for chapter {chapter_num}: {e}")
            return []
    
    async def generate_character_summary(
        self,
        character_name: str,
        settings: GenerationSettings
    ) -> str:
        """Generate a natural language summary of a character from their chunked character information.
        
        Args:
            character_name: Name of the character to summarize
            settings: Generation settings for the request
            
        Returns:
            Natural language summary of the character, or empty string if not found
        """
        if not self.savepoint_manager:
            if settings.debug:
                print(f"[CHARACTER SUMMARY] No savepoint manager available for {character_name}")
            return ""
        
        try:
            # Try to load key character chunks for summary generation
            personality_key = f"characters/{character_name}/personality_chunk"
            motivations_key = f"characters/{character_name}/motivations_chunk"
            current_state_key = f"characters/{character_name}/current_state_chunk"
            
            personality_chunk = await self.savepoint_manager.load_step(personality_key)
            motivations_chunk = await self.savepoint_manager.load_step(motivations_key)
            current_state_chunk = await self.savepoint_manager.load_step(current_state_key)
            
            if not personality_chunk and not motivations_chunk and not current_state_chunk:
                if settings.debug:
                    print(f"[CHARACTER SUMMARY] No character chunks found for {character_name}")
                return ""
            
            # Combine available chunks for summary generation
            character_info = []
            if personality_chunk:
                character_info.append(f"Personality: {personality_chunk}")
            if motivations_chunk:
                character_info.append(f"Motivations: {motivations_chunk}")
            if current_state_chunk:
                character_info.append(f"Current State: {current_state_chunk}")
            
            combined_info = "\n\n".join(character_info)
            
            # Generate natural language summary from the combined chunks
            model_config = ModelConfig.from_string(self.config["models"]["logical_model"])
            
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="characters/create_summary",
                variables={
                    "character_name": character_name,
                    "character_info": combined_info
                },
                savepoint_id=f"characters/{character_name}/summary",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                log_prompt_inputs=settings.log_prompt_inputs,
                system_message=self.system_message
            )
            
            if response and response.content and response.content.strip():
                summary = response.content.strip()
                if settings.debug:
                    print(f"[CHARACTER SUMMARY] Generated summary for {character_name}: {len(summary)} characters")
                return summary
            else:
                if settings.debug:
                    print(f"[CHARACTER SUMMARY] Warning: Empty response when generating summary for {character_name}")
                return ""
                
        except Exception as e:
            if settings.debug:
                print(f"[CHARACTER SUMMARY] Error generating summary for {character_name}: {e}")
            return ""
    
    async def get_character_summaries(
        self,
        character_names: List[str],
        settings: GenerationSettings
    ) -> str:
        """Get natural language summaries for all characters.
        
        Args:
            character_names: List of character names to get summaries for
            settings: Generation settings for the request
            
        Returns:
            Combined natural language summaries of all characters, suitable for prompt injection
        """
        if not character_names:
            return ""
        
        # Check if savepoint manager is available
        if not self.savepoint_manager:
            if settings.debug:
                print(f"[CHARACTER SUMMARIES] No savepoint manager available, returning character names only")
            # Return just the character names as a fallback
            return "\n\n".join([f"**{name}**: Character appears in this scene" for name in character_names])
        
        summaries = []
        for character_name in character_names:
            summary = await self.generate_character_summary(character_name, settings)
            if summary:
                summaries.append(f"**{character_name}**: {summary}")
        
        if summaries:
            combined_summaries = "\n\n".join(summaries)
            if settings.debug:
                print(f"[CHARACTER SUMMARIES] Generated {len(summaries)} character summaries")
            return combined_summaries
        else:
            if settings.debug:
                print(f"[CHARACTER SUMMARIES] No character summaries generated, returning character names only")
            # Return just the character names as a fallback
            return "\n\n".join([f"**{name}**: Character appears in this scene" for name in character_names])
    
    async def get_character_summaries_list(
        self,
        character_names: List[str],
        settings: GenerationSettings
    ) -> str:
        """Get a list of natural language character summaries divided by markdown horizontal rules.
        
        This method generates summaries for each character and formats them as a list separated
        by horizontal rules (---), skipping any characters that don't have abridged summaries.
        
        Args:
            character_names: List of character names to get summaries for
            settings: Generation settings for the request
            
        Returns:
            Formatted list of character summaries with horizontal rule separators, or empty string if none found
        """
        if not character_names:
            return ""
        
        # Check if savepoint manager is available
        if not self.savepoint_manager:
            if settings.debug:
                print(f"[CHARACTER SUMMARIES LIST] No savepoint manager available, returning character names only")
            # Return just the character names as a fallback
            return "\n\n---\n\n".join([f"**{name}**\n\nCharacter appears in this scene" for name in character_names])
        
        summaries = []
        for character_name in character_names:
            summary = await self.generate_character_summary(character_name, settings)
            if summary:
                summaries.append(f"**{character_name}**\n\n{summary}")
        
        if summaries:
            # Join summaries with horizontal rules, but don't add one after the last summary
            formatted_summaries = "\n\n---\n\n".join(summaries)
            
            if settings.debug:
                print(f"[CHARACTER SUMMARIES LIST] Generated {len(summaries)} character summaries with horizontal rule separators")
            
            return formatted_summaries
        else:
            if settings.debug:
                print(f"[CHARACTER SUMMARIES LIST] No character summaries generated, returning character names only")
            # Return just the character names as a fallback
            return "\n\n---\n\n".join([f"**{name}**\n\nCharacter appears in this scene" for name in character_names])
