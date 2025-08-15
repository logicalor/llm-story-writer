"""Scene generation functionality for the outline-chapter strategy."""

import json
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

            # Remove lead_in_to_next_scene from each scene definition
            for scene_def in scene_definitions:
                if "lead_in_to_next_scene" in scene_def:
                    del scene_def["lead_in_to_next_scene"]
            
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

                    previous_scene = scenes[-1].content if scenes else None
                    
                    previous_scene_summary = None
                    # If the scene number is > 1, get the previous scene summary
                    if scene_num > 1:
                        previous_scene_summary = await self.savepoint_manager.load_step(f"chapter_{chapter_num}/scene_{scene_num - 1}_summary")
                        if not previous_scene_summary:
                            previous_scene_summary = await self._extract_scene_events(
                                scene_content=previous_scene,
                                chapter_num=chapter_num,
                                scene_num=scene_num,
                                settings=settings
                            )

                    scene_def_string = json.dumps(scene_def) if scene_def else None

                    # If we are not at the last scene, set the next chapter synopsis to empty
                    if scene_num < len(scene_definitions):
                        next_chapter_synopsis = ""

                    # If there is a next scene get its definition and convert it to a string
                    next_scene_definition = scene_definitions[scene_num] if scene_num < len(scene_definitions) else None
                    next_scene_definition_string = json.dumps(next_scene_definition) if next_scene_definition else None

                    # Generate scene content
                    scene_content = await self._generate_scene_content(
                        chapter_num=chapter_num,
                        scene_num=scene_num,
                        scene_definition=scene_def_string,
                        chapter_outline=chapter_outline,
                        base_context=base_context,
                        story_elements=story_elements,
                        previous_recap=previous_recap,
                        previous_scene=previous_scene_summary,
                        next_scene_definition=next_scene_definition_string,
                        next_chapter_synopsis=next_chapter_synopsis,
                        settings=settings
                    )
                    
                    
                    
                    # Extract scene events in point form
                    await self._extract_scene_events(
                        scene_content=scene_content,
                        chapter_num=chapter_num,
                        scene_num=scene_num,
                        settings=settings
                    )
                    
                    # Clean the scene content to remove commentary and repetition
                    # scene_content = await self._clean_scene_content(
                    #     scene_content=scene_content,
                    #     chapter_num=chapter_num,
                    #     scene_num=scene_num,
                    #     settings=settings
                    # )
                    
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
        
        # Define JSON schema for scene definitions
        SCENE_DEFINITIONS_SCHEMA = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "characters": {"type": "array", "items": {"type": "string"}},
                    "setting": {"type": "string"},
                    "conflict": {"type": "string"},
                    "tone": {"type": "string"},
                    "key_events": {"type": "array", "items": {"type": "string"}},
                    "dialogue": {"type": "string"},
                    "resolution": {"type": "string"},
                    "lead_in": {"type": "string"}
                },
                "required": ["title", "description", "characters", "setting", "conflict", "tone", "key_events", "dialogue", "resolution", "lead_in"]
            }
        }

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
            system_message=self.system_message,
            expect_json=True,
            json_schema=SCENE_DEFINITIONS_SCHEMA
        )
        
        # Parse the response using the new JSON integration
        content = response.content.strip()
        scene_definitions = []
        
        if response.json_parsed:
            # llm-output-parser has already successfully parsed the JSON
            # The content should now be a clean JSON string that we can parse
            try:
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
                scene_definitions = []
        else:
            if settings.debug:
                print(f"[SCENE DEFINITIONS] JSON parsing failed: {response.json_errors}, falling back to default structure")
            scene_definitions = []
        
        # If no scenes found, create a default structure
        if not scene_definitions:
            scene_definitions = [{"title": f"Chapter {chapter_num} Scene", "description": chapter_outline}]
        
        return scene_definitions
    
    async def _generate_scene_content(
        self,
        chapter_num: int,
        scene_num: int,
        scene_definition: str,
        chapter_outline: str,
        base_context: str,
        story_elements: str,
        previous_recap: str,
        previous_scene: str,
        next_scene_definition: str,
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
                "scene_definition": scene_definition,
                "next_scene_definition": next_scene_definition,
                "chapter_outline": chapter_outline,
                "base_context": base_context,
                "story_elements": story_elements,
                "character_sheets": character_sheets,
                "setting_sheets": setting_sheets,
                "previous_recap": previous_recap,
                "previous_scene": previous_scene,
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
    
    async def _clean_scene_content(
        self,
        scene_content: str,
        chapter_num: int,
        scene_num: int,
        settings: GenerationSettings
    ) -> str:
        """Clean the generated scene content to remove commentary and repetition."""
        model_config = self.config.get_model("scene_writer")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="scenes/clean_content",
            variables={"scene_content": scene_content},
            savepoint_id=f"chapter_{chapter_num}/scene_{scene_num}_clean",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def _extract_scene_events(
        self,
        scene_content: str,
        chapter_num: int,
        scene_num: int,
        settings: GenerationSettings
    ) -> str:
        """Extract the key events of the scene in point form."""
        model_config = self.config.get_model("logical_model")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="scenes/extract_events",
            variables={"scene_content": scene_content},
            savepoint_id=f"chapter_{chapter_num}/scene_{scene_num}_summary",
            model_config=model_config,
            seed=settings.seed + chapter_num + scene_num,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
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
