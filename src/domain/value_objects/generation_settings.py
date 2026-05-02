"""Generation settings value objects."""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from ..exceptions import ValidationError


@dataclass(frozen=True)
class GenerationSettings:
    """Settings for story generation process."""

    # Core settings
    seed: int = 12
    wanted_chapters: int = 40  # Default number of desired chapters

    # Feature flags
    enable_final_edit: bool = False
    enable_scrubbing: bool = True
    expand_outline: bool = True
    scene_generation_pipeline: bool = True
    scenes_per_chapter_min: int = 8
    scenes_per_chapter_max: int = 16

    # Critique settings
    enable_outline_critique: bool = True
    enable_concurrent_critics: bool = False

    # Initial outline generation settings
    use_chunked_outline_generation: bool = (
        False  # Use chunked approach vs single-pass generation
    )
    outline_chunk_size: int = 4  # Number of chapters per chunk in outline generation

    # Output settings
    stream: bool = False
    debug: bool = False
    log_prompt_inputs: bool = False  # Log full prompt inputs for debugging

    # Recap sanitizer settings
    use_improved_recap_sanitizer: bool = True
    use_multi_stage_recap_sanitizer: bool = True

    # Translation settings
    translate_language: Optional[str] = None
    translate_prompt_language: Optional[str] = None

    def __post_init__(self):
        """Validate the generation settings."""
        # Validate seed
        if self.seed < 0:
            raise ValidationError(f"Seed cannot be negative, got {self.seed}")

        # Validate wanted chapters
        if self.wanted_chapters < 1:
            raise ValidationError(
                f"Wanted chapters must be at least 1, got {self.wanted_chapters}"
            )

        if self.wanted_chapters > 1000:
            raise ValidationError(
                f"Wanted chapters cannot exceed 1000, got {self.wanted_chapters}"
            )

        # Validate outline chunk size
        if self.outline_chunk_size < 1:
            raise ValidationError(
                f"Outline chunk size must be at least 1, got {self.outline_chunk_size}"
            )

        if self.outline_chunk_size > 20:
            raise ValidationError(
                f"Outline chunk size cannot exceed 20, got {self.outline_chunk_size}"
            )

        if not (1 <= self.scenes_per_chapter_min <= self.scenes_per_chapter_max <= 30):
            raise ValidationError(
                f"scenes_per_chapter_min ({self.scenes_per_chapter_min}) must be >= 1, "
                f"scenes_per_chapter_max ({self.scenes_per_chapter_max}) must be <= 30, "
                "and min must be <= max"
            )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GenerationSettings":
        """Create GenerationSettings from a dictionary."""
        import dataclasses

        known_fields = {f.name for f in dataclasses.fields(cls)}
        filtered_data = {k: v for k, v in data.items() if v is not None and k in known_fields}
        return cls(**filtered_data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert GenerationSettings to a dictionary."""
        return {
            "seed": self.seed,
            "wanted_chapters": self.wanted_chapters,
            "enable_final_edit": self.enable_final_edit,
            "enable_scrubbing": self.enable_scrubbing,
            "expand_outline": self.expand_outline,
            "scene_generation_pipeline": self.scene_generation_pipeline,
            "scenes_per_chapter_min": self.scenes_per_chapter_min,
            "scenes_per_chapter_max": self.scenes_per_chapter_max,
            "enable_outline_critique": self.enable_outline_critique,
            "enable_concurrent_critics": self.enable_concurrent_critics,
            "stream": self.stream,
            "debug": self.debug,
            "use_improved_recap_sanitizer": self.use_improved_recap_sanitizer,
            "use_multi_stage_recap_sanitizer": self.use_multi_stage_recap_sanitizer,
            "use_chunked_outline_generation": self.use_chunked_outline_generation,
            "outline_chunk_size": self.outline_chunk_size,
            "log_prompt_inputs": self.log_prompt_inputs,
            "translate_language": self.translate_language,
            "translate_prompt_language": self.translate_prompt_language,
        }

    def with_updates(self, **kwargs) -> "GenerationSettings":
        """Create a new instance with updated values."""
        current_data = self.to_dict()
        current_data.update(kwargs)
        return self.from_dict(current_data)
