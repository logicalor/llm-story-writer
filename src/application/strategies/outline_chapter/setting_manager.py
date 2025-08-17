"""Setting management functionality for the outline-chapter strategy."""

import json
from typing import List, Optional, Dict, Any
from domain.value_objects.generation_settings import GenerationSettings
from domain.value_objects.model_config import ModelConfig

from application.interfaces.model_provider import ModelProvider
from infrastructure.prompts.prompt_handler import PromptHandler
from infrastructure.prompts.prompt_wrapper import execute_prompt_with_savepoint
from infrastructure.savepoints import SavepointManager
from application.services.rag_service import RAGService
from application.services.rag_integration_service import RAGIntegrationService


class SettingManager:
    """Handles setting generation, extraction, and management functionality."""
    
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
            from application.services.content_chunker import ContentChunker
            content_chunker = ContentChunker(
                max_chunk_size=config.get("max_chunk_size", 1000),
                overlap_size=config.get("overlap_size", 200)
            )
            self.rag_integration = RAGIntegrationService(self.rag_service, content_chunker)
    
    async def generate_setting_sheets(self, story_elements: str, additional_context: str, settings: GenerationSettings) -> None:
        """Generate setting sheets for all settings identified in story elements."""
        try:
            # Extract setting names from story elements
            setting_names = await self.extract_setting_names(story_elements, settings)
            
            if settings.debug:
                print(f"[SETTING SHEETS] Found {len(setting_names)} settings: {setting_names}")
            
            # Generate sheet for each setting
            for setting_name in setting_names:
                if settings.debug:
                    print(f"[SETTING SHEETS] Generating sheet for: {setting_name}")
                
                await self.generate_single_setting_sheet(setting_name, story_elements, additional_context, settings)
        
        except Exception as e:
            if settings.debug:
                print(f"[SETTING SHEETS] Error generating setting sheets: {e}")
            # Don't fail the entire process if setting sheet generation fails
            pass
    
    async def extract_setting_names(self, story_elements: str, settings: GenerationSettings) -> List[str]:
        """Extract setting names from story elements."""
        model_config = ModelConfig.from_string(self.config["models"]["logical_model"])
        
        # Define JSON schema for setting names
        SETTING_NAMES_SCHEMA = {
            "type": "array",
            "items": {"type": "string"}
        }

        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="settings/extract_names",
            variables={"story_elements": story_elements},
            savepoint_id="setting_names",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message,
            expect_json=True,
            json_schema=SETTING_NAMES_SCHEMA
        )
        
        # Parse the response using the new JSON integration
        names_text = response.content.strip()
        
        # First try to parse as JSON (the expected format)
        setting_names = []
        if response.json_parsed:
            # llm-output-parser has already successfully parsed the JSON
            # The content should now be a clean JSON string that we can parse
            try:
                parsed_names = json.loads(names_text)
                if isinstance(parsed_names, list):
                    setting_names = [str(name).strip() for name in parsed_names if name and str(name).strip()]
                    if settings.debug:
                        print(f"[SETTING NAMES] Successfully parsed JSON: {setting_names}")
                else:
                    if settings.debug:
                        print(f"[SETTING NAMES] Expected list but got: {type(parsed_names)}")
            except (json.JSONDecodeError, AttributeError) as e:
                if settings.debug:
                    print(f"[SETTING NAMES] JSON parsing failed: {e}, falling back to line parsing")
                setting_names = []
        else:
            if settings.debug:
                print(f"[SETTING NAMES] JSON parsing failed: {response.json_errors}, falling back to line parsing")
                print(f"[SETTING NAMES] Raw response preview: {names_text[:200]}...")
            setting_names = []
        
        # Fallback to line-by-line parsing if JSON parsing failed
        if not setting_names:
            # Since llm-output-parser handles markdown automatically, 
            # we can use simpler line parsing as fallback
            for line in names_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-') and not line.startswith('```'):
                    # Remove any bullet points, numbers, or other formatting
                    clean_name = line.replace('*', '').replace('-', '').replace('•', '')
                    clean_name = clean_name.strip()
                    if clean_name and len(clean_name) < 100:  # Reasonable setting name length
                        setting_names.append(clean_name)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_names = []
        for name in setting_names:
            if name.lower() not in seen:
                seen.add(name.lower())
                unique_names.append(name)
        
        return unique_names[:10]  # Limit to 10 settings max
    
    async def generate_single_setting_sheet(self, setting_name: str, story_elements: str, additional_context: str, settings: GenerationSettings) -> None:
        """Generate a setting sheet for a single setting."""
        model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
        
        try:
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="settings/create",
                variables={
                    "setting_name": setting_name,
                    "story_elements": story_elements,
                    "additional_context": additional_context
                },
                savepoint_id=f"settings/{setting_name}/sheet",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                log_prompt_inputs=settings.log_prompt_inputs,
                system_message=self.system_message
            )
            
            if settings.debug:
                print(f"[SETTING SHEET] Generated sheet for {setting_name}")
            
            # Generate setting chunks for optimal RAG indexing
            await self._generate_setting_chunks(setting_name, response.content.strip(), story_elements, settings)
            
            # Index setting content in RAG if available
            if self.rag_integration:
                await self.index_setting_in_rag(setting_name, settings)
                
        except Exception as e:
            if settings.debug:
                print(f"[SETTING SHEET] Error generating sheet for {setting_name}: {e}")
    
    async def _index_setting_in_rag(self, setting_name: str, setting_content: str, settings: GenerationSettings) -> None:
        """Index setting content in RAG for world consistency tracking."""
        if not self.rag_integration:
            return
        
        try:
            # Index setting content in RAG
            chunk_ids = await self.rag_integration.index_setting(
                setting_content=setting_content,
                location_name=setting_name,
                metadata={
                    "setting_name": setting_name,
                    "content_type": "setting_sheet",
                    "generation_stage": "outline"
                }
            )
            
            if settings.debug:
                print(f"[RAG SETTING INDEXING] Indexed {len(chunk_ids)} chunks for setting '{setting_name}'")
        
        except Exception as e:
            if settings.debug:
                print(f"[RAG SETTING INDEXING] Error indexing setting '{setting_name}' in RAG: {e}")
    
    async def _generate_setting_chunks(
        self,
        setting_name: str,
        setting_sheet: str,
        story_elements: str,
        settings: GenerationSettings
    ) -> None:
        """Generate focused setting chunks for optimal RAG indexing."""
        try:
            if settings.debug:
                print(f"[SETTING CHUNKS] Generating chunks for {setting_name}")
            
            # Generate each type of setting chunk
            await self._generate_physical_description_chunk(setting_name, setting_sheet, story_elements, settings)
            await self._generate_history_background_chunk(setting_name, setting_sheet, story_elements, settings)
            await self._generate_function_purpose_chunk(setting_name, setting_sheet, story_elements, settings)
            await self._generate_atmosphere_mood_chunk(setting_name, setting_sheet, story_elements, settings)
            await self._generate_rules_constraints_chunk(setting_name, setting_sheet, story_elements, settings)
            await self._generate_connections_relationships_chunk(setting_name, setting_sheet, story_elements, settings)
            
            if settings.debug:
                print(f"[SETTING CHUNKS] Generated all chunks for {setting_name}")
                
        except Exception as e:
            if settings.debug:
                print(f"[SETTING CHUNKS] Error generating chunks for {setting_name}: {e}")
    
    async def _generate_physical_description_chunk(
        self,
        setting_name: str,
        setting_sheet: str,
        story_elements: str,
        settings: GenerationSettings
    ) -> None:
        """Generate physical description chunk for a setting."""
        try:
            model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
            
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="settings/create_physical_description_chunk",
                variables={
                    "setting_name": setting_name,
                    "setting_sheet": setting_sheet,
                    "story_elements": story_elements
                },
                savepoint_id=f"settings/{setting_name}/physical_description_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                log_prompt_inputs=settings.log_prompt_inputs,
                system_message=self.system_message
            )
            
            if settings.debug:
                print(f"[SETTING CHUNK] Generated physical description chunk for {setting_name}")
                
        except Exception as e:
            if settings.debug:
                print(f"[SETTING CHUNK] Error generating physical description chunk for {setting_name}: {e}")
    
    async def _generate_history_background_chunk(
        self,
        setting_name: str,
        setting_sheet: str,
        story_elements: str,
        settings: GenerationSettings
    ) -> None:
        """Generate history and background chunk for a setting."""
        try:
            model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
            
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="settings/create_history_background_chunk",
                variables={
                    "setting_name": setting_name,
                    "setting_sheet": setting_sheet,
                    "story_elements": story_elements
                },
                savepoint_id=f"settings/{setting_name}/history_background_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                log_prompt_inputs=settings.log_prompt_inputs,
                system_message=self.system_message
            )
            
            if settings.debug:
                print(f"[SETTING CHUNK] Generated history background chunk for {setting_name}")
                
        except Exception as e:
            if settings.debug:
                print(f"[SETTING CHUNK] Error generating history background chunk for {setting_name}: {e}")
    
    async def _generate_function_purpose_chunk(
        self,
        setting_name: str,
        setting_sheet: str,
        story_elements: str,
        settings: GenerationSettings
    ) -> None:
        """Generate function and purpose chunk for a setting."""
        try:
            model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
            
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="settings/create_function_purpose_chunk",
                variables={
                    "setting_name": setting_name,
                    "setting_sheet": setting_sheet,
                    "story_elements": story_elements
                },
                savepoint_id=f"settings/{setting_name}/function_purpose_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                log_prompt_inputs=settings.log_prompt_inputs,
                system_message=self.system_message
            )
            
            if settings.debug:
                print(f"[SETTING CHUNK] Generated function purpose chunk for {setting_name}")
                
        except Exception as e:
            if settings.debug:
                print(f"[SETTING CHUNK] Error generating function purpose chunk for {setting_name}: {e}")
    
    async def _generate_atmosphere_mood_chunk(
        self,
        setting_name: str,
        setting_sheet: str,
        story_elements: str,
        settings: GenerationSettings
    ) -> None:
        """Generate atmosphere and mood chunk for a setting."""
        try:
            model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
            
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="settings/create_atmosphere_mood_chunk",
                variables={
                    "setting_name": setting_name,
                    "setting_sheet": setting_sheet,
                    "story_elements": story_elements
                },
                savepoint_id=f"settings/{setting_name}/atmosphere_mood_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                log_prompt_inputs=settings.log_prompt_inputs,
                system_message=self.system_message
            )
            
            if settings.debug:
                print(f"[SETTING CHUNK] Generated atmosphere mood chunk for {setting_name}")
                
        except Exception as e:
            if settings.debug:
                print(f"[SETTING CHUNK] Error generating atmosphere mood chunk for {setting_name}: {e}")
    
    async def _generate_rules_constraints_chunk(
        self,
        setting_name: str,
        setting_sheet: str,
        story_elements: str,
        settings: GenerationSettings
    ) -> None:
        """Generate rules and constraints chunk for a setting."""
        try:
            model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
            
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="settings/create_rules_constraints_chunk",
                variables={
                    "setting_name": setting_name,
                    "setting_sheet": setting_sheet,
                    "story_elements": story_elements
                },
                savepoint_id=f"settings/{setting_name}/rules_constraints_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                log_prompt_inputs=settings.log_prompt_inputs,
                system_message=self.system_message
            )
            
            if settings.debug:
                print(f"[SETTING CHUNK] Generated rules constraints chunk for {setting_name}")
                
        except Exception as e:
            if settings.debug:
                print(f"[SETTING CHUNK] Error generating rules constraints chunk for {setting_name}: {e}")
    
    async def _generate_connections_relationships_chunk(
        self,
        setting_name: str,
        setting_sheet: str,
        story_elements: str,
        settings: GenerationSettings
    ) -> None:
        """Generate connections and relationships chunk for a setting."""
        try:
            model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
            
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="settings/create_connections_relationships_chunk",
                variables={
                    "setting_name": setting_name,
                    "setting_sheet": setting_sheet,
                    "story_elements": story_elements
                },
                savepoint_id=f"settings/{setting_name}/connections_relationships_chunk",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                log_prompt_inputs=settings.log_prompt_inputs,
                system_message=self.system_message
            )
            
            if settings.debug:
                print(f"[SETTING CHUNK] Generated connections relationships chunk for {setting_name}")
                
        except Exception as e:
            if settings.debug:
                print(f"[SETTING CHUNK] Error generating connections relationships chunk for {setting_name}: {e}")
    
    async def index_setting_in_rag(
        self, 
        setting_name: str, 
        settings: GenerationSettings
    ) -> None:
        """Index setting content in RAG from savepoint manager. Can be called by other modules."""
        if not self.rag_integration or not self.savepoint_manager:
            return
        
        try:
            # Load setting sheet content
            sheet_key = f"settings/{setting_name}/sheet"
            setting_content = await self.savepoint_manager.load_step(sheet_key)
            
            if setting_content:
                # Index setting content in RAG
                await self._index_setting_in_rag(setting_name, setting_content, settings)
                
                # Index all setting chunks if available
                chunk_types = [
                    "physical_description_chunk",
                    "history_background_chunk", 
                    "function_purpose_chunk",
                    "atmosphere_mood_chunk",
                    "rules_constraints_chunk",
                    "connections_relationships_chunk"
                ]
                
                for chunk_type in chunk_types:
                    try:
                        chunk_key = f"settings/{setting_name}/{chunk_type}"
                        chunk_content = await self.savepoint_manager.load_step(chunk_key)
                        
                        if chunk_content:
                            chunk_chunk_ids = await self.rag_integration.index_setting(
                                setting_content=chunk_content,
                                location_name=setting_name,
                                metadata={
                                    "setting_name": setting_name,
                                    "content_type": "setting_chunk",
                                    "chunk_type": chunk_type,
                                    "generation_stage": "outline"
                                }
                            )
                            
                            if settings.debug:
                                print(f"[RAG SETTING INDEXING] Indexed {len(chunk_chunk_ids)} {chunk_type} chunks for setting '{setting_name}'")
                    
                    except Exception as e:
                        if settings.debug:
                            print(f"[RAG SETTING INDEXING] Could not index {chunk_type} for {setting_name}: {e}")
        
        except Exception as e:
            if settings.debug:
                print(f"[RAG SETTING INDEXING] Error indexing setting '{setting_name}' in RAG: {e}")
    

    
    async def extract_chapter_settings(self, chapter_synopsis: str, chapter_num: int, settings: GenerationSettings) -> List[str]:
        """Extract setting names from chapter synopsis."""
        model_config = ModelConfig.from_string(self.config["models"]["logical_model"])
        
        try:
            # Define JSON schema for setting names
            SETTING_NAMES_SCHEMA = {
                "type": "array",
                "items": {"type": "string"}
            }

            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="settings/extract_from_chapter",
                variables={
                    "chapter_synopsis": chapter_synopsis,
                    "chapter_num": chapter_num
                },
                savepoint_id=f"chapter_{chapter_num}/settings",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                log_prompt_inputs=settings.log_prompt_inputs,
                system_message=self.system_message,
                expect_json=True,
                json_schema=SETTING_NAMES_SCHEMA
            )
            
            # Parse the response using the new JSON integration
            names_text = response.content.strip()
            
            # First try to parse as JSON (the expected format)
            setting_names = []
            if response.json_parsed:
                try:
                    parsed_names = json.loads(names_text)
                    if isinstance(parsed_names, list):
                        setting_names = [str(name).strip() for name in parsed_names if name and str(name).strip()]
                        if settings.debug:
                            print(f"[SETTING EXTRACTION] Successfully parsed JSON: {setting_names}")
                except (json.JSONDecodeError, AttributeError) as e:
                    if settings.debug:
                        print(f"[SETTING EXTRACTION] JSON parsing failed: {e}, falling back to line parsing")
                    setting_names = []
            else:
                if settings.debug:
                    print(f"[SETTING EXTRACTION] JSON parsing failed: {response.json_errors}, falling back to line parsing")
                setting_names = []
            
            # Fallback to line-by-line parsing if JSON parsing failed
            if not setting_names:
                for line in names_text.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#') and not line.startswith('-'):
                        # Remove any bullet points, numbers, or other formatting
                        clean_name = line.replace('*', '').replace('-', '').replace('•', '')
                        clean_name = clean_name.strip()
                        if clean_name and len(clean_name) < 100:  # Reasonable setting name length
                            setting_names.append(clean_name)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_names = []
            for name in setting_names:
                if name.lower() not in seen:
                    seen.add(name.lower())
                    unique_names.append(name)
            
            return unique_names[:10]  # Limit to 10 settings max
            
        except Exception as e:
            if settings.debug:
                print(f"[CHAPTER SETTINGS] Error extracting settings for chapter {chapter_num}: {e}")
            return []
    
    async def fetch_setting_sheets_for_chapter(self, setting_names: List[str], settings: GenerationSettings) -> str:
        """Fetch setting sheets for the given setting names."""
        if not setting_names or not self.savepoint_manager:
            return ""
        
        setting_sheets = []
        for setting_name in setting_names:
            try:
                sheet_key = f"settings/{setting_name}/sheet"
                sheet_content = await self.savepoint_manager.load_step(sheet_key)
                setting_sheets.append(f"=== {setting_name} ===\n{sheet_content}")
            except:
                if settings.debug:
                    print(f"[SETTING SHEETS] Could not load sheet for {setting_name}")
        
        return "\n\n".join(setting_sheets)



    async def update_setting_sheets(
        self,
        setting_names: List[str],
        chapter_outline: str,
        chapter_num: int,
        settings: GenerationSettings
    ) -> None:
        """Update setting sheets based on new information from chapter outline."""
        if not setting_names or not self.savepoint_manager:
            return
        
        for setting_name in setting_names:
            try:
                # Check if setting sheet exists
                sheet_key = f"settings/{setting_name}/sheet"
                existing_sheet = ""
                try:
                    existing_sheet = await self.savepoint_manager.load_step(sheet_key)
                except:
                    if settings.debug:
                        print(f"[SETTING UPDATE] No existing sheet for {setting_name}, trying physical description chunk")
                        # Try to load physical description chunk as fallback
                        try:
                            physical_key = f"settings/{setting_name}/physical_description_chunk"
                            existing_sheet = await self.savepoint_manager.load_step(physical_key)
                            if settings.debug:
                                print(f"[SETTING UPDATE] Using physical description chunk for {setting_name}")
                        except:
                            if settings.debug:
                                print(f"[SETTING UPDATE] No physical description chunk either for {setting_name}")
                            continue
                
                # Generate updated setting sheet
                model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
                
                response = await execute_prompt_with_savepoint(
                    handler=self.prompt_handler,
                    prompt_id="settings/update",
                    variables={
                        "setting_name": setting_name,
                        "existing_sheet": existing_sheet,
                        "chapter_outline": chapter_outline,
                        "chapter_num": chapter_num
                    },
                    savepoint_id=f"settings/{setting_name}/sheet",
                    model_config=model_config,
                    seed=settings.seed,
                    debug=settings.debug,
                    stream=settings.stream,
                    log_prompt_inputs=settings.log_prompt_inputs,
                    system_message=self.system_message
                )
                
                if settings.debug:
                    print(f"[SETTING UPDATE] Updated sheet for {setting_name} based on chapter {chapter_num}")
                    
            except Exception as e:
                if settings.debug:
                    print(f"[SETTING UPDATE] Error updating sheet for {setting_name}: {e}")
    
    async def generate_setting_summary(
        self,
        setting_name: str,
        settings: GenerationSettings
    ) -> str:
        """Generate a natural language summary of a setting from its chunked setting information.
        
        Args:
            setting_name: Name of the setting to summarize
            settings: Generation settings for the request
            
        Returns:
            Natural language summary of the setting, or empty string if not found
        """
        if not self.savepoint_manager:
            if settings.debug:
                print(f"[SETTING SUMMARY] No savepoint manager available for {setting_name}")
            return ""
        
        try:
            # Try to load key setting chunks for summary generation
            physical_key = f"settings/{setting_name}/physical_description_chunk"
            atmosphere_key = f"settings/{setting_name}/atmosphere_mood_chunk"
            function_key = f"settings/{setting_name}/function_purpose_chunk"
            
            physical_chunk = await self.savepoint_manager.load_step(physical_key)
            atmosphere_chunk = await self.savepoint_manager.load_step(atmosphere_key)
            function_chunk = await self.savepoint_manager.load_step(function_key)
            
            if not physical_chunk and not atmosphere_chunk and not function_chunk:
                if settings.debug:
                    print(f"[SETTING SUMMARY] No setting chunks found for {setting_name}")
                return ""
            
            # Combine available chunks for summary generation
            setting_info = []
            if physical_chunk:
                setting_info.append(f"Physical Description: {physical_chunk}")
            if atmosphere_chunk:
                setting_info.append(f"Atmosphere: {atmosphere_chunk}")
            if function_chunk:
                setting_info.append(f"Function: {function_chunk}")
            
            combined_info = "\n\n".join(setting_info)
            
            # Generate natural language summary from the combined chunks
            model_config = ModelConfig.from_string(self.config["models"]["logical_model"])
            
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="settings/create_summary",
                variables={
                    "setting_name": setting_name,
                    "setting_info": combined_info
                },
                savepoint_id=f"settings/{setting_name}/summary",
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
                    print(f"[SETTING SUMMARY] Generated summary for {setting_name}: {len(summary)} characters")
                return summary
            else:
                if settings.debug:
                    print(f"[SETTING SUMMARY] Warning: Empty response when generating summary for {setting_name}")
                return ""
                
        except Exception as e:
            if settings.debug:
                print(f"[SETTING SUMMARY] Error generating summary for {setting_name}: {e}")
            return ""
    
    async def get_setting_summaries(
        self,
        setting_names: List[str],
        settings: GenerationSettings
    ) -> str:
        """Get natural language summaries for all settings.
        
        Args:
            setting_names: List of setting names to get summaries for
            settings: Generation settings for the request
            
        Returns:
            Combined natural language summaries of all settings, suitable for prompt injection
        """
        if not setting_names:
            return ""
        
        # Check if savepoint manager is available
        if not self.savepoint_manager:
            if settings.debug:
                print(f"[SETTING SUMMARIES] No savepoint manager available, returning setting names only")
            # Return just the setting names as a fallback
            return "\n\n".join([f"**{name}**: Setting appears in this scene" for name in setting_names])
        
        summaries = []
        for setting_name in setting_names:
            summary = await self.generate_setting_summary(setting_name, settings)
            if summary:
                summaries.append(f"**{setting_name}**: {summary}")
        
        if summaries:
            combined_summaries = "\n\n".join(summaries)
            if settings.debug:
                print(f"[SETTING SUMMARIES] Generated {len(summaries)} setting summaries")
            return combined_summaries
        else:
            if settings.debug:
                print(f"[SETTING SUMMARIES] No setting summaries generated, returning setting names only")
            # Return just the setting names as a fallback
            return "\n\n".join([f"**{name}**: Setting appears in this scene" for name in setting_names])
    
    async def get_setting_summaries_list(
        self,
        setting_names: List[str],
        settings: GenerationSettings
    ) -> str:
        """Get a list of natural language setting summaries divided by markdown horizontal rules.
        
        This method generates summaries for each setting and formats them as a list separated
        by horizontal rules (---), skipping any settings that don't have abridged summaries.
        
        Args:
            setting_names: List of setting names to get summaries for
            settings: Generation settings for the request
            
        Returns:
            Formatted list of setting summaries with horizontal rule separators, or empty string if none found
        """
        if not setting_names:
            return ""
        
        # Check if savepoint manager is available
        if not self.savepoint_manager:
            if settings.debug:
                print(f"[SETTING SUMMARIES LIST] No savepoint manager available, returning setting names only")
            # Return just the setting names as a fallback
            return "\n\n---\n\n".join([f"**{name}**\n\nSetting appears in this scene" for name in setting_names])
        
        summaries = []
        for setting_name in setting_names:
            summary = await self.generate_setting_summary(setting_name, settings)
            if summary:
                summaries.append(f"**{setting_name}**\n\n{summary}")
        
        if summaries:
            # Join summaries with horizontal rules, but don't add one after the last summary
            formatted_summaries = "\n\n---\n\n".join(summaries)
            
            if settings.debug:
                print(f"[SETTING SUMMARIES LIST] Generated {len(summaries)} setting summaries with horizontal rule separators")
            
            return formatted_summaries
        else:
            if settings.debug:
                print(f"[SETTING SUMMARIES LIST] No setting summaries generated, returning setting names only")
            # Return just the setting names as a fallback
            return "\n\n---\n\n".join([f"**{name}**\n\nSetting appears in this scene" for name in setting_names])
