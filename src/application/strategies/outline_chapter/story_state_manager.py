"""Story State Manager for progressive chapter generation."""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
import json
import os
from domain.entities.story import Chapter, Scene
from domain.value_objects.generation_settings import GenerationSettings
from domain.value_objects.model_config import ModelConfig
from application.interfaces.model_provider import ModelProvider
from infrastructure.prompts.prompt_handler import PromptHandler
from infrastructure.prompts.prompt_wrapper import execute_prompt_with_savepoint
from infrastructure.savepoints import SavepointManager
from application.services.rag_integration_service import RAGIntegrationService
from application.services.content_chunker import ContentChunker


@dataclass
class CharacterState:
    """Tracks the current state and development of a character."""
    name: str
    current_role: str
    personality_traits: List[str] = field(default_factory=list)
    motivations: List[str] = field(default_factory=list)
    relationships: Dict[str, str] = field(default_factory=dict)
    character_arc: List[str] = field(default_factory=list)
    current_goals: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    growth_points: List[str] = field(default_factory=list)
    last_appearance_chapter: Optional[int] = None
    last_appearance_scene: Optional[str] = None


@dataclass
class PlotThread:
    """Tracks an ongoing plot thread or subplot."""
    name: str
    description: str
    status: str  # "active", "resolved", "paused"
    introduced_in_chapter: int
    current_chapter: int
    key_events: List[str] = field(default_factory=list)
    involved_characters: List[str] = field(default_factory=list)
    tension_level: int = 1  # 1-10 scale
    resolution_hints: List[str] = field(default_factory=list)


@dataclass
class StoryContext:
    """Maintains the current state and context of the story."""
    story_direction: str
    tone_style: str
    target_audience: str
    story_pacing: str  # "slow", "medium", "fast"
    current_themes: List[str] = field(default_factory=list)
    world_rules: List[str] = field(default_factory=list)
    genre_conventions: List[str] = field(default_factory=list)
    current_tension: int = 1  # 1-10 scale
    story_goals: List[str] = field(default_factory=list)
    completed_arcs: List[str] = field(default_factory=list)


@dataclass
class ChapterState:
    """Tracks the state and evolution of a specific chapter."""
    chapter_number: int
    title: str
    status: str  # "planned", "writing", "completed", "revised"
    planned_content: str
    actual_content: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    key_events: List[str] = field(default_factory=list)
    character_developments: List[str] = field(default_factory=list)
    plot_advancements: List[str] = field(default_factory=list)
    themes_explored: List[str] = field(default_factory=list)
    revision_notes: List[str] = field(default_factory=list)


class StoryStateManager:
    """Manages the evolving state of the story during progressive generation."""
    
    def __init__(
        self,
        model_provider: ModelProvider,
        config: Dict[str, Any],
        prompt_handler: PromptHandler,
        system_message: str,
        savepoint_manager: Optional[SavepointManager] = None,
        rag_service: Optional[Any] = None
    ):
        self.model_provider = model_provider
        self.config = config
        self.prompt_handler = prompt_handler
        self.system_message = system_message
        self.savepoint_manager = savepoint_manager
        
        # Story state components
        self.story_context: Optional[StoryContext] = None
        self.characters: Dict[str, CharacterState] = {}
        self.plot_threads: Dict[str, PlotThread] = {}
        self.chapters: Dict[int, ChapterState] = {}
        self.story_evolution: List[str] = []
        
        # State file path
        self.state_file_path: Optional[str] = None
        
        # RAG integration for story interrogation
        self.rag_integration = None
        if rag_service:
            # Initialize RAG integration with the provided service
            try:
                content_chunker = ContentChunker(
                    max_chunk_size=config.get("max_chunk_size", 1000),
                    overlap_size=config.get("overlap_size", 200)
                )
                self.rag_integration = RAGIntegrationService(rag_service, content_chunker)
                
                if config.get("debug", False):
                    print("RAG integration initialized with RAG service")
            except ImportError:
                if config.get("debug", False):
                    print("RAG integration not available - using fallback methods")
        elif self.savepoint_manager and self.savepoint_manager.savepoint_repo:
            # Fallback to mock RAG integration if no service provided
            try:
                # Create a placeholder for now
                self.rag_integration = type('MockRAGIntegration', (), {
                    'query_story_content': lambda self, query: f"Mock RAG response to: {query}"
                })()
                
                if config.get("debug", False):
                    print("RAG integration initialized with mock service")
            except ImportError:
                if config.get("debug", False):
                    print("RAG integration not available - using fallback methods")
        
    def set_story_directory(self, story_name: str) -> None:
        """Set the story directory for state persistence."""
        if self.savepoint_manager and self.savepoint_manager.savepoint_repo:
            story_dir = self.savepoint_manager.savepoint_repo._current_story_dir
            if story_dir:
                self.state_file_path = os.path.join(story_dir, "story_state.json")
                self._load_state()
    
    async def initialize_story_context(self, prompt: str, settings: GenerationSettings) -> StoryContext:
        """Initialize the story context from the initial prompt."""
        model_config = ModelConfig.from_string(self.config["models"]["initial_outline_writer"])
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="story_state/initialize_context",
            variables={"prompt": prompt},
            savepoint_id="story_context_initialization",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        # Parse the response to create StoryContext
        context_data = self._parse_context_response(response.content)
        self.story_context = StoryContext(**context_data)
        
        # Save initial state
        self._save_state()
        
        return self.story_context
    
    async def plan_next_chapter(self, settings: GenerationSettings) -> ChapterState:
        """Plan the next chapter based on current story state."""
        if not self.story_context:
            raise ValueError("Story context must be initialized before planning chapters")
        
        next_chapter_num = len(self.chapters) + 1
        model_config = ModelConfig.from_string(self.config["models"]["chapter_outline_writer"])
        
        # Prepare context for planning
        planning_context = self._prepare_planning_context()
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="story_state/plan_next_chapter",
            variables={
                "chapter_number": next_chapter_num,
                "story_context": planning_context,
                "current_characters": self._serialize_characters(),
                "active_plot_threads": self._serialize_plot_threads(),
                "completed_chapters": self._serialize_completed_chapters()
            },
            savepoint_id=f"chapter_{next_chapter_num}_planning",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        # Parse the response to create ChapterState
        chapter_data = self._parse_chapter_plan_response(response.content, next_chapter_num)
        chapter_state = ChapterState(**chapter_data)
        
        # Add to chapters and save state
        self.chapters[next_chapter_num] = chapter_state
        self._save_state()
        
        return chapter_state
    
    async def update_story_evolution(self, chapter_num: int, settings: GenerationSettings) -> None:
        """Analyze how the chapter affects story evolution using RAG interrogation."""
        model_config = ModelConfig.from_string(self.config["models"]["logical_model"])
        
        # Use RAG to interrogate the chapter instead of reading full content
        evolution_data = await self._analyze_chapter_evolution_rag(chapter_num, settings)
        
        # Apply evolution updates
        self._apply_evolution_updates(evolution_data, chapter_num)
        
        # Save updated state
        self._save_state()
    
    async def revise_chapter_plan(self, chapter_num: int, settings: GenerationSettings) -> ChapterState:
        """Revise a chapter plan based on story evolution."""
        if chapter_num not in self.chapters:
            raise ValueError(f"Chapter {chapter_num} not found")
        
        chapter_state = self.chapters[chapter_num]
        model_config = ModelConfig.from_string(self.config["models"]["chapter_outline_writer"])
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="story_state/revise_chapter_plan",
            variables={
                "chapter_state": self._serialize_chapter_state(chapter_state),
                "current_story_state": self._serialize_current_state(),
                "evolution_since_planning": self._get_evolution_since_chapter(chapter_num)
            },
            savepoint_id=f"chapter_{chapter_num}_plan_revision",
            model_config=model_config,
            seed=settings.seed,
            debug=settings.debug,
            stream=settings.stream,
            log_prompt_inputs=settings.log_prompt_inputs,
            system_message=self.system_message
        )
        
        # Update chapter state with revisions
        revision_data = self._parse_revision_response(response.content)
        self._apply_chapter_revisions(chapter_state, revision_data)
        
        # Save updated state
        self._save_state()
        
        return chapter_state
    
    async def _analyze_chapter_evolution_rag(self, chapter_num: int, settings: GenerationSettings) -> Dict[str, Any]:
        """Analyze chapter evolution using RAG interrogation instead of reading full content."""
        if not self.rag_integration:
            # Fallback to basic analysis if RAG is not available
            return self._get_basic_evolution_data(chapter_num)
        
        evolution_data = {
            "character_updates": [],
            "plot_advancements": [],
            "new_themes": [],
            "tension_changes": [],
            "world_developments": []
        }
        
        # Interrogate RAG about character developments in this chapter
        character_query = f"What character developments, growth, or changes occurred in chapter {chapter_num}? Focus on how characters evolved, learned, or changed."
        character_response = await self._query_rag(character_query, settings)
        if character_response:
            evolution_data["character_updates"] = self._extract_list_items(character_response)
        
        # Interrogate RAG about plot advancements
        plot_query = f"What plot elements advanced or changed in chapter {chapter_num}? What new plot threads were introduced or resolved?"
        plot_response = await self._query_rag(plot_query, settings)
        if plot_response:
            evolution_data["plot_advancements"] = self._extract_list_items(plot_response)
        
        # Interrogate RAG about new themes
        theme_query = f"What new themes emerged or were developed in chapter {chapter_num}? How were existing themes explored?"
        theme_response = await self._query_rag(theme_query, settings)
        if theme_response:
            evolution_data["new_themes"] = self._extract_list_items(theme_response)
        
        # Interrogate RAG about tension changes
        tension_query = f"How did the story's tension level change in chapter {chapter_num}? Did it increase, decrease, or shift in nature?"
        tension_response = await self._query_rag(tension_query, settings)
        if tension_response:
            evolution_data["tension_changes"] = [tension_response]
        
        # Interrogate RAG about world developments
        world_query = f"What new information about the story world, setting, or rules was revealed in chapter {chapter_num}?"
        world_response = await self._query_rag(world_query, settings)
        if world_response:
            evolution_data["world_developments"] = self._extract_list_items(world_response)
        
        return evolution_data
    
    async def _query_rag(self, query: str, settings: GenerationSettings) -> Optional[str]:
        """Query the RAG system for information about the story."""
        try:
            if not self.rag_integration:
                return None
            
            # Use the RAG integration service to query the story
            response = await self.rag_integration.query_story_content(query)
            return response.strip() if response else None
            
        except Exception as e:
            if settings.debug:
                print(f"RAG query failed: {e}")
            return None
    
    def _extract_list_items(self, text: str) -> List[str]:
        """Extract list items from RAG response text."""
        if not text:
            return []
        
        lines = text.strip().split('\n')
        items = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                items.append(line[1:].strip())
            elif line and not line.startswith('#'):  # Skip headers
                items.append(line)
        
        return items if items else [text.strip()]
    
    def _get_basic_evolution_data(self, chapter_num: int) -> Dict[str, Any]:
        """Fallback method for basic evolution data when RAG is not available."""
        return {
            "character_updates": [f"Chapter {chapter_num} character development analyzed"],
            "plot_advancements": [f"Chapter {chapter_num} plot advancement noted"],
            "new_themes": [],
            "tension_changes": [],
            "world_developments": []
        }
    
    def get_story_summary(self) -> str:
        """Get a comprehensive summary of the current story state."""
        if not self.story_context:
            return "Story context not initialized"
        
        summary_parts = [
            f"Story Direction: {self.story_context.story_direction}",
            f"Current Themes: {', '.join(self.story_context.current_themes)}",
            f"Tone: {self.story_context.tone_style}",
            f"Pacing: {self.story_context.story_pacing}",
            f"Current Tension: {self.story_context.current_tension}/10",
            f"Completed Chapters: {len(self.chapters)}",
            f"Active Characters: {len(self.characters)}",
            f"Active Plot Threads: {len([t for t in self.plot_threads.values() if t.status == 'active'])}"
        ]
        
        return "\n".join(summary_parts)
    
    def _prepare_planning_context(self) -> str:
        """Prepare context information for chapter planning."""
        context_parts = [
            f"Story Direction: {self.story_context.story_direction}",
            f"Current Themes: {', '.join(self.story_context.current_themes)}",
            f"Tone: {self.story_context.tone_style}",
            f"Target Audience: {self.story_context.target_audience}",
            f"Current Tension Level: {self.story_context.current_tension}/10"
        ]
        
        if self.chapters:
            context_parts.append(f"Story Progress: {len(self.chapters)} chapters completed")
            context_parts.append(f"Recent Developments: {', '.join(self.story_evolution[-3:])}")
        
        return "\n".join(context_parts)
    
    def _serialize_characters(self) -> str:
        """Serialize character information for prompts."""
        if not self.characters:
            return "No characters introduced yet"
        
        char_info = []
        for char in self.characters.values():
            char_info.append(f"{char.name} ({char.current_role}): {', '.join(char.current_goals)}")
        
        return "\n".join(char_info)
    
    def _serialize_plot_threads(self) -> str:
        """Serialize plot thread information for prompts."""
        active_threads = [t for t in self.plot_threads.values() if t.status == 'active']
        if not active_threads:
            return "No active plot threads"
        
        thread_info = []
        for thread in active_threads:
            thread_info.append(f"{thread.name}: {thread.description} (Tension: {thread.tension_level}/10)")
        
        return "\n".join(thread_info)
    
    def _serialize_completed_chapters(self) -> str:
        """Serialize completed chapter information for prompts."""
        if not self.chapters:
            return "No chapters completed yet"
        
        chapter_info = []
        for chapter in self.chapters.values():
            if chapter.status in ["completed", "revised"]:
                chapter_info.append(f"Chapter {chapter.chapter_number}: {chapter.title}")
        
        return "\n".join(chapter_info)
    
    def _serialize_current_state(self) -> str:
        """Serialize the complete current story state for prompts."""
        state_parts = [
            self._prepare_planning_context(),
            f"\nCharacters:\n{self._serialize_characters()}",
            f"\nPlot Threads:\n{self._serialize_plot_threads()}",
            f"\nCompleted Chapters:\n{self._serialize_completed_chapters()}"
        ]
        
        return "\n".join(state_parts)
    
    def _serialize_chapter_state(self, chapter_state: ChapterState) -> str:
        """Serialize a chapter state for prompts."""
        return f"Chapter {chapter_state.chapter_number}: {chapter_state.title}\nStatus: {chapter_state.status}\nPlanned Content: {chapter_state.planned_content}"
    
    def _get_evolution_since_chapter(self, chapter_num: int) -> str:
        """Get story evolution that occurred after a chapter was planned."""
        if chapter_num >= len(self.story_evolution):
            return "No evolution since planning"
        
        return "\n".join(self.story_evolution[chapter_num:])
    
    def _parse_context_response(self, response: str) -> Dict[str, Any]:
        """Parse the response from context initialization prompt."""
        # This is a simplified parser - in practice, you'd want more robust parsing
        lines = response.strip().split('\n')
        context_data = {
            "story_direction": "",
            "current_themes": [],
            "world_rules": [],
            "tone_style": "",
            "target_audience": "",
            "genre_conventions": [],
            "story_pacing": "medium",
            "current_tension": 1,
            "story_goals": [],
            "completed_arcs": []
        }
        
        for line in lines:
            if line.startswith("Direction:"):
                context_data["story_direction"] = line.replace("Direction:", "").strip()
            elif line.startswith("Themes:"):
                themes = line.replace("Themes:", "").strip()
                context_data["current_themes"] = [t.strip() for t in themes.split(",")]
            elif line.startswith("Tone:"):
                context_data["tone_style"] = line.replace("Tone:", "").strip()
            elif line.startswith("Audience:"):
                context_data["target_audience"] = line.replace("Audience:", "").strip()
            elif line.startswith("Pacing:"):
                context_data["story_pacing"] = line.replace("Pacing:", "").strip()
        
        return context_data
    
    def _parse_chapter_plan_response(self, response: str, chapter_num: int) -> Dict[str, Any]:
        """Parse the response from chapter planning prompt."""
        lines = response.strip().split('\n')
        chapter_data = {
            "chapter_number": chapter_num,
            "title": f"Chapter {chapter_num}",
            "status": "planned",
            "planned_content": "",
            "actual_content": "",
            "key_events": [],
            "character_developments": [],
            "plot_advancements": [],
            "themes_explored": [],
            "revision_notes": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        current_section = ""
        for line in lines:
            if line.startswith("Title:"):
                chapter_data["title"] = line.replace("Title:", "").strip()
            elif line.startswith("Content:"):
                current_section = "content"
            elif line.startswith("Events:"):
                current_section = "events"
            elif line.startswith("Character Development:"):
                current_section = "character_dev"
            elif line.startswith("Plot Advancement:"):
                current_section = "plot_adv"
            elif line.startswith("Themes:"):
                current_section = "themes"
            elif current_section == "content" and line.strip():
                chapter_data["planned_content"] += line + "\n"
            elif current_section == "events" and line.strip() and not line.startswith("-"):
                chapter_data["key_events"].append(line.strip())
            elif current_section == "character_dev" and line.strip() and not line.startswith("-"):
                chapter_data["character_developments"].append(line.strip())
            elif current_section == "plot_adv" and line.strip() and not line.startswith("-"):
                chapter_data["plot_advancements"].append(line.strip())
            elif current_section == "themes" and line.strip() and not line.startswith("-"):
                chapter_data["themes_explored"].append(line.strip())
        
        chapter_data["planned_content"] = chapter_data["planned_content"].strip()
        return chapter_data
    
    def _parse_evolution_response(self, response: str) -> Dict[str, Any]:
        """Parse the response from evolution analysis prompt."""
        # Simplified parser - in practice, you'd want more robust parsing
        evolution_data = {
            "character_updates": [],
            "plot_advancements": [],
            "new_themes": [],
            "tension_changes": [],
            "world_developments": []
        }
        
        lines = response.strip().split('\n')
        current_section = ""
        
        for line in lines:
            if line.startswith("Character Updates:"):
                current_section = "characters"
            elif line.startswith("Plot Advancements:"):
                current_section = "plot"
            elif line.startswith("New Themes:"):
                current_section = "themes"
            elif line.startswith("Tension Changes:"):
                current_section = "tension"
            elif line.startswith("World Developments:"):
                current_section = "world"
            elif current_section and line.strip() and not line.startswith("-"):
                if current_section == "characters":
                    evolution_data["character_updates"].append(line.strip())
                elif current_section == "plot":
                    evolution_data["plot_advancements"].append(line.strip())
                elif current_section == "themes":
                    evolution_data["new_themes"].append(line.strip())
                elif current_section == "tension":
                    evolution_data["tension_changes"].append(line.strip())
                elif current_section == "world":
                    evolution_data["world_developments"].append(line.strip())
        
        return evolution_data
    
    def _parse_revision_response(self, response: str) -> Dict[str, Any]:
        """Parse the response from chapter revision prompt."""
        revision_data = {
            "updated_content": "",
            "new_events": [],
            "character_updates": [],
            "plot_changes": [],
            "revision_reason": ""
        }
        
        lines = response.strip().split('\n')
        current_section = ""
        
        for line in lines:
            if line.startswith("Updated Content:"):
                current_section = "content"
            elif line.startswith("New Events:"):
                current_section = "events"
            elif line.startswith("Character Updates:"):
                current_section = "characters"
            elif line.startswith("Plot Changes:"):
                current_section = "plot"
            elif line.startswith("Revision Reason:"):
                current_section = "reason"
            elif current_section == "content" and line.strip():
                revision_data["updated_content"] += line + "\n"
            elif current_section == "events" and line.strip() and not line.startswith("-"):
                revision_data["new_events"].append(line.strip())
            elif current_section == "characters" and line.strip() and not line.startswith("-"):
                revision_data["character_updates"].append(line.strip())
            elif current_section == "plot" and line.strip() and not line.startswith("-"):
                revision_data["plot_changes"].append(line.strip())
            elif current_section == "reason" and line.strip():
                revision_data["revision_reason"] = line.strip()
        
        revision_data["updated_content"] = revision_data["updated_content"].strip()
        return revision_data
    
    def _apply_evolution_updates(self, evolution_data: Dict[str, Any], chapter_num: int) -> None:
        """Apply evolution updates to the story state."""
        # Update story evolution log
        evolution_summary = f"Chapter {chapter_num} evolution: "
        if evolution_data["character_updates"]:
            evolution_summary += f"Character updates: {len(evolution_data['character_updates'])}. "
        if evolution_data["plot_advancements"]:
            evolution_summary += f"Plot advancements: {len(evolution_data['plot_advancements'])}. "
        if evolution_data["new_themes"]:
            evolution_summary += f"New themes: {len(evolution_data['new_themes'])}. "
        
        self.story_evolution.append(evolution_summary.strip())
        
        # Update story context
        if evolution_data["new_themes"]:
            self.story_context.current_themes.extend(evolution_data["new_themes"])
        
        # Update characters (simplified - in practice, you'd want more sophisticated character tracking)
        for update in evolution_data["character_updates"]:
            # Parse character updates and apply them
            pass
        
        # Update plot threads (simplified - in practice, you'd want more sophisticated plot tracking)
        for advancement in evolution_data["plot_advancements"]:
            # Parse plot advancements and apply them
            pass
    
    async def analyze_character_development_rag(self, character_name: str, settings: GenerationSettings) -> Dict[str, Any]:
        """Analyze character development using RAG interrogation."""
        if not self.rag_integration:
            return self._get_basic_character_data(character_name)
        
        character_data = {
            "current_role": "",
            "personality_traits": [],
            "motivations": [],
            "relationships": {},
            "character_arc": [],
            "current_goals": [],
            "conflicts": [],
            "growth_points": []
        }
        
        # Query RAG about character's current role and development
        role_query = f"What is {character_name}'s current role in the story? How has their role evolved?"
        role_response = await self._query_rag(role_query, settings)
        if role_response:
            character_data["current_role"] = role_response
        
        # Query about personality traits
        traits_query = f"What are {character_name}'s key personality traits? How have they been revealed or developed?"
        traits_response = await self._query_rag(traits_query, settings)
        if traits_response:
            character_data["personality_traits"] = self._extract_list_items(traits_response)
        
        # Query about motivations
        motivations_query = f"What are {character_name}'s current motivations and goals? How have they changed?"
        motivations_response = await self._query_rag(motivations_query, settings)
        if motivations_response:
            character_data["motivations"] = self._extract_list_items(motivations_response)
        
        # Query about relationships
        relationships_query = f"What are {character_name}'s key relationships with other characters? How have they evolved?"
        relationships_response = await self._query_rag(relationships_query, settings)
        if relationships_response:
            # Parse relationships from response
            character_data["relationships"] = self._parse_relationships(relationships_response)
        
        # Query about character arc
        arc_query = f"How has {character_name} grown or changed throughout the story? What is their character arc?"
        arc_response = await self._query_rag(arc_query, settings)
        if arc_response:
            character_data["character_arc"] = self._extract_list_items(arc_response)
        
        # Query about current goals
        goals_query = f"What are {character_name}'s immediate goals and what conflicts do they face?"
        goals_response = await self._query_rag(goals_query, settings)
        if goals_response:
            character_data["current_goals"] = self._extract_list_items(goals_response)
        
        # Query about conflicts
        conflicts_query = f"What internal and external conflicts does {character_name} currently face?"
        conflicts_response = await self._query_rag(conflicts_query, settings)
        if conflicts_response:
            character_data["conflicts"] = self._extract_list_items(conflicts_response)
        
        # Query about growth points
        growth_query = f"What key moments of growth or change has {character_name} experienced?"
        growth_response = await self._query_rag(growth_query, settings)
        if growth_response:
            character_data["growth_points"] = self._extract_list_items(growth_response)
        
        return character_data
    
    async def analyze_plot_threads_rag(self, settings: GenerationSettings) -> Dict[str, Any]:
        """Analyze plot threads using RAG interrogation."""
        if not self.rag_integration:
            return self._get_basic_plot_data()
        
        plot_data = {
            "active_threads": [],
            "resolved_threads": [],
            "new_threads": [],
            "tension_levels": {},
            "character_involvement": {}
        }
        
        # Query RAG about active plot threads
        active_query = "What are the currently active plot threads and subplots in the story? What is their current status?"
        active_response = await self._query_rag(active_query, settings)
        if active_response:
            plot_data["active_threads"] = self._extract_list_items(active_response)
        
        # Query about resolved threads
        resolved_query = "What plot threads or subplots have been resolved or concluded in the story?"
        resolved_response = await self._query_rag(resolved_query, settings)
        if resolved_response:
            plot_data["resolved_threads"] = self._extract_list_items(resolved_response)
        
        # Query about new threads
        new_query = "What new plot threads or subplots have been introduced recently? What new conflicts or mysteries have emerged?"
        new_response = await self._query_rag(new_query, settings)
        if new_response:
            plot_data["new_threads"] = self._extract_list_items(new_response)
        
        # Query about tension levels
        tension_query = "What is the current tension level for each major plot thread? How has the overall story tension evolved?"
        tension_response = await self._query_rag(tension_query, settings)
        if tension_response:
            plot_data["tension_levels"] = self._parse_tension_levels(tension_response)
        
        # Query about character involvement
        involvement_query = "Which characters are most involved in each major plot thread? How has their involvement evolved?"
        involvement_response = await self._query_rag(involvement_query, settings)
        if involvement_response:
            plot_data["character_involvement"] = self._parse_character_involvement(involvement_response)
        
        return plot_data
    
    def _parse_relationships(self, text: str) -> Dict[str, str]:
        """Parse character relationships from RAG response."""
        relationships = {}
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    character = parts[0].strip()
                    relationship = parts[1].strip()
                    relationships[character] = relationship
        
        return relationships
    
    def _parse_tension_levels(self, text: str) -> Dict[str, int]:
        """Parse tension levels from RAG response."""
        tension_levels = {}
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    thread = parts[0].strip()
                    tension_text = parts[1].strip()
                    # Try to extract numeric tension level
                    try:
                        tension = int(tension_text.split('/')[0])
                        tension_levels[thread] = tension
                    except (ValueError, IndexError):
                        tension_levels[thread] = 5  # Default tension level
        
        return tension_levels
    
    def _parse_character_involvement(self, text: str) -> Dict[str, List[str]]:
        """Parse character involvement from RAG response."""
        involvement = {}
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    thread = parts[0].strip()
                    characters_text = parts[1].strip()
                    characters = [c.strip() for c in characters_text.split(',')]
                    involvement[thread] = characters
        
        return involvement
    
    def _get_basic_character_data(self, character_name: str) -> Dict[str, Any]:
        """Fallback method for basic character data when RAG is not available."""
        return {
            "current_role": f"Character in story",
            "personality_traits": [f"{character_name} has developed personality traits"],
            "motivations": [f"{character_name} has motivations"],
            "current_goals": [f"{character_name} has goals"],
            "conflicts": [f"{character_name} faces conflicts"],
            "growth_points": [f"{character_name} has grown"]
        }
    
    def _get_basic_plot_data(self) -> Dict[str, Any]:
        """Fallback method for basic plot data when RAG is not available."""
        return {
            "active_threads": ["Story has active plot threads"],
            "resolved_threads": [],
            "new_threads": [],
            "tension_levels": {},
            "character_involvement": {}
        }
    
    def _apply_chapter_revisions(self, chapter_state: ChapterState, revision_data: Dict[str, Any]) -> None:
        """Apply revisions to a chapter state."""
        if revision_data["updated_content"]:
            chapter_state.planned_content = revision_data["updated_content"]
        
        if revision_data["new_events"]:
            chapter_state.key_events.extend(revision_data["new_events"])
        
        if revision_data["character_updates"]:
            chapter_state.character_developments.extend(revision_data["character_updates"])
        
        if revision_data["plot_changes"]:
            chapter_state.plot_advancements.extend(revision_data["plot_changes"])
        
        if revision_data["revision_reason"]:
            chapter_state.revision_notes.append(revision_data["revision_reason"])
        
        chapter_state.updated_at = datetime.now()
        chapter_state.status = "revised"
    
    def _save_state(self) -> None:
        """Save the current story state to file."""
        if not self.state_file_path:
            return
        
        state_data = {
            "story_context": {
                "story_direction": self.story_context.story_direction if self.story_context else "",
                "current_themes": self.story_context.current_themes if self.story_context else [],
                "world_rules": self.story_context.world_rules if self.story_context else [],
                "tone_style": self.story_context.tone_style if self.story_context else "",
                "target_audience": self.story_context.target_audience if self.story_context else "",
                "genre_conventions": self.story_context.genre_conventions if self.story_context else [],
                "story_pacing": self.story_context.story_pacing if self.story_context else "medium",
                "current_tension": self.story_context.current_tension if self.story_context else 1,
                "story_goals": self.story_context.story_goals if self.story_context else [],
                "completed_arcs": self.story_context.completed_arcs if self.story_context else []
            },
            "characters": {name: {
                "name": char.name,
                "current_role": char.current_role,
                "personality_traits": char.personality_traits,
                "motivations": char.motivations,
                "relationships": char.relationships,
                "character_arc": char.character_arc,
                "current_goals": char.current_goals,
                "conflicts": char.conflicts,
                "growth_points": char.growth_points,
                "last_appearance_chapter": char.last_appearance_chapter,
                "last_appearance_scene": char.last_appearance_scene
            } for name, char in self.characters.items()},
            "plot_threads": {name: {
                "name": thread.name,
                "description": thread.description,
                "status": thread.status,
                "introduced_in_chapter": thread.introduced_in_chapter,
                "current_chapter": thread.current_chapter,
                "key_events": thread.key_events,
                "involved_characters": thread.involved_characters,
                "tension_level": thread.tension_level,
                "resolution_hints": thread.resolution_hints
            } for name, thread in self.plot_threads.items()},
            "chapters": {num: {
                "chapter_number": chapter.chapter_number,
                "title": chapter.title,
                "status": chapter.status,
                "planned_content": chapter.planned_content,
                "actual_content": chapter.actual_content,
                "key_events": chapter.key_events,
                "character_developments": chapter.character_developments,
                "plot_advancements": chapter.plot_advancements,
                "themes_explored": chapter.themes_explored,
                "revision_notes": chapter.revision_notes,
                "created_at": chapter.created_at.isoformat(),
                "updated_at": chapter.updated_at.isoformat()
            } for num, chapter in self.chapters.items()},
            "story_evolution": self.story_evolution
        }
        
        try:
            with open(self.state_file_path, 'w') as f:
                json.dump(state_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save story state: {e}")
    
    def _load_state(self) -> None:
        """Load the story state from file."""
        if not self.state_file_path or not os.path.exists(self.state_file_path):
            return
        
        try:
            with open(self.state_file_path, 'r') as f:
                state_data = json.load(f)
            
            # Restore story context
            if "story_context" in state_data:
                context_data = state_data["story_context"]
                self.story_context = StoryContext(**context_data)
            
            # Restore characters
            if "characters" in state_data:
                for name, char_data in state_data["characters"].items():
                    char_data["created_at"] = datetime.fromisoformat(char_data["created_at"])
                    char_data["updated_at"] = datetime.fromisoformat(char_data["updated_at"])
                    self.characters[name] = CharacterState(**char_data)
            
            # Restore plot threads
            if "plot_threads" in state_data:
                for name, thread_data in state_data["plot_threads"].items():
                    self.plot_threads[name] = PlotThread(**thread_data)
            
            # Restore chapters
            if "chapters" in state_data:
                for num, chapter_data in state_data["chapters"].items():
                    chapter_data["created_at"] = datetime.fromisoformat(chapter_data["created_at"])
                    chapter_data["updated_at"] = datetime.fromisoformat(chapter_data["updated_at"])
                    self.chapters[int(num)] = ChapterState(**chapter_data)
            
            # Restore story evolution
            if "story_evolution" in state_data:
                self.story_evolution = state_data["story_evolution"]
                
        except Exception as e:
            print(f"Warning: Could not load story state: {e}")
