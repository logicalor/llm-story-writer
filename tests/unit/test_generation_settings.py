"""Unit tests for GenerationSettings value object."""

import pytest

from src.domain.exceptions import ValidationError
from src.domain.value_objects.generation_settings import GenerationSettings


class TestGenerationSettings:
    """Verification tests for scene expansion generation settings."""

    def test_scenes_per_chapter_defaults(self) -> None:
        """Default scene expansion bounds match configured defaults."""
        settings = GenerationSettings()

        assert settings.scenes_per_chapter_min == 8
        assert settings.scenes_per_chapter_max == 16
        assert settings.scene_expansion_enabled is True

    def test_scenes_per_chapter_min_too_low(self) -> None:
        """Scene minimum below 1 is rejected."""
        with pytest.raises(ValidationError, match="must be >= 1"):
            GenerationSettings(scenes_per_chapter_min=0)

    def test_scenes_per_chapter_max_too_high(self) -> None:
        """Scene maximum above 30 is rejected."""
        with pytest.raises(ValidationError, match="must be <= 30"):
            GenerationSettings(scenes_per_chapter_max=31)

    def test_scenes_min_exceeds_max(self) -> None:
        """Scene minimum cannot exceed scene maximum."""
        with pytest.raises(ValidationError, match="min must be <= max"):
            GenerationSettings(scenes_per_chapter_min=10, scenes_per_chapter_max=5)

    def test_scene_expansion_enabled_default_true(self) -> None:
        """Scene expansion flag defaults to enabled."""
        assert GenerationSettings().scene_expansion_enabled is True

    def test_from_dict_scenes_fields(self) -> None:
        """from_dict preserves explicit scene range overrides."""
        settings = GenerationSettings.from_dict(
            {
                "scenes_per_chapter_min": 5,
                "scenes_per_chapter_max": 12,
            }
        )

        assert settings.scenes_per_chapter_min == 5
        assert settings.scenes_per_chapter_max == 12
        assert settings.scene_expansion_enabled is True
