"""Verification tests for Issue #11 — setting-mgr Tool.

Confirms the CLI tool (src/tools/setting_manager.py) correctly manages
story setting sheets: extract-names, generate-sheet, update-sheet,
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
TOOL_SCRIPT = str(PROJECT_ROOT / "src" / "tools" / "setting_manager.py")


@pytest.fixture()
def story_env(tmp_path: Path) -> tuple[Path, str]:
    """Provide a temp stories directory with a pre-created story."""
    stories_dir = tmp_path / "stories"
    story_name = "test-story"
    (stories_dir / story_name / "settings").mkdir(parents=True)
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
        "sheet": "The Whispering Forest is an ancient woodland shrouded in mist.",
        "chunks": {
            "geography": "Dense woodland with towering oaks.",
            "atmosphere": "Perpetual twilight and echoing whispers.",
            "history": "Once a sacred druid grove.",
            "inhabitants": "Woodland creatures and fey spirits.",
            "landmarks": "The Stone Circle at the heart.",
            "dangers": "Shifting paths that confuse travelers.",
            "significance": "Key location for the protagonist's quest.",
        },
        "summary": "The Whispering Forest is an ancient, mist-shrouded woodland.",
    }
    gen_result = _run_tool(
        "--operation",
        "generate-sheet",
        "--name",
        name,
        "--setting",
        "The Whispering Forest",
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
        "--setting",
        "The Whispering Forest",
        stories_dir=stories_dir,
    )
    assert load_result.returncode == 0, f"stderr: {load_result.stderr}"
    loaded = json.loads(load_result.stdout)
    assert loaded["name"] == "The Whispering Forest"
    assert loaded["sheet"] == sheet_data["sheet"]
    assert loaded["summary"] == sheet_data["summary"]
    assert loaded["chunks"] == sheet_data["chunks"]
    assert "updated_at" in loaded


def test_update_sheet_merges_chunks(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    initial = {
        "sheet": "Some sheet text.",
        "chunks": {"geography": "old geo", "atmosphere": "old atmo"},
        "summary": "Short summary.",
    }
    _run_tool(
        "--operation",
        "generate-sheet",
        "--name",
        name,
        "--setting",
        "Merge Test",
        "--data",
        json.dumps(initial),
        stories_dir=stories_dir,
    )

    update_data = {"chunks": {"geography": "new geo", "landmarks": "new landmarks"}}
    upd_result = _run_tool(
        "--operation",
        "update-sheet",
        "--name",
        name,
        "--setting",
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
        "--setting",
        "Merge Test",
        stories_dir=stories_dir,
    )
    assert load_result.returncode == 0, f"stderr: {load_result.stderr}"
    loaded = json.loads(load_result.stdout)
    assert loaded["chunks"]["geography"] == "new geo"
    assert loaded["chunks"]["atmosphere"] == "old atmo"
    assert loaded["chunks"]["landmarks"] == "new landmarks"


def test_load_sheet_abridged(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    sheet_data = {
        "sheet": "Full sheet with lots of detail.",
        "chunks": {"geography": "Some geography."},
        "summary": "Short summary.",
    }
    _run_tool(
        "--operation",
        "generate-sheet",
        "--name",
        name,
        "--setting",
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
        "--setting",
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


def test_list_settings(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    for setting_name in ("Castle Ruins", "Dark Cavern"):
        _run_tool(
            "--operation",
            "generate-sheet",
            "--name",
            name,
            "--setting",
            setting_name,
            "--data",
            json.dumps(
                {
                    "sheet": f"{setting_name} sheet.",
                    "summary": f"{setting_name} summary.",
                }
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
    assert set(out["settings"]) == {"Castle Ruins", "Dark Cavern"}


def test_extract_names_parses_json(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "extract-names",
        "--name",
        name,
        "--data",
        '["Whispering Forest", "Shadow Keep", "Crystal Lake"]',
        stories_dir=stories_dir,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    out = json.loads(result.stdout)
    assert out == {"names": ["Whispering Forest", "Shadow Keep", "Crystal Lake"]}


def test_generate_abridged_truncation(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    long_sheet = " ".join(f"word{i}" for i in range(600))
    sheet_data = {"sheet": long_sheet, "summary": ""}
    _run_tool(
        "--operation",
        "generate-sheet",
        "--name",
        name,
        "--setting",
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
        "--setting",
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
        "--setting",
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


def test_path_traversal_setting_name_blocked(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "load-sheet",
        "--name",
        name,
        "--setting",
        "../../../etc/passwd",
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
    assert (
        "must not contain" in result.stderr.lower()
        or "escapes" in result.stderr.lower()
    )


def test_missing_setting_returns_error(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "load-sheet",
        "--name",
        name,
        "--setting",
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
        "--setting",
        "Test",
        stories_dir=stories_dir,
    )
    assert result.returncode == 2


def test_extract_names_double_wrapped_json(story_env: tuple[Path, str]) -> None:
    stories_dir, story_name = story_env
    inner = json.dumps(["Whispering Forest", "Shadow Keep"])
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
    assert parsed["names"] == ["Whispering Forest", "Shadow Keep"]


def test_atomic_write_no_double_close_on_replace_failure(tmp_path: Path) -> None:
    """Verify os.close called exactly once when os.replace fails (Issue #37)."""
    from src.tools.setting_manager import _atomic_write

    target = tmp_path / "output.json"
    fake_fd = 42
    fake_tmp = str(tmp_path / "tmpXXXXXX.tmp")

    with (
        patch(
            "src.tools.setting_manager.tempfile.mkstemp",
            return_value=(fake_fd, fake_tmp),
        ),
        patch("src.tools.setting_manager.os.write"),
        patch("src.tools.setting_manager.os.close") as mock_close,
        patch(
            "src.tools.setting_manager.os.replace",
            side_effect=OSError("replace failed"),
        ),
        patch("src.tools.setting_manager.os.unlink") as mock_unlink,
    ):
        with pytest.raises(OSError, match="replace failed"):
            _atomic_write(target, "test content")

        # os.close called exactly once — not double-closed
        mock_close.assert_called_once_with(fake_fd)
        # Temp file cleaned up
        mock_unlink.assert_called_once_with(fake_tmp)


def test_atomic_write_unlink_failure_preserves_original_error(tmp_path: Path) -> None:
    """Verify original error propagates when os.unlink also fails (Issue #39)."""
    from src.tools.setting_manager import _atomic_write

    target = tmp_path / "output.json"
    fake_fd = 42
    fake_tmp = str(tmp_path / "tmpXXXXXX.tmp")

    with (
        patch(
            "src.tools.setting_manager.tempfile.mkstemp",
            return_value=(fake_fd, fake_tmp),
        ),
        patch("src.tools.setting_manager.os.write"),
        patch("src.tools.setting_manager.os.close"),
        patch(
            "src.tools.setting_manager.os.replace",
            side_effect=OSError("replace failed"),
        ),
        patch(
            "src.tools.setting_manager.os.unlink",
            side_effect=FileNotFoundError("tmp already gone"),
        ),
    ):
        with pytest.raises(OSError, match="replace failed"):
            _atomic_write(target, "test content")
