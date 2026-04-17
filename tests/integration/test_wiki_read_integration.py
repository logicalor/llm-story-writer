"""Integration tests for wiki_read error-path behavior."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WIKI_READ_SCRIPT = PROJECT_ROOT / "src" / "tools" / "wiki_read.py"


def _make_env(stories_dir: Path, chromadb_dir: Path) -> dict[str, str]:
    env = {**os.environ}
    env["STORIES_DIR"] = str(stories_dir)
    env["CHROMADB_DIR"] = str(chromadb_dir)
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    return env


def _run_tool(
    script: Path,
    args: list[str],
    env: dict[str, str],
    timeout: int = 300,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


def _assert_success(
    result: subprocess.CompletedProcess[str], label: str
) -> dict[str, Any]:
    assert result.returncode == 0, (
        f"{label} failed (rc={result.returncode})\n"
        f"STDOUT: {result.stdout[:500]}\n"
        f"STDERR: {result.stderr[:500]}"
    )
    return json.loads(result.stdout)


class TestWikiReadErrorPaths:
    def test_read_nonexistent_slug(self, tmp_path: Path) -> None:
        stories_dir = tmp_path / "stories"
        chromadb_dir = tmp_path / "chromadb"
        story_dir = stories_dir / "test-story"
        wiki_dir = story_dir / "wiki"
        characters_dir = wiki_dir / "characters"
        characters_dir.mkdir(parents=True)
        (characters_dir / "existing-page.md").write_text(
            "---\nslug: existing-page\ntype: character\n---\nExisting page.",
            encoding="utf-8",
        )

        result = _run_tool(
            WIKI_READ_SCRIPT,
            [
                "--operation",
                "read",
                "--name",
                "test-story",
                "--slug",
                "does-not-exist",
            ],
            _make_env(stories_dir, chromadb_dir),
        )

        data = _assert_success(result, "wiki-read read nonexistent slug")
        assert data == {"status": "ok", "pages": []}

    def test_match_entities_no_wiki(self, tmp_path: Path) -> None:
        stories_dir = tmp_path / "stories"
        chromadb_dir = tmp_path / "chromadb"
        (stories_dir / "test-story").mkdir(parents=True)

        result = _run_tool(
            WIKI_READ_SCRIPT,
            [
                "--operation",
                "match-entities",
                "--name",
                "test-story",
                "--text",
                "any text",
            ],
            _make_env(stories_dir, chromadb_dir),
        )

        data = _assert_success(result, "wiki-read match-entities missing wiki")
        assert data == {"status": "ok", "matches": []}

    def test_read_empty_wiki_dir(self, tmp_path: Path) -> None:
        stories_dir = tmp_path / "stories"
        chromadb_dir = tmp_path / "chromadb"
        wiki_dir = stories_dir / "test-story" / "wiki"
        wiki_dir.mkdir(parents=True)

        result = _run_tool(
            WIKI_READ_SCRIPT,
            [
                "--operation",
                "read",
                "--name",
                "test-story",
            ],
            _make_env(stories_dir, chromadb_dir),
        )

        data = _assert_success(result, "wiki-read read empty wiki")
        assert data == {"status": "ok", "pages": []}