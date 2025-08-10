"""Outline-Chapter story writing strategy."""

from typing import List, Optional, Dict
from domain.entities.story import Story, Outline, Chapter, StoryInfo
from domain.value_objects.generation_settings import GenerationSettings
from domain.value_objects.model_config import ModelConfig
from domain.exceptions import StoryGenerationError
from domain.repositories.savepoint_repository import SavepointRepository
from config.settings import AppConfig
from ..interfaces.story_strategy import StoryStrategy
from ..interfaces.model_provider import ModelProvider
from infrastructure.prompts.prompt_loader import PromptLoader
from infrastructure.prompts.prompt_handler import PromptHandler
from infrastructure.prompts.prompt_wrapper import execute_prompt_with_savepoint
from infrastructure.savepoints import SavepointManager


class OutlineChapterStrategy(StoryStrategy):
    """Story writing strategy that generates outline first, then chapters."""
    
    def __init__(
        self, 
        model_provider: ModelProvider, 
        config: AppConfig, 
        prompt_loader: PromptLoader,
        savepoint_repo: Optional[SavepointRepository] = None
    ):
        super().__init__(model_provider)
        self.config = config
        self.prompt_loader = prompt_loader
        self.savepoint_repo = savepoint_repo
        self.savepoint_manager: Optional[SavepointManager] = None
        
        # Create the prompt handler
        self.prompt_handler = PromptHandler(
            model_provider=model_provider,
            prompt_loader=prompt_loader,
            savepoint_repo=savepoint_repo
        )
        
        # System message for consistent context and role signaling
        self.system_message = """You are an expert creative writer and storyteller specializing in novel writing. Your role is to help create compelling, well-structured stories with rich characters, engaging plots, and vivid descriptions.

When responding to prompts:
- Maintain consistency with the established story elements and context
- Provide detailed, creative responses that advance the narrative
- Consider character development, plot progression, and thematic elements
- Write in a clear, engaging style appropriate for the target audience
- Follow any specific formatting or structural requirements given in the prompt
- Ensure your responses contribute to a cohesive overall story arc

You have deep knowledge of storytelling techniques, character development, plot structure, and creative writing principles. Use this expertise to create high-quality story content."""
    
    def _setup_savepoints(self, prompt_filename: str) -> None:
        """Setup savepoint manager for the current story."""
        if self.savepoint_repo:
            self.savepoint_manager = SavepointManager(self.savepoint_repo, prompt_filename)
            # Also set up the prompt handler with the story directory
            self.prompt_handler.set_story_directory(prompt_filename)
    
    def _create_messages_with_system(self, user_content: str) -> List[Dict[str, str]]:
        """Create messages list with system message included."""
        return [
            {"role": "user", "content": self.system_message + "\n\n" + user_content}
        ]
    
    def get_system_message(self) -> str:
        """Get the current system message."""
        return self.system_message
    
    def set_system_message(self, system_message: str) -> None:
        """Set a custom system message."""
        self.system_message = system_message
    
    def get_default_system_message(self) -> str:
        """Get the default system message."""
        return """You are an expert creative writer and storyteller specializing in novel writing. Your role is to help create compelling, well-structured stories with rich characters, engaging plots, and vivid descriptions.

When responding to prompts:
- Maintain consistency with the established story elements and context
- Provide detailed, creative responses that advance the narrative
- Consider character development, plot progression, and thematic elements
- Write in a clear, engaging style appropriate for the target audience
- Follow any specific formatting or structural requirements given in the prompt
- Ensure your responses contribute to a cohesive overall story arc

You have deep knowledge of storytelling techniques, character development, plot structure, and creative writing principles. Use this expertise to create high-quality story content."""
    
    def reset_system_message(self) -> None:
        """Reset the system message to the default."""
        self.system_message = self.get_default_system_message()
    

    
    async def generate_outline(self, prompt: str, settings: GenerationSettings, prompt_filename: Optional[str] = None) -> Outline:
        """Generate story outline from prompt."""
        try:
            # Setup savepoints if available
            if prompt_filename and self.savepoint_repo:
                self._setup_savepoints(prompt_filename)
            
            # Extract story start date
            start_date = await self._extract_story_start_date(prompt, settings)
            
            # Extract base context
            base_context = await self._extract_base_context(prompt, settings)
            
            # Generate story elements
            story_elements = await self._generate_story_elements(prompt, settings)
            
            # Generate initial outline (this now includes critique refinement)
            final_outline = await self._generate_initial_outline(
                prompt, story_elements, base_context, settings
            )
            
            # Get the initial outline from savepoint if available
            initial_outline = None
            if self.savepoint_manager:
                try:
                    initial_outline = await self.savepoint_manager.load_step("initial_outline")
                except:
                    initial_outline = final_outline  # Fallback to final outline if initial not found
            
            # Generate detailed chapter list
            chapter_list = await self._generate_chapter_list(
                final_outline, base_context, story_elements, settings
            )
            
            # Exit the process here
            # import sys
            # print("Exiting after chapter list generation as requested.")
            # sys.exit(0)
            
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
    
    async def generate_chapters(self, outline: Outline, settings: GenerationSettings) -> List[Chapter]:
        """Generate chapters from outline."""
        try:
            if not self.savepoint_manager:
                # Fallback to original behavior if no savepoint manager
                total_chapters = await self._count_chapters(outline.initial_outline, settings)
                
                chapters = []
                for chapter_num in range(1, total_chapters + 1):
                    chapter = await self._generate_chapter(
                        chapter_num, total_chapters, outline, chapters, settings
                    )
                    chapters.append(chapter)
                
                return chapters
            
            # New workflow: iterate over chapter synopses and generate outlines
            # First, find existing chapter directories in the savepoint directory
            import os
            import re
            
            chapter_count = 0
            # The savepoint repository creates a story-specific directory based on prompt filename
            # We need to look in the current story directory, not the base savepoint directory
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
            
            print(f"Found {chapter_count} chapter directories in {story_dir}. Generating outlines...")
            
            # Generate outlines for each chapter
            for chapter_num in range(1, chapter_count + 1):
                # Verify that this chapter has a synopsis
                try:
                    synopsis = await self.savepoint_manager.load_step(f"chapter_{chapter_num}/base_synopsis")
                    if not synopsis or synopsis.strip() == "":
                        print(f"Chapter {chapter_num} has no synopsis, skipping...")
                        continue
                except:
                    print(f"Chapter {chapter_num} synopsis not found, skipping...")
                    continue
                
                # Check if outline already exists
                chapter_outline = None
                try:
                    if await self.savepoint_manager.has_step(f"chapter_{chapter_num}/base_outline"):
                        print(f"Chapter {chapter_num} outline already exists")
                        chapter_outline = await self.savepoint_manager.load_step(f"chapter_{chapter_num}/base_outline")
                except:
                    pass
                
                # Generate outline if not found
                if chapter_outline is None:
                    print(f"Generating outline for chapter {chapter_num}...")
                    chapter_outline = await self._generate_chapter_outline(
                        chapter_num, chapter_count, outline, settings
                    )

                previous_chapter_recap = ""
                if chapter_num > 1:
                    try:
                        previous_chapter_recap = await self.savepoint_manager.load_step(f"chapter_{chapter_num - 1}/recap")
                    except:
                        pass  # Previous chapter recap not available

                if await self.savepoint_manager.has_step(f"chapter_{chapter_num}/recap"):
                    sanitized_recap = await self.savepoint_manager.load_step(f"chapter_{chapter_num}/recap")
                else:
                    # 11. Generate recap information
                    recap = await self._generate_recap(
                        chapter_num, chapter_outline, outline.story_start_date, previous_chapter_recap, settings
                    )
                    # 12. Run recap sanitizer and save to chapter_{number}/recap
                    sanitized_recap = await self._run_recap_sanitizer(recap, outline.story_start_date, previous_chapter_recap, settings)
                
                # Save the sanitized recap
                await self.savepoint_manager.save_step(f"chapter_{chapter_num}/recap", sanitized_recap)
            
            print(f"Chapter outline generation completed for {chapter_count} chapters.")
            return []  # Return empty list since we're stopping after outline generation
            
        except Exception as e:
            raise StoryGenerationError(f"Failed to generate chapters: {e}") from e
    
    async def _generate_chapter_outline(
        self,
        chapter_num: int,
        total_chapters: int,
        outline: Outline,
        settings: GenerationSettings
    ) -> str:
        """Generate outline for a specific chapter from its synopsis."""
        try:
            # 1. Get the current chapter synopsis
            current_chapter_synopsis = await self.savepoint_manager.load_step(f"chapter_{chapter_num}/base_synopsis")
            
            # 2. Get the next chapter synopsis (if applicable)
            next_chapter_synopsis = ""
            if chapter_num < total_chapters:
                try:
                    next_chapter_synopsis = await self.savepoint_manager.load_step(f"chapter_{chapter_num + 1}/base_synopsis")
                except:
                    pass  # Next chapter synopsis not available
            
            # 3. Get previous chapter outline (if applicable)
            previous_chapter_outline = ""
            if chapter_num > 1:
                try:
                    previous_chapter_outline = await self.savepoint_manager.load_step(f"chapter_{chapter_num - 1}/base_outline")
                except:
                    pass  # Previous chapter outline not available
            
            # 4. Get previous chapter recap (if applicable)
            previous_chapter_recap = ""
            if chapter_num > 1:
                try:
                    previous_chapter_recap = await self.savepoint_manager.load_step(f"chapter_{chapter_num - 1}/recap")
                except:
                    pass  # Previous chapter recap not available
            
            # 5. Get initial outline
            initial_outline = outline.initial_outline or outline.final_outline
            
            # 6. Get base context
            base_context = outline.base_context
            
            # 8. Generate the chapter outline using the chapter_outline.md prompt
            step_decorator = self.savepoint_manager.step(f"chapter_{chapter_num}/base_outline")
            
            chapter_outline = await step_decorator(self._generate_chapter_outline_impl)(
                chapter_num=chapter_num,
                outline=initial_outline,
                base_context=base_context,
                recap=previous_chapter_recap,
                current_chapter_synopsis=current_chapter_synopsis,
                next_chapter_synopsis=next_chapter_synopsis,
                previous_chapter_outline=previous_chapter_outline,
                settings=settings
            )
            
            # 9. Run disambiguator prompt over the outline
            chapter_outline = await self._run_disambiguator(chapter_outline, settings)
            
            # 10. Run cleanup prompt over the outline
            chapter_outline = await self._run_cleanup(chapter_outline, settings)
            
            return chapter_outline
            
        except Exception as e:
            raise StoryGenerationError(f"Failed to generate outline for chapter {chapter_num}: {e}") from e
    
    async def _generate_chapter_outline_impl(
        self,
        chapter_num: int,
        outline: str,
        base_context: str,
        recap: str,
        current_chapter_synopsis: str,
        next_chapter_synopsis: str,
        previous_chapter_outline: str,
        settings: GenerationSettings
    ) -> str:
        """Generate the chapter outline using the new multi-prompt pipeline."""
        try:
            if settings.debug:
                print(f"[CHAPTER OUTLINE] Starting multi-prompt pipeline for chapter {chapter_num}")
            
            # Step 1: Generate core outline
            core_outline = await self._generate_core_outline(
                chapter_num, outline, base_context, recap,
                current_chapter_synopsis, next_chapter_synopsis, previous_chapter_outline, settings
            )
            
            # Step 2: Validate quality and continuity
            validation_result = await self._validate_outline_quality(
                core_outline, previous_chapter_outline, next_chapter_synopsis, settings
            )
            
            # Parse validation result and handle issues
            validated_outline = await self._handle_validation_result(
                core_outline, validation_result, chapter_num, outline, base_context, 
                recap, current_chapter_synopsis, next_chapter_synopsis, 
                previous_chapter_outline, settings
            )
            
            # Step 3: Format and structure consistently
            final_outline = await self._format_outline_structure(
                validated_outline, settings
            )
            
            if settings.debug:
                print(f"[CHAPTER OUTLINE] Multi-prompt pipeline completed for chapter {chapter_num}")
            
            return final_outline
            
        except Exception as e:
            if settings.debug:
                print(f"[CHAPTER OUTLINE] Error in multi-prompt pipeline: {e}")
            # Fallback to original method if new pipeline fails
            return await self._generate_chapter_outline_fallback(
                chapter_num, outline, base_context, recap,
                current_chapter_synopsis, next_chapter_synopsis, previous_chapter_outline, settings
            )
    
    async def _run_disambiguator(self, chapter_outline: str, settings: GenerationSettings) -> str:
        """Run the disambiguator prompt over the chapter outline."""
        model_config = self.config.get_model("chapter_outline_writer")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="chapter_outline_disambiguator",
            variables={"chapter_outline": chapter_outline},
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def _run_cleanup(self, chapter_outline: str, settings: GenerationSettings) -> str:
        """Run the cleanup prompt over the chapter outline."""
        model_config = self.config.get_model("chapter_outline_writer")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="chapter_outline_cleanup",
            variables={"chapter_outline": chapter_outline},
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def _generate_core_outline(
        self,
        chapter_num: int,
        outline: str,
        base_context: str,
        recap: str,
        current_chapter_synopsis: str,
        next_chapter_synopsis: str,
        previous_chapter_outline: str,
        settings: GenerationSettings
    ) -> str:
        """Step 1: Generate the core chapter outline using the simplified prompt."""
        model_config = self.config.get_model("chapter_outline_writer")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="chapter_outline_core",
            variables={
                "chapter_number": str(chapter_num),
                "outline": outline,
                "base_context": base_context,
                "recap": recap,
                "current_chapter_synopsis": current_chapter_synopsis,
                "next_chapter_synopsis": next_chapter_synopsis,
                "previous_chapter_outline": previous_chapter_outline
            },
            savepoint_id=f"chapter_{chapter_num}/core_outline",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def _validate_outline_quality(
        self,
        chapter_outline: str,
        previous_chapter_outline: str,
        next_chapter_synopsis: str,
        settings: GenerationSettings
    ) -> str:
        """Step 2: Validate the outline for quality, continuity, and structure."""
        model_config = self.config.get_model("chapter_outline_writer")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="chapter_outline_validator",
            variables={
                "chapter_outline": chapter_outline,
                "previous_chapter_outline": previous_chapter_outline,
                "next_chapter_synopsis": next_chapter_synopsis
            },
            savepoint_id=f"chapter_outline_validation",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def _format_outline_structure(
        self,
        chapter_outline: str,
        settings: GenerationSettings
    ) -> str:
        """Step 3: Ensure consistent formatting and structure."""
        model_config = self.config.get_model("chapter_outline_writer")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="chapter_outline_formatter",
            variables={
                "chapter_outline": chapter_outline
            },
            savepoint_id=f"chapter_outline_formatting",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def _handle_validation_result(
        self,
        current_outline: str,
        validation_result: str,
        chapter_num: int,
        outline: str,
        base_context: str,
        recap: str,
        current_chapter_synopsis: str,
        next_chapter_synopsis: str,
        previous_chapter_outline: str,
        settings: GenerationSettings
    ) -> str:
        """Handle validation results and regenerate outline if issues are found."""
        try:
            # Parse the JSON validation result
            import json
            validation_data = json.loads(validation_result.strip())
            
            if settings.debug:
                print(f"[VALIDATION] Quality: {validation_data.get('overall_quality', 'unknown')}")
                print(f"[VALIDATION] Issues found: {len(validation_data.get('issues', []))}")
            
            # If validation passes, return the current outline
            if validation_data.get('overall_quality') == 'good':
                if settings.debug:
                    print(f"[VALIDATION] Outline passed validation for chapter {chapter_num}")
                return current_outline
            
            # If validation fails, regenerate with feedback
            if settings.debug:
                print(f"[VALIDATION] Regenerating outline for chapter {chapter_num} due to validation issues")
            
            # Create enhanced prompt with validation feedback
            enhanced_outline = await self._regenerate_outline_with_feedback(
                chapter_num, outline, base_context, recap,
                current_chapter_synopsis, next_chapter_synopsis, previous_chapter_outline,
                validation_data.get('issues', []), settings
            )
            
            return enhanced_outline
            
        except (json.JSONDecodeError, KeyError) as e:
            if settings.debug:
                print(f"[VALIDATION] Error parsing validation result: {e}")
                print(f"[VALIDATION] Raw result: {validation_result}")
            # If validation parsing fails, return the original outline
            return current_outline
    
    async def _regenerate_outline_with_feedback(
        self,
        chapter_num: int,
        outline: str,
        base_context: str,
        recap: str,
        current_chapter_synopsis: str,
        next_chapter_synopsis: str,
        previous_chapter_outline: str,
        validation_issues: list,
        settings: GenerationSettings
    ) -> str:
        """Regenerate the outline incorporating validation feedback using the improved prompt."""
        model_config = self.config.get_model("chapter_outline_writer")
        
        # Format validation issues for the prompt
        validation_feedback = self._format_validation_issues(validation_issues)
        
        if settings.debug:
            print(f"[VALIDATION] Regenerating outline for chapter {chapter_num} using improved prompt")
            print(f"[VALIDATION] Issues to address: {len(validation_issues)}")
        
        # Use the dedicated improved outline prompt with all context
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="chapter_outline_improved",
            variables={
                "chapter_number": chapter_num,
                "outline": outline,
                "base_context": base_context,
                "recap": recap,
                "current_chapter_synopsis": current_chapter_synopsis,
                "next_chapter_synopsis": next_chapter_synopsis,
                "previous_chapter_outline": previous_chapter_outline,
                "original_outline": "",  # Could include the failed outline if needed
                "validation_feedback": validation_feedback
            },
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    def _format_validation_issues(self, issues: list) -> str:
        """Format validation issues into readable text for prompts."""
        if not issues:
            return "No specific issues identified."
        
        formatted_issues = []
        for issue in issues:
            issue_type = issue.get('type', 'unknown')
            scene = issue.get('scene', 'unknown')
            description = issue.get('description', 'No description')
            suggestion = issue.get('suggestion', 'No suggestion')
            
            formatted_issues.append(f"""
Issue Type: {issue_type}
Scene: {scene}
Description: {description}
Suggestion: {suggestion}
---""")
        
        return "\n".join(formatted_issues)
    
    async def _generate_chapter_outline_fallback(
        self,
        chapter_num: int,
        outline: str,
        base_context: str,
        recap: str,
        current_chapter_synopsis: str,
        next_chapter_synopsis: str,
        previous_chapter_outline: str,
        settings: GenerationSettings
    ) -> str:
        """Fallback method using the original single prompt approach."""
        if settings.debug:
            print(f"[CHAPTER OUTLINE] Using fallback method for chapter {chapter_num}")
        
        model_config = self.config.get_model("chapter_outline_writer")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="chapter_outline",
            variables={
                "chapter_number": str(chapter_num),
                "outline": outline,
                "base_context": base_context,
                "recap": recap,
                "current_chapter_synopsis": current_chapter_synopsis,
                "next_chapter_synopsis": next_chapter_synopsis,
                "previous_chapter_outline": previous_chapter_outline
            },
            savepoint_id=f"chapter_{chapter_num}/fallback_outline",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def _generate_recap(
        self,
        chapter_num: int,
        chapter_outline: str,
        story_start_date: str,
        previous_chapter_recap: str,
        settings: GenerationSettings
    ) -> str:
        """Generate recap information from the chapter outline using the new multi-prompt pipeline."""
        if settings.debug:
            print(f"[RECAP GENERATION] Starting multi-prompt pipeline for chapter {chapter_num}")
        
        try:
            # Step 1: Extract basic events
            events = await self._extract_chapter_events(chapter_outline, settings)
            
            # Step 2: Assign timing to events
            timed_events = await self._assign_event_timing(events, story_start_date, settings)
            
            # Step 3: Enrich events with details
            enriched_events = await self._enrich_event_details(timed_events, settings)
            
            # Step 4: Format final recap output
            final_recap = await self._format_recap_output(enriched_events, settings)
            
            if settings.debug:
                print(f"[RECAP GENERATION] Successfully generated recap with {len(timed_events)} events")
            
            return final_recap
            
        except Exception as e:
            if settings.debug:
                print(f"[RECAP GENERATION] Error in pipeline: {e}")
            # Fallback to original method if new pipeline fails
            return await self._generate_recap_fallback(chapter_num, chapter_outline, story_start_date, previous_chapter_recap, settings)
    
    async def _extract_chapter_events(self, chapter_outline: str, settings: GenerationSettings) -> str:
        """Step 1: Extract basic events from chapter outline."""
        model_config = self.config.get_model("chapter_outline_writer")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="extract_chapter_events",
            variables={
                "chapter_outline": chapter_outline
            },
            savepoint_id=f"chapter_events_extraction",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def _assign_event_timing(self, events: str, story_start_date: str, settings: GenerationSettings) -> str:
        """Step 2: Assign timing to extracted events."""
        model_config = self.config.get_model("chapter_outline_writer")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="assign_event_timing",
            variables={
                "story_start_date": story_start_date,
                "events": events
            },
            savepoint_id=f"event_timing_assignment",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def _enrich_event_details(self, timed_events: str, settings: GenerationSettings) -> str:
        """Step 3: Enrich events with character development, locations, symbols, and impact."""
        model_config = self.config.get_model("chapter_outline_writer")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="enrich_event_details",
            variables={
                "timed_events": timed_events
            },
            savepoint_id=f"event_detail_enrichment",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def _format_recap_output(self, enriched_events: str, settings: GenerationSettings) -> str:
        """Step 4: Format enriched events into final recap output."""
        model_config = self.config.get_model("chapter_outline_writer")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="format_recap_output",
            variables={
                "enriched_events": enriched_events
            },
            savepoint_id=f"recap_formatting",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def _generate_recap_fallback(self, chapter_num: int, chapter_outline: str, story_start_date: str, previous_chapter_recap: str, settings: GenerationSettings) -> str:
        """Fallback method using the original single-prompt approach."""
        if settings.debug:
            print(f"[RECAP GENERATION] Using fallback method for chapter {chapter_num}")
        
        model_config = self.config.get_model("chapter_outline_writer")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="chapter_outline_recap_v2",
            variables={
                "story_start_date": story_start_date,
                "full_recap": previous_chapter_recap,
                "chapter_outline": chapter_outline
            },
            savepoint_id=f"chapter_{chapter_num}/recap_fallback",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def _run_recap_sanitizer(self, recap: str, story_start_date: str, previous_chapter_recap: str, settings: GenerationSettings) -> str:
        """Run the multi-stage recap sanitizer pipeline."""
        if settings.debug:
            print("Using multi-stage recap sanitizer with format-specific prompts")
        
        return await self._run_multi_stage_recap_sanitizer(recap, story_start_date, previous_chapter_recap, settings)
    

    
    async def _run_multi_stage_recap_sanitizer(self, recap: str, story_start_date: str, previous_chapter_recap: str, settings: GenerationSettings) -> str:
        """Run the improved multi-stage recap sanitizer pipeline."""
        model_config = self.config.get_model("logical_model")
        
        if settings.debug:
            print("[MULTI-STAGE RECAP SANITIZER] Starting multi-stage pipeline with format-specific prompts")
        
        try:
            # Stage 1: Extract and normalize events
            if settings.debug:
                print("Recap sanitizer: Starting Stage 1 - Event extraction")
            
            stage1_response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="recap_extract_events",
                variables={
                    "previous_recap": previous_chapter_recap,
                    "recap": recap
                },
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                system_message=self.system_message
            )
            
            events_json = stage1_response.content.strip()
            
            # Stage 2: Sanitize JSON and programmatically classify events by recency
            if settings.debug:
                print("Recap sanitizer: Starting Stage 2 - JSON sanitization and programmatic event classification")
            
            # Sanitize the JSON response first
            sanitized_events_json = self._sanitize_json_response(events_json)
            
            # Extract current date from the latest recap or use story start date
            current_date = self._extract_current_date_from_recap(recap, story_start_date)
            
            # Programmatically classify events by recency
            classified_events_json = self._classify_event_recency_programmatically(sanitized_events_json, current_date)

            # Log the classified events
            if settings.debug:
                print(f"Classified events: {classified_events_json}")
            
            if settings.debug:
                print(f"Current date used for classification: {current_date}")
                print(f"Events after classification: {len(classified_events_json.split('date_start'))-1} events")
            
            # Stage 3: Format output using format-specific prompts
            if settings.debug:
                print("Recap sanitizer: Starting Stage 3 - Format-specific output formatting")
            
            # Parse the classified events JSON for formatting
            import json
            
            try:
                events = json.loads(classified_events_json)
            except json.JSONDecodeError:
                if settings.debug:
                    print("Failed to parse classified events JSON, using empty list")
                events = []
            
            # Group events by format
            historical_events = [e for e in events if e.get("format") == "historical"]
            recent_events = [e for e in events if e.get("format") == "recent"]
            current_events = [e for e in events if e.get("format") == "current"]
            
            if settings.debug:
                print(f"Grouped events: {len(historical_events)} historical, {len(recent_events)} recent, {len(current_events)} current")
            
            formatted_sections = []
            
            # Format historical events if any exist
            if historical_events:
                if settings.debug:
                    print("Formatting historical events...")
                historical_response = await execute_prompt_with_savepoint(
                    handler=self.prompt_handler,
                    prompt_id="recap_format_historical",
                    variables={
                        "historical_events_json": json.dumps(historical_events, indent=2)
                    },
                    model_config=model_config,
                    seed=settings.seed,
                    debug=settings.debug,
                    stream=settings.stream,
                    system_message=self.system_message
                )
                formatted_sections.append(historical_response.content.strip())
            
            # Format recent events if any exist
            if recent_events:
                if settings.debug:
                    print("Formatting recent events...")
                recent_response = await execute_prompt_with_savepoint(
                    handler=self.prompt_handler,
                    prompt_id="recap_format_recent",
                    variables={
                        "recent_events_json": json.dumps(recent_events, indent=2)
                    },
                    model_config=model_config,
                    seed=settings.seed,
                    debug=settings.debug,
                    stream=settings.stream,
                    system_message=self.system_message
                )
                formatted_sections.append(recent_response.content.strip())
            
            # Format current events if any exist
            if current_events:
                if settings.debug:
                    print("Formatting current events...")
                current_response = await execute_prompt_with_savepoint(
                    handler=self.prompt_handler,
                    prompt_id="recap_format_current",
                    variables={
                        "current_events_json": json.dumps(current_events, indent=2)
                    },
                    model_config=model_config,
                    seed=settings.seed,
                    debug=settings.debug,
                    stream=settings.stream,
                    system_message=self.system_message
                )
                formatted_sections.append(current_response.content.strip())
            
            # Combine all sections into final recap
            if formatted_sections:
                final_recap = "## Recap\n\n" + "\n\n".join(formatted_sections)
            else:
                final_recap = "## Recap\n\nNo events to display."
            
            if settings.debug:
                print(f"Final recap sections combined: {len(formatted_sections)} sections")
                print("Recap sanitizer: Multi-stage pipeline completed successfully using format-specific prompts")
            
            return final_recap
            
        except Exception as e:
            # Fallback to single-stage if multi-stage fails
            if settings.debug:
                print(f"Multi-stage recap sanitizer failed, falling back to single-stage: {e}")
            
            return await self._run_single_stage_recap_sanitizer(recap, story_start_date, previous_chapter_recap, settings)
    
    def _extract_current_date_from_recap(self, recap: str, story_start_date: str) -> str:
        """Extract the current date from the latest recap for event classification."""
        # Simple extraction - look for the most recent date mentioned
        import re
        from datetime import datetime, timedelta
        
        # Try to find dates in the recap
        date_pattern = r'(\d{4}-\d{2}-\d{2})'
        dates = re.findall(date_pattern, recap)
        
        if dates:
            # Return the most recent date found
            return max(dates)
        
        # If no dates found, try to estimate from story start date
        # Assume the current chapter is a few days after story start
        try:
            start_date = datetime.strptime(story_start_date, "%Y-%m-%d")
            current_date = start_date + timedelta(days=7)  # Assume 1 week into story
            return current_date.strftime("%Y-%m-%d")
        except:
            # Fallback to story start date
            return story_start_date
    
    def _sanitize_json_response(self, response_text: str) -> str:
        """Sanitize model response to extract valid JSON."""
        import re
        import json
        
        # Remove code blocks if present
        response_text = re.sub(r'```json\s*', '', response_text)
        response_text = re.sub(r'```\s*', '', response_text)
        
        # Remove any text before the first [ or {
        json_match = re.search(r'(\[.*\]|\{.*\})', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(1)
        
        # Try to parse and reformat to ensure it's valid
        try:
            parsed = json.loads(response_text)
            return json.dumps(parsed, indent=2)
        except json.JSONDecodeError:
            # If still invalid, try to fix common issues
            response_text = response_text.strip()
            if not response_text.startswith('[') and not response_text.startswith('{'):
                response_text = '[' + response_text + ']'
            return response_text
    
    def _classify_event_recency_programmatically(self, events_json: str, current_date: str) -> str:
        """Programmatically classify events by recency for formatting."""
        import json
        from datetime import datetime, timedelta
        
        try:
            # Parse the events JSON
            events = json.loads(events_json)
            current_dt = datetime.strptime(current_date, "%Y-%m-%d")
            
            processed_events = []
            
            for event in events:
                try:
                    # Parse event date
                    event_date_str = event.get("date_start", "").split(" ")[0]  # Get just the date part
                    event_dt = datetime.strptime(event_date_str, "%Y-%m-%d")
                    
                    # Calculate days difference (current_date - event_date)
                    days_diff = (current_dt - event_dt).days
                    
                    # Create a copy of the event to modify
                    processed_event = event.copy()
                    
                    # Classify based on age (handle negative days as current)
                    if days_diff <= 0:
                        # Same day or future events - treat as current
                        processed_event["compacted"] = False
                        processed_event["format"] = "current"
                        classification = "current"
                    elif days_diff <= 7:
                        # Recent events (1-7 days ago)
                        processed_event["compacted"] = True
                        processed_event["format"] = "recent"
                        classification = "recent"
                    else:
                        # Historical events (>7 days ago)
                        processed_event["compacted"] = True
                        processed_event["format"] = "historical"
                        classification = "historical"
                    
                    # Debug output
                    print(f"[DATE CLASSIFICATION] Event: {event_date_str} | Current: {current_date} | Days diff: {days_diff} | Classification: {classification}")
                    
                    processed_events.append(processed_event)
                    
                except (ValueError, KeyError) as e:
                    # If we can't parse this event's date, keep it as-is with "recent" classification
                    processed_event = event.copy()
                    processed_event["compacted"] = True
                    processed_event["format"] = "recent"
                    processed_events.append(processed_event)
            
            return json.dumps(processed_events, indent=2)
            
        except json.JSONDecodeError as e:
            # If JSON parsing fails, return original
            return events_json
    
    async def generate_story_info(self, outline: Outline, chapters: List[Chapter], settings: GenerationSettings) -> StoryInfo:
        """Generate story metadata."""
        try:
            # Generate title
            title = await self._generate_title(outline, chapters, settings)
            
            # Generate summary
            summary = await self._generate_summary(outline, chapters, settings)
            
            # Generate tags
            tags = await self._generate_tags(outline, chapters, settings)
            
            # Calculate word count
            word_count = sum(len(chapter.content.split()) for chapter in chapters)
            
            return StoryInfo(
                title=title,
                summary=summary,
                tags=tags,
                chapter_count=len(chapters),
                word_count=word_count
            )
            
        except Exception as e:
            raise StoryGenerationError(f"Failed to generate story info: {e}") from e
    
    def get_strategy_name(self) -> str:
        """Get the name of this strategy."""
        return "outline-chapter"
    
    def get_strategy_version(self) -> str:
        """Get the version of this strategy."""
        return "1.0.0"
    
    def get_strategy_description(self) -> str:
        """Get a description of this strategy."""
        return "Generates a detailed outline first, then writes chapters based on the outline structure."
    
    def get_required_models(self) -> List[str]:
        """Get list of required model names for this strategy."""
        return [
            "sanity_model",
            "initial_outline_writer",
            "chapter_outline_writer",
            "logical_model",
            "chapter_stage1_writer",
            "info_model"
        ]
    
    def get_prompt_directory(self) -> str:
        """Get the directory containing prompts for this strategy."""
        return "src/application/strategies/prompts/outline-chapter"
    
    # Private methods with savepoint integration
    async def _extract_story_start_date(self, prompt: str, settings: GenerationSettings) -> str:
        """Extract story start date from prompt."""
        model_config = self.config.get_model("logical_model")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="extract_story_start_date",
            variables={"prompt": prompt},
            savepoint_id="story_start_date",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def _extract_base_context(self, prompt: str, settings: GenerationSettings) -> str:
        """Extract important base context from prompt."""
        model_config = self.config.get_model("initial_outline_writer")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="extract_base_context",
            variables={"prompt": prompt},
            savepoint_id="base_context",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def _generate_story_elements(self, prompt: str, settings: GenerationSettings) -> str:
        """Generate story elements from prompt."""
        model_config = self.config.get_model("initial_outline_writer")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="generate_story_elements",
            variables={"prompt": prompt},
            savepoint_id="story_elements",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            system_message=self.system_message
        )
        
        story_elements = response.content.strip()
        
        # Generate character sheets after story elements
        if self.savepoint_manager:
            await self._generate_character_sheets(story_elements, settings)
            # Generate setting sheets after character sheets
            await self._generate_setting_sheets(story_elements, settings)
        
        return story_elements
    
    async def _generate_character_sheets(self, story_elements: str, settings: GenerationSettings) -> None:
        """Generate character sheets for all characters identified in story elements."""
        try:
            # Extract character names from story elements
            character_names = await self._extract_character_names(story_elements, settings)
            
            if not character_names:
                print("No characters found in story elements.")
                return
            
            print(f"Found {len(character_names)} characters. Generating character sheets...")
            
            # Generate character sheet for each character
            for character_name in character_names:
                await self._generate_single_character_sheet(
                    character_name, story_elements, settings
                )
                
        except Exception as e:
            print(f"Error generating character sheets: {e}")
            # Don't fail the entire process if character sheet generation fails
    
    async def _extract_character_names(self, story_elements: str, settings: GenerationSettings) -> List[str]:
        """Extract character names from story elements text using AI prompt."""
        try:
            model_config = self.config.get_model("initial_outline_writer")
            
            # Generate character names using AI prompt
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="extract_character_names",
                variables={
                    "story_elements": story_elements
                },
                savepoint_id="characters/extract_character_names",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                system_message=self.system_message
            )
            
            if not response or not response.content or not response.content.strip():
                print("Warning: Empty response when extracting character names")
                return []
            
            # Parse the JSON response to extract character names
            import json
            import re
            
            # Clean the response to extract just the JSON part
            json_match = re.search(r'```json\s*(\[.*?\])\s*```', response.content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON array without markdown formatting
                json_match = re.search(r'\[.*?\]', response.content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    print(f"Warning: Could not parse JSON response for character names: {response.content[:200]}...")
                    return []
            
            try:
                character_names = json.loads(json_str)
                if isinstance(character_names, list):
                    # Clean up character names
                    cleaned_names = []
                    for name in character_names:
                        if isinstance(name, str) and name.strip():
                            cleaned_name = name.strip()
                            if len(cleaned_name) > 1 and cleaned_name not in cleaned_names:
                                cleaned_names.append(cleaned_name)
                    return cleaned_names
                else:
                    print(f"Warning: Expected list but got {type(character_names)} for character names")
                    return []
            except json.JSONDecodeError as e:
                print(f"Warning: JSON decode error when parsing character names: {e}")
                print(f"Response: {response.content[:200]}...")
                return []
                
        except Exception as e:
            print(f"Error extracting character names: {e}")
            return []
    
    async def _generate_single_character_sheet(
        self, 
        character_name: str, 
        story_elements: str, 
        settings: GenerationSettings
    ) -> None:
        """Generate a character sheet for a single character."""
        try:
            model_config = self.config.get_model("initial_outline_writer")
            
            # Create savepoint path for this character
            savepoint_id = f"characters/{character_name}/character_sheet"
            
            # Generate the character sheet
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="generate_character_sheet",
                variables={
                    "story_elements": story_elements,
                    "character_name": character_name,
                    "additional_context": f"Focus on developing {character_name} as a compelling, three-dimensional character that will serve the story well."
                },
                savepoint_id=savepoint_id,
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                system_message=self.system_message
            )
            
            if response and response.content and response.content.strip():
                print(f"Generated character sheet for {character_name}")
                if settings.debug:
                    print(f"Character sheet preview: {response.content[:200]}...")
                
                # Generate abridged summary based on the character sheet
                await self._generate_character_abridged_summary(
                    character_name=character_name,
                    character_sheet=response.content,
                    settings=settings
                )
            else:
                print(f"Warning: Empty response when generating character sheet for {character_name}")
                
        except Exception as e:
            print(f"Error generating character sheet for {character_name}: {e}")
            # Don't fail the entire process if a single character sheet generation fails
    
    async def _generate_setting_sheets(self, story_elements: str, settings: GenerationSettings) -> None:
        """Generate setting sheets for all settings identified in story elements."""
        try:
            # Extract setting names from story elements
            setting_names = await self._extract_setting_names(story_elements, settings)
            
            if not setting_names:
                print("No settings found in story elements.")
                return
            
            print(f"Found {len(setting_names)} settings. Generating setting sheets...")
            
            # Generate setting sheet for each setting
            for setting_name in setting_names:
                await self._generate_single_setting_sheet(
                    setting_name, story_elements, settings
                )
                
        except Exception as e:
            print(f"Error generating setting sheets: {e}")
            # Don't fail the entire process if setting sheet generation fails
    
    async def _extract_setting_names(self, story_elements: str, settings: GenerationSettings) -> List[str]:
        """Extract setting names from story elements text using AI prompt."""
        try:
            model_config = self.config.get_model("initial_outline_writer")
            
            # Generate setting names using AI prompt
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="extract_setting_names",
                variables={
                    "story_elements": story_elements
                },
                savepoint_id="settings/extract_setting_names",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                system_message=self.system_message
            )
            
            if not response or not response.content or not response.content.strip():
                print("Warning: Empty response when extracting setting names")
                return []
            
            # Parse the JSON response to extract setting names
            import json
            import re
            
            # Clean the response to extract the LAST JSON part
            # First try to find all JSON blocks with markdown formatting
            json_matches = re.findall(r'```json\s*(\[.*?\])\s*```', response.content, re.DOTALL)
            if json_matches:
                # Use the last JSON block found
                json_str = json_matches[-1]
            else:
                # Try to find all JSON arrays without markdown formatting
                json_matches = re.findall(r'\[.*?\]', response.content, re.DOTALL)
                if json_matches:
                    # Use the last JSON array found
                    json_str = json_matches[-1]
                else:
                    print(f"Warning: Could not parse JSON response for setting names: {response.content[:200]}...")
                    return []
            
            try:
                setting_names = json.loads(json_str)
                if isinstance(setting_names, list):
                    # Clean up setting names
                    cleaned_names = []
                    for name in setting_names:
                        if isinstance(name, str) and name.strip():
                            cleaned_name = name.strip()
                            if len(cleaned_name) > 1 and cleaned_name not in cleaned_names:
                                cleaned_names.append(cleaned_name)
                    return cleaned_names
                else:
                    print(f"Warning: Expected list but got {type(setting_names)} for setting names")
                    return []
            except json.JSONDecodeError as e:
                print(f"Warning: JSON decode error when parsing setting names: {e}")
                print(f"Response: {response.content[:200]}...")
                return []
                
        except Exception as e:
            print(f"Error extracting setting names: {e}")
            return []
    
    async def _generate_single_setting_sheet(
        self, 
        setting_name: str, 
        story_elements: str, 
        settings: GenerationSettings
    ) -> None:
        """Generate a setting sheet for a single setting."""
        try:
            model_config = self.config.get_model("initial_outline_writer")
            
            # Create savepoint path for this setting
            savepoint_id = f"settings/{setting_name}/setting_sheet"
            
            # Generate the setting sheet
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="generate_setting_sheet",
                variables={
                    "story_elements": story_elements,
                    "setting_name": setting_name,
                    "additional_context": f"Focus on developing {setting_name} as a compelling, immersive setting that will serve the story well."
                },
                savepoint_id=savepoint_id,
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                system_message=self.system_message
            )
            
            if response and response.content and response.content.strip():
                print(f"Generated setting sheet for {setting_name}")
                if settings.debug:
                    print(f"Setting sheet preview: {response.content[:200]}...")
                
                # Generate abridged summary based on the setting sheet
                await self._generate_setting_abridged_summary(
                    setting_name=setting_name,
                    setting_sheet=response.content,
                    settings=settings
                )
            else:
                print(f"Warning: Empty response when generating setting sheet for {setting_name}")
                
        except Exception as e:
            print(f"Error generating setting sheet for {setting_name}: {e}")
            # Don't fail the entire process if a single setting sheet generation fails
    
    async def _generate_character_abridged_summary(
        self,
        character_name: str,
        character_sheet: str,
        settings: GenerationSettings
    ) -> None:
        """Generate an abridged character summary suitable for prompt injection."""
        try:
            model_config = self.config.get_model("initial_outline_writer")
            
            # Create savepoint path for this character's abridged summary
            savepoint_id = f"characters/{character_name}/sheet-abridged"
            
            # Generate the abridged character summary
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="generate_character_abridged",
                variables={
                    "character_sheet": character_sheet,
                    "character_name": character_name
                },
                savepoint_id=savepoint_id,
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                system_message=self.system_message
            )
            
            if response and response.content and response.content.strip():
                print(f"Generated abridged summary for character {character_name}")
                if settings.debug:
                    print(f"Character abridged summary preview: {response.content[:200]}...")
            else:
                print(f"Warning: Empty response when generating abridged summary for character {character_name}")
                
        except Exception as e:
            print(f"Error generating abridged summary for character {character_name}: {e}")
            # Don't fail the entire process if a single abridged summary generation fails
    
    async def _generate_setting_abridged_summary(
        self,
        setting_name: str,
        setting_sheet: str,
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
                prompt_id="generate_setting_abridged",
                variables={
                    "setting_sheet": setting_sheet,
                    "setting_name": setting_name
                },
                savepoint_id=savepoint_id,
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                system_message=self.system_message
            )
            
            if response and response.content and response.content.strip():
                print(f"Generated abridged summary for setting {setting_name}")
                if settings.debug:
                    print(f"Setting abridged summary preview: {response.content[:200]}...")
            else:
                print(f"Warning: Empty response when generating abridged summary for setting {setting_name}")
                
        except Exception as e:
            print(f"Error generating abridged summary for setting {setting_name}: {e}")
            # Don't fail the entire process if a single abridged summary generation fails
    
    async def _generate_initial_outline(
        self,
        prompt: str,
        story_elements: str,
        base_context: str,
        settings: GenerationSettings
    ) -> str:
        """Generate initial story outline with iterative critique refinement."""
        model_config = self.config.get_model("initial_outline_writer")
        
        # Generate initial outline using the prompt handler
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="generate_initial_outline",
            variables={
                "prompt": prompt,
                "story_elements": story_elements,
                "base_context": base_context,
                "desired_chapters": settings.wanted_chapters
            },
            savepoint_id="initial_outline",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            system_message=self.system_message,
            min_word_count=500
        )
        
        initial_outline = response.content.strip()
        
        # Perform sanity check on the initial outline
        # initial_outline = await self._perform_outline_sanity_check(
        #     initial_outline=initial_outline,
        #     base_context=base_context,
        #    story_elements=story_elements,
        #    settings=settings
        #)
        
        # Apply iterative critique refinement if enabled
        if settings.enable_outline_critique:
            from ..services.critique_service import CritiqueService
            critique_service = CritiqueService(self.model_provider, self.config, self.prompt_loader)
            
            # Save the initial outline
            if self.savepoint_manager:
                await self.savepoint_manager.save_step("initial_outline", initial_outline)
            
            refined_outline = await critique_service.refine_outline_iteratively(
                initial_outline=initial_outline,
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
            # Save the initial outline as final if critique is disabled
            if self.savepoint_manager:
                await self.savepoint_manager.save_step("initial_outline", initial_outline)
                await self.savepoint_manager.save_step("final_outline", initial_outline)
            
            return initial_outline
    

    
    async def _perform_outline_sanity_check(
        self,
        initial_outline: str,
        base_context: str,
        story_elements: str,
        settings: GenerationSettings
    ) -> str:
        """Perform a sanity check on the initial outline and fix any issues found."""
        model_config = self.config.get_model("sanity_model")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="initial_outline_sanity_check",
            variables={
                "initial_outline": initial_outline,
                "base_context": base_context,
                "story_elements": story_elements
            },
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            system_message=self.system_message
        )
        
        return response.content.strip()
    

    
    async def _generate_chapter_list(
        self,
        outline: str,
        base_context: str,
        story_elements: str,
        settings: GenerationSettings
    ) -> str:
        """Generate detailed chapter list iteratively."""
        return await self._generate_chapter_list_iterative(outline, base_context, story_elements, settings)
    
    async def _generate_chapter_list_iterative(
        self,
        outline: str,
        base_context: str,
        story_elements: str,
        settings: GenerationSettings
    ) -> str:
        """Generate chapter list iteratively, one chapter at a time."""
        # First, count the total number of chapters
        total_chapters = settings.wanted_chapters
        
        # Generate chapters iteratively, saving each synopsis individually
        for chapter_num in range(1, total_chapters + 1):
            # Check if this chapter's synopsis already exists
            existing_synopsis = await self.savepoint_manager.load_step(f"chapter_{chapter_num}/base_synopsis")
            
            if existing_synopsis:
                # Skip if already generated
                continue
            
            # For chapters after the first, load the previous chapter's synopsis
            previous_chapter = ""
            if chapter_num > 1:
                try:
                    previous_synopsis = await self.savepoint_manager.load_step(f"chapter_{chapter_num - 1}/base_synopsis")
                    if previous_synopsis:
                        previous_chapter = previous_synopsis
                except Exception as e:
                    print(f"Warning: Could not load previous chapter synopsis for chapter {chapter_num}: {e}")
            
            # Generate this chapter's synopsis
            chapter_synopsis = await self._generate_single_chapter_synopsis(
                chapter_num, outline, base_context, story_elements, previous_chapter, settings
            )
            
            # Save the individual chapter synopsis
            await self.savepoint_manager.save_step(f"chapter_{chapter_num}/base_synopsis", chapter_synopsis)
        
        # Return a summary message indicating completion
        return f"Generated {total_chapters} chapter synopses. Each synopsis saved to chapter_X/base_synopsis.md savepoints."
    
    def _count_existing_chapters(self, chapter_list: str) -> int:
        """Count how many chapters exist in the current chapter list."""
        if not chapter_list:
            return 0
        
        # Count lines that start with "#### Chapter"
        lines = chapter_list.split('\n')
        chapter_count = 0
        
        for line in lines:
            if line.strip().startswith('#### Chapter'):
                chapter_count += 1
        
        return chapter_count
    
    async def _generate_single_chapter_synopsis(
        self,
        chapter_num: int,
        outline: str,
        base_context: str,
        story_elements: str,
        previous_chapter: str,
        settings: GenerationSettings
    ) -> str:
        """Generate a single chapter synopsis."""
        model_config = self.config.get_model("chapter_outline_writer")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="generate_iterative_chapter_list",
            variables={
                "Chapter": str(chapter_num),
                "outline": outline,
                "story_elements": story_elements,
                "base_context": base_context,
                "previous_chapter": previous_chapter
            },
            savepoint_id=f"chapter_{chapter_num}/base_synopsis",
            model_config=model_config,
            seed=settings.seed + chapter_num,
            debug=settings.debug,
            stream=settings.stream,
            system_message=self.system_message,
            min_word_count=100
        )
        
        return response.content.strip()
    

    
    async def _count_chapters(self, outline: str, settings: GenerationSettings) -> int:
        return self.config.wanted_chapters

        """Count the number of chapters in the outline."""
        model_config = self.config.get_model("logical_model")
        
        from infrastructure.prompts.prompt_wrapper import execute_json_prompt_with_savepoint
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="count_chapters",
            variables={"outline": outline},
            savepoint_id="count_chapters",
            model_config=model_config,
            seed=settings.seed,
            system_message=self.system_message
        )
        
        # Handle both JSON object and direct integer responses
        if isinstance(response, dict) and "TotalChapters" in response:
            return response["TotalChapters"]
        elif isinstance(response, int):
            return response
        else:
            # Try to parse as integer if it's a string
            try:
                return int(str(response))
            except (ValueError, TypeError):
                raise StoryGenerationError(f"Invalid response format for chapter count: {response}")
    
    async def _generate_chapter(
        self,
        chapter_num: int,
        total_chapters: int,
        outline: Outline,
        previous_chapters: List[Chapter],
        settings: GenerationSettings
    ) -> Chapter:
        """Generate a single chapter."""
        # Get chapter outline
        chapter_outline = await self._get_chapter_outline(chapter_num, outline.content, settings)
        
        # Get previous chapter recap
        previous_recap = await self._get_previous_chapter_recap(
            chapter_num, previous_chapters, outline, settings
        )
        
        # Get next chapter outline
        next_chapter_outline = await self._get_next_chapter_outline(
            chapter_num, total_chapters, outline, settings
        )
        
        # Generate chapter content
        content = await self._generate_chapter_content(
            chapter_num, total_chapters, chapter_outline, previous_recap,
            next_chapter_outline, outline, settings
        )
        
        # Generate chapter title
        title = await self._generate_chapter_title(
            chapter_num, content, chapter_outline, settings
        )
        
        return Chapter(
            number=chapter_num,
            title=title,
            content=content,
            outline=chapter_outline
        )
    
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
            prompt_id="get_chapter_outline",
            variables={
                "chapter_num": chapter_num,
                "outline": outline
            },
            savepoint_id=f"chapter_{chapter_num}/base_outline",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def _get_previous_chapter_recap(
        self,
        chapter_num: int,
        previous_chapters: List[Chapter],
        outline: Outline,
        settings: GenerationSettings
    ) -> str:
        """Generate recap of previous chapter."""
        if chapter_num <= 1 or not previous_chapters:
            return ""
        
        last_chapter = previous_chapters[-1]
        
        model_config = self.config.get_model("chapter_writer")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="get_previous_chapter_recap",
            variables={
                "chapter_num": chapter_num,
                "previous_chapters": [chapter.content for chapter in previous_chapters],
                "outline": outline.content
            },
            savepoint_id=f"chapter_{chapter_num}/recap",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
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
    
    async def _generate_chapter_content(
        self,
        chapter_num: int,
        total_chapters: int,
        chapter_outline: str,
        previous_recap: str,
        next_chapter_outline: str,
        outline: Outline,
        settings: GenerationSettings
    ) -> str:
        """Generate the actual chapter content."""
        model_config = self.config.get_model("chapter_stage1_writer")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="generate_chapter_content",
            variables={
                "chapter_num": chapter_num,
                "total_chapters": total_chapters,
                "outline": outline.content,
                "chapter_outline": chapter_outline,
                "previous_recap": previous_recap,
                "next_chapter_outline": next_chapter_outline
            },
            savepoint_id=f"chapter_{chapter_num}/content",
            model_config=model_config,
            seed=settings.seed + chapter_num,
            debug=settings.debug,
            stream=settings.stream,
            system_message=self.system_message,
            min_word_count=1000
        )
        
        return response.content.strip()
    
    async def _generate_chapter_title(
        self,
        chapter_num: int,
        content: str,
        chapter_outline: str,
        settings: GenerationSettings
    ) -> str:
        """Generate a title for the chapter."""
        model_config = self.config.get_model("chapter_outline_writer")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="generate_chapter_title",
            variables={
                "chapter_outline": chapter_outline,
                "chapter_content": content[:500] + "..."
            },
            savepoint_id=f"chapter_{chapter_num}/title",
            model_config=model_config,
            seed=settings.seed + chapter_num,
            debug=settings.debug,
            stream=settings.stream,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def _generate_title(
        self,
        outline: Outline,
        chapters: List[Chapter],
        settings: GenerationSettings
    ) -> str:
        """Generate a title for the story."""
        model_config = self.config.get_model("info_model")
        
        # Use first chapter content for context
        first_chapter_content = chapters[0].content if chapters else ""
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="generate_title",
            variables={
                "outline": outline.content,
                "first_chapter": first_chapter_content[:1000] + "..."
            },
            savepoint_id="title",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def _generate_summary(
        self,
        outline: Outline,
        chapters: List[Chapter],
        settings: GenerationSettings
    ) -> str:
        """Generate a summary for the story."""
        model_config = self.config.get_model("info_model")
        
        # Use first few chapters for context
        chapter_content = "\n\n".join([ch.content[:500] for ch in chapters[:3]])
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="generate_summary",
            variables={
                "outline": outline.content,
                "chapter_content": chapter_content
            },
            savepoint_id="summary",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def _generate_tags(
        self,
        outline: Outline,
        chapters: List[Chapter],
        settings: GenerationSettings
    ) -> List[str]:
        """Generate tags for the story."""
        model_config = self.config.get_model("info_model")
        
        # Use first chapter for context
        first_chapter_content = chapters[0].content if chapters else ""
        
        from infrastructure.prompts.prompt_wrapper import execute_json_prompt_with_savepoint
        
        response = await execute_json_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="generate_tags",
            required_attributes=["tags"],
            variables={
                "outline": outline.content,
                "first_chapter": first_chapter_content[:1000] + "..."
            },
            savepoint_id="tags",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            system_message=self.system_message
        )
        
        # Handle different response formats
        if isinstance(response, dict) and "tags" in response:
            tags = response["tags"]
        elif isinstance(response, list):
            tags = response
        else:
            # Fallback: extract tags from response
            tags = []
            if isinstance(response, dict):
                for key, value in response.items():
                    if isinstance(value, list):
                        tags.extend(value)
                    elif isinstance(value, str):
                        tags.append(value)
        
        # Ensure tags are strings and clean them up
        tags = [str(tag).strip().lower() for tag in tags if tag]
        return tags[:10]  # Limit to 10 tags 