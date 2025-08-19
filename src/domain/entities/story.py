"""Story entity and related components."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from ..exceptions import ValidationError


@dataclass
class Chapter:
    """A chapter in a story."""
    
    number: int
    title: str
    content: str
    word_count: int = 0
    outline: Optional[str] = None
    summary: Optional[str] = None
    scenes: List["Scene"] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate chapter data."""
        if self.number < 1:
            raise ValidationError(f"Chapter number must be positive, got {self.number}")
        
        if not self.title:
            raise ValidationError("Chapter title cannot be empty")
        
        if not self.content:
            raise ValidationError("Chapter content cannot be empty")
        
        # Calculate word count if not provided
        if self.word_count == 0:
            self.word_count = len(self.content.split())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chapter to dictionary."""
        return {
            "number": self.number,
            "title": self.title,
            "content": self.content,
            "word_count": self.word_count,
            "outline": self.outline,
            "summary": self.summary,
            "scenes": [scene.to_dict() for scene in self.scenes],
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chapter":
        """Create Chapter from dictionary."""
        # Extract scenes if they exist
        scenes_data = data.get("scenes", [])
        scenes = [Scene.from_dict(scene_data) for scene_data in scenes_data]
        
        # Create chapter without scenes first, then add them
        chapter_without_scenes = {k: v for k, v in data.items() if k != "scenes"}
        chapter = cls(**chapter_without_scenes)
        chapter.scenes = scenes
        return chapter


@dataclass
class Scene:
    """A scene within a chapter."""
    
    number: int
    title: str
    content: str
    word_count: int = 0
    outline: Optional[str] = None
    summary: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate scene data."""
        if self.number < 1:
            raise ValidationError(f"Scene number must be positive, got {self.number}")
        
        if not self.title:
            raise ValidationError("Scene title cannot be empty")
        
        if not self.content:
            raise ValidationError("Scene content cannot be empty")
        
        # Calculate word count if not provided
        if self.word_count == 0:
            self.word_count = len(self.content.split())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert scene to dictionary."""
        return {
            "number": self.number,
            "title": self.title,
            "content": self.content,
            "word_count": self.word_count,
            "outline": self.outline,
            "summary": self.summary,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Scene":
        """Create Scene from dictionary."""
        return cls(**data)





@dataclass
class Outline:
    """Story outline with all its components."""
    

    story_elements: str

    base_context: str
    story_start_date: Optional[str] = None
    initial_outline: Optional[str] = None  # The original outline before critique refinement

    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate outline data."""
        if not self.story_elements:
            raise ValidationError("Story elements cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert outline to dictionary."""
        return {
            "story_elements": self.story_elements,
            "base_context": self.base_context,
            "story_start_date": self.story_start_date,
            "initial_outline": self.initial_outline,
            "metadata": self.metadata,
        }


@dataclass
class StoryInfo:
    """Metadata about a story."""
    
    title: str
    summary: str
    tags: List[str]
    word_count: int = 0
    chapter_count: int = 0
    generation_date: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate story info."""
        if not self.title:
            raise ValidationError("Story title cannot be empty")
        
        if not self.summary:
            raise ValidationError("Story summary cannot be empty")
        
        if self.word_count < 0:
            raise ValidationError(f"Word count cannot be negative, got {self.word_count}")
        
        if self.chapter_count < 0:
            raise ValidationError(f"Chapter count cannot be negative, got {self.chapter_count}")
        
        if self.generation_date is None:
            self.generation_date = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert story info to dictionary."""
        return {
            "title": self.title,
            "summary": self.summary,
            "tags": self.tags,
            "word_count": self.word_count,
            "chapter_count": self.chapter_count,
            "generation_date": self.generation_date.isoformat() if self.generation_date else None,
            "metadata": self.metadata,
        }


@dataclass
class Story:
    """A complete story with all its components."""
    
    info: StoryInfo
    outline: Outline
    chapters: List[Chapter]
    prompt: str
    settings: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate story data."""
        if not self.prompt:
            raise ValidationError("Story prompt cannot be empty")
        
        # Update info with calculated values
        self.info.word_count = sum(chapter.word_count for chapter in self.chapters)
        self.info.chapter_count = len(self.chapters)
        
        # Validate chapter numbers are sequential
        chapter_numbers = [chapter.number for chapter in self.chapters]
        expected_numbers = list(range(1, len(self.chapters) + 1))
        if chapter_numbers != expected_numbers:
            raise ValidationError(f"Chapter numbers must be sequential starting from 1, got {chapter_numbers}")
    
    def get_chapter(self, number: int) -> Optional[Chapter]:
        """Get a chapter by number."""
        for chapter in self.chapters:
            if chapter.number == number:
                return chapter
        return None
    
    def get_full_content(self) -> str:
        """Get the complete story content."""
        content_parts = []
        for chapter in self.chapters:
            content_parts.append(f"### Chapter {chapter.number}\n\n{chapter.content}")
        return "\n\n".join(content_parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert story to dictionary."""
        return {
            "info": self.info.to_dict(),
            "outline": self.outline.to_dict(),
            "chapters": [chapter.to_dict() for chapter in self.chapters],
            "prompt": self.prompt,
            "settings": self.settings,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Story":
        """Create Story from dictionary."""
        info = StoryInfo(**data["info"])
        outline = Outline(**data["outline"])
        
        # Handle chapters with scenes
        chapters = []
        for chapter_data in data["chapters"]:
            # Extract scenes if they exist
            scenes_data = chapter_data.get("scenes", [])
            scenes = [Scene.from_dict(scene_data) for scene_data in scenes_data]
            
            # Create chapter without scenes first, then add them
            chapter_without_scenes = {k: v for k, v in chapter_data.items() if k != "scenes"}
            chapter = Chapter(**chapter_without_scenes)
            chapter.scenes = scenes
            chapters.append(chapter)
        
        return cls(
            info=info,
            outline=outline,
            chapters=chapters,
            prompt=data["prompt"],
            settings=data.get("settings", {}),
            metadata=data.get("metadata", {}),
        ) 