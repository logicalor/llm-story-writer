"""Verification tests for Issue #10 — outline-generator Tool.

Confirms the CLI tool (src/tools/outline_generator.py) correctly handles
error paths, input validation, and the non-LLM generate-elements operation.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_SCRIPT = str(PROJECT_ROOT / "src" / "tools" / "outline_generator.py")

# The 8 analysis chunk types (must match CHUNK_TYPES in outline_generator.py)
CHUNK_TYPES = (
    "core_story_foundation",
    "character_foundation",
    "setting_foundation",
    "plot_structure",
    "theme_message",
    "tone_style",
    "conflict_stakes",
    "world_rules_logic",
)


@pytest.fixture()
def story_env(tmp_path: Path) -> tuple[Path, str]:
    """Provide a temp stories directory with a pre-created story."""
    stories_dir = tmp_path / "stories"
    story_name = "test-story"
    (stories_dir / story_name / "savepoints").mkdir(parents=True)
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
    stories_dir: Path, story_name: str, step_name: str, data: str
) -> None:
    """Write a string savepoint file directly (matches FilesystemSavepointRepository format)."""
    savepoint_dir = stories_dir / story_name / "savepoints"
    if "/" in step_name:
        parts = step_name.split("/")
        filename = parts[-1]
        subdirs = parts[:-1]
        target_dir = savepoint_dir
        for subdir in subdirs:
            target_dir = target_dir / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        filepath = target_dir / f"{filename}.md"
    else:
        filepath = savepoint_dir / f"{step_name}.md"
    filepath.write_text(f"# Savepoint: {step_name}\n\n{data}", encoding="utf-8")


# ---------------------------------------------------------------------------
# Test: missing required arguments
# ---------------------------------------------------------------------------


def test_analyze_prompt_missing_name(story_env: tuple[Path, str]) -> None:
    """Call without --name exits with argparse error code 2."""
    stories_dir, _ = story_env
    result = _run_tool(
        "--operation",
        "analyze-prompt",
        "--prompt",
        "A story about dragons",
        stories_dir=stories_dir,
    )
    assert result.returncode == 2


def test_analyze_prompt_missing_prompt(story_env: tuple[Path, str]) -> None:
    """Call analyze-prompt without --prompt exits with code 2."""
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "analyze-prompt",
        "--name",
        name,
        stories_dir=stories_dir,
    )
    assert result.returncode == 2
    assert "prompt" in result.stderr.lower()


# ---------------------------------------------------------------------------
# Test: missing savepoints for dependent operations
# ---------------------------------------------------------------------------


def test_generate_elements_missing_savepoints(story_env: tuple[Path, str]) -> None:
    """generate-elements without analysis chunks exits 1 with missing chunk message."""
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "generate-elements",
        "--name",
        name,
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
    assert "missing chunk savepoint" in result.stderr.lower()


def test_generate_outline_missing_savepoints(story_env: tuple[Path, str]) -> None:
    """generate-outline without story_elements exits 1."""
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "generate-outline",
        "--name",
        name,
        "--desired-chapters",
        "10",
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
    assert "story_elements" in result.stderr.lower()


def test_expand_chapter_missing_savepoints(story_env: tuple[Path, str]) -> None:
    """expand-chapter without story_elements exits 1."""
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "expand-chapter",
        "--name",
        name,
        "--chunk-start",
        "1",
        "--chunk-end",
        "5",
        "--total-chapters",
        "20",
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
    assert "story_elements" in result.stderr.lower()


def test_refine_missing_savepoints(story_env: tuple[Path, str]) -> None:
    """refine without initial_outline exits 1."""
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "refine",
        "--name",
        name,
        "--feedback",
        "Add more conflict",
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
    assert "initial_outline" in result.stderr.lower()


# ---------------------------------------------------------------------------
# Test: generate-elements (non-LLM, fully testable)
# ---------------------------------------------------------------------------


def test_generate_elements_with_savepoints(story_env: tuple[Path, str]) -> None:
    """Pre-populate 8 chunk savepoints, call generate-elements, verify concatenated output."""
    stories_dir, name = story_env

    # Write all 8 chunk savepoints
    for chunk_type in CHUNK_TYPES:
        step = f"story_analysis/{chunk_type}_chunk"
        _write_savepoint(stories_dir, name, step, f"Content for {chunk_type} analysis.")

    result = _run_tool(
        "--operation",
        "generate-elements",
        "--name",
        name,
        stories_dir=stories_dir,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    out = json.loads(result.stdout)

    # All 8 chunks should be concatenated in story_elements
    story_elements = out["data"]["story_elements"]
    for chunk_type in CHUNK_TYPES:
        header = chunk_type.replace("_", " ").title()
        assert f"=== {header} ===" in story_elements
        assert f"Content for {chunk_type} analysis." in story_elements


def test_generate_elements_output_format(story_env: tuple[Path, str]) -> None:
    """Verify output is valid JSON with status, operation, data keys."""
    stories_dir, name = story_env

    # Write all 8 chunk savepoints
    for chunk_type in CHUNK_TYPES:
        step = f"story_analysis/{chunk_type}_chunk"
        _write_savepoint(stories_dir, name, step, f"Chunk {chunk_type}")

    result = _run_tool(
        "--operation",
        "generate-elements",
        "--name",
        name,
        stories_dir=stories_dir,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    out = json.loads(result.stdout)
    assert "status" in out
    assert "operation" in out
    assert "data" in out
    assert out["status"] == "success"
    assert out["operation"] == "generate-elements"


# ---------------------------------------------------------------------------
# Test: input validation
# ---------------------------------------------------------------------------


def test_invalid_story_name_path_traversal(story_env: tuple[Path, str]) -> None:
    """Path traversal attempt (../evil) exits 1."""
    stories_dir, _ = story_env
    result = _run_tool(
        "--operation",
        "generate-elements",
        "--name",
        "../evil",
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
    assert "escapes" in result.stderr.lower()


def test_invalid_operation(story_env: tuple[Path, str]) -> None:
    """Unknown operation exits 2 (argparse choices validation)."""
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "invalid",
        "--name",
        name,
        stories_dir=stories_dir,
    )
    assert result.returncode == 2
