"""Recap generation and processing functionality for the outline-chapter strategy."""

import json
import re
from datetime import datetime, timedelta
from typing import List, Optional
from domain.entities.story import Outline, Chapter
from domain.value_objects.generation_settings import GenerationSettings
from config.settings import AppConfig
from application.interfaces.model_provider import ModelProvider
from infrastructure.prompts.prompt_handler import PromptHandler
from infrastructure.prompts.prompt_wrapper import execute_prompt_with_savepoint
from infrastructure.savepoints import SavepointManager


class RecapManager:
    """Handles recap generation, processing, and sanitization functionality."""
    
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
    
    async def get_previous_chapter_recap_from_savepoint(
        self,
        chapter_num: int,
        outline: Outline,
        settings: GenerationSettings
    ) -> str:
        """Get previous chapter recap from savepoint."""
        if chapter_num <= 1:
            return ""
        
        try:
            # Try to load existing recap from savepoint
            return await self.savepoint_manager.load_step(f"chapter_{chapter_num-1}/recap")
        except:
            if settings.debug:
                print(f"[RECAP LOAD] No previous recap found in savepoint for chapter {chapter_num-1}")
            return ""
    
    async def generate_chapter_recap(
        self,
        chapter_num: int,
        chapter_content: str,
        chapter_outline: str,
        story_start_date: str,
        previous_chapter_recap: str,
        settings: GenerationSettings
    ) -> str:
        """Generate recap for a chapter using multi-stage approach."""
        # Use the new multi-stage recap generation approach
        try:
            # Step 1: Extract events from the chapter content
            events = await self.extract_chapter_events(
                chapter_content, chapter_num, settings
            )
            
            # Step 2: Assign timing to the events
            timed_events = await self.assign_event_timing(
                events, story_start_date, previous_chapter_recap, chapter_num, settings
            )
            
            # Step 3: Enrich the event details
            enriched_events = await self.enrich_event_details(
                timed_events, chapter_num, settings
            )
            
            # Step 4: Format the recap output
            formatted_recap = await self.format_recap_output(
                enriched_events, chapter_num, settings
            )
            
            # Step 5: Filter out aged and non-high-importance events
            filtered_recap = await self.filter_aged_events(
                formatted_recap, story_start_date, settings
            )
            
            return filtered_recap
            
        except Exception as e:
            # Fallback to simpler recap generation if the multi-stage approach fails
            if settings.debug:
                print(f"[RECAP GENERATION] Multi-stage approach failed for chapter {chapter_num}: {e}")
                print("[RECAP GENERATION] Falling back to simple recap generation")
            
            return await self.generate_recap_fallback(
                chapter_num, chapter_outline, story_start_date, previous_chapter_recap, settings
            )
    
    async def extract_chapter_events(self, chapter_content: str, chapter_num: int, settings: GenerationSettings) -> str:
        """Extract events from chapter content."""
        model_config = self.config.get_model("logical_model")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="recap/extract_events",
            variables={
                "chapter_content": chapter_content,
                "chapter_num": chapter_num
            },
            savepoint_id=f"chapter_{chapter_num}/extracted_events",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def assign_event_timing(self, events: str, story_start_date: str, previous_chapter_recap: str, chapter_num: int, settings: GenerationSettings) -> str:
        """Assign timing to events."""
        model_config = self.config.get_model("logical_model")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="recap/assign_event_timing",
            variables={
                "events": events,
                "story_start_date": story_start_date,
                "previous_chapter_recap": previous_chapter_recap,
                "chapter_num": chapter_num
            },
            savepoint_id=f"chapter_{chapter_num}/timed_events",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def enrich_event_details(self, timed_events: str, chapter_num: int, settings: GenerationSettings) -> str:
        """Enrich event details."""
        model_config = self.config.get_model("logical_model")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="recap/enrich_event_details",
            variables={
                "timed_events": timed_events,
                "chapter_num": chapter_num
            },
            savepoint_id=f"chapter_{chapter_num}/enriched_events",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        return response.content.strip()
    
    async def format_recap_output(self, enriched_events: str, chapter_num: int, settings: GenerationSettings) -> str:
        """Format recap output in JSON format."""
        model_config = self.config.get_model("logical_model")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="recap/format_json",
            variables={
                "enriched_events": enriched_events,
                "chapter_num": chapter_num
            },
            savepoint_id=f"chapter_{chapter_num}/formatted_recap",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        # Ensure the response is valid JSON
        try:
            # Try to parse as JSON to validate
            json.loads(response.content.strip())
            return response.content.strip()
        except json.JSONDecodeError:
            if settings.debug:
                print(f"[RECAP FORMAT] Invalid JSON response, attempting to sanitize")
            # Try to sanitize the response to extract JSON
            return await self.sanitize_json_response(response.content.strip())
    
    async def generate_recap_fallback(self, chapter_num: int, chapter_outline: str, story_start_date: str, previous_chapter_recap: str, settings: GenerationSettings) -> str:
        """Fallback recap generation method."""
        model_config = self.config.get_model("chapter_writer")
        
        # Since we're always loading from savepoints now, this fallback function is no longer needed
        # The recap should already exist in the savepoint from when the chapter was created
        if settings.debug:
            print(f"[RECAP FALLBACK] Attempting to load existing recap from savepoint")
        
        try:
            # Try to load the existing recap from savepoint
            if self.savepoint_manager:
                return await self.savepoint_manager.load_step(f"chapter_{chapter_num}/recap")
            else:
                return ""
        except:
            if settings.debug:
                print(f"[RECAP FALLBACK] No existing recap found in savepoint")
            return ""
        
        # Ensure the response is valid JSON
        try:
            # Try to parse as JSON to validate
            json.loads(response.content.strip())
            return response.content.strip()
        except json.JSONDecodeError:
            if settings.debug:
                print(f"[RECAP FALLBACK] Invalid JSON response, attempting to sanitize")
            # Try to sanitize the response to extract JSON
            return await self.sanitize_json_response(response.content.strip())
    
    async def run_recap_sanitizer(self, recap: str, story_start_date: str, previous_chapter_recap: str, settings: GenerationSettings) -> str:
        """Run recap sanitizer to ensure consistency."""
        model_config = self.config.get_model("logical_model")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="recap/sanitize",
            variables={
                "recap": recap,
                "story_start_date": story_start_date,
                "previous_chapter_recap": previous_chapter_recap
            },
            savepoint_id="sanitized_recap",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        # Ensure the response is valid JSON
        try:
            # Try to parse as JSON to validate
            json.loads(response.content.strip())
            return response.content.strip()
        except json.JSONDecodeError:
            if settings.debug:
                print(f"[RECAP SANITIZER] Invalid JSON response, attempting to sanitize")
            # Try to sanitize the response to extract JSON
            return await self.sanitize_json_response(response.content.strip())
    
    async def run_multi_stage_recap_sanitizer(self, recap: str, story_start_date: str, previous_chapter_recap: str, settings: GenerationSettings) -> str:
        """Run enhanced recap sanitizer with progressive compaction."""
        if settings.debug:
            print("[RECAP SANITIZER] Running enhanced recap sanitizer")
        
        try:
            # Use the enhanced sanitizer directly (no more multi-stage)
            model_config = self.config.get_model("logical_model")
            
            response = await execute_prompt_with_savepoint(
                handler=self.prompt_handler,
                prompt_id="recap/sanitize",
                variables={
                    "recap": recap,
                    "story_start_date": story_start_date,
                    "previous_chapter_recap": previous_chapter_recap
                },
                savepoint_id="sanitized_recap",
                model_config=model_config,
                seed=settings.seed,
                debug=settings.debug,
                stream=settings.stream,
                log_prompt_inputs=settings.log_prompt_inputs,
                system_message=self.system_message
            )
            
            sanitized_recap = response.content.strip()
            
            # Ensure the response is valid JSON
            try:
                json.loads(sanitized_recap)
            except json.JSONDecodeError:
                if settings.debug:
                    print(f"[RECAP SANITIZER] Invalid JSON response, attempting to sanitize")
                sanitized_recap = await self.sanitize_json_response(sanitized_recap)
            
            # Extract current date from the recap to check for consistency
            current_date = self.extract_current_date_from_recap(sanitized_recap, story_start_date)
            
            if settings.debug:
                print(f"[RECAP SANITIZER] Extracted current date: {current_date}")
            
            # Programmatic classification of event recency (if enabled)
            if hasattr(settings, 'enable_programmatic_event_classification') and settings.enable_programmatic_event_classification:
                # Convert recap to JSON format for programmatic analysis
                json_recap = await self.convert_recap_to_json(sanitized_recap, settings)
                
                # Classify events by recency
                classified_recap = await self.classify_event_recency_programmatically(json_recap, current_date, settings)
                
                # Since we're always working with JSON now, just return the classified recap
                final_recap = classified_recap
            else:
                final_recap = sanitized_recap
            
            if settings.debug:
                print("[RECAP SANITIZER] Enhanced sanitization completed")
            
            return final_recap
            
        except Exception as e:
            if settings.debug:
                print(f"[RECAP SANITIZER] Enhanced sanitization failed: {e}")
                print("[RECAP SANITIZER] Falling back to basic sanitization")
            
            # Fallback to basic sanitization
            return await self.run_recap_sanitizer(recap, story_start_date, previous_chapter_recap, settings)
    
    def extract_current_date_from_recap(self, recap: str, story_start_date: str) -> str:
        """Extract the current date from a JSON recap."""
        try:
            # Try to parse as JSON first
            recap_data = json.loads(recap)
            
            # Look for the latest event date in the JSON structure
            latest_date = None
            
            # Check if it's the new format with events_by_timeline
            if "events_by_timeline" in recap_data:
                timeline = recap_data["events_by_timeline"]
                # Check current chapter first (most recent)
                if "current" in timeline and timeline["current"]["events"]:
                    for event in timeline["current"]["events"]:
                        if "date_start" in event:
                            event_date = event["date_start"]
                            if not latest_date or event_date > latest_date:
                                latest_date = event_date
                
                # Check recent events
                if "recent_events" in timeline and timeline["recent_events"]["events"]:
                    for event in timeline["recent_events"]["events"]:
                        if "date_start" in event:
                            event_date = event["date_start"]
                            if not latest_date or event_date > latest_date:
                                latest_date = event_date
            
            # Check if it's the old format with direct events array
            elif "events" in recap_data and isinstance(recap_data["events"], list):
                for event in recap_data["events"]:
                    if "date_start" in event:
                        event_date = event["date_start"]
                        if not latest_date or event_date > latest_date:
                            latest_date = event_date
            
            # Check if it's the new format with meta.latest_event_date
            elif "meta" in recap_data and "latest_event_date" in recap_data["meta"]:
                latest_date = recap_data["meta"]["latest_event_date"]
            
            if latest_date:
                # Extract just the date part (YYYY-MM-DD) if time is included
                if " " in latest_date:
                    return latest_date.split(" ")[0]
                return latest_date
                
        except (json.JSONDecodeError, KeyError, TypeError):
            # Fallback to regex pattern matching for non-JSON or malformed JSON
            pass
        
        # Fallback: look for date patterns in the text
        date_patterns = [
            r'\b(\d{1,2}/\d{1,2}/\d{4})\b',  # MM/DD/YYYY
            r'\b(\d{4}-\d{1,2}-\d{1,2})\b',  # YYYY-MM-DD
            r'\b(\w+ \d{1,2}, \d{4})\b',     # Month DD, YYYY
            r'\b(\d{1,2} \w+ \d{4})\b',      # DD Month YYYY
        ]
        
        dates_found = []
        for pattern in date_patterns:
            matches = re.findall(pattern, recap)
            dates_found.extend(matches)
        
        if dates_found:
            # Return the last date found (most likely to be current)
            return dates_found[-1]
        
        # Fallback: assume it's the story start date
        return story_start_date
    
    async def sanitize_json_response(self, response_text: str) -> str:
        """Sanitize JSON response by removing markdown formatting."""
        # Remove markdown code block formatting
        response_text = response_text.replace('```json', '').replace('```', '')
        
        # Remove any leading/trailing whitespace
        response_text = response_text.strip()
        
        # Find the first { and last } to extract just the JSON part
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        if start_idx != -1 and end_idx != 0:
            return response_text[start_idx:end_idx]
        
        return response_text
    
    async def convert_recap_to_json(self, recap: str, settings: GenerationSettings) -> str:
        """Convert recap to JSON format for programmatic analysis."""
        model_config = self.config.get_model("logical_model")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="recap/compact_events",
            variables={"recap": recap},
            savepoint_id="recap_json",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        return await self.sanitize_json_response(response.content.strip())
    
    async def classify_event_recency_programmatically(self, events_json: str, current_date: str, settings: GenerationSettings) -> str:
        """Classify events by recency using programmatic logic."""
        try:
            # Parse the JSON
            events_data = json.loads(events_json)
            
            # Parse current date
            try:
                current_dt = datetime.strptime(current_date, "%Y-%m-%d")
            except:
                try:
                    current_dt = datetime.strptime(current_date, "%m/%d/%Y")
                except:
                    # Fallback - just return original
                    return events_json
            
            # Classify events
            for event in events_data.get('events', []):
                event_date_str = event.get('date', current_date)
                
                try:
                    event_dt = datetime.strptime(event_date_str, "%Y-%m-%d")
                except:
                    try:
                        event_dt = datetime.strptime(event_date_str, "%m/%d/%Y")
                    except:
                        event_dt = current_dt  # Fallback
                
                # Calculate days difference
                days_diff = (current_dt - event_dt).days
                
                # Classify by recency
                if days_diff == 0:
                    event['recency'] = 'current'
                elif days_diff <= 1:
                    event['recency'] = 'recent'
                elif days_diff <= 7:
                    event['recency'] = 'this_week'
                elif days_diff <= 30:
                    event['recency'] = 'this_month'
                else:
                    event['recency'] = 'historical'
            
            return json.dumps(events_data, indent=2)
            
        except Exception as e:
            if settings.debug:
                print(f"[EVENT CLASSIFICATION] Error in programmatic classification: {e}")
            # Fallback to model-based classification
            return await self.classify_event_recency_model_based(events_json, current_date, settings)
    
    async def classify_event_recency_model_based(self, events_json: str, current_date: str, settings: GenerationSettings) -> str:
        """Classify events by recency using model-based approach."""
        model_config = self.config.get_model("logical_model")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="outline/analyze_continuity",  # Reuse existing prompt
            variables={
                "events_json": events_json,
                "current_date": current_date
            },
            savepoint_id="classified_events",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        return await self.sanitize_json_response(response.content.strip())
    
    async def convert_json_to_recap(self, classified_json: str, settings: GenerationSettings) -> str:
        """Convert classified JSON back to JSON recap format (no longer narrative)."""
        # Since we're now always working with JSON, just return the classified JSON
        # The format_recap_output prompt now returns JSON, so we don't need to convert
        try:
            # Validate that it's proper JSON
            json.loads(classified_json)
            return classified_json
        except json.JSONDecodeError:
            if settings.debug:
                print(f"[JSON CONVERSION] Invalid JSON, attempting to sanitize")
            return await self.sanitize_json_response(classified_json)
    
    async def compact_events_progressively(self, recap: str, chapter_num: int, settings: GenerationSettings) -> str:
        """Apply progressive compaction to events based on chapter number."""
        if chapter_num <= 5:
            # Early chapters - no compaction needed
            return recap
        
        # Determine compaction level based on chapter number
        if chapter_num <= 10:
            compaction_level = "light"
        elif chapter_num <= 20:
            compaction_level = "moderate"
        else:
            compaction_level = "heavy"
        
        model_config = self.config.get_model("logical_model")
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="recap/compact_events",
            variables={
                "recap": recap,
                "compaction_level": compaction_level,
                "chapter_num": chapter_num
            },
            savepoint_id=f"chapter_{chapter_num}/compacted_recap",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        # Ensure the response is valid JSON
        try:
            # Try to parse as JSON to validate
            json.loads(response.content.strip())
            return response.content.strip()
        except json.JSONDecodeError:
            if settings.debug:
                print(f"[RECAP COMPACTION] Invalid JSON response, attempting to sanitize")
            # Try to sanitize the response to extract JSON
            return await self.sanitize_json_response(response.content.strip())
    
    async def filter_aged_events(self, recap: str, story_start_date: str, settings: GenerationSettings) -> str:
        """Filter out events that are too old to be relevant using programmatic logic."""
        try:
            # Parse the recap JSON
            recap_data = json.loads(recap)
            
            # Get current date for age calculation
            current_date = self.extract_current_date_from_recap(recap, story_start_date)
            if not current_date:
                return recap  # Fallback if we can't determine current date
            
            # Parse current date
            try:
                current_dt = datetime.strptime(current_date, "%Y-%m-%d")
            except:
                try:
                    current_dt = datetime.strptime(current_date, "%m/%d/%Y")
                except:
                    return recap  # Fallback if date parsing fails
            
            # Get max age from settings or use default
            max_age_days = 30
            if hasattr(settings, 'max_event_age_days'):
                max_age_days = settings.max_event_age_days
            
            # Filter events based on age and importance
            filtered_events = []
            
            # Handle different recap structures
            if "events_by_timeline" in recap_data:
                # New structure with timeline organization
                timeline = recap_data["events_by_timeline"]
                for timeline_key, timeline_data in timeline.items():
                    if "events" in timeline_data and isinstance(timeline_data["events"], list):
                        filtered_timeline_events = []
                        for event in timeline_data["events"]:
                            if self._should_keep_event(event, current_dt, max_age_days):
                                # Clean up event properties before adding
                                cleaned_event = self._clean_event_properties(event)
                                filtered_timeline_events.append(cleaned_event)
                        timeline_data["events"] = filtered_timeline_events
                        filtered_events.extend(filtered_timeline_events)
            elif "events" in recap_data and isinstance(recap_data["events"], list):
                # Direct events array
                for event in recap_data["events"]:
                    if self._should_keep_event(event, current_dt, max_age_days):
                        # Clean up event properties before adding
                        cleaned_event = self._clean_event_properties(event)
                        filtered_events.append(cleaned_event)
                recap_data["events"] = filtered_events
            
            # Update meta information
            if "meta" in recap_data:
                recap_data["meta"]["total_events"] = len(filtered_events)
                recap_data["meta"]["filtering_applied"] = {
                    "max_age_days": max_age_days,
                    "events_removed": "non_high_importance_and_aged_out",
                    "filtering_method": "programmatic_high_importance_only"
                }
            
            return json.dumps(recap_data, indent=2)
            
        except Exception as e:
            if settings.debug:
                print(f"[EVENT FILTERING] Error in programmatic filtering: {e}")
            # Fallback to original recap if filtering fails
            return recap
    
    def _should_keep_event(self, event: dict, current_dt: datetime, max_age_days: int) -> bool:
        """Determine if an event should be kept based on age and importance."""
        try:
            # BLANKET RULE: Only keep high importance events
            importance = event.get('importance', 'medium').lower()
            if importance != 'high':
                return False
            
            # Get event date
            event_date_str = event.get('date_start', '')
            if not event_date_str:
                return True  # Keep high importance events without dates
            
            # Parse event date
            try:
                event_dt = datetime.strptime(event_date_str, "%Y-%m-%d")
            except:
                try:
                    event_dt = datetime.strptime(event_date_str, "%m/%d/%Y")
                except:
                    return True  # Keep high importance events with unparseable dates
            
            # Calculate age in days
            age_days = (current_dt - event_dt).days
            
            # Apply filtering rules (only for high importance events now)
            if age_days <= 7:
                # Keep all high importance events from the last week
                return True
            elif age_days <= 30:
                # Keep high importance events 1 week to 1 month old
                return True
            elif age_days <= max_age_days:
                # Keep high importance events 1 month to max_age_days old
                return True
            else:
                # Keep high importance events even if older than max_age_days
                return True
                
        except Exception:
            # Keep event if we can't process it (assuming it's high importance)
            return True
    
    def _clean_event_properties(self, event: dict) -> dict:
        """Remove specified properties from an event."""
        # Create a copy of the event to avoid modifying the original
        cleaned_event = event.copy()
        
        # Remove the specified properties
        properties_to_remove = ['date_start', 'date_end', 'symbols_motifs', 'importance', 'chapter_context']
        for prop in properties_to_remove:
            cleaned_event.pop(prop, None)  # Use pop with None default to avoid KeyError
        
        return cleaned_event
