from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import chromadb
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

import tools._chroma_sync as chroma_sync_module
import tools.rag_reconcile as rag_reconcile
from tools._chroma_sync import ReconcileReport, upsert_from_source

TOOL_SCRIPT = str(PROJECT_ROOT / "src" / "tools" / "rag_reconcile.py")


@pytest.fixture()
def source_project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    project_root = tmp_path / "project"
    stories_dir = project_root / "stories"
    stories_dir.mkdir(parents=True)

    monkeypatch.setattr(chroma_sync_module, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(rag_reconcile, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(rag_reconcile, "CHROMA_PROJECT_ROOT", project_root)
    monkeypatch.setattr(rag_reconcile, "STORIES_DIR", stories_dir)

    return project_root


@pytest.fixture()
def chromadb_dir(tmp_path: Path) -> Path:
    path = tmp_path / "chromadb"
    path.mkdir()
    return path


def _client(chromadb_dir: Path):
    return chromadb.PersistentClient(path=str(chromadb_dir))


def _collection(chromadb_dir: Path, name: str):
    return _client(chromadb_dir).get_or_create_collection(name=name)


def _story_dir(project_root: Path, story_name: str) -> Path:
    story_dir = project_root / "stories" / story_name
    story_dir.mkdir(parents=True, exist_ok=True)
    return story_dir


def _write_markdown(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _set_mtime(path: Path, offset_seconds: float) -> None:
    mtime = path.stat().st_mtime + offset_seconds
    os.utime(path, (mtime, mtime))


def _run_tool(
    *args: str,
    chromadb_dir: Path,
    stories_dir: Path,
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ}
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    env["STORIES_DIR"] = str(stories_dir)
    env["CHROMADB_DIR"] = str(chromadb_dir)
    try:
        return subprocess.run(
            [sys.executable, TOOL_SCRIPT, *args],
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        pytest.fail(
            "rag_reconcile.py timed out after 10s.\n"
            f"stdout:\n{stdout[-2000:]}\n"
            f"stderr:\n{stderr[-2000:]}"
        )


@pytest.fixture()
def cli_story_dir(tmp_path: Path) -> Path:
    story_name = f"test-rag-reconcile-cli-{tmp_path.name.replace('_', '-')}"
    story_dir = PROJECT_ROOT / "stories" / story_name
    if story_dir.exists():
        shutil.rmtree(story_dir)
    story_dir.mkdir(parents=True)
    try:
        yield story_dir
    finally:
        if story_dir.exists():
            shutil.rmtree(story_dir)


class TestWikiReconcile:
    def test_wiki_reconcile_adds_new_entries(
        self, source_project_root: Path, chromadb_dir: Path
    ) -> None:
        story_dir = _story_dir(source_project_root, "my-story")
        _write_markdown(story_dir / "wiki" / "characters" / "hero.md", "Hero body")
        _write_markdown(story_dir / "wiki" / "locations" / "city.md", "City body")

        reports = rag_reconcile.reconcile_story(
            "my-story", "wiki", False, str(chromadb_dir)
        )

        result = _collection(chromadb_dir, "wiki-my-story").get(include=["documents"])
        assert reports["wiki"].added == 2
        assert set(result["ids"]) == {"hero", "city"}

    def test_wiki_reconcile_updates_stale_entries(
        self, source_project_root: Path, chromadb_dir: Path
    ) -> None:
        story_dir = _story_dir(source_project_root, "my-story")
        source_path = _write_markdown(
            story_dir / "wiki" / "characters" / "hero.md", "Old hero body"
        )
        collection = _collection(chromadb_dir, "wiki-my-story")
        upsert_from_source(
            collection,
            doc_id="hero",
            source_path=str(source_path.relative_to(source_project_root)),
            extra_metadata={},
        )

        source_path.write_text("New hero body", encoding="utf-8")
        _set_mtime(source_path, 10)

        reports = rag_reconcile.reconcile_story(
            "my-story", "wiki", False, str(chromadb_dir)
        )

        result = collection.get(ids=["hero"], include=["documents"])
        assert reports["wiki"].updated == 1
        assert result["documents"][0] == "New hero body"

    def test_wiki_reconcile_deletes_orphaned_entries(
        self, source_project_root: Path, chromadb_dir: Path
    ) -> None:
        story_dir = _story_dir(source_project_root, "my-story")
        source_path = _write_markdown(
            story_dir / "wiki" / "characters" / "hero.md", "Hero body"
        )
        collection = _collection(chromadb_dir, "wiki-my-story")
        upsert_from_source(
            collection,
            doc_id="hero",
            source_path=str(source_path.relative_to(source_project_root)),
            extra_metadata={},
        )
        source_path.unlink()

        reports = rag_reconcile.reconcile_story(
            "my-story", "wiki", False, str(chromadb_dir)
        )

        result = collection.get(include=["documents"])
        assert reports["wiki"].deleted == 1
        assert result["ids"] == []

    def test_wiki_reconcile_unchanged_entries(
        self, source_project_root: Path, chromadb_dir: Path
    ) -> None:
        story_dir = _story_dir(source_project_root, "my-story")
        source_path = _write_markdown(
            story_dir / "wiki" / "characters" / "hero.md", "Stable hero body"
        )
        collection = _collection(chromadb_dir, "wiki-my-story")
        upsert_from_source(
            collection,
            doc_id="hero",
            source_path=str(source_path.relative_to(source_project_root)),
            extra_metadata={},
        )

        reports = rag_reconcile.reconcile_story(
            "my-story", "wiki", False, str(chromadb_dir)
        )

        assert reports["wiki"].unchanged == 1
        assert reports["wiki"].added == 0
        assert reports["wiki"].updated == 0
        assert reports["wiki"].deleted == 0

    def test_wiki_reconcile_dry_run_no_writes(
        self, source_project_root: Path, chromadb_dir: Path
    ) -> None:
        story_dir = _story_dir(source_project_root, "my-story")
        _write_markdown(story_dir / "wiki" / "characters" / "hero.md", "Hero body")

        reports = rag_reconcile.reconcile_story(
            "my-story", "wiki", True, str(chromadb_dir)
        )

        assert reports["wiki"].added == 1
        assert rag_reconcile._get_collection(str(chromadb_dir), "wiki-my-story") is None

    def test_wiki_reconcile_missing_wiki_dir_skips_gracefully(
        self, source_project_root: Path, chromadb_dir: Path
    ) -> None:
        _story_dir(source_project_root, "my-story")

        reports = rag_reconcile.reconcile_story(
            "my-story", "wiki", False, str(chromadb_dir)
        )

        assert reports["wiki"] == ReconcileReport()


class TestStoriesReconcile:
    def test_stories_reconcile_updates_stale_source(
        self, source_project_root: Path, chromadb_dir: Path
    ) -> None:
        _story_dir(source_project_root, "my-story")
        source_path = _write_markdown(
            source_project_root / "stories" / "my-story" / "chapters" / "chapter-1.md",
            "Old chapter body",
        )
        collection = _collection(chromadb_dir, "stories-my-story")
        upsert_from_source(
            collection,
            doc_id="chapter-1",
            source_path=str(source_path.relative_to(source_project_root)),
            extra_metadata={"story": "my-story", "content_type": "chapter"},
        )

        source_path.write_text("New chapter body", encoding="utf-8")
        _set_mtime(source_path, 10)

        reports = rag_reconcile.reconcile_story(
            "my-story", "stories", False, str(chromadb_dir)
        )

        result = collection.get(ids=["chapter-1"], include=["documents"])
        assert reports["stories"].updated == 1
        assert result["documents"][0] == "New chapter body"

    def test_stories_reconcile_deletes_orphan(
        self, source_project_root: Path, chromadb_dir: Path
    ) -> None:
        _story_dir(source_project_root, "my-story")
        source_path = _write_markdown(
            source_project_root / "stories" / "my-story" / "chapters" / "chapter-1.md",
            "Chapter body",
        )
        collection = _collection(chromadb_dir, "stories-my-story")
        upsert_from_source(
            collection,
            doc_id="chapter-1",
            source_path=str(source_path.relative_to(source_project_root)),
            extra_metadata={"story": "my-story", "content_type": "chapter"},
        )
        source_path.unlink()

        reports = rag_reconcile.reconcile_story(
            "my-story", "stories", False, str(chromadb_dir)
        )

        result = collection.get(include=["documents"])
        assert reports["stories"].deleted == 1
        assert result["ids"] == []

    def test_stories_reconcile_skips_synthetic_entries(
        self, source_project_root: Path, chromadb_dir: Path
    ) -> None:
        _story_dir(source_project_root, "my-story")
        collection = _collection(chromadb_dir, "stories-my-story")
        upsert_from_source(
            collection,
            doc_id="synthetic-summary",
            source_path="",
            extra_metadata={"story": "my-story", "content_type": "summary"},
            body="Synthetic body",
        )

        reports = rag_reconcile.reconcile_story(
            "my-story", "stories", False, str(chromadb_dir)
        )

        result = collection.get(ids=["synthetic-summary"], include=["documents"])
        assert reports["stories"].unchanged == 1
        assert reports["stories"].deleted == 0
        assert result["documents"][0] == "Synthetic body"

    def test_stories_reconcile_dry_run_no_writes(
        self, source_project_root: Path, chromadb_dir: Path
    ) -> None:
        _story_dir(source_project_root, "my-story")
        source_path = _write_markdown(
            source_project_root / "stories" / "my-story" / "chapters" / "chapter-1.md",
            "Old chapter body",
        )
        collection = _collection(chromadb_dir, "stories-my-story")
        upsert_from_source(
            collection,
            doc_id="chapter-1",
            source_path=str(source_path.relative_to(source_project_root)),
            extra_metadata={"story": "my-story", "content_type": "chapter"},
        )

        source_path.write_text("New chapter body", encoding="utf-8")
        _set_mtime(source_path, 10)

        reports = rag_reconcile.reconcile_story(
            "my-story", "stories", True, str(chromadb_dir)
        )

        result = collection.get(ids=["chapter-1"], include=["documents"])
        assert reports["stories"].updated == 1
        assert result["documents"][0] == "Old chapter body"


class TestReconcileStory:
    def test_reconcile_story_both_collections(
        self, source_project_root: Path, chromadb_dir: Path
    ) -> None:
        story_dir = _story_dir(source_project_root, "my-story")
        _write_markdown(story_dir / "wiki" / "characters" / "hero.md", "Hero body")

        reports = rag_reconcile.reconcile_story(
            "my-story", None, False, str(chromadb_dir)
        )

        assert set(reports) == {"wiki", "stories"}

    def test_reconcile_story_wiki_only(
        self, source_project_root: Path, chromadb_dir: Path
    ) -> None:
        story_dir = _story_dir(source_project_root, "my-story")
        _write_markdown(story_dir / "wiki" / "characters" / "hero.md", "Hero body")

        reports = rag_reconcile.reconcile_story(
            "my-story", "wiki", False, str(chromadb_dir)
        )

        assert set(reports) == {"wiki"}

    def test_reconcile_story_stories_only(
        self, source_project_root: Path, chromadb_dir: Path
    ) -> None:
        _story_dir(source_project_root, "my-story")

        reports = rag_reconcile.reconcile_story(
            "my-story", "stories", False, str(chromadb_dir)
        )

        assert set(reports) == {"stories"}

    def test_reconcile_story_empty_collections_skip_gracefully(
        self, source_project_root: Path, chromadb_dir: Path
    ) -> None:
        _story_dir(source_project_root, "my-story")

        reports = rag_reconcile.reconcile_story(
            "my-story", None, False, str(chromadb_dir)
        )

        assert reports["wiki"] == ReconcileReport()
        assert reports["stories"] == ReconcileReport()


class TestFormatReports:
    def test_format_reports_contains_story_name(self) -> None:
        output = rag_reconcile.format_reports(
            "my-story", {"wiki": ReconcileReport(added=1)}
        )

        assert "Story: my-story" in output

    def test_format_reports_shows_all_counts(self) -> None:
        output = rag_reconcile.format_reports(
            "my-story",
            {"wiki": ReconcileReport(added=1, updated=2, deleted=3, unchanged=4)},
        )

        assert "Added:" in output
        assert "Updated:" in output
        assert "Deleted:" in output
        assert "Unchanged:" in output


class TestCLI:
    def test_cli_dry_run_flag(self, cli_story_dir: Path, chromadb_dir: Path) -> None:
        _write_markdown(cli_story_dir / "wiki" / "Dry run.md", "Preview only")

        result = _run_tool(
            "--story",
            cli_story_dir.name,
            "--dry-run",
            chromadb_dir=chromadb_dir,
            stories_dir=PROJECT_ROOT / "stories",
        )

        assert result.returncode == 0, result.stderr
        assert "Dry run" in result.stdout

    def test_cli_json_flag(self, cli_story_dir: Path, chromadb_dir: Path) -> None:
        _write_markdown(cli_story_dir / "wiki" / "characters" / "hero.md", "Hero body")

        result = _run_tool(
            "--story",
            cli_story_dir.name,
            "--json",
            chromadb_dir=chromadb_dir,
            stories_dir=PROJECT_ROOT / "stories",
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["story"] == cli_story_dir.name
        assert set(payload) >= {"story", "wiki", "stories"}
        assert set(payload["wiki"]) >= {
            "added",
            "updated",
            "deleted",
            "unchanged",
            "log",
        }

    def test_cli_missing_story_and_all_exits_nonzero(self, chromadb_dir: Path) -> None:
        result = _run_tool(
            chromadb_dir=chromadb_dir,
            stories_dir=PROJECT_ROOT / "stories",
        )

        assert result.returncode == 2
        assert "--story is required unless --all is set" in result.stderr
