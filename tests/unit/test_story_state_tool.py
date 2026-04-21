"""Verification tests for Issue #8 — story-state Tool.

Confirms the CLI tool (src/tools/story_state.py) correctly manages
story state: init, read, write, and list operations.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_SCRIPT = str(PROJECT_ROOT / "src" / "tools" / "story_state.py")
STORIES_DIR = PROJECT_ROOT / "stories"


@pytest.fixture()
def story_dir(tmp_path: Path) -> Path:
    """Provide a temp stories directory for isolation via env var."""
    return tmp_path / "stories"


def _run_tool(
    *args: str, stories_dir: Path | None = None, stdin: str | None = None
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ}
    if stories_dir is not None:
        env["STORIES_DIR"] = str(stories_dir)
    return subprocess.run(
        [sys.executable, TOOL_SCRIPT, *args],
        capture_output=True,
        text=True,
        env=env,
        input=stdin,
    )


class TestInit:
    def test_init_creates_story(self, story_dir: Path) -> None:
        result = _run_tool(
            "--operation", "init", "--name", "my-tale", stories_dir=story_dir
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "created"
        assert (story_dir / "my-tale" / "state.json").exists()
        assert (story_dir / "my-tale" / "chapters").is_dir()
        assert (story_dir / "my-tale" / "characters").is_dir()
        assert (story_dir / "my-tale" / "settings").is_dir()
        assert (story_dir / "my-tale" / "savepoints").is_dir()

    def test_init_state_matches_schema(self, story_dir: Path) -> None:
        _run_tool("--operation", "init", "--name", "schema-test", stories_dir=story_dir)
        state = json.loads((story_dir / "schema-test" / "state.json").read_text())
        assert "story_context" in state
        assert "characters" in state
        assert "plot_threads" in state
        assert "chapters" in state
        assert state["story_context"]["story_pacing"] == "medium"
        assert state["story_context"]["current_tension"] == 1

    def test_init_duplicate_fails(self, story_dir: Path) -> None:
        _run_tool("--operation", "init", "--name", "dup", stories_dir=story_dir)
        result = _run_tool(
            "--operation", "init", "--name", "dup", stories_dir=story_dir
        )
        assert result.returncode == 1
        assert "already exists" in result.stderr

    def test_init_missing_name(self) -> None:
        result = _run_tool("--operation", "init")
        assert result.returncode == 2


class TestRead:
    def test_read_full_state(self, story_dir: Path) -> None:
        _run_tool("--operation", "init", "--name", "reader", stories_dir=story_dir)
        result = _run_tool(
            "--operation", "read", "--name", "reader", stories_dir=story_dir
        )
        assert result.returncode == 0
        state = json.loads(result.stdout)
        assert "story_context" in state

    def test_read_nested_field(self, story_dir: Path) -> None:
        _run_tool("--operation", "init", "--name", "nested", stories_dir=story_dir)
        result = _run_tool(
            "--operation",
            "read",
            "--name",
            "nested",
            "--field",
            "story_context.story_pacing",
            stories_dir=story_dir,
        )
        assert result.returncode == 0
        assert json.loads(result.stdout) == "medium"

    def test_read_nonexistent_story(self, story_dir: Path) -> None:
        result = _run_tool(
            "--operation", "read", "--name", "ghost", stories_dir=story_dir
        )
        assert result.returncode == 1
        assert "not found" in result.stderr

    def test_read_nonexistent_field(self, story_dir: Path) -> None:
        _run_tool("--operation", "init", "--name", "badfield", stories_dir=story_dir)
        result = _run_tool(
            "--operation",
            "read",
            "--name",
            "badfield",
            "--field",
            "story_context.nonexistent",
            stories_dir=story_dir,
        )
        assert result.returncode == 1
        assert "field not found" in result.stderr

    def test_read_missing_name(self) -> None:
        result = _run_tool("--operation", "read")
        assert result.returncode == 2


class TestWrite:
    def test_write_leaf_field(self, story_dir: Path) -> None:
        _run_tool("--operation", "init", "--name", "writer", stories_dir=story_dir)
        result = _run_tool(
            "--operation",
            "write",
            "--name",
            "writer",
            "--field",
            "story_context.tone_style",
            "--value",
            '"dark"',
            stories_dir=story_dir,
        )
        assert result.returncode == 0
        read_result = _run_tool(
            "--operation",
            "read",
            "--name",
            "writer",
            "--field",
            "story_context.tone_style",
            stories_dir=story_dir,
        )
        assert json.loads(read_result.stdout) == "dark"

    def test_write_preserves_siblings(self, story_dir: Path) -> None:
        _run_tool("--operation", "init", "--name", "sibling", stories_dir=story_dir)
        _run_tool(
            "--operation",
            "write",
            "--name",
            "sibling",
            "--field",
            "story_context",
            "--value",
            '{"tone_style": "gothic"}',
            stories_dir=story_dir,
        )
        read_result = _run_tool(
            "--operation",
            "read",
            "--name",
            "sibling",
            "--field",
            "story_context",
            stories_dir=story_dir,
        )
        ctx = json.loads(read_result.stdout)
        assert ctx["tone_style"] == "gothic"
        assert ctx["story_pacing"] == "medium"

    def test_write_new_character(self, story_dir: Path) -> None:
        _run_tool("--operation", "init", "--name", "chars", stories_dir=story_dir)
        char_data = json.dumps(
            {
                "name": "Alice",
                "current_role": "protagonist",
                "personality_traits": ["brave"],
                "motivations": ["justice"],
            }
        )
        result = _run_tool(
            "--operation",
            "write",
            "--name",
            "chars",
            "--field",
            "characters.Alice",
            "--value",
            char_data,
            stories_dir=story_dir,
        )
        assert result.returncode == 0
        read_result = _run_tool(
            "--operation",
            "read",
            "--name",
            "chars",
            "--field",
            "characters.Alice.current_role",
            stories_dir=story_dir,
        )
        assert json.loads(read_result.stdout) == "protagonist"

    def test_write_invalid_json_value(self, story_dir: Path) -> None:
        _run_tool("--operation", "init", "--name", "badjson", stories_dir=story_dir)
        result = _run_tool(
            "--operation",
            "write",
            "--name",
            "badjson",
            "--field",
            "story_context.tone_style",
            "--value",
            "not valid json",
            stories_dir=story_dir,
        )
        assert result.returncode == 1
        assert "invalid json" in result.stderr.lower()

    def test_write_missing_field(self, story_dir: Path) -> None:
        _run_tool("--operation", "init", "--name", "nofield", stories_dir=story_dir)
        result = _run_tool(
            "--operation",
            "write",
            "--name",
            "nofield",
            "--value",
            '"x"',
            stories_dir=story_dir,
        )
        assert result.returncode == 2

    def test_write_missing_value(self, story_dir: Path) -> None:
        result = _run_tool(
            "--operation",
            "write",
            "--name",
            "noval",
            "--field",
            "x",
            stories_dir=story_dir,
        )
        assert result.returncode == 2

    def test_write_value_from_stdin(self, story_dir: Path) -> None:
        """--value - reads JSON from stdin, supporting values with single quotes."""
        _run_tool("--operation", "init", "--name", "stdin-story", stories_dir=story_dir)
        json_with_apostrophe = '{"prompt": "humanity\'s first transmission"}'
        result = _run_tool(
            "--operation",
            "write",
            "--name",
            "stdin-story",
            "--field",
            "metadata",
            "--value",
            "-",
            stories_dir=story_dir,
            stdin=json_with_apostrophe,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        read_result = _run_tool(
            "--operation",
            "read",
            "--name",
            "stdin-story",
            "--field",
            "metadata.prompt",
            stories_dir=story_dir,
        )
        assert json.loads(read_result.stdout) == "humanity's first transmission"


class TestList:
    def test_list_empty(self, story_dir: Path) -> None:
        result = _run_tool("--operation", "list", stories_dir=story_dir)
        assert result.returncode == 0
        assert json.loads(result.stdout) == []

    def test_list_stories(self, story_dir: Path) -> None:
        _run_tool("--operation", "init", "--name", "alpha", stories_dir=story_dir)
        _run_tool("--operation", "init", "--name", "beta", stories_dir=story_dir)
        result = _run_tool("--operation", "list", stories_dir=story_dir)
        assert result.returncode == 0
        stories = json.loads(result.stdout)
        assert stories == ["alpha", "beta"]


class TestSecurity:
    def test_path_traversal_blocked(self, story_dir: Path) -> None:
        result = _run_tool(
            "--operation",
            "init",
            "--name",
            "../../etc/passwd",
            stories_dir=story_dir,
        )
        assert result.returncode == 1
        assert "escapes" in result.stderr

    def test_path_traversal_read(self, story_dir: Path) -> None:
        result = _run_tool(
            "--operation",
            "read",
            "--name",
            "../secrets",
            stories_dir=story_dir,
        )
        assert result.returncode == 1
        assert "escapes" in result.stderr


class TestArgparse:
    def test_missing_operation(self) -> None:
        result = _run_tool()
        assert result.returncode == 2
