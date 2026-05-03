"""Verification tests for Issue #14 — wiki-update Tool.

Confirms the CLI tool (src/tools/wiki_update.py) correctly creates,
updates, and manages wiki pages for a story.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_SCRIPT = str(PROJECT_ROOT / "src" / "tools" / "wiki_update.py")


def _run_tool(
    *args: str,
    stories_dir: Path | None = None,
    chromadb_dir: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ}
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    if stories_dir is not None:
        env["STORIES_DIR"] = str(stories_dir)
    if chromadb_dir is not None:
        env["CHROMADB_DIR"] = str(chromadb_dir)
    return subprocess.run(
        [sys.executable, TOOL_SCRIPT, *args],
        capture_output=True,
        text=True,
        env=env,
    )


@pytest.fixture()
def story_dir(tmp_path: Path) -> Path:
    """Create a story with an initialised wiki structure."""
    stories = tmp_path / "stories"
    story = stories / "test-story"
    wiki = story / "wiki"
    wiki.mkdir(parents=True)
    for subdir in [
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
    ]:
        (wiki / subdir).mkdir()
    (wiki / "index.md").write_text(
        "# Wiki Index\n\n<!-- slug | type | name | aliases -->\n\n"
    )
    (wiki / "log.md").write_text("# Wiki Change Log\n")
    (wiki / "timeline" / "main-timeline.md").write_text("# Main Timeline\n\n")
    return stories


@pytest.fixture()
def chromadb_dir(tmp_path: Path) -> Path:
    d = tmp_path / "chromadb"
    d.mkdir()
    return d


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Minimal frontmatter parser for test assertions."""
    import yaml

    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    metadata = yaml.safe_load(parts[1])
    body = parts[2].lstrip("\n")
    return metadata or {}, body


class TestCreate:
    def test_create_page_basic(self, story_dir: Path) -> None:
        result = _run_tool(
            "--operation",
            "create",
            "--name",
            "test-story",
            "--slug",
            "alice",
            "--page-type",
            "character",
            "--page-name",
            "Alice",
            stories_dir=story_dir,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"
        assert output["slug"] == "alice"

        page_path = story_dir / "test-story" / "wiki" / "characters" / "alice.md"
        assert page_path.exists()

        metadata, _ = _parse_frontmatter(page_path.read_text())
        assert metadata["type"] == "character"
        assert metadata["name"] == "Alice"
        assert metadata["slug"] == "alice"
        assert metadata["confidence"] == "verified"
        assert metadata["first_appearance"] == 1
        assert metadata["version"] == 1
        assert "last_updated" in metadata

        # Check index.md updated
        index = (story_dir / "test-story" / "wiki" / "index.md").read_text()
        assert "alice" in index
        assert "character" in index

    def test_create_page_with_detail_levels(self, story_dir: Path) -> None:
        detail = json.dumps({"L1": "Short", "L2": "Medium", "L3": "Full desc"})
        result = _run_tool(
            "--operation",
            "create",
            "--name",
            "test-story",
            "--slug",
            "bob",
            "--page-type",
            "character",
            "--page-name",
            "Bob",
            "--detail-levels",
            detail,
            stories_dir=story_dir,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"

        page_path = story_dir / "test-story" / "wiki" / "characters" / "bob.md"
        metadata, _ = _parse_frontmatter(page_path.read_text())
        assert metadata["detail_levels"] == {
            "L1": "Short",
            "L2": "Medium",
            "L3": "Full desc",
        }

    def test_create_page_type_specific_fields(self, story_dir: Path) -> None:
        # Character with role + status
        result = _run_tool(
            "--operation",
            "create",
            "--name",
            "test-story",
            "--slug",
            "hero",
            "--page-type",
            "character",
            "--page-name",
            "The Hero",
            "--role",
            "protagonist",
            "--status",
            "alive",
            stories_dir=story_dir,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        page = story_dir / "test-story" / "wiki" / "characters" / "hero.md"
        meta, _ = _parse_frontmatter(page.read_text())
        assert meta["role"] == "protagonist"
        assert meta["status"] == "alive"

        # Event with chapter + impact
        result = _run_tool(
            "--operation",
            "create",
            "--name",
            "test-story",
            "--slug",
            "battle",
            "--page-type",
            "event",
            "--page-name",
            "The Battle",
            "--chapter",
            "3",
            "--impact",
            "major",
            stories_dir=story_dir,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        page = story_dir / "test-story" / "wiki" / "events" / "battle.md"
        meta, _ = _parse_frontmatter(page.read_text())
        assert meta["chapter"] == 3
        assert meta["impact"] == "major"

    def test_create_page_with_aliases(self, story_dir: Path) -> None:
        aliases = json.dumps(["Al", "Big Al"])
        result = _run_tool(
            "--operation",
            "create",
            "--name",
            "test-story",
            "--slug",
            "albert",
            "--page-type",
            "character",
            "--page-name",
            "Albert",
            "--aliases",
            aliases,
            stories_dir=story_dir,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"

        page = story_dir / "test-story" / "wiki" / "characters" / "albert.md"
        meta, _ = _parse_frontmatter(page.read_text())
        assert meta["aliases"] == ["Al", "Big Al"]

        index = (story_dir / "test-story" / "wiki" / "index.md").read_text()
        assert "Al" in index
        assert "Big Al" in index


class TestUpdate:
    def _create_page(self, story_dir: Path, slug: str = "alice") -> None:
        _run_tool(
            "--operation",
            "create",
            "--name",
            "test-story",
            "--slug",
            slug,
            "--page-type",
            "character",
            "--page-name",
            "Alice",
            "--body",
            "Original body.",
            stories_dir=story_dir,
        )

    def test_update_page_merge_semantics(self, story_dir: Path) -> None:
        self._create_page(story_dir)
        result = _run_tool(
            "--operation",
            "update",
            "--name",
            "test-story",
            "--slug",
            "alice",
            "--frontmatter",
            json.dumps({"role": "antagonist"}),
            stories_dir=story_dir,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"

        page = story_dir / "test-story" / "wiki" / "characters" / "alice.md"
        meta, _ = _parse_frontmatter(page.read_text())
        # Original fields preserved
        assert meta["name"] == "Alice"
        assert meta["type"] == "character"
        assert meta["slug"] == "alice"
        # New field applied
        assert meta["role"] == "antagonist"

    def test_update_page_version_increment(self, story_dir: Path) -> None:
        self._create_page(story_dir)

        page = story_dir / "test-story" / "wiki" / "characters" / "alice.md"
        meta, _ = _parse_frontmatter(page.read_text())
        assert meta["version"] == 1

        # First update -> version 2
        result = _run_tool(
            "--operation",
            "update",
            "--name",
            "test-story",
            "--slug",
            "alice",
            "--frontmatter",
            json.dumps({"role": "scout"}),
            stories_dir=story_dir,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["version"] == 2

        meta, _ = _parse_frontmatter(page.read_text())
        assert meta["version"] == 2

        # Second update -> version 3
        result = _run_tool(
            "--operation",
            "update",
            "--name",
            "test-story",
            "--slug",
            "alice",
            "--frontmatter",
            json.dumps({"role": "leader"}),
            stories_dir=story_dir,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        meta, _ = _parse_frontmatter(page.read_text())
        assert meta["version"] == 3

    def test_update_page_body_replace(self, story_dir: Path) -> None:
        self._create_page(story_dir)

        result = _run_tool(
            "--operation",
            "update",
            "--name",
            "test-story",
            "--slug",
            "alice",
            "--body",
            "replaced",
            stories_dir=story_dir,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"

        page = story_dir / "test-story" / "wiki" / "characters" / "alice.md"
        _, body = _parse_frontmatter(page.read_text())
        assert body.strip() == "replaced"

    def test_update_page_merge_body(self, story_dir: Path) -> None:
        self._create_page(story_dir)

        result = _run_tool(
            "--operation",
            "update",
            "--name",
            "test-story",
            "--slug",
            "alice",
            "--merge-body",
            "appended",
            stories_dir=story_dir,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"

        page = story_dir / "test-story" / "wiki" / "characters" / "alice.md"
        _, body = _parse_frontmatter(page.read_text())
        assert "Original body." in body
        assert "appended" in body

    def test_update_page_index_sync(self, story_dir: Path) -> None:
        self._create_page(story_dir)

        result = _run_tool(
            "--operation",
            "update",
            "--name",
            "test-story",
            "--slug",
            "alice",
            "--frontmatter",
            json.dumps({"name": "Alicia", "aliases": ["Aly"]}),
            stories_dir=story_dir,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"

        index = (story_dir / "test-story" / "wiki" / "index.md").read_text()
        assert "Alicia" in index
        assert "Aly" in index


class TestAppendTimeline:
    def test_append_timeline(self, story_dir: Path) -> None:
        events = json.dumps(
            [
                {"time": "0800", "description": "Dawn breaks", "chapter": 1},
                {"time": "1200", "description": "Noon arrives", "chapter": 1},
            ]
        )
        result = _run_tool(
            "--operation",
            "append-timeline",
            "--name",
            "test-story",
            "--events",
            events,
            stories_dir=story_dir,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"
        assert output["events_added"] == 2

        tl = (
            story_dir / "test-story" / "wiki" / "timeline" / "main-timeline.md"
        ).read_text()
        assert "Dawn breaks" in tl
        assert "Noon arrives" in tl
        # Should be sorted by time — 0800 before 1200
        idx_dawn = tl.index("Dawn breaks")
        idx_noon = tl.index("Noon arrives")
        assert idx_dawn < idx_noon


class TestBatch:
    def test_batch_operations(self, story_dir: Path) -> None:
        payload = json.dumps(
            {
                "creates": [
                    {"slug": "char-a", "page_type": "character", "page_name": "Char A"},
                    {"slug": "loc-b", "page_type": "location", "page_name": "Loc B"},
                ],
                "updates": [],
            }
        )
        result = _run_tool(
            "--operation",
            "batch",
            "--name",
            "test-story",
            "--payload",
            payload,
            stories_dir=story_dir,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"
        assert output["created"] == 2

        assert (story_dir / "test-story" / "wiki" / "characters" / "char-a.md").exists()
        assert (story_dir / "test-story" / "wiki" / "locations" / "loc-b.md").exists()

    def test_batch_with_update(self, story_dir: Path) -> None:
        # Pre-create a page so we can update it in a batch
        _run_tool(
            "--operation",
            "create",
            "--name",
            "test-story",
            "--slug",
            "eve",
            "--page-type",
            "character",
            "--page-name",
            "Eve",
            stories_dir=story_dir,
        )
        payload = json.dumps(
            {
                "creates": [
                    {"slug": "frank", "page_type": "character", "page_name": "Frank"},
                ],
                "updates": [
                    {"slug": "eve", "frontmatter": {"role": "villain"}},
                ],
            }
        )
        result = _run_tool(
            "--operation",
            "batch",
            "--name",
            "test-story",
            "--payload",
            payload,
            stories_dir=story_dir,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["created"] == 1
        assert output["updated"] == 1

    def test_batch_rollback_on_failure(self, story_dir: Path) -> None:
        payload = json.dumps(
            {
                "creates": [
                    {"slug": "first", "page_type": "character", "page_name": "First"},
                    {
                        "slug": "first",
                        "page_type": "character",
                        "page_name": "Duplicate First",
                    },
                ],
                "updates": [],
            }
        )
        result = _run_tool(
            "--operation",
            "batch",
            "--name",
            "test-story",
            "--payload",
            payload,
            stories_dir=story_dir,
        )
        assert result.returncode != 0

        output = json.loads(result.stdout)
        assert output["status"] == "error"
        assert "rollback" in output

        # First page should have been cleaned up
        first_page = story_dir / "test-story" / "wiki" / "characters" / "first.md"
        assert not first_page.exists(), (
            "Rollback should have deleted the first created file"
        )

    def test_batch_with_timeline_events(self, story_dir: Path) -> None:
        """Test batch operation including timeline events."""
        payload = json.dumps(
            {
                "creates": [],
                "updates": [],
                "timeline_events": [
                    {
                        "time": "Day 1",
                        "description": "Something happened",
                        "chapter": 1,
                    },
                    {
                        "time": "Day 2",
                        "description": "Another thing happened",
                        "chapter": 1,
                    },
                ],
            }
        )
        result = _run_tool(
            "--operation",
            "batch",
            "--name",
            "test-story",
            "--payload",
            payload,
            stories_dir=story_dir,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["status"] == "ok"
        assert data["timeline_events"] == 2

        # Verify events in timeline file
        timeline = (
            story_dir / "test-story" / "wiki" / "timeline" / "main-timeline.md"
        ).read_text()
        assert "Something happened" in timeline
        assert "Another thing happened" in timeline


class TestLog:
    def test_log_append(self, story_dir: Path) -> None:
        result = _run_tool(
            "--operation",
            "log",
            "--name",
            "test-story",
            "--message",
            "Test log entry",
            stories_dir=story_dir,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"

        log = (story_dir / "test-story" / "wiki" / "log.md").read_text()
        assert "Test log entry" in log
        # Should contain an ISO timestamp
        assert "T" in log  # ISO format has T separator


class TestChromaDB:
    def test_chromadb_upsert_on_create(self, chromadb_dir: Path) -> None:
        import chromadb

        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as temp_dir:
            stories_dir = Path(temp_dir) / "stories"
            story = stories_dir / "test-story"
            wiki = story / "wiki"
            wiki.mkdir(parents=True)
            for subdir in [
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
            ]:
                (wiki / subdir).mkdir()
            (wiki / "index.md").write_text(
                "# Wiki Index\n\n<!-- slug | type | name | aliases -->\n\n"
            )
            (wiki / "log.md").write_text("# Wiki Change Log\n")
            (wiki / "timeline" / "main-timeline.md").write_text("# Main Timeline\n\n")

            result = _run_tool(
                "--operation",
                "create",
                "--name",
                "test-story",
                "--slug",
                "chroma-char",
                "--page-type",
                "character",
                "--page-name",
                "Chroma Char",
                "--body",
                "A character for ChromaDB testing.",
                stories_dir=stories_dir,
                chromadb_dir=chromadb_dir,
            )
            assert result.returncode == 0, f"stderr: {result.stderr}"

            client = chromadb.PersistentClient(path=str(chromadb_dir))
            collection = client.get_collection(name="wiki-test-story")
            docs = collection.get(ids=["chroma-char"])
            assert len(docs["ids"]) == 1
            assert docs["ids"][0] == "chroma-char"

    def test_chromadb_upsert_carries_source_metadata(self, chromadb_dir: Path) -> None:
        import chromadb

        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as temp_dir:
            stories_dir = Path(temp_dir) / "stories"
            story = stories_dir / "test-story"
            wiki = story / "wiki"
            wiki.mkdir(parents=True)
            for subdir in [
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
            ]:
                (wiki / subdir).mkdir()
            (wiki / "index.md").write_text(
                "# Wiki Index\n\n<!-- slug | type | name | aliases -->\n\n"
            )
            (wiki / "log.md").write_text("# Wiki Change Log\n")
            (wiki / "timeline" / "main-timeline.md").write_text("# Main Timeline\n\n")

            result = _run_tool(
                "--operation",
                "create",
                "--name",
                "test-story",
                "--slug",
                "source-meta-char",
                "--page-type",
                "character",
                "--page-name",
                "Source Meta Char",
                "--body",
                "Metadata-backed body.",
                stories_dir=stories_dir,
                chromadb_dir=chromadb_dir,
            )
            assert result.returncode == 0, f"stderr: {result.stderr}"

            client = chromadb.PersistentClient(path=str(chromadb_dir))
            collection = client.get_collection(name="wiki-test-story")
            docs = collection.get(ids=["source-meta-char"], include=["metadatas"])
            metadata = docs["metadatas"][0]

            assert metadata["source_path"].endswith(".md")
            assert isinstance(metadata["source_mtime"], float)
            assert isinstance(metadata["source_sha256"], str)
            assert len(metadata["source_sha256"]) == 64


class TestValidation:
    def test_path_traversal_blocked(self, story_dir: Path) -> None:
        result = _run_tool(
            "--operation",
            "create",
            "--name",
            "test-story",
            "--slug",
            "../etc/passwd",
            "--page-type",
            "character",
            "--page-name",
            "Evil",
            stories_dir=story_dir,
        )
        assert result.returncode != 0

    def test_invalid_page_type_rejected(self, story_dir: Path) -> None:
        result = _run_tool(
            "--operation",
            "create",
            "--name",
            "test-story",
            "--slug",
            "something",
            "--page-type",
            "invalid_type",
            "--page-name",
            "Something",
            stories_dir=story_dir,
        )
        assert result.returncode != 0
        assert "invalid page type" in result.stderr.lower()

    def test_create_duplicate_slug_rejected(self, story_dir: Path) -> None:
        # Create first
        result = _run_tool(
            "--operation",
            "create",
            "--name",
            "test-story",
            "--slug",
            "dupetest",
            "--page-type",
            "character",
            "--page-name",
            "First",
            stories_dir=story_dir,
        )
        assert result.returncode == 0

        # Duplicate
        result = _run_tool(
            "--operation",
            "create",
            "--name",
            "test-story",
            "--slug",
            "dupetest",
            "--page-type",
            "character",
            "--page-name",
            "Second",
            stories_dir=story_dir,
        )
        assert result.returncode != 0
        assert "already exists" in result.stderr
