"""Verification tests for Issue #13 — critique-runner Tool.

Confirms the CLI tool (src/tools/critique_runner.py) correctly handles
parse-scores, should-refine, generate-feedback, and error paths.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_SCRIPT = str(PROJECT_ROOT / "src" / "tools" / "critique_runner.py")

CRITIC_TYPES = [
    "audiobook-producer",
    "book-club-moderator",
    "commercial-fiction-editor",
    "literary-fiction-reviewer",
    "publishing-acquisitions-editor",
    "subject-expert",
]


@pytest.fixture()
def story_env(tmp_path: Path) -> tuple[Path, str]:
    """Provide a temp stories directory with a pre-created story."""
    stories_dir = tmp_path / "stories"
    story_name = "test-story"
    (stories_dir / story_name / "savepoints").mkdir(parents=True)
    (stories_dir / story_name / "state.json").write_text('{"story_name": "test-story"}')
    return stories_dir, story_name


def _run_tool(
    *args: str, stories_dir: Path | None = None
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ}
    if stories_dir is not None:
        env["STORIES_DIR"] = str(stories_dir)
    return subprocess.run(
        [sys.executable, TOOL_SCRIPT, *args],
        capture_output=True,
        text=True,
        env=env,
    )


def _write_savepoint(
    stories_dir: Path, story_name: str, step_name: str, data: str | dict
) -> None:
    """Write a savepoint file directly using extension-based repository format."""
    base_path = stories_dir / story_name / "savepoints" / step_name
    base_path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, dict):
        filepath = base_path.with_suffix(".json")
        content = json.dumps(data, indent=2, ensure_ascii=False)
    else:
        filepath = base_path.with_suffix(".md")
        content = data
    filepath.write_text(content, encoding="utf-8")


def _build_critic_response(
    scores: dict[str, tuple[int, int]],
) -> str:
    """Build a well-formed critic response text with ### Criterion (score/max) format."""
    parts = []
    for criterion, (score, max_score) in scores.items():
        parts.append(f"### {criterion} ({score}/{max_score})")
        parts.append(f"Notes on {criterion.lower()}.")
        parts.append("")
    parts.append("### Summary")
    parts.append("Overall good work.")
    return "\n".join(parts)


def _make_critique_results_savepoint(
    stories_dir: Path,
    story_name: str,
    iteration: int,
    overall_scores: dict[str, tuple[int, int]] | None = None,
    overall_average: float | None = None,
) -> None:
    """Write a critique_results_iteration_N savepoint with all 6 critics."""
    if overall_scores is None:
        overall_scores = {
            "Pacing": (12, 15),
            "Details": (13, 15),
            "Flow": (13, 15),
            "Genre": (8, 10),
            "Consistency": (9, 10),
            "Character Arc & Theme": (17, 20),
            "Structure": (13, 15),
        }

    critic_results = []
    for ct in CRITIC_TYPES:
        scores_list = []
        for criterion, (score, max_score) in overall_scores.items():
            scores_list.append(
                {
                    "criterion": criterion,
                    "score": score,
                    "max_score": max_score,
                    "percentage": round((score / max_score) * 100, 1),
                    "notes": f"Notes on {criterion.lower()}",
                }
            )
        critic_overall = sum(s["score"] for s in scores_list)
        critic_results.append(
            {
                "critic_type": ct,
                "scores": scores_list,
                "summary": "Good overall",
                "overall_score": float(critic_overall),
            }
        )

    # Compute average_scores (percentage averages across critics per criterion)
    avg_scores: dict[str, float] = {}
    for criterion in overall_scores:
        percentages = [
            s["percentage"]
            for cr in critic_results
            for s in cr["scores"]
            if s["criterion"] == criterion
        ]
        avg_scores[criterion] = sum(percentages) / len(percentages)

    if overall_average is None:
        overall_average = sum(cr["overall_score"] for cr in critic_results) / len(
            critic_results
        )

    savepoint_data = {
        "iteration": iteration,
        "critic_results": critic_results,
        "average_scores": avg_scores,
        "overall_average": overall_average,
    }

    _write_savepoint(
        stories_dir,
        story_name,
        f"critique_results_iteration_{iteration}",
        savepoint_data,
    )


# ---------------------------------------------------------------------------
# Test 1: parse-scores with valid response
# ---------------------------------------------------------------------------


def test_parse_scores_valid_response() -> None:
    """Well-formed critic response → all 7 criteria extracted with correct percentages."""
    response_text = _build_critic_response(
        {
            "Pacing": (12, 15),
            "Details": (13, 15),
            "Flow": (14, 15),
            "Genre": (8, 10),
            "Consistency": (9, 10),
            "Character Arc & Theme": (17, 20),
            "Structure": (13, 15),
        }
    )
    result = _run_tool(
        "--operation",
        "parse-scores",
        "--critic-type",
        "audiobook-producer",
        "--response-text",
        response_text,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    out = json.loads(result.stdout)
    assert out["status"] == "success"
    assert out["operation"] == "parse-scores"

    scores = out["data"]["scores"]
    assert len(scores) == 7

    expected = {
        "Pacing": (12, 15, 80.0),
        "Details": (13, 15, 86.67),
        "Flow": (14, 15, 93.33),
        "Genre": (8, 10, 80.0),
        "Consistency": (9, 10, 90.0),
        "Character Arc & Theme": (17, 20, 85.0),
        "Structure": (13, 15, 86.67),
    }
    for s in scores:
        exp = expected[s["criterion"]]
        assert s["score"] == exp[0]
        assert s["max_score"] == exp[1]
        assert abs(s["percentage"] - exp[2]) < 0.1


# ---------------------------------------------------------------------------
# Test 2: parse-scores with malformed response
# ---------------------------------------------------------------------------


def test_parse_scores_malformed_response() -> None:
    """Garbled/empty text → graceful handling, no crash, zero or missing scores."""
    result = _run_tool(
        "--operation",
        "parse-scores",
        "--critic-type",
        "audiobook-producer",
        "--response-text",
        "This is completely garbled nonsense with no score format at all.",
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    out = json.loads(result.stdout)
    assert out["status"] == "success"
    # Parser should return result with no extracted scores
    scores = out["data"]["scores"]
    assert isinstance(scores, list)
    assert len(scores) == 0
    assert out["data"]["overall_score"] == 0.0


# ---------------------------------------------------------------------------
# Test 3: should-refine below threshold
# ---------------------------------------------------------------------------


def test_should_refine_below_threshold(story_env: tuple[Path, str]) -> None:
    """Low scores (below 85 overall) → should_refine: true."""
    stories_dir, name = story_env
    # Use low scores (~60-70% of max)
    _make_critique_results_savepoint(
        stories_dir,
        name,
        iteration=1,
        overall_scores={
            "Pacing": (9, 15),
            "Details": (10, 15),
            "Flow": (9, 15),
            "Genre": (6, 10),
            "Consistency": (6, 10),
            "Character Arc & Theme": (12, 20),
            "Structure": (9, 15),
        },
    )
    result = _run_tool(
        "--operation",
        "should-refine",
        "--name",
        name,
        "--iteration",
        "1",
        stories_dir=stories_dir,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    out = json.loads(result.stdout)
    assert out["status"] == "success"
    assert out["data"]["should_refine"] is True


# ---------------------------------------------------------------------------
# Test 4: should-refine above threshold
# ---------------------------------------------------------------------------


def test_should_refine_above_threshold(story_env: tuple[Path, str]) -> None:
    """High scores (above 85 overall, all criteria above 75%) → should_refine: false."""
    stories_dir, name = story_env
    _make_critique_results_savepoint(
        stories_dir,
        name,
        iteration=1,
        overall_scores={
            "Pacing": (14, 15),
            "Details": (14, 15),
            "Flow": (14, 15),
            "Genre": (9, 10),
            "Consistency": (9, 10),
            "Character Arc & Theme": (18, 20),
            "Structure": (14, 15),
        },
    )
    result = _run_tool(
        "--operation",
        "should-refine",
        "--name",
        name,
        "--iteration",
        "1",
        stories_dir=stories_dir,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    out = json.loads(result.stdout)
    assert out["status"] == "success"
    assert out["data"]["should_refine"] is False


# ---------------------------------------------------------------------------
# Test 5: should-refine with custom threshold
# ---------------------------------------------------------------------------


def test_should_refine_custom_threshold(story_env: tuple[Path, str]) -> None:
    """Same high scores but --quality-threshold 95 → should_refine: true (92 < 95)."""
    stories_dir, name = story_env
    _make_critique_results_savepoint(
        stories_dir,
        name,
        iteration=1,
        overall_scores={
            "Pacing": (14, 15),
            "Details": (14, 15),
            "Flow": (14, 15),
            "Genre": (9, 10),
            "Consistency": (9, 10),
            "Character Arc & Theme": (18, 20),
            "Structure": (14, 15),
        },
    )
    result = _run_tool(
        "--operation",
        "should-refine",
        "--name",
        name,
        "--iteration",
        "1",
        "--quality-threshold",
        "95.0",
        stories_dir=stories_dir,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    out = json.loads(result.stdout)
    assert out["status"] == "success"
    assert out["data"]["should_refine"] is True
    assert out["data"]["threshold"] == 95.0


# ---------------------------------------------------------------------------
# Test 6: generate-feedback output format
# ---------------------------------------------------------------------------


def test_generate_feedback_output_format(story_env: tuple[Path, str]) -> None:
    """generate-feedback → markdown sections for each of the 6 critics."""
    stories_dir, name = story_env
    _make_critique_results_savepoint(stories_dir, name, iteration=1)

    result = _run_tool(
        "--operation",
        "generate-feedback",
        "--name",
        name,
        "--iteration",
        "1",
        stories_dir=stories_dir,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    out = json.loads(result.stdout)
    assert out["status"] == "success"
    assert out["operation"] == "generate-feedback"

    feedback = out["data"]["feedback"]
    assert isinstance(feedback, str)

    # Each critic type should appear as a section heading
    for ct in CRITIC_TYPES:
        heading = ct.replace("-", " ").title()
        assert heading in feedback, f"Missing section for {ct}"


# ---------------------------------------------------------------------------
# Test 7: run-critics with missing story
# ---------------------------------------------------------------------------


def test_run_critics_missing_story(story_env: tuple[Path, str]) -> None:
    """run-critics with nonexistent story name → error exit code and stderr message."""
    stories_dir, _ = story_env
    result = _run_tool(
        "--operation",
        "run-critics",
        "--name",
        "nonexistent-story",
        stories_dir=stories_dir,
    )
    assert result.returncode != 0
    assert (
        "not initialized" in result.stderr.lower()
        or "not found" in result.stderr.lower()
    )


# ---------------------------------------------------------------------------
# Test 8: run-critics with missing outline
# ---------------------------------------------------------------------------


def test_run_critics_missing_outline(story_env: tuple[Path, str]) -> None:
    """Valid story dir but no outline savepoint → error about missing outline."""
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "run-critics",
        "--name",
        name,
        stories_dir=stories_dir,
    )
    assert result.returncode != 0
    assert "outline" in result.stderr.lower()


# ---------------------------------------------------------------------------
# Test 9: parse-scores missing required args
# ---------------------------------------------------------------------------


def test_parse_scores_missing_args() -> None:
    """parse-scores without --critic-type or --response-text → exit code 2."""
    # Missing --critic-type
    result_no_type = _run_tool(
        "--operation",
        "parse-scores",
        "--response-text",
        "some text",
    )
    assert result_no_type.returncode == 2

    # Missing --response-text
    result_no_text = _run_tool(
        "--operation",
        "parse-scores",
        "--critic-type",
        "audiobook-producer",
    )
    assert result_no_text.returncode == 2


# ---------------------------------------------------------------------------
# Test 10: invalid operation
# ---------------------------------------------------------------------------


def test_invalid_operation() -> None:
    """Invalid operation name → argparse error (exit code 2)."""
    result = _run_tool("--operation", "bogus-operation")
    assert result.returncode == 2
    assert "invalid choice" in result.stderr.lower()
