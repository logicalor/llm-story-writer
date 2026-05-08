"""Verification tests for scene critique scoring in CritiqueParser."""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from tools.critique_parser import CritiqueParser, passed_quality_threshold


def _score_by_criterion(parser_result: object) -> dict[str, float]:
    return {score.criterion: score.score for score in parser_result.scores}


def test_parse_scene_critique_empty_json_returns_full_score() -> None:
    parser = CritiqueParser()

    result = parser.parse_scene_critique("{}")

    assert result.overall_score == 100.0
    assert _score_by_criterion(result) == {
        "outline_adherence": 25.0,
        "pov_consistency": 25.0,
        "continuity": 25.0,
        "style_violations": 25.0,
    }


def test_parse_scene_critique_single_finding_deducts_correctly() -> None:
    parser = CritiqueParser()

    result = parser.parse_scene_critique(
        json.dumps({"outline_adherence": ["missing beat"]})
    )

    assert result.overall_score == 92.0
    assert _score_by_criterion(result)["outline_adherence"] == 17.0


def test_parse_scene_critique_multiple_findings_deduct_correctly() -> None:
    parser = CritiqueParser()

    result = parser.parse_scene_critique(json.dumps({"outline_adherence": ["x", "y"]}))

    assert result.overall_score == 84.0
    assert _score_by_criterion(result)["outline_adherence"] == 9.0


def test_parse_scene_critique_findings_capped_at_zero_per_category() -> None:
    parser = CritiqueParser()

    result = parser.parse_scene_critique(
        json.dumps({"outline_adherence": ["x", "y", "z", "w"]})
    )

    assert result.overall_score == 75.0
    assert _score_by_criterion(result)["outline_adherence"] == 0.0


def test_parse_scene_critique_all_categories_with_findings() -> None:
    parser = CritiqueParser()

    result = parser.parse_scene_critique(
        json.dumps(
            {
                "outline_adherence": ["x"],
                "pov_consistency": ["x"],
                "continuity": ["x"],
                "style_violations": ["x"],
            }
        )
    )

    assert result.overall_score == 68.0
    assert _score_by_criterion(result) == {
        "outline_adherence": 17.0,
        "pov_consistency": 17.0,
        "continuity": 17.0,
        "style_violations": 17.0,
    }


def test_parse_scene_critique_malformed_json_returns_full_score() -> None:
    parser = CritiqueParser()

    result = parser.parse_scene_critique("not valid json")

    assert result.overall_score == 100.0
    assert all(score.score == 25.0 for score in result.scores)


def test_parse_scene_critique_empty_string_returns_full_score() -> None:
    parser = CritiqueParser()

    result = parser.parse_scene_critique("")

    assert result.overall_score == 100.0
    assert all(score.score == 25.0 for score in result.scores)


def test_parse_scene_critique_returns_scene_critique_type() -> None:
    parser = CritiqueParser()

    result = parser.parse_scene_critique("{}")

    assert result.critic_type == "scene-critique"
    assert result.summary == "Scene critique: 100/100"


def test_passed_quality_threshold_passes_at_threshold() -> None:
    assert passed_quality_threshold(75.0, 75.0) is True


def test_passed_quality_threshold_fails_below_threshold() -> None:
    assert passed_quality_threshold(74.9, 75.0) is False


def test_passed_quality_threshold_default_threshold_is_75() -> None:
    assert passed_quality_threshold(75.0) is True
    assert passed_quality_threshold(74.9) is False


def test_existing_outline_critic_still_works() -> None:
    parser = CritiqueParser()
    response = "\n".join(
        [
            "### Pacing (12/15)",
            "Strong pacing overall.",
            "",
            "### Details (13/15)",
            "Vivid details.",
            "",
            "### Flow (14/15)",
            "Transitions work.",
            "",
            "### Genre (8/10)",
            "Genre fit is clear.",
            "",
            "### Consistency (9/10)",
            "Consistent throughout.",
            "",
            "### Character Arc & Theme (17/20)",
            "Arc lands.",
            "",
            "### Structure (13/15)",
            "Structure is solid.",
            "",
            "### Summary",
            "Overall good work.",
        ]
    )

    result = parser.parse_critique("audiobook-producer", response)

    assert result.critic_type == "audiobook-producer"
    assert len(result.scores) == 7
    assert result.overall_score == 86.0
    assert result.summary == "Overall good work."
