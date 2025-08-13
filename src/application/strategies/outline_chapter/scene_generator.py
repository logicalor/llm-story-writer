"""Scene generation functionality for the outline-chapter strategy."""

import json
import re
from typing import List, Optional
from domain.entities.story import Scene
from domain.value_objects.generation_settings import GenerationSettings
from domain.exceptions import StoryGenerationError
from config.settings import AppConfig
from application.interfaces.model_provider import ModelProvider
from infrastructure.prompts.prompt_handler import PromptHandler
from infrastructure.prompts.prompt_wrapper import execute_prompt_with_savepoint
from infrastructure.savepoints import SavepointManager
from .character_manager import CharacterManager
from .setting_manager import SettingManager


class SceneGenerator:
    """Handles scene generation functionality."""
    
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
    
    async def generate_scenes(
        self,
        chapter_num: int,
        chapter_outline: str,
        base_context: str,
        story_elements: str,
        previous_recap: str,
        next_chapter_synopsis: str,
        settings: GenerationSettings
    ) -> List[Scene]:
        """Generate scenes from chapter outline."""
        try:
            if not self.savepoint_manager:
                raise StoryGenerationError("Savepoint manager is required for scene generation")
            
            # Parse the chapter outline to extract scene definitions
            scene_definitions = await self._parse_scene_definitions(chapter_num, chapter_outline, settings)
            
            if not scene_definitions:
                # If no scene definitions found, create a single scene from the entire chapter
                scene_definitions = [{"title": f"Chapter {chapter_num} Scene", "description": chapter_outline}]
            
            # Generate scenes
            scenes = []
            for scene_num, scene_def in enumerate(scene_definitions, 1):
                try:
                    print(f"    Generating Scene {scene_num} for Chapter {chapter_num}...")
                    
                    # Check if scene already exists
                    scene_savepoint_id = f"chapter_{chapter_num}/scene_{scene_num}"
                    if await self.savepoint_manager.has_step(scene_savepoint_id):
                        print(f"    Scene {scene_num} already exists, loading...")
                        scene_content = await self.savepoint_manager.load_step(scene_savepoint_id)
                        scene_title = await self.savepoint_manager.load_step(f"chapter_{chapter_num}/scene_{scene_num}_title")
                        
                        scene = Scene(
                            number=scene_num,
                            title=scene_title,
                            content=scene_content,
                            outline=scene_def.get("description", "")
                        )
                        scenes.append(scene)
                        continue
                    
                    # Generate scene content
                    scene_content = await self._generate_scene_content(
                        chapter_num=chapter_num,
                        scene_num=scene_num,
                        scene_definition=scene_def,
                        chapter_outline=chapter_outline,
                        base_context=base_context,
                        story_elements=story_elements,
                        previous_recap=previous_recap,
                        next_chapter_synopsis=next_chapter_synopsis,
                        settings=settings
                    )
                    
                    # Generate scene title
                    scene_title = await self._generate_scene_title(
                        chapter_num=chapter_num,
                        scene_num=scene_num,
                        scene_content=scene_content,
                        scene_definition=scene_def,
                        settings=settings
                    )
                    
                    # Save scene content and title
                    await self.savepoint_manager.save_step(scene_savepoint_id, scene_content)
                    await self.savepoint_manager.save_step(f"chapter_{chapter_num}/scene_{scene_num}_title", scene_title)
                    
                    # Create Scene object
                    scene = Scene(
                        number=scene_num,
                        title=scene_title,
                        content=scene_content,
                        outline=scene_def.get("description", "")
                    )
                    scenes.append(scene)
                    
                    print(f"    Scene {scene_num} generated and saved: '{scene_title}'")
                    
                except Exception as e:
                    print(f"    Error generating Scene {scene_num}: {e}")
                    continue
            
            return scenes
            
        except Exception as e:
            raise StoryGenerationError(f"Failed to generate scenes: {e}") from e
    
    async def _parse_scene_definitions(
        self,
        chapter_num: int,
        chapter_outline: str,
        settings: GenerationSettings
    ) -> List[dict]:
        """Parse chapter outline to extract scene definitions."""
        model_config = self.config.get_model("logical_model")
        
        try:
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="scenes/parse_definitions",
                variables={"chapter_outline": chapter_outline},
                savepoint_id=f"chapter_{chapter_num}/scene_definitions",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                log_prompt_inputs=settings.log_prompt_inputs,
                system_message=self.system_message
            )
            
            # Parse the response to extract scene definitions from JSON
            content = response.content.strip()
            scene_definitions = []
            
            try:
                # First, try to find JSON content wrapped in markdown backticks
                json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', content, re.DOTALL)
                if json_match:
                    json_content = json_match.group(1)
                    scene_definitions = json.loads(json_content)
                else:
                    # Try to find JSON array without backticks
                    json_match = re.search(r'(\[.*?\])', content, re.DOTALL)
                    if json_match:
                        json_content = json_match.group(1)
                        scene_definitions = json.loads(json_content)
                    else:
                        # If no JSON found, try to parse the entire content as JSON
                        scene_definitions = json.loads(content)
                
                # Validate that we got a list of scene objects
                if not isinstance(scene_definitions, list):
                    raise ValueError("Expected JSON array of scenes")
                
                # Validate each scene has required fields
                for scene in scene_definitions:
                    if not isinstance(scene, dict) or "title" not in scene or "description" not in scene:
                        raise ValueError("Each scene must be an object with title and description")
                
                if settings.debug:
                    print(f"[SCENE DEFINITIONS] Successfully parsed {len(scene_definitions)} scenes from JSON")
                
            except (json.JSONDecodeError, ValueError) as e:
                if settings.debug:
                    print(f"[SCENE DEFINITIONS] JSON parsing failed: {e}, falling back to default structure")
                
                # Fallback: create a single scene from the chapter outline
                scene_definitions = [{"title": f"Chapter {chapter_num} Scene", "description": chapter_outline}]
            
            # If no scenes found, create a default structure
            if not scene_definitions:
                scene_definitions = [{"title": f"Chapter {chapter_num} Scene", "description": chapter_outline}]
            
            return scene_definitions
            
        except Exception as e:
            print(f"Warning: Failed to parse scene definitions: {e}")
            # Fallback: create a single scene
            return [{"title": f"Chapter {chapter_num} Scene", "description": chapter_outline}]
    
    async def _generate_scene_content(
        self,
        chapter_num: int,
        scene_num: int,
        scene_definition: dict,
        chapter_outline: str,
        base_context: str,
        story_elements: str,
        previous_recap: str,
        next_chapter_synopsis: str,
        settings: GenerationSettings
    ) -> str:
        """Generate content for a specific scene."""
        model_config = self.config.get_model("scene_writer")
        
        # Get character and setting context for this scene
        character_sheets = await self.character_manager.fetch_character_sheets_for_chapter(
            [], settings  # We'll extract characters from the scene definition
        )
        setting_sheets = await self.setting_manager.fetch_setting_sheets_for_chapter(
            [], settings  # We'll extract settings from the scene definition
        )
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="scenes/create_content",
            variables={
                "chapter_num": chapter_num,
                "scene_num": scene_num,
                "scene_title": scene_definition.get("title", ""),
                "scene_description": scene_definition.get("description", ""),
                "chapter_outline": chapter_outline,
                "base_context": base_context,
                "story_elements": story_elements,
                "character_sheets": character_sheets,
                "setting_sheets": setting_sheets,
                "previous_recap": previous_recap,
                "next_chapter_synopsis": next_chapter_synopsis
            },
            savepoint_id=f"chapter_{chapter_num}/scene_{scene_num}_content_gen",
            model_config=model_config,
            seed=settings.seed + chapter_num + scene_num,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message,
            min_word_count=500  # Scenes should be shorter than chapters
        )
        
        return response.content.strip()
    
    async def _generate_scene_title(
        self,
        chapter_num: int,
        scene_num: int,
        scene_content: str,
        scene_definition: dict,
        settings: GenerationSettings
    ) -> str:
        """Generate title for a scene."""
        model_config = self.config.get_model("scene_writer")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="scenes/create_title",
            variables={
                "chapter_num": chapter_num,
                "scene_num": scene_num,
                "scene_content": scene_content,
                "scene_definition": scene_definition
            },
            savepoint_id=f"chapter_{chapter_num}/scene_{scene_num}_title_gen",
            model_config=model_config,
            seed=settings.seed + chapter_num + scene_num,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        return response.content.strip()
