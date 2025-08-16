"""Scene generation functionality for the outline-chapter strategy."""

import json
from typing import List, Optional, Dict, Any
from domain.entities.story import Scene
from domain.value_objects.generation_settings import GenerationSettings
from domain.value_objects.model_config import ModelConfig
from domain.exceptions import StoryGenerationError

from application.interfaces.model_provider import ModelProvider
from infrastructure.prompts.prompt_handler import PromptHandler
from infrastructure.prompts.prompt_wrapper import execute_prompt_with_savepoint, execute_messages_with_savepoint, load_prompt
from infrastructure.savepoints import SavepointManager
from .character_manager import CharacterManager
from .setting_manager import SettingManager


class SceneGenerator:
    """Handles scene generation functionality."""
    
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
    
    def update_savepoint_manager(self, savepoint_manager: SavepointManager):
        """Update the savepoint manager for all child managers."""
        self.savepoint_manager = savepoint_manager
        self.character_manager.savepoint_manager = savepoint_manager
        self.setting_manager.savepoint_manager = savepoint_manager
    
    async def generate_scenes(
        self,
        chapter_num: int,
        chapter_count: int,
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
                    scene_content = await self._generate_scene_content_multistep(
                        chapter_num=chapter_num,
                        chapter_count=chapter_count,
                        scene_count=len(scene_definitions),
                        scene_num=scene_num,
                        scene_definition=scene_def_string,
                        chapter_outline=chapter_outline,
                        base_context=base_context,
                        story_elements=story_elements,
                        previous_recap=previous_recap,
                        previous_scene=previous_scene,
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
        model_config = ModelConfig.from_string(self.config["models"]["scene_writer"])
        
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
        model_config = ModelConfig.from_string(self.config["models"]["scene_writer"])
        
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
    
    async def _get_scene_outline_summary(
        self,
        chapter_num: int,
        scene_num: int,
        scene_definition: str,
        tense: str = "present",
        settings: GenerationSettings = None
    ) -> str:
        """
        Get a natural language summary of a scene outline from its JSON definition.
        
        Args:
            chapter_num: Chapter number for savepoint organization
            scene_num: Scene number for savepoint organization
            scene_definition: JSON string containing the scene definition
            tense: Tense to write in ("past", "present", or "future")
            settings: Generation settings for the model
            
        Returns:
            Natural language paragraph summary of the scene outline in the specified tense
        """
        if not settings:
            return "Error: Generation settings required"
        
        try:
            # Execute the prompt with the model to generate a natural language summary
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="scenes/create_outline_summary",
                variables={
                    "scene_definition": scene_definition,
                    "tense": tense
                },
                savepoint_id=f"chapter_{chapter_num}/scene_{scene_num}_outline_summary_{tense}",
                model_config=ModelConfig.from_string(self.config["models"]["logical_model"]),
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream
            )
            
            summary = response.content.strip()
            
            if settings.debug:
                print(f"[SCENE OUTLINE SUMMARY] Generated {tense} tense summary: {len(summary)} characters")
            
            return summary
            
        except Exception as e:
            if settings.debug:
                print(f"[SCENE OUTLINE SUMMARY] Error generating summary: {e}")
            return f"Error generating scene summary: {e}"
    
    async def _get_scene_outline_summary_programmatic(
        self,
        scene_definition: str,
        settings: GenerationSettings = None
    ) -> str:
        """
        Get a natural language summary of a scene outline programmatically from its JSON definition.
        
        This method generates summaries directly from the JSON data without using AI models.
        
        Args:
            chapter_num: Chapter number for savepoint organization
            scene_num: Scene number for savepoint organization
            scene_definition: JSON string containing the scene definition
            settings: Generation settings for debugging
            
        Returns:
            Natural language summary of the scene outline with property-based headers
        """
        if not settings:
            return "Error: Generation settings required"
        
        try:
            # Parse the JSON scene definition
            import json
            scene_data = json.loads(scene_definition)
            
            if not isinstance(scene_data, dict):
                return "Invalid scene definition format"
            
            # Extract key information from the scene definition
            title = scene_data.get('title', 'Untitled Scene')
            description = scene_data.get('description', '')
            characters = scene_data.get('characters', [])
            setting = scene_data.get('setting', '')
            conflict = scene_data.get('conflict', '')
            tone = scene_data.get('tone', '')
            key_events = scene_data.get('key_events', [])
            dialogue = scene_data.get('dialogue', '')
            ending = scene_data.get('ending', '')
            literary_devices = scene_data.get('literary_devices', '')
            
            # Build a natural language summary using the properties as headers
            summary_parts = []
            
            if title:
                summary_parts.append(f"**{title}**")
            
            if description:
                summary_parts.append(description)
            
            if characters:
                if isinstance(characters, list):
                    char_bullets = "\n".join([f"• {str(char)}" for char in characters])
                    summary_parts.append(f"**Characters:**\n{char_bullets}")
                else:
                    summary_parts.append(f"**Characters:** {str(characters)}")
            
            if setting:
                summary_parts.append(f"**Setting:** {setting}")
            
            if conflict:
                summary_parts.append(f"**Conflict:** {conflict}")
            
            if tone:
                summary_parts.append(f"**Tone:** {tone}")
            
            if key_events:
                if isinstance(key_events, list):
                    event_bullets = "\n".join([f"• {str(event)}" for event in key_events])
                    summary_parts.append(f"**Key Events:**\n{event_bullets}")
                else:
                    summary_parts.append(f"**Key Events:** {str(key_events)}")
            
            if dialogue:
                summary_parts.append(f"**Example Dialogue:**\n{dialogue}")
            
            if ending:
                summary_parts.append(f"**Ending:** {ending}")
            
            if literary_devices:
                summary_parts.append(f"**Literary Devices:** {literary_devices}")
            
            # Join all parts with line breaks
            summary = "\n\n".join(summary_parts)
            
            if settings.debug:
                print(f"[SCENE OUTLINE SUMMARY PROGRAMMATIC] Generated summary: {len(summary)} characters")
            
            return summary
            
        except json.JSONDecodeError as e:
            if settings.debug:
                print(f"[SCENE OUTLINE SUMMARY PROGRAMMATIC] Error parsing JSON: {e}")
            return f"Error parsing scene definition: {e}"
        except Exception as e:
            if settings.debug:
                print(f"[SCENE OUTLINE SUMMARY PROGRAMMATIC] Error generating summary: {e}")
            return f"Error generating scene summary: {e}"
    
    async def _get_chapter_outline_summary(
        self,
        chapter_num: int,
        chapter_outline: str,
        tense: str = "present",
        settings: GenerationSettings = None
    ) -> str:
        """
        Get a natural language summary of a chapter outline.
        
        Args:
            chapter_num: Chapter number for savepoint organization
            chapter_outline: Chapter outline text to summarize
            tense: Tense to write in ("past", "present", or "future")
            settings: Generation settings for the model
            
        Returns:
            Natural language paragraph summary of the chapter outline in the specified tense
        """
        if not settings:
            return "Error: Generation settings required"
        
        try:
            # Execute the prompt with the model to generate a natural language summary
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="chapters/create_outline_summary",
                variables={
                    "chapter_outline": chapter_outline,
                    "tense": tense
                },
                savepoint_id=f"chapter_{chapter_num}/outline_summary_{tense}",
                model_config=ModelConfig.from_string(self.config["models"]["logical_model"]),
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream
            )
            
            summary = response.content.strip()
            
            if settings.debug:
                print(f"[CHAPTER OUTLINE SUMMARY] Generated {tense} tense summary: {len(summary)} characters")
            
            return summary
            
        except Exception as e:
            if settings.debug:
                print(f"[CHAPTER OUTLINE SUMMARY] Error generating summary: {e}")
            return f"Error generating chapter summary: {e}"
    
    async def _generate_scene_content_multistep(
        self,
        chapter_num: int,
        chapter_count: int,
        scene_count: int,
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
        """Generate content for a specific scene using multi-step conversation approach.
        
        This is a stub method that will implement scene generation using the multi-step
        conversation functionality for more coherent and context-aware scene creation.
        """

        instructions_config = ModelConfig.from_string(self.config["models"]["scene_writer"])
        scene_writer_config = ModelConfig.from_string(self.config["models"]["scene_writer"])
        scene_writer_config.parameters['temperature'] = 0.8
        scene_writer_config.parameters['top_p'] = 1
        scene_writer_config.parameters['top_k'] = 25
        scene_writer_config.parameters['frequency_penalty'] = 0.55
        scene_writer_config.parameters['presence_penalty'] = 0.55
        scene_writer_config.parameters['repeat_penalty'] = 1.1
        scene_writer_config.parameters['seed'] = 8080

        
        # Load the system message for multi-step scene generation
        system_message = load_prompt(
            handler=self.prompt_handler,
            prompt_id="multistep/scene/scene_writer_system",
            variables={"system_message": self.system_message}
        )

        # Extract character names from scene definition and get their summaries
        character_names = []
        try:
            import json
            scene_data = json.loads(scene_definition)
            if isinstance(scene_data, dict) and 'characters' in scene_data:
                character_names = scene_data['characters']
                if not isinstance(character_names, list):
                    character_names = [str(character_names)]
                # Ensure all character names are strings
                character_names = [str(name).strip() for name in character_names if name and str(name).strip()]
            else:
                if settings.debug:
                    print(f"[MULTISTEP SCENE] No 'characters' property found in scene definition or invalid format")
        except (json.JSONDecodeError, AttributeError) as e:
            if settings.debug:
                print(f"[MULTISTEP SCENE] Error parsing scene definition JSON: {e}")
                print(f"[MULTISTEP SCENE] Scene definition: {scene_definition[:200]}...")
            character_names = []

        # Get character summaries using the character manager utility
        characters_prompt = ""
        if character_names:
            try:
                character_summaries = await self.character_manager.get_character_summaries(character_names, settings)
                characters_prompt = load_prompt(
                    handler=self.prompt_handler,
                    prompt_id="multistep/scene/understand_characters",
                    variables={"characters": character_summaries}
                )
                if settings.debug:
                    print(f"[MULTISTEP SCENE] Retrieved summaries for {len(character_names)} characters: {character_names}")
            except Exception as e:
                if settings.debug:
                    print(f"[MULTISTEP SCENE] Error getting character summaries: {e}")
        else:
            if settings.debug:
                print(f"[MULTISTEP SCENE] No character names found in scene definition")

        # Extract setting names from scene definition and get their summaries
        setting_names = []
        try:
            # Reuse the already parsed scene_data if available, otherwise parse again
            if 'scene_data' not in locals():
                import json
                scene_data = json.loads(scene_definition)
            
            if isinstance(scene_data, dict) and 'setting' in scene_data:
                setting_names = scene_data['setting']
                if not isinstance(setting_names, list):
                    setting_names = [str(setting_names)]
                # Ensure all setting names are strings
                setting_names = [str(name).strip() for name in setting_names if name and str(name).strip()]
            else:
                if settings.debug:
                    print(f"[MULTISTEP SCENE] No 'setting' property found in scene definition or invalid format")
        except (json.JSONDecodeError, AttributeError) as e:
            if settings.debug:
                print(f"[MULTISTEP SCENE] Error parsing scene definition for settings: {e}")
            setting_names = []

        # Get setting summaries using the setting manager utility
        setting_prompt= ""
        if setting_names:
            try:
                setting_summary = await self.setting_manager.get_setting_summaries(setting_names, settings)
                setting_prompt = load_prompt(
                    handler=self.prompt_handler,
                    prompt_id="multistep/scene/understand_setting",
                    variables={"setting": setting_summary}
                )
                if settings.debug:
                    print(f"[MULTISTEP SCENE] Retrieved summaries for {len(setting_names)} settings: {setting_names}")
            except Exception as e:
                if settings.debug:
                    print(f"[MULTISTEP SCENE] Error getting setting summaries: {e}")
        else:
            if settings.debug:
                print(f"[MULTISTEP SCENE] No setting names found in scene definition")

            # Progressive multi-step conversation building
        conversation_history = []
            #    {"role": "user", "content": system_message},
            #    {"role": "assistant", "content": "I understand the system message"},
            #]

        next_scene_outline = ""
        if scene_num == 1 or scene_num != chapter_count:
            next_scene_outline = await self._get_scene_outline_summary(
                chapter_num=chapter_num,
                scene_num=scene_num + 1,
                scene_definition=next_scene_definition,
                settings=settings
            )

        next_chapter_outline = ""
        if scene_num == chapter_count:
            next_chapter_outline = await self._get_chapter_outline_summary(
                chapter_num=chapter_num + 1,
                chapter_outline=chapter_outline,
                settings=settings
            )

        if scene_num == chapter_count or scene_num != 1:
            previous_scene_summary = await self.savepoint_manager.load_step(f"chapter_{chapter_num}/scene_{scene_num - 1}_multistep_content")
        try:
            # Get the model provider for multi-step conversation
            model_config = ModelConfig.from_string(self.config["models"]["scene_writer"])
            
            if settings.debug:
                print(f"[MULTISTEP SCENE] Starting progressive multi-step conversation")
                print(f"[MULTISTEP SCENE] System message loaded: {len(system_message)} characters")
            
            # Step 1: First user message (understand elements)
            try:
                elements_prompt = load_prompt(
                    handler=self.prompt_handler,
                    prompt_id="multistep/scene/understand_elements",
                    variables={"story_elements": story_elements}
                )
                
                conversation_history.append({"role": "user", "content": elements_prompt})

                if settings.debug:
                    print(f"[MULTISTEP SCENE] Step 1: First message added (understand elements)")
                    print(f"[MULTISTEP SCENE] Message length: {len(elements_prompt)} characters")
                
                response = await execute_messages_with_savepoint(
                    handler=self.prompt_handler,
                    conversation_history=conversation_history,
                    model_config=instructions_config,
                    seed=settings.seed + chapter_num + scene_num,
                    debug=settings.debug,
                    stream=True
                )


                
                # Extract content from PromptResponse
                conversation_history.append({"role": "assistant", "content": response.content})
                
                if settings.debug:
                    print(f"[MULTISTEP SCENE] Step 1 completed")

            except Exception as e:
                if settings.debug:
                    print(f"[MULTISTEP SCENE] Error in step 1: {e}")
            
            # Step 2: Second user message (understand context) # Only continue if first step succeeded
            try:
                context_prompt = load_prompt(
                    handler=self.prompt_handler,
                    prompt_id="multistep/scene/understand_context",
                    variables={"base_context": base_context}
                )
                
                conversation_history.append({"role": "user", "content": context_prompt})
                
                if settings.debug:
                    print(f"[MULTISTEP SCENE] Step 2: Second message added (understand context)")
                    print(f"[MULTISTEP SCENE] Message length: {len(context_prompt)} characters")

                
                response = await execute_messages_with_savepoint(
                    handler=self.prompt_handler,
                    conversation_history=conversation_history,
                    model_config=instructions_config,
                    seed=settings.seed + chapter_num + scene_num,
                    debug=settings.debug,
                    stream=True
                )


                
                conversation_history.append({"role": "assistant", "content": response.content})

                if settings.debug:
                    print(f"[MULTISTEP SCENE] Step 2 completed")
            
            except Exception as e:
                if settings.debug:
                    print(f"[MULTISTEP SCENE] Error in step 2: {e}")
            
            # Step 3: Third user message (understand characters) - only if characters exist
            if character_names:  # Only continue if previous step succeeded and characters exist
                try:
                    # Add third user message to array
                    conversation_history.append({"role": "user", "content": characters_prompt})
                    
                    if settings.debug:
                        print(f"[MULTISTEP SCENE] Step 3: Third message added (understand characters)")
                        print(f"[MULTISTEP SCENE] Message length: {len(characters_prompt)} characters")
                    
                    response = await execute_messages_with_savepoint(
                        handler=self.prompt_handler,
                        conversation_history=conversation_history,
                        model_config=instructions_config,
                        seed=settings.seed + chapter_num + scene_num,
                        debug=settings.debug,
                        stream=True
                    )


                    
                    conversation_history.append({"role": "assistant", "content": response.content})
                    
                    if settings.debug:
                        print(f"[MULTISTEP SCENE] Step 3 completed")
                
                except Exception as e:
                    if settings.debug:
                        print(f"[MULTISTEP SCENE] Error in step 3: {e}")
            elif not character_names and settings.debug:
                print(f"[MULTISTEP SCENE] Step 3 skipped - no characters found in scene definition")
            
            # Step 4: Fourth user message (understand setting) - only if settings exist
            if setting_names:  # Only continue if previous step succeeded and settings exist
                try:
                    # Add fourth user message to array
                    conversation_history.append({"role": "user", "content": setting_prompt})
                    
                    if settings.debug:
                        print(f"[MULTISTEP SCENE] Step 4: Fourth message added (understand setting)")
                        print(f"[MULTISTEP SCENE] Message length: {len(setting_prompt)} characters")
                    
                    response = await execute_messages_with_savepoint(
                        handler=self.prompt_handler,
                        conversation_history=conversation_history,
                        model_config=instructions_config,
                        seed=settings.seed + chapter_num + scene_num,
                        debug=settings.debug,
                        stream=True
                    )


                    
                    conversation_history.append({"role": "assistant", "content": response.content})
                    
                    if settings.debug:
                        print(f"[MULTISTEP SCENE] Step 4 completed")

                except Exception as e:
                    if settings.debug:
                        print(f"[MULTISTEP SCENE] Error in step 4: {e}")
            elif not setting_names and settings.debug:
                print(f"[MULTISTEP SCENE] Step 4 skipped - no settings found in scene definition")


            if scene_num == 1 or scene_num != chapter_count:
                try:
                    next_scene_outline = await self._get_scene_outline_summary(
                        chapter_num=chapter_num,
                        scene_num=scene_num + 1,
                        scene_definition=next_scene_definition,
                        settings=settings
                    )
                    # Another step in the multistep conversation to understand the next scene
                    understand_next_scene_prompt = load_prompt(
                        handler=self.prompt_handler,
                        prompt_id="multistep/scene/understand_next_scene",
                        variables={"next_scene_outline": next_scene_outline}
                    )
                    conversation_history.append({"role": "user", "content": understand_next_scene_prompt})

                    response = await execute_messages_with_savepoint(
                        handler=self.prompt_handler,
                        conversation_history=conversation_history,
                        model_config=instructions_config,
                        seed=settings.seed + chapter_num + scene_num,
                        debug=settings.debug,
                        stream=True
                    )

                    
                    conversation_history.append({"role": "assistant", "content": response.content})
                    
                    if settings.debug:
                        print(f"[MULTISTEP SCENE] Step 5 completed")
                
                except Exception as e:
                    if settings.debug:
                        print(f"[MULTISTEP SCENE] Error in step 5: {e}")

            if scene_num == chapter_count or scene_num != 1:
                try:
                    # Another step in the multistep conversation to understand the previous scene
                    understand_previous_scene_prompt = load_prompt(
                        handler=self.prompt_handler,
                        prompt_id="multistep/scene/understand_previous_scene",
                        variables={"previous_scene_summary": previous_scene_summary}
                    )
                    conversation_history.append({"role": "user", "content": understand_previous_scene_prompt})

                    response = await execute_messages_with_savepoint(
                        handler=self.prompt_handler,
                        conversation_history=conversation_history,
                        model_config=instructions_config,
                        seed=settings.seed + chapter_num + scene_num,
                        debug=settings.debug,
                        stream=True
                    )

                    
                    conversation_history.append({"role": "assistant", "content": response.content})
                    
                    if settings.debug:
                        print(f"[MULTISTEP SCENE] Step 6 completed")

                except Exception as e:
                    if settings.debug:
                        print(f"[MULTISTEP SCENE] Error in step 6: {e}")

            if scene_num == chapter_count:
                try:
                    # Another step in the multistep conversation to understand the next chapter
                    understand_next_chapter_prompt = load_prompt(
                        handler=self.prompt_handler,
                        prompt_id="multistep/scene/understand_next_chapter",
                        variables={"next_chapter_summary": next_chapter_outline}
                    )
                    conversation_history.append({"role": "user", "content": understand_next_chapter_prompt})
                    
                    response = await execute_messages_with_savepoint(
                        handler=self.prompt_handler,
                        conversation_history=conversation_history,
                        model_config=instructions_config,
                        seed=settings.seed + chapter_num + scene_num,
                        debug=settings.debug,
                        stream=True
                    )

                    
                    conversation_history.append({"role": "assistant", "content": response.content})
                    
                    if settings.debug:
                        print(f"[MULTISTEP SCENE] Step 7 completed")
                    
                except Exception as e:
                    if settings.debug:
                        print(f"[MULTISTEP SCENE] Error in step 7: {e}")

            scene_outline = await self._get_scene_outline_summary_programmatic(
                scene_definition=scene_definition,
                settings=settings
            )

            # If we are at the first chapter
            if scene_num == 1:
                content_prompt = load_prompt(
                    handler=self.prompt_handler,
                    prompt_id="multistep/scene/create_content_first",
                    variables={
                        "current_scene_summary": scene_outline,
                        "base_context": base_context
                    }
                )
            # Else if we are at the last chapter
            elif scene_num == chapter_count:
                content_prompt = load_prompt(
                    handler=self.prompt_handler,
                    prompt_id="multistep/scene/create_content_last",
                    variables={
                        "current_scene_summary": scene_outline,
                        "base_context": base_context
                    }
                )

            # Else we are in the middle of the story
            else:
                content_prompt = load_prompt(
                    handler=self.prompt_handler,
                    prompt_id="multistep/scene/create_content_middle",
                    variables={
                        "current_scene_summary": scene_outline,
                        "base_context": base_context
                    }
                )

            conversation_history.append({"role": "user", "content": content_prompt})

            response = await execute_messages_with_savepoint(
                handler=self.prompt_handler,
                conversation_history=conversation_history,
                savepoint_id=f"chapter_{chapter_num}/scene_{scene_num}_multistep_content",
                model_config=scene_writer_config,
                seed=settings.seed + chapter_num + scene_num,
                debug=settings.debug,
                stream=True
            )
            
            # TODO: Continue with additional steps as needed
            # Each step will:
            # 1. Add new user message to user_messages array
            # 2. Call generate_multistep_conversation with all user messages
            # 3. Repeat for next step
            
            if settings.debug:
                print(f"[MULTISTEP SCENE] Progressive conversation completed")
            
        except Exception as e:
            if settings.debug:
                print(f"[MULTISTEP SCENE] Error in progressive conversation: {e}")
            # Fall back to standard generation
            pass

        return response.content.strip()
    
    async def _clean_scene_content(
        self,
        scene_content: str,
        chapter_num: int,
        scene_num: int,
        settings: GenerationSettings
    ) -> str:
        """Clean the generated scene content to remove commentary and repetition."""
        model_config = ModelConfig.from_string(self.config["models"]["scene_writer"])
        
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
        model_config = ModelConfig.from_string(self.config["models"]["scene_writer"])
        
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
        model_config = ModelConfig.from_string(self.config["models"]["scene_writer"])
        
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
