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


class TestPersonaSettings:
    """Verification tests for author persona generation settings."""

    def test_persona_word_budget_default(self) -> None:
        """Persona word budget defaults to the configured midpoint."""
        settings = GenerationSettings()

        assert settings.persona_word_budget == 225

    def test_persona_word_budget_min_valid(self) -> None:
        """Persona word budget accepts the lower bound."""
        settings = GenerationSettings(persona_word_budget=100)

        assert settings.persona_word_budget == 100

    def test_persona_word_budget_max_valid(self) -> None:
        """Persona word budget accepts the upper bound."""
        settings = GenerationSettings(persona_word_budget=500)

        assert settings.persona_word_budget == 500

    def test_persona_word_budget_below_min_raises(self) -> None:
        """Persona word budget below the lower bound is rejected."""
        with pytest.raises(ValidationError, match="persona_word_budget"):
            GenerationSettings(persona_word_budget=99)

    def test_persona_word_budget_above_max_raises(self) -> None:
        """Persona word budget above the upper bound is rejected."""
        with pytest.raises(ValidationError, match="persona_word_budget"):
            GenerationSettings(persona_word_budget=501)

    def test_enable_author_persona_default_true(self) -> None:
        """Author persona is enabled by default."""
        settings = GenerationSettings()

        assert settings.enable_author_persona is True

    def test_enable_emphasis_delta_default_true(self) -> None:
        """Emphasis delta is enabled by default."""
        settings = GenerationSettings()

        assert settings.enable_emphasis_delta is True

    def test_persona_model_default_none(self) -> None:
        """Persona model falls back to None by default."""
        settings = GenerationSettings()

        assert settings.persona_model is None

    def test_to_dict_includes_persona_fields(self) -> None:
        """to_dict includes persona fields with default values."""
        settings = GenerationSettings()

        assert settings.to_dict()["enable_author_persona"] is True
        assert settings.to_dict()["persona_model"] is None
        assert settings.to_dict()["persona_word_budget"] == 225
        assert settings.to_dict()["enable_emphasis_delta"] is True

    def test_from_dict_persona_model_null_uses_default(self) -> None:
        """from_dict ignores explicit None and retains the default persona model."""
        settings = GenerationSettings.from_dict({"persona_model": None})

        assert settings.persona_model is None


class TestConsistencyRevisionLoopSettings:
    """Verification tests for consistency revision loop generation settings."""

    def test_consistency_fields_defaults(self) -> None:
        """Consistency revision loop defaults match spec."""
        settings = GenerationSettings()

        assert settings.enable_consistency_revision_loop is True
        assert settings.consistency_max_iterations == 2

    def test_consistency_max_iterations_validation_too_low(self) -> None:
        """consistency_max_iterations below 1 is rejected."""
        with pytest.raises(ValidationError):
            GenerationSettings(consistency_max_iterations=0)

    def test_consistency_max_iterations_validation_too_high(self) -> None:
        """consistency_max_iterations above 10 is rejected."""
        with pytest.raises(ValidationError):
            GenerationSettings(consistency_max_iterations=11)

    def test_consistency_max_iterations_lower_bound_valid(self) -> None:
        """consistency_max_iterations=1 is accepted."""
        settings = GenerationSettings(consistency_max_iterations=1)

        assert settings.consistency_max_iterations == 1

    def test_consistency_max_iterations_upper_bound_valid(self) -> None:
        """consistency_max_iterations=10 is accepted."""
        settings = GenerationSettings(consistency_max_iterations=10)

        assert settings.consistency_max_iterations == 10

    def test_to_dict_includes_consistency_fields(self) -> None:
        """to_dict includes both consistency revision fields."""
        settings = GenerationSettings(
            enable_consistency_revision_loop=False,
            consistency_max_iterations=3,
        )
        result = settings.to_dict()

        assert "enable_consistency_revision_loop" in result
        assert "consistency_max_iterations" in result
        assert result["enable_consistency_revision_loop"] is False
        assert result["consistency_max_iterations"] == 3
