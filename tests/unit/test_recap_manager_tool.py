"""Verification tests for Issue #9 — recap-manager Tool.

Confirms the CLI tool (src/tools/recap_manager.py) correctly manages
chapter recaps: load, generate, sanitize, compact operations —
only I/O and error-handling paths that don't require a running LLM.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_SCRIPT = str(PROJECT_ROOT / "src" / "tools" / "recap_manager.py")


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


def _save_recap_file(
    stories_dir: Path, story_name: str, chapter: int, data: str
) -> None:
    """Write a recap savepoint .md file directly to the expected path."""
    recap_dir = stories_dir / story_name / "savepoints" / f"chapter_{chapter}"
    recap_dir.mkdir(parents=True, exist_ok=True)
    recap_file = recap_dir / "recap.md"
    # Store as markdown with YAML frontmatter (matches FilesystemSavepointRepository)
    import yaml

    yaml_data = yaml.dump(
        json.loads(data) if isinstance(data, str) else data,
        default_flow_style=False,
        allow_unicode=True,
    )
    content = (
        f"---\n{yaml_data}---\n\n"
        f"# Savepoint: chapter_{chapter}/recap\n\n"
        "Data saved in YAML frontmatter above."
    )
    recap_file.write_text(content, encoding="utf-8")


def test_load_missing_recap_exits_1(story_env: tuple[Path, str]) -> None:
    """Load from non-existent savepoint returns exit code 1."""
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "load",
        "--name",
        name,
        "--chapter",
        "1",
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
    assert "not found" in result.stderr.lower()


def test_load_existing_recap(story_env: tuple[Path, str]) -> None:
    """Save a recap JSON file to the expected savepoint path, then load it."""
    stories_dir, name = story_env
    recap_data = {"events": [{"description": "Hero arrived", "importance": "high"}]}
    _save_recap_file(stories_dir, name, 1, json.dumps(recap_data))

    result = _run_tool(
        "--operation",
        "load",
        "--name",
        name,
        "--chapter",
        "1",
        stories_dir=stories_dir,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    out = json.loads(result.stdout)
    assert out["status"] == "success"
    assert out["operation"] == "load"
    assert out["data"]["events"][0]["description"] == "Hero arrived"


def test_generate_missing_content_exits_1(story_env: tuple[Path, str]) -> None:
    """Generate without chapter content savepoint exits 1."""
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "generate",
        "--name",
        name,
        "--chapter",
        "1",
        "--story-start-date",
        "2025-01-01",
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
    assert "content not found" in result.stderr.lower()


def test_compact_no_compaction_early_chapters(story_env: tuple[Path, str]) -> None:
    """Compact with chapter 1-5 returns recap unchanged (no LLM needed)."""
    stories_dir, name = story_env
    recap_data = {
        "events": [{"description": "Test event", "importance": "high"}],
        "meta": {"total_events": 1},
    }
    _save_recap_file(stories_dir, name, 3, json.dumps(recap_data))

    result = _run_tool(
        "--operation",
        "compact",
        "--name",
        name,
        "--chapter",
        "3",
        stories_dir=stories_dir,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    out = json.loads(result.stdout)
    assert out["status"] == "success"
    assert out["operation"] == "compact"
    assert out["data"]["events"][0]["description"] == "Test event"


def test_invalid_story_name_exits_1(story_env: tuple[Path, str]) -> None:
    """Path traversal attempt (e.g., ../evil) exits 1."""
    stories_dir, _ = story_env
    result = _run_tool(
        "--operation",
        "load",
        "--name",
        "../evil",
        "--chapter",
        "1",
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
    assert "escapes" in result.stderr.lower()


def test_missing_required_args_exits_2(story_env: tuple[Path, str]) -> None:
    """Missing --chapter exits 2."""
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "load",
        "--name",
        name,
        stories_dir=stories_dir,
    )
    assert result.returncode == 2


def test_invalid_operation_exits_2(story_env: tuple[Path, str]) -> None:
    """Unknown operation exits 2."""
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "unknown-op",
        "--name",
        name,
        "--chapter",
        "1",
        stories_dir=stories_dir,
    )
    assert result.returncode == 2


def test_load_returns_json_output(story_env: tuple[Path, str]) -> None:
    """Verify output is valid JSON with status/operation/data fields."""
    stories_dir, name = story_env
    recap_data = {"events": [], "meta": {"total_events": 0}}
    _save_recap_file(stories_dir, name, 1, json.dumps(recap_data))

    result = _run_tool(
        "--operation",
        "load",
        "--name",
        name,
        "--chapter",
        "1",
        stories_dir=stories_dir,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    out = json.loads(result.stdout)
    assert "status" in out
    assert "operation" in out
    assert "data" in out
    assert out["status"] == "success"
    assert out["operation"] == "load"


# ---------------------------------------------------------------------------
# Pure helper function tests (direct import)
# ---------------------------------------------------------------------------


class TestFilterLowImportanceEvents:
    """Tests for _filter_low_importance_events helper."""

    def test_filter_keeps_high_importance_events(self) -> None:
        """Mixed importance events — only high-importance survive."""
        from src.tools.recap_manager import _filter_low_importance_events

        recap_data = {
            "events": [
                {"description": "Hero born", "importance": "high"},
                {"description": "Bought bread", "importance": "low"},
                {"description": "Battle won", "importance": "high"},
                {"description": "Napped", "importance": "medium"},
            ],
            "meta": {"total_events": 4},
        }
        result = _filter_low_importance_events(recap_data, "2025-01-01")
        assert len(result["events"]) == 2
        descs = [e["description"] for e in result["events"]]
        assert "Hero born" in descs
        assert "Battle won" in descs
        assert "Bought bread" not in descs
        assert "Napped" not in descs
        assert result["meta"]["total_events"] == 2

    def test_filter_handles_empty_events(self) -> None:
        """Empty events list passes through cleanly."""
        from src.tools.recap_manager import _filter_low_importance_events

        recap_data = {
            "events": [],
            "meta": {"total_events": 0},
        }
        result = _filter_low_importance_events(recap_data, "2025-01-01")
        assert result["events"] == []
        assert result["meta"]["total_events"] == 0


class TestClassifyEventRecency:
    """Tests for _classify_event_recency helper."""

    def test_classify_recency_current_events(self) -> None:
        """Events from today classified as 'current'."""
        from src.tools.recap_manager import _classify_event_recency

        data = {
            "events": [
                {"description": "Fight today", "date_start": "2025-06-15"},
            ],
        }
        _classify_event_recency(data, "2025-06-15")
        assert data["events"][0]["recency"] == "current"

    def test_classify_recency_historical_events(self) -> None:
        """Events from 30+ days ago classified as 'historical'."""
        from src.tools.recap_manager import _classify_event_recency

        data = {
            "events": [
                {"description": "Ancient battle", "date_start": "2025-01-01"},
            ],
        }
        _classify_event_recency(data, "2025-06-15")
        assert data["events"][0]["recency"] == "historical"
