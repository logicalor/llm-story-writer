"""Verification tests for Issue #7 — savepoint-mgr Tool.

Confirms the CLI tool (src/tools/savepoint_manager.py) correctly manages
story savepoints: save, load, has, list, and clear operations.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_SCRIPT = str(PROJECT_ROOT / "src" / "tools" / "savepoint_manager.py")


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


def test_save_and_load_string(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    save_result = _run_tool(
        "--operation",
        "save",
        "--name",
        name,
        "--step",
        "greeting",
        "--data",
        '"hello world"',
        stories_dir=stories_dir,
    )
    assert save_result.returncode == 0, f"stderr: {save_result.stderr}"
    save_out = json.loads(save_result.stdout)
    assert save_out["status"] == "saved"

    load_result = _run_tool(
        "--operation",
        "load",
        "--name",
        name,
        "--step",
        "greeting",
        stories_dir=stories_dir,
    )
    assert load_result.returncode == 0, f"stderr: {load_result.stderr}"
    load_out = json.loads(load_result.stdout)
    assert load_out["step"] == "greeting"
    assert load_out["data"] == "hello world"


def test_save_and_load_dict(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    payload = {"title": "Chapter One", "word_count": 500}
    save_result = _run_tool(
        "--operation",
        "save",
        "--name",
        name,
        "--step",
        "chapter_meta",
        "--data",
        json.dumps(payload),
        stories_dir=stories_dir,
    )
    assert save_result.returncode == 0, f"stderr: {save_result.stderr}"

    load_result = _run_tool(
        "--operation",
        "load",
        "--name",
        name,
        "--step",
        "chapter_meta",
        stories_dir=stories_dir,
    )
    assert load_result.returncode == 0, f"stderr: {load_result.stderr}"
    load_out = json.loads(load_result.stdout)
    assert load_out["step"] == "chapter_meta"
    assert load_out["data"] == payload


def test_has_existing_step(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    _run_tool(
        "--operation",
        "save",
        "--name",
        name,
        "--step",
        "chapter_1",
        "--data",
        '"some data"',
        stories_dir=stories_dir,
    )
    result = _run_tool(
        "--operation",
        "has",
        "--name",
        name,
        "--step",
        "chapter_1",
        stories_dir=stories_dir,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    out = json.loads(result.stdout)
    assert out["exists"] is True


def test_has_missing_step(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "has",
        "--name",
        name,
        "--step",
        "nonexistent",
        stories_dir=stories_dir,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    out = json.loads(result.stdout)
    assert out["exists"] is False


def test_list_savepoints(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    for step in ("step_a", "step_b", "step_c"):
        _run_tool(
            "--operation",
            "save",
            "--name",
            name,
            "--step",
            step,
            "--data",
            f'"{step} data"',
            stories_dir=stories_dir,
        )
    result = _run_tool(
        "--operation",
        "list",
        "--name",
        name,
        stories_dir=stories_dir,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    out = json.loads(result.stdout)
    assert set(out["savepoints"].keys()) == {"step_a", "step_b", "step_c"}


def test_clear_savepoints(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    for step in ("s1", "s2"):
        _run_tool(
            "--operation",
            "save",
            "--name",
            name,
            "--step",
            step,
            "--data",
            '"x"',
            stories_dir=stories_dir,
        )
    clear_result = _run_tool(
        "--operation",
        "clear",
        "--name",
        name,
        stories_dir=stories_dir,
    )
    assert clear_result.returncode == 0, f"stderr: {clear_result.stderr}"
    assert json.loads(clear_result.stdout)["status"] == "cleared"

    list_result = _run_tool(
        "--operation",
        "list",
        "--name",
        name,
        stories_dir=stories_dir,
    )
    assert list_result.returncode == 0
    out = json.loads(list_result.stdout)
    assert out["savepoints"] == {}


def test_hierarchical_step_names(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    save_result = _run_tool(
        "--operation",
        "save",
        "--name",
        name,
        "--step",
        "chapter_1/scene_2",
        "--data",
        '"scene content"',
        stories_dir=stories_dir,
    )
    assert save_result.returncode == 0, f"stderr: {save_result.stderr}"

    load_result = _run_tool(
        "--operation",
        "load",
        "--name",
        name,
        "--step",
        "chapter_1/scene_2",
        stories_dir=stories_dir,
    )
    assert load_result.returncode == 0, f"stderr: {load_result.stderr}"
    load_out = json.loads(load_result.stdout)
    assert load_out["step"] == "chapter_1/scene_2"
    assert load_out["data"] == "scene content"


def test_load_missing_step(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "load",
        "--name",
        name,
        "--step",
        "does_not_exist",
        stories_dir=stories_dir,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    out = json.loads(result.stdout)
    assert out["data"] is None


def test_path_traversal_blocked_name(story_env: tuple[Path, str]) -> None:
    stories_dir, _ = story_env
    result = _run_tool(
        "--operation",
        "list",
        "--name",
        "../etc/passwd",
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
    assert "escapes stories directory" in result.stderr


def test_path_traversal_blocked_step(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "has",
        "--name",
        name,
        "--step",
        "../../etc/passwd",
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
    assert "must not contain '..'" in result.stderr


def test_missing_step_for_save(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "save",
        "--name",
        name,
        stories_dir=stories_dir,
    )
    assert result.returncode == 2


def test_missing_data_for_save(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "save",
        "--name",
        name,
        "--step",
        "some_step",
        stories_dir=stories_dir,
    )
    assert result.returncode == 2


def test_clear_nonexistent_story(tmp_path: Path) -> None:
    stories_dir = tmp_path / "stories"
    stories_dir.mkdir()
    result = _run_tool(
        "--operation",
        "clear",
        "--name",
        "no-such-story",
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
    assert "story not found" in result.stderr
