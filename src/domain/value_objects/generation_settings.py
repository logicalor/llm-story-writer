"""Generation settings value objects."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from ..exceptions import ValidationError


@dataclass(frozen=True)
class GenerationSettings:
    """Settings for story generation process."""
    
    # Core settings
    seed: int = 12
    outline_quality: int = 87
    chapter_quality: int = 85
    wanted_chapters: int = 40  # Default number of desired chapters
    
    # Revision settings
    outline_min_revisions: int = 2
    outline_max_revisions: int = 3
    chapter_min_revisions: int = 2
    chapter_max_revisions: int = 3
    
    # Feature flags
    enable_final_edit: bool = False
    enable_scrubbing: bool = True
    enable_chapter_revisions: bool = True
    expand_outline: bool = True
    scene_generation_pipeline: bool = True
    
    # Critique settings
    enable_outline_critique: bool = True
    outline_critique_iterations: int = 3
    
    # Output settings
    stream: bool = False
    debug: bool = False
    
    # Strategy settings
    strategy: str = "outline-chapter"
    
    # Recap sanitizer settings
    use_improved_recap_sanitizer: bool = True
    use_multi_stage_recap_sanitizer: bool = True
    
    # Translation settings
    translate_language: Optional[str] = None
    translate_prompt_language: Optional[str] = None
    
    # Advanced settings
    optional_output_name: Optional[str] = None
    
    def __post_init__(self):
        """Validate the generation settings."""
        # Validate quality thresholds
        if not 0 <= self.outline_quality <= 100:
            raise ValidationError(f"Outline quality must be between 0 and 100, got {self.outline_quality}")
        
        if not 0 <= self.chapter_quality <= 100:
            raise ValidationError(f"Chapter quality must be between 0 and 100, got {self.chapter_quality}")
        
        # Validate revision counts
        if self.outline_min_revisions < 0:
            raise ValidationError(f"Outline min revisions cannot be negative, got {self.outline_min_revisions}")
        
        if self.outline_max_revisions < self.outline_min_revisions:
            raise ValidationError(
                f"Outline max revisions ({self.outline_max_revisions}) cannot be less than min revisions ({self.outline_min_revisions})"
            )
        
        if self.chapter_min_revisions < 0:
            raise ValidationError(f"Chapter min revisions cannot be negative, got {self.chapter_min_revisions}")
        
        if self.chapter_max_revisions < self.chapter_min_revisions:
            raise ValidationError(
                f"Chapter max revisions ({self.chapter_max_revisions}) cannot be less than min revisions ({self.chapter_min_revisions})"
            )
        
        # Validate seed
        if self.seed < 0:
            raise ValidationError(f"Seed cannot be negative, got {self.seed}")
        
        # Validate wanted chapters
        if self.wanted_chapters < 1:
            raise ValidationError(f"Wanted chapters must be at least 1, got {self.wanted_chapters}")
        
        if self.wanted_chapters > 1000:
            raise ValidationError(f"Wanted chapters cannot exceed 1000, got {self.wanted_chapters}")
        
        # Validate critique iterations
        if self.outline_critique_iterations < 1:
            raise ValidationError(f"Outline critique iterations must be at least 1, got {self.outline_critique_iterations}")
        
        if self.outline_critique_iterations > 10:
            raise ValidationError(f"Outline critique iterations cannot exceed 10, got {self.outline_critique_iterations}")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GenerationSettings":
        """Create GenerationSettings from a dictionary."""
        # Filter out None values and use defaults
        filtered_data = {k: v for k, v in data.items() if v is not None}
        return cls(**filtered_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert GenerationSettings to a dictionary."""
        return {
            "seed": self.seed,
            "outline_quality": self.outline_quality,
            "chapter_quality": self.chapter_quality,
            "wanted_chapters": self.wanted_chapters,
            "outline_min_revisions": self.outline_min_revisions,
            "outline_max_revisions": self.outline_max_revisions,
            "chapter_min_revisions": self.chapter_min_revisions,
            "chapter_max_revisions": self.chapter_max_revisions,
            "enable_final_edit": self.enable_final_edit,
            "enable_scrubbing": self.enable_scrubbing,
            "enable_chapter_revisions": self.enable_chapter_revisions,
            "expand_outline": self.expand_outline,
            "scene_generation_pipeline": self.scene_generation_pipeline,
            "enable_outline_critique": self.enable_outline_critique,
            "outline_critique_iterations": self.outline_critique_iterations,
            "stream": self.stream,
            "debug": self.debug,
            "strategy": self.strategy,
            "use_improved_recap_sanitizer": self.use_improved_recap_sanitizer,
            "use_multi_stage_recap_sanitizer": self.use_multi_stage_recap_sanitizer,
            "translate_language": self.translate_language,
            "translate_prompt_language": self.translate_prompt_language,
            "optional_output_name": self.optional_output_name,
        }
    
    def with_updates(self, **kwargs) -> "GenerationSettings":
        """Create a new instance with updated values."""
        current_data = self.to_dict()
        current_data.update(kwargs)
        return self.from_dict(current_data) 