"""Verification tests for Issue #16 — wiki-read Tool.

Confirms the CLI tool (src/tools/wiki_read.py) correctly reads wiki pages
and matches entities against the wiki index.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_SCRIPT = str(PROJECT_ROOT / "src" / "tools" / "wiki_read.py")


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
def wiki_env(tmp_path: Path) -> tuple[Path, Path]:
    """Create a story with an initialised wiki directory."""
    stories = tmp_path / "stories"
    story = stories / "test-story"
    wiki = story / "wiki"
    wiki.mkdir(parents=True)

    # Create index
    (wiki / "index.md").write_text(
        "# Wiki Index\n\n<!-- slug | type | name | aliases -->\n"
    )

    # Create subdirectories
    for subdir in ["characters", "locations", "events"]:
        (wiki / subdir).mkdir()

    return stories, wiki


def _write_wiki_page(wiki: Path, subdir: str, slug: str, content: str) -> Path:
    """Write a wiki page to the given subdirectory."""
    page = wiki / subdir / f"{slug}.md"
    page.write_text(content)
    return page


class TestRead:
    def test_read_by_slug(self, wiki_env: tuple[Path, Path]) -> None:
        stories, wiki = wiki_env
        _write_wiki_page(
            wiki,
            "characters",
            "alice",
            "---\nslug: alice\ntype: character\n---\nAlice is brave.",
        )
        result = _run_tool(
            "--operation",
            "read",
            "--name",
            "test-story",
            "--slug",
            "alice",
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"
        assert len(output["pages"]) == 1
        assert output["pages"][0]["slug"] == "alice"

    def test_read_by_type(self, wiki_env: tuple[Path, Path]) -> None:
        stories, wiki = wiki_env
        _write_wiki_page(
            wiki,
            "characters",
            "bob",
            "---\nslug: bob\ntype: character\n---\nBob is clever.",
        )
        _write_wiki_page(
            wiki,
            "characters",
            "carol",
            "---\nslug: carol\ntype: character\n---\nCarol is wise.",
        )
        result = _run_tool(
            "--operation",
            "read",
            "--name",
            "test-story",
            "--type",
            "character",
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"
        assert len(output["pages"]) == 2
        slugs = {p["slug"] for p in output["pages"]}
        assert slugs == {"bob", "carol"}

    def test_read_headline_detail(self, wiki_env: tuple[Path, Path]) -> None:
        stories, wiki = wiki_env
        page_content = (
            "---\n"
            "slug: hero\n"
            "type: character\n"
            "detail_levels:\n"
            "  L1: Hero is the protagonist.\n"
            "---\n"
            "Full detailed description of hero."
        )
        _write_wiki_page(wiki, "characters", "hero", page_content)
        result = _run_tool(
            "--operation",
            "read",
            "--name",
            "test-story",
            "--slug",
            "hero",
            "--detail-level",
            "headline",
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["pages"][0]["content"] == "Hero is the protagonist."

    def test_read_brief_detail(self, wiki_env: tuple[Path, Path]) -> None:
        stories, wiki = wiki_env
        page_content = (
            "---\n"
            "slug: city\n"
            "type: location\n"
            "detail_levels:\n"
            "  L2: A sprawling metropolis in the north.\n"
            "---\n"
            "Full city description."
        )
        _write_wiki_page(wiki, "locations", "city", page_content)
        result = _run_tool(
            "--operation",
            "read",
            "--name",
            "test-story",
            "--slug",
            "city",
            "--detail-level",
            "brief",
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        page = output["pages"][0]
        assert page["content"] == "A sprawling metropolis in the north."
        assert "city" in page["metadata"]["slug"]

    def test_read_full_detail(self, wiki_env: tuple[Path, Path]) -> None:
        stories, wiki = wiki_env
        body = "Full detailed description of the village.\nIt has many houses."
        page_content = f"---\nslug: village\ntype: location\n---\n{body}"
        _write_wiki_page(wiki, "locations", "village", page_content)
        result = _run_tool(
            "--operation",
            "read",
            "--name",
            "test-story",
            "--slug",
            "village",
            "--detail-level",
            "full",
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["pages"][0]["content"] == body

    def test_read_empty_wiki(self, wiki_env: tuple[Path, Path]) -> None:
        stories, _wiki = wiki_env
        result = _run_tool(
            "--operation",
            "read",
            "--name",
            "test-story",
            "--type",
            "character",
            stories_dir=stories,
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["pages"] == []

    def test_read_missing_wiki(self, tmp_path: Path) -> None:
        stories = tmp_path / "stories"
        (stories / "no-wiki-story").mkdir(parents=True)
        result = _run_tool(
            "--operation",
            "read",
            "--name",
            "no-wiki-story",
            stories_dir=stories,
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["pages"] == []

    def test_read_path_traversal_blocked(self, wiki_env: tuple[Path, Path]) -> None:
        stories, _wiki = wiki_env
        result = _run_tool(
            "--operation",
            "read",
            "--name",
            "../evil",
            stories_dir=stories,
        )
        assert result.returncode == 1
        assert "escapes" in result.stderr

    def test_read_missing_operation(self) -> None:
        result = _run_tool("--name", "test-story")
        assert result.returncode == 2


class TestMatchEntities:
    def test_match_entities_finds_names(self, wiki_env: tuple[Path, Path]) -> None:
        stories, wiki = wiki_env
        index_content = (
            "# Wiki Index\n\n"
            "<!-- slug | type | name | aliases -->\n\n"
            "- alice | character | Alice |\n"
            "- bob | character | Bob |\n"
        )
        (wiki / "index.md").write_text(index_content)
        result = _run_tool(
            "--operation",
            "match-entities",
            "--name",
            "test-story",
            "--text",
            "Alice went to the market with Bob.",
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"
        slugs = {m["slug"] for m in output["matches"]}
        assert slugs == {"alice", "bob"}

    def test_match_entities_finds_aliases(self, wiki_env: tuple[Path, Path]) -> None:
        stories, wiki = wiki_env
        index_content = (
            "# Wiki Index\n\n"
            "<!-- slug | type | name | aliases -->\n\n"
            "- queen-elara | character | Queen Elara | Elara, The Queen\n"
        )
        (wiki / "index.md").write_text(index_content)
        result = _run_tool(
            "--operation",
            "match-entities",
            "--name",
            "test-story",
            "--text",
            "Elara commanded her armies to march.",
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert len(output["matches"]) == 1
        assert output["matches"][0]["slug"] == "queen-elara"

    def test_match_entities_empty_index(self, wiki_env: tuple[Path, Path]) -> None:
        stories, _wiki = wiki_env
        result = _run_tool(
            "--operation",
            "match-entities",
            "--name",
            "test-story",
            "--text",
            "Nobody is mentioned here.",
            stories_dir=stories,
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["matches"] == []
