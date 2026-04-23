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
    # 'list' returns names only (sorted list)
    assert set(out["savepoints"]) == {"step_a", "step_b", "step_c"}

    # 'list-full' returns names + data (dict)
    full_result = _run_tool(
        "--operation",
        "list-full",
        "--name",
        name,
        stories_dir=stories_dir,
    )
    assert full_result.returncode == 0
    full_out = json.loads(full_result.stdout)
    assert set(full_out["savepoints"].keys()) == {"step_a", "step_b", "step_c"}


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
    assert out["savepoints"] == []


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
    assert "escapes stories directory" in result.stderr or "kebab-case" in result.stderr


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
    assert "not initialized" in result.stderr or "not found" in result.stderr


# --- next-phase operation (issue #148) -----------------------------------


def _save(stories_dir: Path, name: str, step: str, data: str = '"x"') -> None:
    result = _run_tool(
        "--operation",
        "save",
        "--name",
        name,
        "--step",
        step,
        "--data",
        data,
        stories_dir=stories_dir,
    )
    assert result.returncode == 0, f"save {step} failed: {result.stderr}"


def _next_phase(stories_dir: Path, name: str) -> dict:
    result = _run_tool(
        "--operation",
        "next-phase",
        "--name",
        name,
        stories_dir=stories_dir,
    )
    assert result.returncode == 0, f"next-phase failed: {result.stderr}"
    return json.loads(result.stdout)


def test_next_phase_empty_story(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    out = _next_phase(stories_dir, name)
    assert out["last_completed"] == ""
    assert out["last_canonical"] == ""
    assert out["last_chapter_complete"] == 0
    assert "Phase 1" in out["next_phase"]


def test_next_phase_only_init(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    _save(stories_dir, name, "init")
    out = _next_phase(stories_dir, name)
    assert out["last_completed"] == "init"
    assert "Phase 2" in out["next_phase"]
    assert out["missing_below_top"] == []


def test_next_phase_tolerates_gaps(story_env: tuple[Path, str]) -> None:
    """outline_complete missing but characters_complete present — picks highest."""
    stories_dir, name = story_env
    _save(stories_dir, name, "init")
    _save(stories_dir, name, "arc_analysis_complete")
    _save(stories_dir, name, "characters_complete")
    out = _next_phase(stories_dir, name)
    assert out["last_completed"] == "characters_complete"
    assert "Phase 5" in out["next_phase"]
    assert "outline_complete" in out["missing_below_top"]


def test_next_phase_settings_complete(story_env: tuple[Path, str]) -> None:
    """The exact scenario from issue #148: characters + settings present."""
    stories_dir, name = story_env
    _save(stories_dir, name, "init")
    _save(stories_dir, name, "arc_analysis_complete")
    _save(stories_dir, name, "characters_complete")
    _save(stories_dir, name, "settings_complete")
    out = _next_phase(stories_dir, name)
    assert out["last_completed"] == "settings_complete"
    assert "Phase 6" in out["next_phase"]


def test_next_phase_chapter_loop(story_env: tuple[Path, str]) -> None:
    """chapter_3_complete + chapter_5_complete → highest is 5."""
    stories_dir, name = story_env
    _save(stories_dir, name, "init")
    _save(stories_dir, name, "wiki_populated")
    _save(stories_dir, name, "chapter_1_complete")
    _save(stories_dir, name, "chapter_3_complete")
    _save(stories_dir, name, "chapter_5_complete")
    out = _next_phase(stories_dir, name)
    assert out["last_completed"] == "chapter_5_complete"
    assert out["last_chapter_complete"] == 5
    assert "chapter 6" in out["next_phase"]


def test_next_phase_outlines_expanded(story_env: tuple[Path, str]) -> None:
    """After Phase 7a completes, next phase is 7b (per-chapter loop)."""
    stories_dir, name = story_env
    _save(stories_dir, name, "init")
    _save(stories_dir, name, "wiki_populated")
    _save(stories_dir, name, "outlines_expanded")
    out = _next_phase(stories_dir, name)
    assert out["last_completed"] == "outlines_expanded"
    assert "Phase 7b" in out["next_phase"]


def test_next_phase_story_complete(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    _save(stories_dir, name, "init")
    _save(stories_dir, name, "wiki_populated")
    _save(stories_dir, name, "chapter_1_complete")
    _save(stories_dir, name, "story_complete")
    out = _next_phase(stories_dir, name)
    assert out["last_completed"] == "story_complete"
    assert "Phase 9" in out["next_phase"]


def test_next_phase_final_edit_complete(story_env: tuple[Path, str]) -> None:
    stories_dir, name = story_env
    _save(stories_dir, name, "init")
    _save(stories_dir, name, "wiki_populated")
    _save(stories_dir, name, "story_complete")
    _save(stories_dir, name, "final_edit_complete")
    out = _next_phase(stories_dir, name)
    assert out["last_completed"] == "final_edit_complete"
    assert "complete" in out["next_phase"].lower()


def test_next_phase_nonexistent_story(tmp_path: Path) -> None:
    stories_dir = tmp_path / "stories"
    stories_dir.mkdir()
    result = _run_tool(
        "--operation",
        "next-phase",
        "--name",
        "no-such-story",
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
