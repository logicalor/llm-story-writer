"""Character management functionality for the outline-chapter strategy."""

import json
from typing import List, Optional, Dict, Any
from domain.value_objects.generation_settings import GenerationSettings
from domain.value_objects.model_config import ModelConfig

from application.interfaces.model_provider import ModelProvider
from infrastructure.prompts.prompt_handler import PromptHandler
from infrastructure.prompts.prompt_wrapper import execute_prompt_with_savepoint
from infrastructure.savepoints import SavepointManager


class CharacterManager:
    """Handles character generation, extraction, and management functionality."""
    
    def __init__(
        self,
        model_provider: ModelProvider,
        config: Dict[str, Any],
        prompt_handler: PromptHandler,
        system_message: str,
        savepoint_manager: Optional[SavepointManager] = None
    ):
        self.model_provider = model_provider
        self.config = config
        self.prompt_handler = prompt_handler
        self.system_message = system_message
        self.savepoint_manager = savepoint_manager
    
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
        """Generate a character sheet for a single character."""
        model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
        
        try:
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="characters/create",
                variables={
                    "character_name": character_name,
                    "story_elements": story_elements,
                    "additional_context": additional_context
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
                print(f"[CHARACTER SHEET] Generated sheet for {character_name}")
            
            # Generate abridged character summary after full sheet
            await self._generate_character_abridged_summary(character_name, response.content.strip(), story_elements, settings)
                
        except Exception as e:
            if settings.debug:
                print(f"[CHARACTER SHEET] Error generating sheet for {character_name}: {e}")
    
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
                        print(f"[CHARACTER UPDATE] No existing sheet for {character_name}, trying abridged version")
                        # Try to load abridged character summary as fallback
                        try:
                            abridged_key = f"characters/{character_name}/sheet-abridged"
                            existing_sheet = await self.savepoint_manager.load_step(abridged_key)
                            if settings.debug:
                                print(f"[CHARACTER UPDATE] Using abridged summary for {character_name}")
                        except:
                            if settings.debug:
                                print(f"[CHARACTER UPDATE] No abridged summary either for {character_name}")
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
    
    async def _generate_character_abridged_summary(
        self,
        character_name: str,
        character_sheet: str,
        story_elements: str,
        settings: GenerationSettings
    ) -> None:
        """Generate an abridged character summary suitable for prompt injection."""
        try:
            model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
            
            # Create savepoint path for this character's abridged summary
            savepoint_id = f"characters/{character_name}/sheet-abridged"
            
            # Generate the abridged character summary
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="characters/create_abridged",
                variables={
                    "character_sheet": character_sheet,
                    "character_name": character_name,
                    "story_elements": story_elements
                },
                savepoint_id=savepoint_id,
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                log_prompt_inputs=settings.log_prompt_inputs,
                system_message=self.system_message
            )
            
            if response and response.content and response.content.strip():
                if settings.debug:
                    print(f"[CHARACTER ABRIDGED] Generated abridged summary for {character_name}")
            else:
                if settings.debug:
                    print(f"[CHARACTER ABRIDGED] Warning: Empty response when generating abridged summary for {character_name}")
                
        except Exception as e:
            if settings.debug:
                print(f"[CHARACTER ABRIDGED] Error generating abridged summary for {character_name}: {e}")
    
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
        """Generate a natural language summary of a character from their abridged character sheet.
        
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
            # Try to load the abridged character sheet
            abridged_key = f"characters/{character_name}/sheet-abridged"
            abridged_sheet = await self.savepoint_manager.load_step(abridged_key)
            
            if not abridged_sheet:
                if settings.debug:
                    print(f"[CHARACTER SUMMARY] No abridged sheet found for {character_name}")
                return ""
            
            # Generate natural language summary from the abridged sheet
            model_config = ModelConfig.from_string(self.config["models"]["logical_model"])
            
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="characters/create_summary",
                variables={
                    "character_name": character_name,
                    "abridged_sheet": abridged_sheet
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
