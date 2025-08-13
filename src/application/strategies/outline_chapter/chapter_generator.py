"""Chapter generation functionality for the outline-chapter strategy."""

import json
import os
import re
from typing import List, Optional
from domain.entities.story import Outline, Chapter, Scene
from domain.value_objects.generation_settings import GenerationSettings
from domain.exceptions import StoryGenerationError
from config.settings import AppConfig
from application.interfaces.model_provider import ModelProvider
from infrastructure.prompts.prompt_handler import PromptHandler
from infrastructure.prompts.prompt_wrapper import execute_prompt_with_savepoint
from infrastructure.savepoints import SavepointManager
from .character_manager import CharacterManager
from .setting_manager import SettingManager
from .recap_manager import RecapManager
from .scene_generator import SceneGenerator


class ChapterGenerator:
    """Handles chapter generation functionality."""
    
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
        
        # Initialize managers
        self.character_manager = CharacterManager(
            model_provider=model_provider,
            config=config,
            prompt_handler=prompt_handler,
            system_message=system_message,
            savepoint_manager=savepoint_manager
        )
        
        self.setting_manager = SettingManager(
            model_provider=model_provider,
            config=config,
            prompt_handler=prompt_handler,
            system_message=system_message,
            savepoint_manager=savepoint_manager
        )
        
        self.recap_manager = RecapManager(
            model_provider=model_provider,
            config=config,
            prompt_handler=prompt_handler,
            system_message=system_message,
            savepoint_manager=savepoint_manager
        )
        
        self.scene_generator = SceneGenerator(
            model_provider=model_provider,
            config=config,
            prompt_handler=prompt_handler,
            system_message=system_message,
            savepoint_manager=savepoint_manager
        )
    
    async def generate_chapters(self, outline: Outline, settings: GenerationSettings) -> List[Chapter]:
        """Generate chapters from outline."""
        try:
            if not self.savepoint_manager:
                # Savepoint manager is required for the unified workflow
                raise StoryGenerationError("Savepoint manager is required for chapter generation")
            
            # Unified workflow: generate outlines, content, and recaps in sequence
            # First, find existing chapter directories in the savepoint directory
            chapter_count = 0
            story_dir = self.savepoint_manager.savepoint_repo._current_story_dir
            
            if story_dir and os.path.exists(story_dir):
                for item in os.listdir(story_dir):
                    # Match pattern like "chapter_1", "chapter_42", etc.
                    match = re.match(r'chapter_(\d+)$', item)
                    if match:
                        chapter_num = int(match.group(1))
                        chapter_count = max(chapter_count, chapter_num)
            
            if chapter_count == 0:
                print(f"No chapter directories found in {story_dir}. Returning empty list.")
                return []
            
            print(f"Found {chapter_count} chapter directories in {story_dir}.")
            
            # Single loop: process each chapter through all steps
            chapters = []
            for chapter_num in range(1, chapter_count + 1):
                try:
                    print(f"\nProcessing Chapter {chapter_num}...")
                    
                    # Step 1: Generate/load chapter outline
                    print(f"  Step 1: Checking outline for Chapter {chapter_num}...")
                    chapter_outline = None
                    try:
                        if await self.savepoint_manager.has_step(f"chapter_{chapter_num}/outline"):
                            print(f"  Chapter {chapter_num} outline already exists, loading...")
                            chapter_outline = await self.savepoint_manager.load_step(f"chapter_{chapter_num}/outline")
                        else:
                            # Verify that this chapter has a synopsis
                            try:
                                synopsis = await self.savepoint_manager.load_step(f"chapter_{chapter_num}/synopsis")
                                if not synopsis or synopsis.strip() == "":
                                    print(f"  Chapter {chapter_num} has no synopsis, skipping...")
                                    continue
                            except:
                                print(f"  Chapter {chapter_num} synopsis not found, skipping...")
                                continue
                            
                            print(f"  Generating outline for Chapter {chapter_num}...")



                            chapter_outline = await self._generate_chapter_outline(
                                chapter_num=chapter_num,
                                chapter_synopsis=synopsis,
                                outline=outline,
                                settings=settings
                            )
                    except Exception as e:
                        print(f"  Error processing outline for Chapter {chapter_num}: {e}")
                        continue
                    
                    # Step 2: Generate/load chapter scenes
                    print(f"  Step 2: Checking scenes for Chapter {chapter_num}...")
                    chapter_scenes = []
                    try:
                        # First, check if scene definitions exist and load them
                        expected_scene_count = 0
                        scene_definitions = []
                        
                        if await self.savepoint_manager.has_step(f"chapter_{chapter_num}/scene_definitions"):
                            print(f"  Chapter {chapter_num} scene definitions found, loading...")
                            try:
                                # Load and parse scene definitions
                                scene_definitions_raw = await self.savepoint_manager.load_step(f"chapter_{chapter_num}/scene_definitions")
                                
                                # Parse JSON and strip non-JSON content if needed
                                try:
                                    # First, try to find JSON content wrapped in markdown backticks
                                    json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', scene_definitions_raw, re.DOTALL)
                                    if json_match:
                                        json_content = json_match.group(1)
                                        scene_definitions = json.loads(json_content)
                                    else:
                                        # Try to find JSON array without backticks
                                        json_match = re.search(r'(\[.*?\])', scene_definitions_raw, re.DOTALL)
                                        if json_match:
                                            json_content = json_match.group(1)
                                            scene_definitions = json.loads(json_content)
                                        else:
                                            # If no JSON found, try to parse the entire content as JSON
                                            scene_definitions = json.loads(scene_definitions_raw)
                                    
                                    # Validate that we got a list of scene objects
                                    if isinstance(scene_definitions, list):
                                        expected_scene_count = len(scene_definitions)
                                        if settings.debug:
                                            print(f"    Successfully parsed {expected_scene_count} scene definitions from JSON")
                                    else:
                                        raise ValueError("Expected JSON array of scenes")
                                        
                                except (json.JSONDecodeError, ValueError) as e:
                                    if settings.debug:
                                        print(f"    JSON parsing failed: {e}, will regenerate scene definitions")
                                    # If parsing fails, we'll regenerate scenes below
                                    scene_definitions = []
                                    expected_scene_count = 0
                            except Exception as e:
                                if settings.debug:
                                    print(f"    Error loading scene definitions: {e}, will regenerate")
                                scene_definitions = []
                                expected_scene_count = 0
                        
                        # Check if all expected scenes already exist
                        if expected_scene_count > 0:
                            all_scenes_exist = True
                            missing_scenes = []
                            
                            for scene_num in range(1, expected_scene_count + 1):
                                if not await self.savepoint_manager.has_step(f"chapter_{chapter_num}/scene_{scene_num}"):
                                    all_scenes_exist = False
                                    missing_scenes.append(scene_num)
                            
                            if all_scenes_exist:
                                print(f"  Chapter {chapter_num} has all {expected_scene_count} scenes, loading...")
                                # Load existing scenes
                                for scene_num in range(1, expected_scene_count + 1):
                                    scene_content = await self.savepoint_manager.load_step(f"chapter_{chapter_num}/scene_{scene_num}")
                                    scene_title = await self.savepoint_manager.load_step(f"chapter_{chapter_num}/scene_{scene_num}_title")
                                    
                                    scene = Scene(
                                        number=scene_num,
                                        title=scene_title,
                                        content=scene_content,
                                        outline=""
                                    )
                                    chapter_scenes.append(scene)
                                
                                chapter_content = "\n\n".join([f"## {scene.title}\n\n{scene.content}" for scene in chapter_scenes])
                            else:
                                print(f"  Chapter {chapter_num} missing scenes: {missing_scenes}, regenerating all scenes...")
                                # Some scenes are missing, regenerate all
                                scene_definitions = []
                                expected_scene_count = 0
                        else:
                            print(f"  Chapter {chapter_num} has no scene definitions, will generate...")
                        
                        # If we need to generate scenes (either no definitions or missing scenes)
                        if expected_scene_count == 0 or len(chapter_scenes) == 0:
                            print(f"  Generating scenes for Chapter {chapter_num}...")
                            
                            # Update managers with current savepoint manager
                            self.recap_manager.savepoint_manager = self.savepoint_manager
                            self.scene_generator.savepoint_manager = self.savepoint_manager
                            
                            # Get previous chapter recap
                            previous_recap = await self.recap_manager.get_previous_chapter_recap_from_savepoint(
                                chapter_num, outline, settings
                            )
                            
                            # Get next chapter synopsis
                            next_chapter_synopsis = await self._get_next_chapter_synopsis_from_savepoint(
                                chapter_num, chapter_count, settings
                            )

                            chapter_outline_for_scene = await self.savepoint_manager.load_step(f"chapter_{chapter_num}/outline")
                            
                            # Generate scenes for this chapter
                            chapter_scenes = await self.scene_generator.generate_scenes(
                                chapter_num=chapter_num,
                                chapter_outline=chapter_outline_for_scene,
                                base_context=outline.base_context,
                                story_elements=outline.story_elements,
                                previous_recap=previous_recap,
                                next_chapter_synopsis=next_chapter_synopsis,
                                settings=settings
                            )
                            
                            # Combine scenes into chapter content
                            chapter_content = "\n\n".join([f"## {scene.title}\n\n{scene.content}" for scene in chapter_scenes])
                            
                            # Save the combined content
                            await self.savepoint_manager.save_step(f"chapter_{chapter_num}/content", chapter_content)
                            print(f"  Chapter {chapter_num} scenes generated and combined.")
                            
                            # Update character and setting sheets based on new chapter content
                            print(f"  Updating character and setting sheets for Chapter {chapter_num}...")
                            try:
                                # Extract character names from chapter content
                                chapter_characters = await self.character_manager.extract_chapter_characters(chapter_content, chapter_num, settings)
                                if chapter_characters:
                                    print(f"    Found characters in chapter: {', '.join(chapter_characters)}")
                                    # Update character sheets based on new chapter content
                                    await self.character_manager.update_character_sheets(
                                        chapter_characters, chapter_content, chapter_num, settings
                                    )
                                
                                # Extract setting names from chapter content
                                chapter_settings = await self.setting_manager.extract_chapter_settings(chapter_content, chapter_num, settings)
                                if chapter_settings:
                                    print(f"    Found settings in chapter: {', '.join(chapter_settings)}")
                                    # Update setting sheets based on new chapter content
                                    await self.setting_manager.update_setting_sheets(
                                        chapter_settings, chapter_content, chapter_num, settings
                                    )
                                
                                print(f"    Character and setting sheets updated for Chapter {chapter_num}")
                                
                            except Exception as e:
                                print(f"    Warning: Failed to update character/setting sheets for Chapter {chapter_num}: {e}")
                                # Continue processing even if updates fail
                    except Exception as e:
                        print(f"  Error processing scenes for Chapter {chapter_num}: {e}")
                        continue
                    
                    # Step 3: Generate/load chapter recap
                    print(f"  Step 3: Checking recap for Chapter {chapter_num}...")
                    try:
                        if await self.savepoint_manager.has_step(f"chapter_{chapter_num}/recap"):
                            print(f"  Chapter {chapter_num} recap already exists, skipping...")
                        else:
                            print(f"  Generating recap for Chapter {chapter_num}...")
                            
                            # Get previous chapter recap
                            previous_recap = ""
                            if chapter_num > 1:
                                try:
                                    previous_recap = await self.savepoint_manager.load_step(f"chapter_{chapter_num-1}/recap")
                                except:
                                    if settings.debug:
                                        print(f"    No previous recap found for chapter {chapter_num-1}")
                            
                            # Get story start date from savepoint or use a default
                            story_start_date = "2024-01-01"  # Default fallback
                            try:
                                story_start_date = await self.savepoint_manager.load_step("story_start_date")
                            except:
                                if settings.debug:
                                    print(f"    Using default story start date for chapter {chapter_num}")
                            
                            # Generate recap for this chapter
                            chapter_recap = await self.recap_manager.generate_chapter_recap(
                                chapter_num=chapter_num,
                                chapter_content=chapter_content,
                                chapter_outline=chapter_outline,
                                story_start_date=story_start_date,
                                previous_chapter_recap=previous_recap,
                                settings=settings
                            )
                            
                            # Save the recap to savepoint
                            await self.savepoint_manager.save_step(f"chapter_{chapter_num}/recap", chapter_recap)
                            
                            if settings.debug:
                                print(f"    Generated and saved recap for chapter {chapter_num}")
                            else:
                                print(f"    Chapter {chapter_num} recap generated and saved.")
                    except Exception as e:
                        print(f"  Error processing recap for Chapter {chapter_num}: {e}")
                        # Continue to next step even if recap fails
                    
                    # Step 4: Generate title and create Chapter object
                    print(f"  Step 4: Creating Chapter object for Chapter {chapter_num}...")
                    try:
                        # Generate chapter title
                        title = await self._generate_chapter_title(
                            chapter_num, chapter_content, chapter_outline, settings
                        )
                        
                        chapter = Chapter(
                            number=chapter_num,
                            title=title,
                            content=chapter_content,
                            outline=chapter_outline,
                            scenes=chapter_scenes
                        )
                        chapters.append(chapter)
                        print(f"  Chapter {chapter_num} object created: '{title}'")
                        
                    except Exception as e:
                        print(f"  Error creating Chapter {chapter_num} object: {e}")
                        continue
                    
                    print(f"  Chapter {chapter_num} processing complete!")
                    
                except Exception as e:
                    print(f"Error processing Chapter {chapter_num}: {e}")
                    continue
            
            return chapters
            
        except Exception as e:
            raise StoryGenerationError(f"Failed to generate chapters: {e}") from e
    

    
    async def _generate_chapter_outline(
        self,
        chapter_num: int,
        chapter_synopsis: str,
        outline: Outline,
        settings: GenerationSettings
    ) -> str:
        """Generate detailed outline for a chapter from its synopsis."""
        # Update managers with current savepoint manager
        self.character_manager.savepoint_manager = self.savepoint_manager
        self.setting_manager.savepoint_manager = self.savepoint_manager
        
        # Extract character names for this chapter
        chapter_characters = await self.character_manager.extract_chapter_characters(chapter_synopsis, chapter_num, settings)
        
        # Fetch character sheets for this chapter
        character_sheets = await self.character_manager.fetch_character_sheets_for_chapter(chapter_characters, settings)
        
        # Extract setting names for this chapter
        chapter_settings = await self.setting_manager.extract_chapter_settings(chapter_synopsis, chapter_num, settings)
        
        # Fetch setting sheets for this chapter
        setting_sheets = await self.setting_manager.fetch_setting_sheets_for_chapter(chapter_settings, settings)
        
        # Get previous chapter recap if available
        previous_recap = ""
        if chapter_num > 1:
            try:
                previous_recap = await self.savepoint_manager.load_step(f"chapter_{chapter_num-1}/recap")
            except:
                previous_recap = ""
        
        # Generate the detailed chapter outline
        return await self._generate_chapter_outline_impl(
            chapter_num=chapter_num,
            chapter_synopsis=chapter_synopsis,
            outline=outline,
            character_sheets=character_sheets,
            setting_sheets=setting_sheets,
            previous_recap=previous_recap,
            settings=settings
        )
    
    async def _generate_chapter_outline_impl(
        self,
        chapter_num: int,
        chapter_synopsis: str,
        outline: Outline,
        character_sheets: str,
        setting_sheets: str,
        previous_recap: str,
        settings: GenerationSettings
    ) -> str:
        """Implementation of chapter outline generation."""
        model_config = self.config.get_model("chapter_outline_writer")
        
        # First, generate the core outline
        core_outline = await self._generate_core_outline(
            chapter_num, chapter_synopsis, outline, character_sheets, 
            setting_sheets, previous_recap, settings
        )
        
        # Run quality validation
        validation_issues = await self._validate_outline_quality(core_outline, chapter_num, settings)
        
        if validation_issues:
            if settings.debug:
                print(f"[CHAPTER OUTLINE] Quality issues found: {validation_issues}")
            
            # Regenerate with feedback
            core_outline = await self._regenerate_outline_with_feedback(
                core_outline, validation_issues, chapter_num, chapter_synopsis,
                outline, character_sheets, setting_sheets, previous_recap, settings
            )
        
        # Run disambiguator
        disambiguated_outline = await self._run_disambiguator(core_outline, chapter_num, settings)
        
        # Run cleanup
        final_outline = await self._run_cleanup(disambiguated_outline, chapter_num, settings)
        
        # Format the final structure
        # formatted_outline = await self._format_outline_structure(final_outline, settings)

        formatted_outline = final_outline
        
        # Save the outline
        if self.savepoint_manager:
            await self.savepoint_manager.save_step(f"chapter_{chapter_num}/outline", formatted_outline)
        
        return formatted_outline
    
    async def _generate_core_outline(
        self,
        chapter_num: int,
        chapter_synopsis: str,
        outline: Outline,
        character_sheets: str,
        setting_sheets: str,
        previous_recap: str,
        settings: GenerationSettings
    ) -> str:
        """Generate the core chapter outline."""
        model_config = self.config.get_model("chapter_outline_writer")
        
        # Get next chapter synopsis if available
        next_chapter_synopsis = ""
        if self.savepoint_manager:
            try:
                next_chapter_synopsis = await self.savepoint_manager.load_step(f"chapter_{chapter_num+1}/synopsis")
            except:
                if settings.debug:
                    print(f"[OUTLINE GENERATION] Could not load next chapter synopsis for chapter {chapter_num}")
        
        # Get previous chapter outline if available
        previous_chapter_outline = ""
        if chapter_num > 1 and self.savepoint_manager:
            try:
                previous_chapter_outline = await self.savepoint_manager.load_step(f"chapter_{chapter_num-1}/outline")
            except:
                if settings.debug:
                    print(f"[OUTLINE GENERATION] Could not load previous chapter outline for chapter {chapter_num}")
        
        # Get abridged character and setting summaries for context
        character_context = ""
        setting_context = ""
        if self.savepoint_manager:
            try:
                character_context = await self.savepoint_manager.load_step(f"chapter_{chapter_num}/characters_abridged")
            except:
                if settings.debug:
                    print(f"[OUTLINE GENERATION] Could not load abridged character summary for chapter {chapter_num}")
                character_context = character_sheets  # Fallback to full sheets
        
        if self.savepoint_manager:
            try:
                setting_context = await self.savepoint_manager.load_step(f"chapter_{chapter_num}/settings_abridged")
            except:
                if settings.debug:
                    print(f"[OUTLINE GENERATION] Could not load abridged setting summary for chapter {chapter_num}")
                setting_context = setting_sheets  # Fallback to full sheets
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="chapters/outline_core",
            variables={
                "chapter_number": chapter_num,
                "outline": outline.content,
                "base_context": outline.base_context,
                "recap": previous_recap,
                "story_elements": outline.story_elements,
                "current_chapter_synopsis": chapter_synopsis,
                "next_chapter_synopsis": next_chapter_synopsis,
                "previous_chapter_outline": previous_chapter_outline,
                "character_context": character_context,
                "setting_context": setting_context
            },
            savepoint_id=f"chapter_{chapter_num}/core_outline",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def _validate_outline_quality(self, outline: str, chapter_num: int, settings: GenerationSettings) -> List[str]:
        """Validate the quality of a chapter outline."""
        model_config = self.config.get_model("logical_model")
        
        try:
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="chapters/outline_validator",
                variables={"chapter_outline": outline},
                savepoint_id=f"chapter_{chapter_num}/outline_validation",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                log_prompt_inputs=settings.log_prompt_inputs,
                system_message=self.system_message
            )
            
            validation_result = response.content.strip()
            
            # Parse validation issues if any
            if "ISSUES:" in validation_result:
                issues_text = validation_result.split("ISSUES:")[1].strip()
                issues = [issue.strip() for issue in issues_text.split('\n') if issue.strip()]
                return issues
            
            return []
            
        except Exception as e:
            if settings.debug:
                print(f"[OUTLINE VALIDATION] Error during validation: {e}")
            return []
    
    async def _regenerate_outline_with_feedback(
        self,
        outline: str,
        issues: List[str],
        chapter_num: int,
        chapter_synopsis: str,
        story_outline: Outline,
        character_sheets: str,
        setting_sheets: str,
        previous_recap: str,
        settings: GenerationSettings
    ) -> str:
        """Regenerate outline with feedback from validation."""
        model_config = self.config.get_model("chapter_outline_writer")
        
        issues_text = self._format_validation_issues(issues)
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="chapters/outline_improved",
            variables={
                "chapter_num": chapter_num,
                "chapter_synopsis": chapter_synopsis,
                "base_context": story_outline.base_context,
                "story_elements": story_outline.story_elements,
                "story_start_date": story_outline.story_start_date,
                "character_sheets": character_sheets,
                "setting_sheets": setting_sheets,
                "previous_recap": previous_recap,
                "current_outline": outline,
                "validation_issues": issues_text
            },
            savepoint_id=f"chapter_{chapter_num}/improved_outline",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    def _format_validation_issues(self, issues: List[str]) -> str:
        """Format validation issues for prompt inclusion."""
        if not issues:
            return "No issues found."
        
        formatted = "The following issues were identified:\n"
        for i, issue in enumerate(issues, 1):
            formatted += f"{i}. {issue}\n"
        
        return formatted
    
    async def _run_disambiguator(self, chapter_outline: str, chapter_num: int, settings: GenerationSettings) -> str:
        """Run disambiguator on chapter outline."""
        model_config = self.config.get_model("logical_model")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="chapters/outline_disambiguator",
            variables={"chapter_outline": chapter_outline},
            savepoint_id=f"chapter_{chapter_num}/disambiguated_outline",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def _run_cleanup(self, chapter_outline: str, chapter_num: int, settings: GenerationSettings) -> str:
        """Run cleanup on chapter outline."""
        model_config = self.config.get_model("logical_model")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="chapters/outline_cleanup",
            variables={"chapter_outline": chapter_outline},
            savepoint_id=f"chapter_{chapter_num}/cleaned_outline",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def _format_outline_structure(self, outline: str, settings: GenerationSettings) -> str:
        """Format the outline structure."""
        model_config = self.config.get_model("logical_model")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="chapters/outline_formatter",
            variables={"chapter_outline": outline},
            savepoint_id="formatted_outline",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def _get_chapter_outline(
        self,
        chapter_num: int,
        outline: str,
        settings: GenerationSettings
    ) -> str:
        """Get outline for specific chapter."""
        model_config = self.config.get_model("chapter_outline_writer")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="chapters/get_outline",
            variables={
                "chapter_num": chapter_num,
                "outline": outline
            },
            savepoint_id=f"chapter_{chapter_num}/base_outline",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        return response.content.strip()
    

    
    async def _get_next_chapter_outline(
        self,
        chapter_num: int,
        total_chapters: int,
        outline: Outline,
        settings: GenerationSettings
    ) -> str:
        """Get outline for next chapter."""
        if chapter_num >= total_chapters:
            return ""
        
        return await self._get_chapter_outline(chapter_num + 1, outline.content, settings)
    
    async def _get_next_chapter_synopsis_from_savepoint(
        self,
        chapter_num: int,
        total_chapters: int,
        settings: GenerationSettings
    ) -> str:
        """Get next chapter synopsis from savepoint."""
        if chapter_num >= total_chapters:
            return ""
        
        try:
            return await self.savepoint_manager.load_step(f"chapter_{chapter_num+1}/synopsis")
        except:
            return ""
    
    async def _generate_chapter_content(
        self,
        base_context: str,
        chapter_num: int,
        total_chapters: int,
        chapter_outline: str,
        previous_recap: str,
        next_chapter_synopsis: str,
        outline: Outline,
        settings: GenerationSettings
    ) -> str:
        """Generate the actual chapter content."""
        model_config = self.config.get_model("chapter_stage1_writer")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="chapters/create_content",
            variables={
                "base_context": base_context,
                "chapter_num": chapter_num,
                "total_chapters": total_chapters,
                "outline": outline,
                "chapter_outline": chapter_outline,
                "previous_recap": previous_recap,
                "next_chapter_synopsis": next_chapter_synopsis
            },
            savepoint_id=f"chapter_{chapter_num}/content",
            model_config=model_config,
            seed=settings.seed + chapter_num,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message,
            min_word_count=1000
        )
        
        return response.content.strip()
    
    async def _generate_chapter_title(
        self,
        chapter_num: int,
        content: str,
        outline: str,
        settings: GenerationSettings
    ) -> str:
        """Generate title for chapter."""
        model_config = self.config.get_model("chapter_writer")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="chapters/create_title",
            variables={
                "chapter_num": chapter_num,
                "content": content,
                "outline": outline
            },
            savepoint_id=f"chapter_{chapter_num}/title",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        return response.content.strip()
    

    

    

