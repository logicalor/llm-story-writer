"""Verification tests for issue #325 Chroma sync read paths."""

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

from src.tools._chroma_sync import compute_fingerprint, upsert_from_source

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAG_QUERY_SCRIPT = str(PROJECT_ROOT / "src" / "tools" / "rag_query.py")
WIKI_SEARCH_SCRIPT = str(PROJECT_ROOT / "src" / "tools" / "wiki_search.py")
TIMEOUT_SECONDS = 20


def _run_tool(
    script: str,
    *args: str,
    stories_dir: Path | None = None,
    chromadb_dir: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
    if stories_dir is not None:
        env["STORIES_DIR"] = str(stories_dir)
    if chromadb_dir is not None:
        env["CHROMADB_DIR"] = str(chromadb_dir)

    try:
        return subprocess.run(
            [sys.executable, script, *args],
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
            f"Tool timed out after {TIMEOUT_SECONDS}s.\n"
            f"stdout (truncated):\n{stdout[-2000:]}\n"
            f"stderr (truncated):\n{stderr[-2000:]}"
        )


def _run_rag_query(
    *args: str,
    stories_dir: Path,
    chromadb_dir: Path,
) -> subprocess.CompletedProcess[str]:
    return _run_tool(
        RAG_QUERY_SCRIPT,
        *args,
        stories_dir=stories_dir,
        chromadb_dir=chromadb_dir,
    )


def _run_wiki_search(
    *args: str,
    stories_dir: Path,
    chromadb_dir: Path,
) -> subprocess.CompletedProcess[str]:
    return _run_tool(
        WIKI_SEARCH_SCRIPT,
        *args,
        stories_dir=stories_dir,
        chromadb_dir=chromadb_dir,
    )


def _read_json(result: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(result.stdout)


def _write_repo_source(base_dir: Path, filename: str, content: str) -> tuple[Path, str]:
    path = base_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path, str(path.relative_to(PROJECT_ROOT))


def _force_mtime_change(path: Path) -> None:
    updated_mtime = path.stat().st_mtime + 10
    os.utime(path, (updated_mtime, updated_mtime))


def _get_story_doc(chromadb_dir: Path, story_name: str, doc_id: str) -> dict:
    client = chromadb.PersistentClient(path=str(chromadb_dir))
    collection = client.get_collection(name=f"stories-{story_name}")
    return collection.get(ids=[doc_id], include=["documents", "metadatas"])


@pytest.fixture()
def cli_env(tmp_path: Path) -> tuple[Path, Path, str]:
    stories_dir = tmp_path / "stories"
    story_name = "test-story"
    (stories_dir / story_name).mkdir(parents=True)
    chromadb_dir = tmp_path / "chromadb"
    chromadb_dir.mkdir()
    return stories_dir, chromadb_dir, story_name


@pytest.fixture()
def repo_source_dir() -> Path:
    source_dir = PROJECT_ROOT / "stories" / f"_issue_325_{uuid4().hex}"
    source_dir.mkdir(parents=True, exist_ok=True)
    try:
        yield source_dir
    finally:
        shutil.rmtree(source_dir, ignore_errors=True)


class TestRagQueryIndex:
    def test_index_synthetic_records_empty_source_path(
        self,
        cli_env: tuple[Path, Path, str],
    ) -> None:
        stories_dir, chromadb_dir, story_name = cli_env

        result = _run_rag_query(
            "--operation",
            "index",
            "--name",
            story_name,
            "--doc-id",
            "outline",
            "--content",
            "Synthetic body.",
            stories_dir=stories_dir,
            chromadb_dir=chromadb_dir,
        )

        assert result.returncode == 0, result.stderr
        stored = _get_story_doc(chromadb_dir, story_name, "outline")
        metadata = stored["metadatas"][0]
        assert metadata["source_path"] == ""

    def test_index_with_source_path_records_metadata(
        self,
        cli_env: tuple[Path, Path, str],
        repo_source_dir: Path,
    ) -> None:
        stories_dir, chromadb_dir, story_name = cli_env
        source_file, source_path = _write_repo_source(
            repo_source_dir,
            "outline.md",
            "Body from source file.",
        )
        expected_mtime, expected_sha256 = compute_fingerprint(source_file)

        result = _run_rag_query(
            "--operation",
            "index",
            "--name",
            story_name,
            "--doc-id",
            "outline",
            "--source-path",
            source_path,
            stories_dir=stories_dir,
            chromadb_dir=chromadb_dir,
        )

        assert result.returncode == 0, result.stderr
        stored = _get_story_doc(chromadb_dir, story_name, "outline")
        metadata = stored["metadatas"][0]
        assert metadata["source_path"] == source_path
        assert metadata["source_mtime"] == expected_mtime
        assert metadata["source_sha256"] == expected_sha256

    def test_index_without_content_or_source_path_errors(
        self,
        cli_env: tuple[Path, Path, str],
    ) -> None:
        stories_dir, chromadb_dir, story_name = cli_env

        result = _run_rag_query(
            "--operation",
            "index",
            "--name",
            story_name,
            "--doc-id",
            "outline",
            stories_dir=stories_dir,
            chromadb_dir=chromadb_dir,
        )

        assert result.returncode == 2
        assert "--content or --source-path is required" in result.stderr

    def test_index_with_source_path_only_reads_body_from_file(
        self,
        cli_env: tuple[Path, Path, str],
        repo_source_dir: Path,
    ) -> None:
        stories_dir, chromadb_dir, story_name = cli_env
        source_file, source_path = _write_repo_source(
            repo_source_dir,
            "chapter.md",
            "Known source body for indexing.",
        )

        result = _run_rag_query(
            "--operation",
            "index",
            "--name",
            story_name,
            "--doc-id",
            "chapter-1",
            "--source-path",
            source_path,
            "--content-type",
            "chapter",
            stories_dir=stories_dir,
            chromadb_dir=chromadb_dir,
        )

        assert result.returncode == 0, result.stderr
        stored = _get_story_doc(chromadb_dir, story_name, "chapter-1")
        assert stored["documents"][0] == source_file.read_text()


class TestRagQueryStaleRefresh:
    def test_query_refreshes_stale_entry_and_returns_updated_body(
        self,
        cli_env: tuple[Path, Path, str],
        repo_source_dir: Path,
    ) -> None:
        stories_dir, chromadb_dir, story_name = cli_env
        source_file, source_path = _write_repo_source(
            repo_source_dir,
            "refresh.md",
            "original body",
        )

        index_result = _run_rag_query(
            "--operation",
            "index",
            "--name",
            story_name,
            "--doc-id",
            "outline",
            "--source-path",
            source_path,
            stories_dir=stories_dir,
            chromadb_dir=chromadb_dir,
        )
        assert index_result.returncode == 0, index_result.stderr

        source_file.write_text("updated body")
        _force_mtime_change(source_file)

        query_result = _run_rag_query(
            "--operation",
            "query",
            "--name",
            story_name,
            "--query",
            "body",
            stories_dir=stories_dir,
            chromadb_dir=chromadb_dir,
        )

        assert query_result.returncode == 0, query_result.stderr
        output = _read_json(query_result)
        assert output["results"][0]["doc_id"] == "outline"
        assert "updated body" in output["results"][0]["excerpt"]
        assert "original body" not in output["results"][0]["excerpt"]


class TestWikiSearchStaleRefresh:
    def test_semantic_search_refreshes_stale_wiki_entry(
        self,
        cli_env: tuple[Path, Path, str],
        repo_source_dir: Path,
    ) -> None:
        stories_dir, chromadb_dir, story_name = cli_env
        source_file, source_path = _write_repo_source(
            repo_source_dir,
            "wiki/hero.md",
            "original wiki body",
        )
        client = chromadb.PersistentClient(path=str(chromadb_dir))
        collection = client.get_or_create_collection(name=f"wiki-{story_name}")
        upsert_from_source(
            collection,
            doc_id="hero",
            source_path=source_path,
            extra_metadata={"type": "character", "slug": "hero"},
        )

        source_file.write_text("updated wiki body")
        _force_mtime_change(source_file)

        result = _run_wiki_search(
            "--operation",
            "semantic",
            "--name",
            story_name,
            "--query",
            "something",
            stories_dir=stories_dir,
            chromadb_dir=chromadb_dir,
        )

        assert result.returncode == 0, result.stderr
        output = _read_json(result)
        assert output["results"][0]["slug"] == "hero"
        assert "updated wiki body" in output["results"][0]["excerpt"]
        assert "original wiki body" not in output["results"][0]["excerpt"]

    def test_metadata_search_refreshes_stale_wiki_entry(
        self,
        cli_env: tuple[Path, Path, str],
        repo_source_dir: Path,
    ) -> None:
        stories_dir, chromadb_dir, story_name = cli_env
        source_file, source_path = _write_repo_source(
            repo_source_dir,
            "wiki/character.md",
            "original character wiki body",
        )
        client = chromadb.PersistentClient(path=str(chromadb_dir))
        collection = client.get_or_create_collection(name=f"wiki-{story_name}")
        upsert_from_source(
            collection,
            doc_id="character-page",
            source_path=source_path,
            extra_metadata={"type": "character", "slug": "character-page"},
        )

        source_file.write_text("updated character wiki body")
        _force_mtime_change(source_file)

        result = _run_wiki_search(
            "--operation",
            "metadata",
            "--name",
            story_name,
            "--where",
            '{"type": "character"}',
            stories_dir=stories_dir,
            chromadb_dir=chromadb_dir,
        )

        assert result.returncode == 0, result.stderr
        output = _read_json(result)
        assert output["results"][0]["slug"] == "character-page"
        assert "updated character wiki body" in output["results"][0]["excerpt"]
        assert "original character wiki body" not in output["results"][0]["excerpt"]
