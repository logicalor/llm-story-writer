"""Tests for issue #422: scene critic ensemble."""

import pytest

from src.domain.value_objects.generation_settings import GenerationSettings
from src.tools.critique_parser import CritiqueParser


class TestSceneCritiqueEnsembleSettings:
    def test_default_critics_list_has_one_entry(self):
        settings = GenerationSettings()
        assert settings.scene_critique_critics == ["scene-default"]

    def test_multiple_critics_accepted(self):
        settings = GenerationSettings(
            scene_critique_critics=["scene-default", "commercial-fiction-editor"]
        )
        assert len(settings.scene_critique_critics) == 2

    def test_empty_critics_list_raises_validation_error(self):
        from src.domain.exceptions import ValidationError

        with pytest.raises(ValidationError):
            GenerationSettings(scene_critique_critics=[])

    def test_single_custom_critic_accepted(self):
        settings = GenerationSettings(
            scene_critique_critics=["literary-fiction-reviewer"]
        )
        assert settings.scene_critique_critics == ["literary-fiction-reviewer"]

    def test_to_dict_includes_critics(self):
        settings = GenerationSettings(
            scene_critique_critics=["scene-default", "commercial-fiction-editor"]
        )
        d = settings.to_dict()
        assert d["scene_critique_critics"] == [
            "scene-default",
            "commercial-fiction-editor",
        ]

    def test_from_dict_roundtrip(self):
        original = GenerationSettings(
            scene_critique_critics=["scene-default", "literary-fiction-reviewer"]
        )
        d = original.to_dict()
        restored = GenerationSettings.from_dict(d)
        assert restored.scene_critique_critics == original.scene_critique_critics


class TestEnsembleScoreAggregation:
    """Tests for the two-critic ensemble aggregation (AC#6).

    AC#6: Unit test: two-critic ensemble; verify aggregated score is average of both.

    Score calculation:
      - 4 categories, 25 points each → max 100
      - deduction_per_finding = 8; raw = max(0, 25 - n*8)
      - "{}" → all categories clean → overall = 100.0
      - 1 finding each in all 4 categories → raw = 17 each → overall = 68.0
      - 1 finding in outline_adherence only → overall = 17+25+25+25 = 92.0
      - 2 findings in style_violations only → raw = max(0,25-16)=9 → overall = 25+25+25+9 = 84.0
    """

    def test_two_critic_average_score(self):
        """Two critics with known scores: aggregate equals arithmetic mean."""
        parser = CritiqueParser()
        # Critic 1: all categories clean → score 100
        response_100 = "{}"
        # Critic 2: one finding in each of 4 categories → raw=17 each → overall=68
        response_68 = (
            '{"outline_adherence": ["missing A"], "pov_consistency": ["shift B"],'
            ' "continuity": ["break C"], "style_violations": ["purple D"]}'
        )

        result_100 = parser.parse_scene_critique(response_100)
        result_68 = parser.parse_scene_critique(response_68)

        assert result_100.overall_score == 100.0
        assert result_68.overall_score == 68.0

        average = parser.get_overall_average_score([result_100, result_68])
        assert average == pytest.approx((100.0 + 68.0) / 2)  # 84.0

    def test_three_critics_average_score(self):
        """Three critics: aggregate equals arithmetic mean of all three."""
        parser = CritiqueParser()
        # r1: all clean → 100.0
        r1 = parser.parse_scene_critique("{}")
        # r2: 1 finding in outline_adherence → 17+25+25+25 = 92.0
        r2 = parser.parse_scene_critique('{"outline_adherence": ["issue1"]}')
        # r3: 2 findings in style_violations → 25+25+25+9 = 84.0
        r3 = parser.parse_scene_critique('{"style_violations": ["issue1", "issue2"]}')

        assert r1.overall_score == pytest.approx(100.0)
        assert r2.overall_score == pytest.approx(92.0)
        assert r3.overall_score == pytest.approx(84.0)

        expected = (100.0 + 92.0 + 84.0) / 3
        actual = parser.get_overall_average_score([r1, r2, r3])
        assert actual == pytest.approx(expected)

    def test_single_critic_no_aggregation_needed(self):
        """Single-entry list: overall_average_score equals single result score."""
        parser = CritiqueParser()
        result = parser.parse_scene_critique("{}")
        assert parser.get_overall_average_score([result]) == result.overall_score

    def test_get_average_scores_per_criterion_two_critics(self):
        """Per-criterion averages computed correctly across two critics."""
        parser = CritiqueParser()
        # r1: outline_adherence has 1 finding → raw=17, pct=68%; others pct=100%
        r1 = parser.parse_scene_critique('{"outline_adherence": ["issue"]}')
        # r2: all clean → all pct=100%
        r2 = parser.parse_scene_critique("{}")

        averages = parser.get_average_scores([r1, r2])

        # outline_adherence: (68 + 100) / 2 = 84.0
        assert averages["outline_adherence"] == pytest.approx(84.0)
        # others: (100 + 100) / 2 = 100.0
        assert averages["pov_consistency"] == pytest.approx(100.0)
        assert averages["continuity"] == pytest.approx(100.0)
        assert averages["style_violations"] == pytest.approx(100.0)
