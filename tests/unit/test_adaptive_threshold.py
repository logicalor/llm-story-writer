"""Verification tests for adaptive quality thresholds (#421)."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from domain.value_objects.generation_settings import GenerationSettings
from tools.adaptive_threshold import compute_effective_threshold


def _settings(**overrides: object) -> GenerationSettings:
    base = {
        "scene_critique_score_threshold": 80.0,
        "scene_critique_threshold_mode": "fixed",
        "scene_critique_adaptive_slack": 10.0,
    }
    base.update(overrides)
    return GenerationSettings(**base)


def test_fixed_mode_returns_threshold_unchanged() -> None:
    settings = _settings(scene_critique_threshold_mode="fixed")

    assert (
        compute_effective_threshold(
            settings, chapter_number=5, style_notes_first_chapter=10
        )
        == 80.0
    )


def test_adaptive_chapter_1_uses_floor() -> None:
    settings = _settings(
        scene_critique_threshold_mode="adaptive",
        scene_critique_score_threshold=80.0,
        scene_critique_adaptive_slack=10.0,
    )

    assert (
        compute_effective_threshold(
            settings, chapter_number=1, style_notes_first_chapter=10
        )
        == 70.0
    )


def test_adaptive_chapter_equals_n_uses_threshold() -> None:
    settings = _settings(scene_critique_threshold_mode="adaptive")

    assert (
        compute_effective_threshold(
            settings, chapter_number=10, style_notes_first_chapter=10
        )
        == 80.0
    )


def test_adaptive_chapter_5_linear_ramp() -> None:
    settings = _settings(
        scene_critique_threshold_mode="adaptive",
        scene_critique_score_threshold=80.0,
        scene_critique_adaptive_slack=10.0,
    )

    assert compute_effective_threshold(
        settings, chapter_number=5, style_notes_first_chapter=10
    ) == pytest.approx(
        74.44,
        abs=0.01,
    )


def test_adaptive_chapter_10_linear_ramp() -> None:
    settings = _settings(
        scene_critique_threshold_mode="adaptive",
        scene_critique_score_threshold=80.0,
        scene_critique_adaptive_slack=10.0,
    )

    assert (
        compute_effective_threshold(
            settings, chapter_number=10, style_notes_first_chapter=10
        )
        == 80.0
    )


def test_adaptive_style_notes_none_returns_floor() -> None:
    settings = _settings(
        scene_critique_threshold_mode="adaptive",
        scene_critique_score_threshold=80.0,
        scene_critique_adaptive_slack=10.0,
    )

    assert (
        compute_effective_threshold(
            settings, chapter_number=3, style_notes_first_chapter=None
        )
        == 70.0
    )


def test_adaptive_chapter_beyond_n_clamped_to_threshold() -> None:
    settings = _settings(scene_critique_threshold_mode="adaptive")

    assert (
        compute_effective_threshold(
            settings, chapter_number=15, style_notes_first_chapter=10
        )
        == 80.0
    )


def test_adaptive_style_notes_first_chapter_1_returns_threshold() -> None:
    settings = _settings(scene_critique_threshold_mode="adaptive")

    assert (
        compute_effective_threshold(
            settings, chapter_number=1, style_notes_first_chapter=1
        )
        == 80.0
    )


def test_fixed_mode_ignores_slack() -> None:
    settings = _settings(
        scene_critique_threshold_mode="fixed",
        scene_critique_score_threshold=80.0,
        scene_critique_adaptive_slack=50.0,
    )

    assert (
        compute_effective_threshold(
            settings, chapter_number=1, style_notes_first_chapter=None
        )
        == 80.0
    )
