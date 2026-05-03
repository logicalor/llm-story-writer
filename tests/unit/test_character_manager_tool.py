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
from unittest.mock import patch

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
        "abridged": "Abridged version.",
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
    assert loaded["abridged"] == "Abridged version."
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


def test_generate_abridged_data_escape_hatch(story_env: tuple[Path, str]) -> None:
    """generate-abridged --data stores content directly to the abridged field."""
    stories_dir, name = story_env
    sheet_data = {"sheet": "Alice sheet content.", "summary": ""}
    _run_tool(
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

    abridged_text = "Alice is a warrior. Short and sweet."
    abr_result = _run_tool(
        "--operation",
        "generate-abridged",
        "--name",
        name,
        "--character",
        "Alice",
        "--data",
        abridged_text,
        stories_dir=stories_dir,
    )
    assert abr_result.returncode == 0, f"stderr: {abr_result.stderr}"

    load_result = _run_tool(
        "--operation",
        "load-sheet",
        "--name",
        name,
        "--character",
        "Alice",
        stories_dir=stories_dir,
    )
    loaded = json.loads(load_result.stdout)
    assert loaded["abridged"] == abridged_text


def test_generate_abridged_requires_story_elements_when_no_data(
    story_env: tuple[Path, str],
) -> None:
    """generate-abridged without --data requires story_elements savepoint."""
    stories_dir, name = story_env
    sheet_data = {"sheet": "Alice sheet content.", "summary": ""}
    _run_tool(
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

    abr_result = _run_tool(
        "--operation",
        "generate-abridged",
        "--name",
        name,
        "--character",
        "Alice",
        stories_dir=stories_dir,
    )
    assert abr_result.returncode == 1
    assert "story_elements" in abr_result.stderr


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
    # Without --data and without a story_elements savepoint, tool exits 1
    # with a descriptive error (not argparse exit 2, since --data is optional).
    assert result.returncode == 1
    assert "story_elements" in result.stderr


def test_generate_chunks_requires_sheet(story_env: tuple[Path, str]) -> None:
    """generate-chunks fails with clear error when sheet is missing."""
    stories_dir, name = story_env
    # Create a character with empty sheet
    sheet_data = {"sheet": "", "summary": ""}
    _run_tool(
        "--operation",
        "generate-sheet",
        "--name",
        name,
        "--character",
        "Empty",
        "--data",
        json.dumps(sheet_data),
        stories_dir=stories_dir,
    )
    result = _run_tool(
        "--operation",
        "generate-chunks",
        "--name",
        name,
        "--character",
        "Empty",
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
    assert "generate-sheet" in result.stderr


def test_generate_chunks_missing_character(story_env: tuple[Path, str]) -> None:
    """generate-chunks fails cleanly for nonexistent character."""
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "generate-chunks",
        "--name",
        name,
        "--character",
        "Ghost",
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
    assert "not found" in result.stderr.lower()


def test_generate_sheet_initialises_abridged_field(story_env: tuple[Path, str]) -> None:
    """generate-sheet --data initialises the abridged field in the stored JSON."""
    stories_dir, name = story_env
    sheet_data = {"sheet": "Alice sheet.", "summary": "Short.", "abridged": "Compact."}
    _run_tool(
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
    load_result = _run_tool(
        "--operation",
        "load-sheet",
        "--name",
        name,
        "--character",
        "Alice",
        stories_dir=stories_dir,
    )
    loaded = json.loads(load_result.stdout)
    assert "abridged" in loaded
    assert loaded["abridged"] == "Compact."


def test_extract_names_double_wrapped_json(story_env: tuple[Path, str]) -> None:
    stories_dir, story_name = story_env
    inner = json.dumps(["Alice", "Bob"])
    data = json.dumps(inner)  # double-wrapped
    result = _run_tool(
        "--operation",
        "extract-names",
        "--name",
        story_name,
        "--data",
        data,
        stories_dir=stories_dir,
    )
    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    assert parsed["names"] == ["Alice", "Bob"]


def test_atomic_write_no_double_close_on_replace_failure(tmp_path: Path) -> None:
    """Verify os.close called exactly once when os.replace fails (Issue #37)."""
    from tools._io import _atomic_write

    target = tmp_path / "output.json"
    fake_fd = 42
    fake_tmp = str(tmp_path / "tmpXXXXXX.tmp")

    with (
        patch(
            "tools._io.tempfile.mkstemp",
            return_value=(fake_fd, fake_tmp),
        ),
        patch("tools._io.os.write"),
        patch("tools._io.os.close") as mock_close,
        patch(
            "tools._io.os.replace",
            side_effect=OSError("replace failed"),
        ),
        patch("tools._io.os.unlink") as mock_unlink,
    ):
        with pytest.raises(OSError, match="replace failed"):
            _atomic_write(target, "test content")

        # os.close called exactly once — not double-closed
        mock_close.assert_called_once_with(fake_fd)
        # Temp file cleaned up
        mock_unlink.assert_called_once_with(fake_tmp)


def test_atomic_write_unlink_failure_preserves_original_error(tmp_path: Path) -> None:
    """Verify original error propagates when os.unlink also fails (Issue #39)."""
    from tools._io import _atomic_write

    target = tmp_path / "output.json"
    fake_fd = 42
    fake_tmp = str(tmp_path / "tmpXXXXXX.tmp")

    with (
        patch(
            "tools._io.tempfile.mkstemp",
            return_value=(fake_fd, fake_tmp),
        ),
        patch("tools._io.os.write"),
        patch("tools._io.os.close"),
        patch(
            "tools._io.os.replace",
            side_effect=OSError("replace failed"),
        ),
        patch(
            "tools._io.os.unlink",
            side_effect=FileNotFoundError("tmp already gone"),
        ),
    ):
        with pytest.raises(OSError, match="replace failed"):
            _atomic_write(target, "test content")
