import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from presentation.agents.story_planner import _parse_verdict


def test_parse_verdict_strong_arc() -> None:
    assert (
        _parse_verdict(
            "Arc lands cleanly. Stakes escalate with no arc issues keywords."
        )
        == "strong"
    )


def test_parse_verdict_significant_issues() -> None:
    assert _parse_verdict("The middle act has significant issues with escalation.") == (
        "significant_issues"
    )


def test_parse_verdict_negated_significant_no_false_positive() -> None:
    assert _parse_verdict("No significant issues were found in the narrative arc.") == (
        "strong"
    )


def test_parse_verdict_insignificant_no_false_positive() -> None:
    assert _parse_verdict("only insignificant details remain") == "strong"


def test_parse_verdict_minor_concerns() -> None:
    assert _parse_verdict("There are minor concerns about act two pacing") == (
        "minor_concerns"
    )


def test_parse_verdict_concern_keyword() -> None:
    assert (
        _parse_verdict("The main concern is the lack of motivation in act three")
        == "minor_concerns"
    )
