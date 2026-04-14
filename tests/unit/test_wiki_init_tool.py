"""Verification tests for Issue #16 — wiki-init Tool.

Confirms the CLI tool (src/tools/wiki_init.py) correctly initialises
a wiki directory structure for a story.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_SCRIPT = str(PROJECT_ROOT / "src" / "tools" / "wiki_init.py")
SCHEMA_TEMPLATE = PROJECT_ROOT / "src" / "tools" / "wiki_schema_template.md"

EXPECTED_SUBDIRS = [
    "characters",
    "locations",
    "events",
    "factions",
    "items",
    "plot-threads",
    "world-rules",
    "themes",
    "relationships",
    "timeline",
    "chapters",
]


def _run_tool(
    *args: str, stories_dir: Path | None = None
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ}
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    if stories_dir is not None:
        env["STORIES_DIR"] = str(stories_dir)
    return subprocess.run(
        [sys.executable, TOOL_SCRIPT, *args],
        capture_output=True,
        text=True,
        env=env,
    )


@pytest.fixture()
def story_dir(tmp_path: Path) -> Path:
    """Create a minimal story directory for testing."""
    stories = tmp_path / "stories"
    story = stories / "test-story"
    story.mkdir(parents=True)
    (story / "state.json").write_text("{}")
    return stories


class TestInit:
    def test_init_creates_wiki_directory(self, story_dir: Path) -> None:
        result = _run_tool(
            "--operation", "init", "--name", "test-story", stories_dir=story_dir
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"
        assert output["created"] is True

        wiki_dir = story_dir / "test-story" / "wiki"
        assert wiki_dir.is_dir()
        for subdir in EXPECTED_SUBDIRS:
            assert (wiki_dir / subdir).is_dir(), f"missing subdir: {subdir}"

    def test_init_creates_schema_file(self, story_dir: Path) -> None:
        _run_tool("--operation", "init", "--name", "test-story", stories_dir=story_dir)
        schema = story_dir / "test-story" / "wiki" / "_schema.md"
        assert schema.exists()
        assert schema.read_text() == SCHEMA_TEMPLATE.read_text()

    def test_init_creates_index_file(self, story_dir: Path) -> None:
        _run_tool("--operation", "init", "--name", "test-story", stories_dir=story_dir)
        index = story_dir / "test-story" / "wiki" / "index.md"
        assert index.exists()
        content = index.read_text()
        assert content.startswith("# Wiki Index")
        assert "slug | type | name" in content

    def test_init_creates_log_file(self, story_dir: Path) -> None:
        _run_tool("--operation", "init", "--name", "test-story", stories_dir=story_dir)
        log = story_dir / "test-story" / "wiki" / "log.md"
        assert log.exists()
        assert "# Wiki Change Log" in log.read_text()

    def test_init_creates_contradictions_file(self, story_dir: Path) -> None:
        _run_tool("--operation", "init", "--name", "test-story", stories_dir=story_dir)
        contradictions = story_dir / "test-story" / "wiki" / "contradictions.md"
        assert contradictions.exists()
        assert "# Contradictions Log" in contradictions.read_text()

    def test_init_idempotent(self, story_dir: Path) -> None:
        _run_tool("--operation", "init", "--name", "test-story", stories_dir=story_dir)
        result = _run_tool(
            "--operation", "init", "--name", "test-story", stories_dir=story_dir
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["already_exists"] is True
        assert output["created"] is False

    def test_init_requires_existing_story(self, story_dir: Path) -> None:
        result = _run_tool(
            "--operation", "init", "--name", "nonexistent", stories_dir=story_dir
        )
        assert result.returncode == 1
        assert "not found" in result.stderr

    def test_init_path_traversal_blocked(self, story_dir: Path) -> None:
        result = _run_tool(
            "--operation", "init", "--name", "../evil", stories_dir=story_dir
        )
        assert result.returncode == 1
        assert "escapes" in result.stderr

    def test_init_missing_operation(self) -> None:
        result = _run_tool("--name", "test-story")
        assert result.returncode == 2
