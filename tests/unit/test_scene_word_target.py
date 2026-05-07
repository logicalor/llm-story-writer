"""Verification tests for dynamic per-scene word targets."""

import pytest

from src.domain.exceptions import ValidationError
from src.domain.value_objects.generation_settings import GenerationSettings


def _compute_target(scene: dict[str, object], floor: int, ceiling: int) -> int:
    key_events = scene.get("key_events", [])
    description = scene.get("description", "")

    target = floor + 150 * len(key_events)
    if len(description) > 200:
        target += 100
    return min(target, ceiling)


def test_one_event_scene_yields_floor_plus_one_event() -> None:
    scene = {"key_events": ["Event 1"], "description": "short"}
    settings = GenerationSettings()

    # Independent expected value - intentional test design.
    assert (
        _compute_target(
            scene, settings.scene_word_target_floor, settings.scene_word_target_ceiling
        )
        == 750
    )


def test_six_event_scene_hits_ceiling() -> None:
    scene = {
        "key_events": [
            "Event 1",
            "Event 2",
            "Event 3",
            "Event 4",
            "Event 5",
            "Event 6",
        ],
        "description": "short",
    }
    settings = GenerationSettings()

    # Independent expected value - intentional test design.
    assert (
        _compute_target(
            scene, settings.scene_word_target_floor, settings.scene_word_target_ceiling
        )
        == 1500
    )


def test_zero_event_scene_yields_floor() -> None:
    scene = {"key_events": [], "description": "short"}
    settings = GenerationSettings()

    # Independent expected value - intentional test design.
    assert (
        _compute_target(
            scene, settings.scene_word_target_floor, settings.scene_word_target_ceiling
        )
        == 600
    )


def test_long_description_adds_bonus() -> None:
    scene = {
        "key_events": ["Event 1", "Event 2"],
        "description": "x" * 201,
    }
    settings = GenerationSettings()

    # Independent expected value - intentional test design.
    assert (
        _compute_target(
            scene, settings.scene_word_target_floor, settings.scene_word_target_ceiling
        )
        == 1000
    )


def test_generation_settings_default_values() -> None:
    settings = GenerationSettings()

    assert settings.scene_word_target_floor == 600
    assert settings.scene_word_target_ceiling == 1500


def test_generation_settings_yaml_round_trip() -> None:
    settings = GenerationSettings.from_dict(
        {
            "scene_word_target_floor": 800,
            "scene_word_target_ceiling": 2000,
        }
    )

    assert settings.scene_word_target_floor == 800
    assert settings.scene_word_target_ceiling == 2000


def test_floor_zero_raises_value_error() -> None:
    with pytest.raises(
        ValidationError, match="scene_word_target_floor must be at least 1"
    ):
        GenerationSettings(scene_word_target_floor=0)


def test_ceiling_below_floor_raises_value_error() -> None:
    with pytest.raises(
        ValidationError,
        match="scene_word_target_ceiling must be >= scene_word_target_floor",
    ):
        GenerationSettings(scene_word_target_floor=1000, scene_word_target_ceiling=500)
