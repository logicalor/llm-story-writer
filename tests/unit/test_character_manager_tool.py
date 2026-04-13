"""Verification tests for Issue #6 — character-mgr Tool.

Confirms the CLI tool (src/tools/character_manager.py) correctly manages
story character sheets: extract-names, generate-sheet, update-sheet,
load-sheet, list, and generate-abridged operations.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_SCRIPT = str(PROJECT_ROOT / "src" / "tools" / "character_manager.py")


@pytest.fixture()
def story_env(tmp_path: Path) -> tuple[Path, str]:
    """Provide a temp stories directory with a pre-created story."""
    stories_dir = tmp_path / "stories"
    story_name = "test-story"
    (stories_dir / story_name / "characters").mkdir(parents=True)
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


def test_generate_sheet_round_trip(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    sheet_data = {
        "sheet": "Alice is a brave warrior from the northern lands.",
        "chunks": {
            "background": "Grew up in the north.",
            "personality": "Brave and loyal.",
            "appearance": "Tall with red hair.",
            "skills": "Sword fighting.",
            "relationships": "Best friend of Bob.",
            "goals": "Defeat the dark lord.",
            "flaws": "Impulsive.",
        },
        "summary": "Alice is a brave warrior.",
    }
    gen_result = _run_tool(
        "--operation",
        "generate-sheet",
        "--name",
        name,
        "--character",
        "Alice",
        "--data",
        json.dumps(sheet_data),
        stories_dir=stories_dir,
    )
    assert gen_result.returncode == 0, f"stderr: {gen_result.stderr}"
    gen_out = json.loads(gen_result.stdout)
    assert gen_out["status"] == "ok"

    load_result = _run_tool(
        "--operation",
        "load-sheet",
        "--name",
        name,
        "--character",
        "Alice",
        stories_dir=stories_dir,
    )
    assert load_result.returncode == 0, f"stderr: {load_result.stderr}"
    loaded = json.loads(load_result.stdout)
    assert loaded["name"] == "Alice"
    assert loaded["sheet"] == sheet_data["sheet"]
    assert loaded["summary"] == sheet_data["summary"]
    assert loaded["chunks"] == sheet_data["chunks"]
    assert "updated_at" in loaded


def test_update_sheet_merges_chunks(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    initial = {
        "sheet": "Some sheet text.",
        "chunks": {"background": "old bg", "personality": "old pers"},
        "summary": "Short summary.",
    }
    _run_tool(
        "--operation",
        "generate-sheet",
        "--name",
        name,
        "--character",
        "Merge Test",
        "--data",
        json.dumps(initial),
        stories_dir=stories_dir,
    )

    update_data = {"chunks": {"background": "new bg", "skills": "new skills"}}
    upd_result = _run_tool(
        "--operation",
        "update-sheet",
        "--name",
        name,
        "--character",
        "Merge Test",
        "--data",
        json.dumps(update_data),
        stories_dir=stories_dir,
    )
    assert upd_result.returncode == 0, f"stderr: {upd_result.stderr}"

    load_result = _run_tool(
        "--operation",
        "load-sheet",
        "--name",
        name,
        "--character",
        "Merge Test",
        stories_dir=stories_dir,
    )
    assert load_result.returncode == 0, f"stderr: {load_result.stderr}"
    loaded = json.loads(load_result.stdout)
    assert loaded["chunks"]["background"] == "new bg"
    assert loaded["chunks"]["personality"] == "old pers"
    assert loaded["chunks"]["skills"] == "new skills"


def test_load_sheet_abridged(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    sheet_data = {
        "sheet": "Full sheet with lots of detail.",
        "chunks": {"background": "Some background."},
        "summary": "Short summary.",
    }
    _run_tool(
        "--operation",
        "generate-sheet",
        "--name",
        name,
        "--character",
        "Abridged",
        "--data",
        json.dumps(sheet_data),
        stories_dir=stories_dir,
    )

    load_result = _run_tool(
        "--operation",
        "load-sheet",
        "--name",
        name,
        "--character",
        "Abridged",
        "--abridged",
        stories_dir=stories_dir,
    )
    assert load_result.returncode == 0, f"stderr: {load_result.stderr}"
    loaded = json.loads(load_result.stdout)
    assert loaded["name"] == "Abridged"
    assert loaded["summary"] == "Short summary."
    assert "updated_at" in loaded
    assert "sheet" not in loaded
    assert "chunks" not in loaded


def test_list_characters(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    for char_name in ("Alice", "Bob"):
        _run_tool(
            "--operation",
            "generate-sheet",
            "--name",
            name,
            "--character",
            char_name,
            "--data",
            json.dumps(
                {"sheet": f"{char_name} sheet.", "summary": f"{char_name} summary."}
            ),
            stories_dir=stories_dir,
        )

    list_result = _run_tool(
        "--operation",
        "list",
        "--name",
        name,
        stories_dir=stories_dir,
    )
    assert list_result.returncode == 0, f"stderr: {list_result.stderr}"
    out = json.loads(list_result.stdout)
    assert set(out["characters"]) == {"Alice", "Bob"}


def test_extract_names_parses_json(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "extract-names",
        "--name",
        name,
        "--data",
        '["Alice", "Bob", "Charlie"]',
        stories_dir=stories_dir,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    out = json.loads(result.stdout)
    assert out == {"names": ["Alice", "Bob", "Charlie"]}


def test_generate_abridged_truncation(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    long_sheet = " ".join(f"word{i}" for i in range(600))
    sheet_data = {"sheet": long_sheet, "summary": ""}
    _run_tool(
        "--operation",
        "generate-sheet",
        "--name",
        name,
        "--character",
        "Verbose",
        "--data",
        json.dumps(sheet_data),
        stories_dir=stories_dir,
    )

    abr_result = _run_tool(
        "--operation",
        "generate-abridged",
        "--name",
        name,
        "--character",
        "Verbose",
        "--budget",
        "100",
        stories_dir=stories_dir,
    )
    assert abr_result.returncode == 0, f"stderr: {abr_result.stderr}"

    load_result = _run_tool(
        "--operation",
        "load-sheet",
        "--name",
        name,
        "--character",
        "Verbose",
        stories_dir=stories_dir,
    )
    loaded = json.loads(load_result.stdout)
    word_count = len(loaded["summary"].split())
    assert word_count <= 75, f"Expected ≤75 words, got {word_count}"


def test_path_traversal_story_name_blocked(story_env: tuple[Path, str]) -> None:
    stories_dir, _ = story_env
    result = _run_tool(
        "--operation",
        "list",
        "--name",
        "../etc/passwd",
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
    assert "escapes" in result.stderr.lower()


def test_path_traversal_character_name_blocked(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "load-sheet",
        "--name",
        name,
        "--character",
        "../../../etc/passwd",
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
    assert (
        "must not contain" in result.stderr.lower()
        or "escapes" in result.stderr.lower()
    )


def test_missing_character_returns_error(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "load-sheet",
        "--name",
        name,
        "--character",
        "Nonexistent",
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
    assert "not found" in result.stderr.lower()


def test_missing_required_args(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "generate-sheet",
        "--name",
        name,
        "--character",
        "Test",
        stories_dir=stories_dir,
    )
    assert result.returncode == 2
