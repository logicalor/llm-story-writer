"""Verification tests for Issue #17 — wiki-lint Tool.

Confirms the CLI tool (src/tools/wiki_lint.py) correctly detects
contradictions, orphans, broken wikilinks, and other consistency issues.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_SCRIPT = str(PROJECT_ROOT / "src" / "tools" / "wiki_lint.py")

WIKI_SUBDIRS = [
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

_TYPE_TO_DIR = {
    "character": "characters",
    "location": "locations",
    "event": "events",
    "faction": "factions",
    "item": "items",
    "plot_thread": "plot-threads",
    "world_rule": "world-rules",
    "theme": "themes",
    "relationship": "relationships",
    "timeline_entry": "timeline",
    "chapter_synopsis": "chapters",
}


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


def _create_wiki(stories_dir: Path, story_name: str = "test-story") -> Path:
    """Create a minimal wiki structure for testing."""
    story_dir = stories_dir / story_name
    wiki_dir = story_dir / "wiki"
    wiki_dir.mkdir(parents=True)

    for subdir in WIKI_SUBDIRS:
        (wiki_dir / subdir).mkdir()

    (wiki_dir / "index.md").write_text(
        "# Wiki Index\n\n<!-- slug | type | name | aliases -->\n"
    )
    (wiki_dir / "log.md").write_text("# Wiki Log\n")
    (wiki_dir / "contradictions.md").write_text("# Contradictions\n")

    return wiki_dir


def _create_page(
    wiki_dir: Path,
    page_type: str,
    slug: str,
    name: str,
    extra_frontmatter: dict | None = None,
    body: str = "",
) -> Path:
    """Create a wiki page with frontmatter."""
    metadata: dict = {
        "type": page_type,
        "name": name,
        "slug": slug,
        "confidence": "verified",
        "first_appearance": 1,
        "aliases": [],
        "last_updated": "2026-01-01T00:00:00Z",
        "version": 1,
        "detail_levels": {"L1": "Short", "L2": "Medium", "L3": "Full"},
    }
    if extra_frontmatter:
        metadata.update(extra_frontmatter)

    content = f"---\n{yaml.dump(metadata, default_flow_style=False)}---\n{body}"

    type_dir = _TYPE_TO_DIR.get(page_type, "characters")
    page_path = wiki_dir / type_dir / f"{slug}.md"
    page_path.parent.mkdir(exist_ok=True)
    page_path.write_text(content)
    return page_path


def _add_to_index(
    wiki_dir: Path,
    slug: str,
    page_type: str,
    name: str,
    aliases: list[str] | None = None,
) -> None:
    """Add entry to index.md."""
    aliases_str = ", ".join(aliases) if aliases else ""
    line = f"- {slug} | {page_type} | {name} | {aliases_str}\n"
    with open(wiki_dir / "index.md", "a") as f:
        f.write(line)


def _write_chapter_text(stories_dir: Path, story_name: str, text: str) -> Path:
    """Write chapter text to a file inside the story directory."""
    chapter_path = stories_dir / story_name / "chapter.txt"
    chapter_path.parent.mkdir(parents=True, exist_ok=True)
    chapter_path.write_text(text)
    return chapter_path


# ---------------------------------------------------------------------------
# TestCheckChapter
# ---------------------------------------------------------------------------


class TestCheckChapter:
    def test_detects_dead_character_mentioned(self, tmp_path: Path) -> None:
        stories = tmp_path / "stories"
        wiki = _create_wiki(stories)
        _create_page(
            wiki,
            "character",
            "alice",
            "Alice",
            extra_frontmatter={"status": "dead"},
        )
        _add_to_index(wiki, "alice", "character", "Alice")

        chapter_path = _write_chapter_text(
            stories, "test-story", "Alice walked into the room."
        )

        result = _run_tool(
            "--operation",
            "check-chapter",
            "--name",
            "test-story",
            "--chapter-number",
            "5",
            "--chapter-text",
            str(chapter_path),
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"

        findings = output["findings"]
        status_findings = [
            f for f in findings if f["subtype"] == "status_contradiction"
        ]
        assert len(status_findings) >= 1
        assert status_findings[0]["severity"] == "error"
        assert status_findings[0]["category"] == "characterization"

    def test_detects_missing_entity_page(self, tmp_path: Path) -> None:
        stories = tmp_path / "stories"
        wiki = _create_wiki(stories)
        # Index entry but no page file
        _add_to_index(wiki, "bob", "character", "Bob")

        chapter_path = _write_chapter_text(
            stories, "test-story", "Bob appeared at the gate."
        )

        result = _run_tool(
            "--operation",
            "check-chapter",
            "--name",
            "test-story",
            "--chapter-number",
            "3",
            "--chapter-text",
            str(chapter_path),
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"

        missing = [f for f in output["findings"] if f["subtype"] == "missing_entity"]
        assert len(missing) >= 1
        assert missing[0]["severity"] == "warning"

    def test_detects_broken_wikilink_in_chapter(self, tmp_path: Path) -> None:
        stories = tmp_path / "stories"
        _create_wiki(stories)

        chapter_path = _write_chapter_text(
            stories, "test-story", "She visited [[nonexistent-place]] today."
        )

        result = _run_tool(
            "--operation",
            "check-chapter",
            "--name",
            "test-story",
            "--chapter-number",
            "2",
            "--chapter-text",
            str(chapter_path),
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"

        broken = [f for f in output["findings"] if f["subtype"] == "broken_wikilink"]
        assert len(broken) >= 1
        assert broken[0]["severity"] == "warning"
        assert "nonexistent-place" in broken[0]["message"]

    def test_clean_chapter_no_findings(self, tmp_path: Path) -> None:
        stories = tmp_path / "stories"
        wiki = _create_wiki(stories)
        _create_page(wiki, "character", "carol", "Carol")
        _add_to_index(wiki, "carol", "character", "Carol")

        chapter_path = _write_chapter_text(
            stories, "test-story", "Carol smiled warmly."
        )

        result = _run_tool(
            "--operation",
            "check-chapter",
            "--name",
            "test-story",
            "--chapter-number",
            "1",
            "--chapter-text",
            str(chapter_path),
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"
        assert output["summary"]["total"] == 0
        assert len(output["findings"]) == 0

    def test_findings_appended_to_contradictions_md(self, tmp_path: Path) -> None:
        stories = tmp_path / "stories"
        wiki = _create_wiki(stories)
        _add_to_index(wiki, "dan", "character", "Dan")
        # No page for Dan → will produce a missing_entity finding

        chapter_path = _write_chapter_text(stories, "test-story", "Dan rushed forward.")

        result = _run_tool(
            "--operation",
            "check-chapter",
            "--name",
            "test-story",
            "--chapter-number",
            "4",
            "--chapter-text",
            str(chapter_path),
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"

        contradictions = (wiki / "contradictions.md").read_text()
        assert "Chapter 4 check" in contradictions
        assert "missing_entity" in contradictions


# ---------------------------------------------------------------------------
# TestCheckFull
# ---------------------------------------------------------------------------


class TestCheckFull:
    def test_detects_orphan_page_on_disk(self, tmp_path: Path) -> None:
        stories = tmp_path / "stories"
        wiki = _create_wiki(stories)
        # Page on disk, not in index
        _create_page(wiki, "character", "orphan-char", "OrphanChar")

        result = _run_tool(
            "--operation",
            "check-full",
            "--name",
            "test-story",
            "--current-chapter",
            "5",
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"

        orphans = [f for f in output["findings"] if f["subtype"] == "orphan_reference"]
        disk_orphans = [f for f in orphans if "exists on disk" in f["message"]]
        assert len(disk_orphans) >= 1
        assert disk_orphans[0]["severity"] == "warning"

    def test_detects_orphan_index_entry(self, tmp_path: Path) -> None:
        stories = tmp_path / "stories"
        wiki = _create_wiki(stories)
        # In index but no file on disk
        _add_to_index(wiki, "ghost", "character", "Ghost")

        result = _run_tool(
            "--operation",
            "check-full",
            "--name",
            "test-story",
            "--current-chapter",
            "5",
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"

        orphans = [f for f in output["findings"] if f["subtype"] == "orphan_reference"]
        index_orphans = [
            f for f in orphans if "no corresponding .md file" in f["message"]
        ]
        assert len(index_orphans) >= 1
        assert index_orphans[0]["severity"] == "warning"

    def test_detects_stale_claims(self, tmp_path: Path) -> None:
        stories = tmp_path / "stories"
        wiki = _create_wiki(stories)
        _create_page(
            wiki,
            "character",
            "old-char",
            "OldChar",
            extra_frontmatter={"first_appearance": 1},
        )
        _add_to_index(wiki, "old-char", "character", "OldChar")

        result = _run_tool(
            "--operation",
            "check-full",
            "--name",
            "test-story",
            "--current-chapter",
            "10",
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"

        stale = [f for f in output["findings"] if f["subtype"] == "stale_claim"]
        assert len(stale) >= 1
        assert stale[0]["severity"] == "info"

    def test_detects_broken_wikilinks_in_pages(self, tmp_path: Path) -> None:
        stories = tmp_path / "stories"
        wiki = _create_wiki(stories)
        _create_page(
            wiki,
            "character",
            "eve",
            "Eve",
            body="Eve knows [[missing-slug]] very well.\n",
        )
        _add_to_index(wiki, "eve", "character", "Eve")

        result = _run_tool(
            "--operation",
            "check-full",
            "--name",
            "test-story",
            "--current-chapter",
            "3",
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"

        broken = [f for f in output["findings"] if f["subtype"] == "broken_wikilink"]
        assert len(broken) >= 1
        assert "missing-slug" in broken[0]["message"]

    def test_detects_timeline_ordering_violation(self, tmp_path: Path) -> None:
        stories = tmp_path / "stories"
        wiki = _create_wiki(stories)

        # Create out-of-order timeline
        timeline_content = (
            "# Main Timeline\n\n"
            "- **Chapter 3** — Morning — Something happened\n"
            "- **Chapter 1** — Evening — Earlier event\n"
        )
        (wiki / "timeline" / "main-timeline.md").write_text(timeline_content)

        result = _run_tool(
            "--operation",
            "check-full",
            "--name",
            "test-story",
            "--current-chapter",
            "5",
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"

        temporal = [
            f for f in output["findings"] if f["subtype"] == "temporal_ordering"
        ]
        assert len(temporal) >= 1
        assert temporal[0]["severity"] == "error"

    def test_clean_wiki_no_findings(self, tmp_path: Path) -> None:
        stories = tmp_path / "stories"
        wiki = _create_wiki(stories)
        _create_page(wiki, "character", "frank", "Frank")
        _add_to_index(wiki, "frank", "character", "Frank")

        result = _run_tool(
            "--operation",
            "check-full",
            "--name",
            "test-story",
            "--current-chapter",
            "2",
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"
        assert output["summary"]["total"] == 0


# ---------------------------------------------------------------------------
# TestCheckEntity
# ---------------------------------------------------------------------------


class TestCheckEntity:
    def test_validates_missing_frontmatter_fields(self, tmp_path: Path) -> None:
        stories = tmp_path / "stories"
        wiki = _create_wiki(stories)
        # Write page with missing required fields (no confidence, no first_appearance)
        page_path = wiki / "characters" / "incomplete.md"
        page_path.write_text(
            "---\ntype: character\nname: Incomplete\nslug: incomplete\n---\nBody.\n"
        )
        _add_to_index(wiki, "incomplete", "character", "Incomplete")

        result = _run_tool(
            "--operation",
            "check-entity",
            "--name",
            "test-story",
            "--slug",
            "incomplete",
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"

        missing = [f for f in output["findings"] if f["subtype"] == "missing_entity"]
        assert len(missing) >= 1
        # Should flag at least confidence and first_appearance
        messages = " ".join(f["message"] for f in missing)
        assert "confidence" in messages
        assert "first_appearance" in messages

    def test_detects_broken_wikilinks_in_body(self, tmp_path: Path) -> None:
        stories = tmp_path / "stories"
        wiki = _create_wiki(stories)
        _create_page(
            wiki,
            "character",
            "gina",
            "Gina",
            body="Gina visited [[missing-place]] yesterday.\n",
        )
        _add_to_index(wiki, "gina", "character", "Gina")

        result = _run_tool(
            "--operation",
            "check-entity",
            "--name",
            "test-story",
            "--slug",
            "gina",
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"

        broken = [f for f in output["findings"] if f["subtype"] == "broken_wikilink"]
        assert len(broken) >= 1
        assert "missing-place" in broken[0]["message"]

    def test_missing_entity_returns_error(self, tmp_path: Path) -> None:
        stories = tmp_path / "stories"
        _create_wiki(stories)

        result = _run_tool(
            "--operation",
            "check-entity",
            "--name",
            "test-story",
            "--slug",
            "nonexistent",
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"

        missing = [f for f in output["findings"] if f["subtype"] == "missing_entity"]
        assert len(missing) >= 1
        assert missing[0]["severity"] == "error"

    def test_entity_not_in_index(self, tmp_path: Path) -> None:
        stories = tmp_path / "stories"
        wiki = _create_wiki(stories)
        # Page exists but not in index
        _create_page(wiki, "character", "hermit", "Hermit")

        result = _run_tool(
            "--operation",
            "check-entity",
            "--name",
            "test-story",
            "--slug",
            "hermit",
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"

        orphans = [f for f in output["findings"] if f["subtype"] == "orphan_reference"]
        assert len(orphans) >= 1
        assert orphans[0]["severity"] == "warning"


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_path_traversal_rejected(self, tmp_path: Path) -> None:
        stories = tmp_path / "stories"
        _create_wiki(stories)

        result = _run_tool(
            "--operation",
            "check-chapter",
            "--name",
            "test-story",
            "--chapter-number",
            "1",
            "--chapter-text",
            "../../etc/passwd",
            stories_dir=stories,
        )
        assert result.returncode != 0
        assert "stories directory" in result.stderr.lower() or result.returncode == 1
