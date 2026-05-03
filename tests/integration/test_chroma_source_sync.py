from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import chromadb
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

import tools._chroma_sync as chroma_sync_module
import tools.rag_reconcile as rag_reconcile
from tools._chroma_sync import upsert_from_source

_TEST_STORY = f"test-327-{uuid4().hex[:8]}"
WIKI_SEARCH_SCRIPT = str(PROJECT_ROOT / "src" / "tools" / "wiki_search.py")
TIMEOUT_SECONDS = 20


@pytest.fixture()
def chromadb_dir(tmp_path: Path) -> Path:
    path = tmp_path / "chromadb"
    path.mkdir()
    return path


@pytest.fixture()
def story_dir() -> Path:
    path = PROJECT_ROOT / "stories" / _TEST_STORY
    if path.exists():
        shutil.rmtree(path)
    (path / "wiki" / "characters").mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture()
def patched_sync_roots(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chroma_sync_module, "PROJECT_ROOT", PROJECT_ROOT)
    monkeypatch.setattr(rag_reconcile, "CHROMA_PROJECT_ROOT", PROJECT_ROOT)
    monkeypatch.setattr(rag_reconcile, "STORIES_DIR", PROJECT_ROOT / "stories")


def _wiki_collection(chromadb_dir: Path):  # type: ignore[no-untyped-def]
    client = chromadb.PersistentClient(path=str(chromadb_dir))
    return client.get_or_create_collection(name=f"wiki-{_TEST_STORY}")


def _run_wiki_search(
    chromadb_dir: Path, *args: str
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "CHROMADB_DIR": str(chromadb_dir),
        "STORIES_DIR": str(PROJECT_ROOT / "stories"),
        "PYTHONPATH": str(PROJECT_ROOT),
    }
    try:
        return subprocess.run(
            [sys.executable, WIKI_SEARCH_SCRIPT, *args],
            capture_output=True,
            text=True,
            env=env,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = (
            (exc.stdout or b"").decode(errors="replace")
            if isinstance(exc.stdout, bytes)
            else (exc.stdout or "")
        )
        stderr = (
            (exc.stderr or b"").decode(errors="replace")
            if isinstance(exc.stderr, bytes)
            else (exc.stderr or "")
        )
        pytest.fail(
            f"wiki_search.py timed out after {TIMEOUT_SECONDS}s.\n"
            f"stdout (truncated):\n{stdout[-2000:]}\n"
            f"stderr (truncated):\n{stderr[-2000:]}"
        )


def _bump_mtime(path: Path) -> None:
    updated_mtime = path.stat().st_mtime + 10
    os.utime(path, (updated_mtime, updated_mtime))


def test_edit_and_retrieve(
    story_dir: Path,
    chromadb_dir: Path,
    patched_sync_roots: None,
) -> None:
    hero_md = story_dir / "wiki" / "characters" / "hero.md"
    hero_md.write_text("The hero has blue eyes.", encoding="utf-8")

    collection = _wiki_collection(chromadb_dir)
    upsert_from_source(collection, "hero", str(hero_md), {})

    hero_md.write_text("The hero has green eyes.", encoding="utf-8")
    _bump_mtime(hero_md)

    result = _run_wiki_search(
        chromadb_dir,
        "--operation",
        "semantic",
        "--name",
        _TEST_STORY,
        "--query",
        "hero eye color",
        "--n-results",
        "1",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert len(payload["results"]) == 1
    assert payload["results"][0]["slug"] == "hero"
    assert "green eyes" in payload["results"][0]["excerpt"]


def test_orphan_deletion_via_reconcile(
    story_dir: Path,
    chromadb_dir: Path,
    patched_sync_roots: None,
) -> None:
    ghost_md = story_dir / "wiki" / "characters" / "ghost.md"
    ghost_md.write_text("A ghost character.", encoding="utf-8")

    collection = _wiki_collection(chromadb_dir)
    upsert_from_source(collection, "ghost", str(ghost_md), {})

    ghost_md.unlink()

    reports = rag_reconcile.reconcile_story(
        _TEST_STORY,
        "wiki",
        dry_run=False,
        chromadb_dir=str(chromadb_dir),
    )

    assert reports["wiki"].deleted == 1
    assert collection.get(ids=["ghost"])["ids"] == []


def test_reconcile_is_idempotent(
    story_dir: Path,
    chromadb_dir: Path,
    patched_sync_roots: None,
) -> None:
    knight_md = story_dir / "wiki" / "characters" / "knight.md"
    knight_md.write_text("A steadfast knight.", encoding="utf-8")

    collection = _wiki_collection(chromadb_dir)
    upsert_from_source(collection, "knight", str(knight_md), {})

    first_reports = rag_reconcile.reconcile_story(
        _TEST_STORY,
        "wiki",
        dry_run=False,
        chromadb_dir=str(chromadb_dir),
    )
    second_reports = rag_reconcile.reconcile_story(
        _TEST_STORY,
        "wiki",
        dry_run=False,
        chromadb_dir=str(chromadb_dir),
    )

    assert first_reports["wiki"].deleted == 0
    assert second_reports["wiki"].added == 0
    assert second_reports["wiki"].updated == 0
    assert second_reports["wiki"].deleted == 0
