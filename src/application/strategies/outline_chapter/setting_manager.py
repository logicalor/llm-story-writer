"""Setting management functionality for the outline-chapter strategy."""

import json
from typing import List, Optional
from domain.value_objects.generation_settings import GenerationSettings
from config.settings import AppConfig
from application.interfaces.model_provider import ModelProvider
from infrastructure.prompts.prompt_handler import PromptHandler
from infrastructure.prompts.prompt_wrapper import execute_prompt_with_savepoint
from infrastructure.savepoints import SavepointManager


class SettingManager:
    """Handles setting generation, extraction, and management functionality."""
    
    def __init__(
        self,
        model_provider: ModelProvider,
        config: AppConfig,
        prompt_handler: PromptHandler,
        system_message: str,
        savepoint_manager: Optional[SavepointManager] = None
    ):
        self.model_provider = model_provider
        self.config = config
        self.prompt_handler = prompt_handler
        self.system_message = system_message
        self.savepoint_manager = savepoint_manager
    
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
        model_config = self.config.get_model("logical_model")
        
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
        model_config = self.config.get_model("initial_outline_writer")
        
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
            
            # Generate abridged setting summary after full sheet
            await self._generate_setting_abridged_summary(setting_name, response.content.strip(), story_elements, settings)
                
        except Exception as e:
            if settings.debug:
                print(f"[SETTING SHEET] Error generating sheet for {setting_name}: {e}")
    
    async def extract_chapter_settings(self, chapter_synopsis: str, chapter_num: int, settings: GenerationSettings) -> List[str]:
        """Extract setting names from chapter synopsis."""
        model_config = self.config.get_model("logical_model")
        
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

    async def _generate_setting_abridged_summary(
        self,
        setting_name: str,
        setting_sheet: str,
        story_elements: str,
        settings: GenerationSettings
    ) -> None:
        """Generate an abridged setting summary suitable for prompt injection."""
        try:
            model_config = self.config.get_model("initial_outline_writer")
            
            # Create savepoint path for this setting's abridged summary
            savepoint_id = f"settings/{setting_name}/sheet-abridged"
            
            # Generate the abridged setting summary
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="settings/create_abridged",
                variables={
                    "setting_sheet": setting_sheet,
                    "setting_name": setting_name,
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
                    print(f"[SETTING ABRIDGED] Generated abridged summary for {setting_name}")
            else:
                if settings.debug:
                    print(f"[SETTING ABRIDGED] Warning: Empty response when generating abridged summary for {setting_name}")
                
        except Exception as e:
            if settings.debug:
                print(f"[SETTING ABRIDGED] Error generating abridged summary for {setting_name}: {e}")

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
                        print(f"[SETTING UPDATE] No existing sheet for {setting_name}, trying abridged version")
                        # Try to load abridged setting summary as fallback
                        try:
                            abridged_key = f"settings/{setting_name}/sheet-abridged"
                            existing_sheet = await self.savepoint_manager.load_step(abridged_key)
                            if settings.debug:
                                print(f"[SETTING UPDATE] Using abridged summary for {setting_name}")
                        except:
                            if settings.debug:
                                print(f"[SETTING UPDATE] No abridged summary either for {setting_name}")
                            continue
                
                # Generate updated setting sheet
                model_config = self.config.get_model("initial_outline_writer")
                
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
