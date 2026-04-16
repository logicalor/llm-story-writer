"""Verification tests for Issue #24 — rag-query Tool.

Confirms src/tools/rag_query.py correctly indexes and queries story
content via ChromaDB with per-story collections.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_SCRIPT = str(PROJECT_ROOT / "src" / "tools" / "rag_query.py")


def _run_tool(
    *args: str,
    chromadb_dir: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ}
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    if chromadb_dir is not None:
        env["CHROMADB_DIR"] = str(chromadb_dir)
    return subprocess.run(
        [sys.executable, TOOL_SCRIPT, *args],
        capture_output=True,
        text=True,
        env=env,
    )


@pytest.fixture()
def chromadb_dir(tmp_path: Path) -> Path:
    d = tmp_path / "chromadb"
    d.mkdir()
    return d


class TestIndex:
    def test_index_creates_collection(self, chromadb_dir: Path) -> None:
        result = _run_tool(
            "--operation", "index",
            "--name", "my-story",
            "--doc-id", "outline",
            "--content", "A tale of two cities in a war-torn land.",
            "--content-type", "outline",
            chromadb_dir=chromadb_dir,
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["status"] == "ok"
        assert data["indexed"] == "outline"
        assert data["story"] == "my-story"
        assert data["content_type"] == "outline"

    def test_index_chapter_with_chapter_num(self, chromadb_dir: Path) -> None:
        result = _run_tool(
            "--operation", "index",
            "--name", "my-story",
            "--doc-id", "chapter-1",
            "--content", "Chapter one content about the hero's journey.",
            "--content-type", "chapter",
            "--chapter-num", "1",
            chromadb_dir=chromadb_dir,
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["status"] == "ok"
        assert data["indexed"] == "chapter-1"

    def test_index_upserts_on_duplicate_id(self, chromadb_dir: Path) -> None:
        """Second index with same doc-id should succeed (upsert semantic)."""
        for content in ["First version of outline.", "Updated outline content."]:
            result = _run_tool(
                "--operation", "index",
                "--name", "my-story",
                "--doc-id", "outline",
                "--content", content,
                "--content-type", "outline",
                chromadb_dir=chromadb_dir,
            )
            assert result.returncode == 0, result.stderr

    def test_index_default_content_type(self, chromadb_dir: Path) -> None:
        """Default content type should be 'outline'."""
        result = _run_tool(
            "--operation", "index",
            "--name", "my-story",
            "--doc-id", "outline",
            "--content", "Some outline text.",
            chromadb_dir=chromadb_dir,
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["content_type"] == "outline"

    def test_index_missing_doc_id_errors(self, chromadb_dir: Path) -> None:
        result = _run_tool(
            "--operation", "index",
            "--name", "my-story",
            "--content", "Some content",
            chromadb_dir=chromadb_dir,
        )
        assert result.returncode != 0

    def test_index_missing_content_errors(self, chromadb_dir: Path) -> None:
        result = _run_tool(
            "--operation", "index",
            "--name", "my-story",
            "--doc-id", "outline",
            chromadb_dir=chromadb_dir,
        )
        assert result.returncode != 0

    def test_index_invalid_content_type_errors(self, chromadb_dir: Path) -> None:
        result = _run_tool(
            "--operation", "index",
            "--name", "my-story",
            "--doc-id", "outline",
            "--content", "Some content",
            "--content-type", "invalid-type",
            chromadb_dir=chromadb_dir,
        )
        assert result.returncode != 0


class TestQuery:
    def test_query_empty_collection_returns_empty_results(
        self, chromadb_dir: Path
    ) -> None:
        result = _run_tool(
            "--operation", "query",
            "--name", "my-story",
            "--query", "hero journey",
            chromadb_dir=chromadb_dir,
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["status"] == "ok"
        assert data["results"] == []

    def test_query_returns_indexed_content(self, chromadb_dir: Path) -> None:
        # Index content first
        _run_tool(
            "--operation", "index",
            "--name", "my-story",
            "--doc-id", "character-elena",
            "--content", "Elena is a fierce warrior from the northern mountains.",
            "--content-type", "character",
            chromadb_dir=chromadb_dir,
        )

        result = _run_tool(
            "--operation", "query",
            "--name", "my-story",
            "--query", "warrior character",
            chromadb_dir=chromadb_dir,
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["status"] == "ok"
        assert len(data["results"]) >= 1
        result_ids = [r["doc_id"] for r in data["results"]]
        assert "character-elena" in result_ids

    def test_query_result_includes_score_and_excerpt(
        self, chromadb_dir: Path
    ) -> None:
        _run_tool(
            "--operation", "index",
            "--name", "my-story",
            "--doc-id", "outline",
            "--content", "A hero must save the kingdom from darkness.",
            "--content-type", "outline",
            chromadb_dir=chromadb_dir,
        )

        result = _run_tool(
            "--operation", "query",
            "--name", "my-story",
            "--query", "hero save kingdom",
            chromadb_dir=chromadb_dir,
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert len(data["results"]) >= 1
        r = data["results"][0]
        assert "doc_id" in r
        assert "score" in r
        assert "excerpt" in r
        assert "metadata" in r
        assert isinstance(r["score"], float)
        assert 0.0 <= r["score"] <= 1.0

    def test_query_filters_by_content_type(self, chromadb_dir: Path) -> None:
        # Index multiple content types
        for doc_id, ctype, content in [
            ("outline", "outline", "The outline of the epic story."),
            ("chapter-1", "chapter", "The hero walks into the dark forest."),
            ("character-bob", "character", "Bob is a brave knight."),
        ]:
            _run_tool(
                "--operation", "index",
                "--name", "my-story",
                "--doc-id", doc_id,
                "--content", content,
                "--content-type", ctype,
                chromadb_dir=chromadb_dir,
            )

        result = _run_tool(
            "--operation", "query",
            "--name", "my-story",
            "--query", "brave hero story",
            "--content-type", "character",
            chromadb_dir=chromadb_dir,
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        for r in data["results"]:
            assert r["metadata"]["content_type"] == "character"

    def test_query_per_story_isolation(self, chromadb_dir: Path) -> None:
        """Each story has its own collection — queries do not cross stories."""
        _run_tool(
            "--operation", "index",
            "--name", "story-a",
            "--doc-id", "outline",
            "--content", "Dragon attacks the village near the river.",
            "--content-type", "outline",
            chromadb_dir=chromadb_dir,
        )

        result = _run_tool(
            "--operation", "query",
            "--name", "story-b",
            "--query", "dragon attack",
            chromadb_dir=chromadb_dir,
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["results"] == []

    def test_query_missing_query_text_errors(self, chromadb_dir: Path) -> None:
        result = _run_tool(
            "--operation", "query",
            "--name", "my-story",
            chromadb_dir=chromadb_dir,
        )
        assert result.returncode != 0

    def test_query_n_results_parameter(self, chromadb_dir: Path) -> None:
        # Index several chunks
        for i in range(5):
            _run_tool(
                "--operation", "index",
                "--name", "my-story",
                "--doc-id", f"chunk-{i}",
                "--content", f"Chunk number {i} containing story content about adventures.",
                "--content-type", "chapter",
                chromadb_dir=chromadb_dir,
            )

        result = _run_tool(
            "--operation", "query",
            "--name", "my-story",
            "--query", "adventure story",
            "--n-results", "3",
            chromadb_dir=chromadb_dir,
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert len(data["results"]) <= 3


class TestValidation:
    def test_path_traversal_blocked(self, chromadb_dir: Path) -> None:
        result = _run_tool(
            "--operation", "query",
            "--name", "../escape",
            "--query", "test",
            chromadb_dir=chromadb_dir,
        )
        assert result.returncode != 0

    def test_unknown_operation_errors(self, chromadb_dir: Path) -> None:
        result = _run_tool(
            "--operation", "invalid",
            "--name", "my-story",
            chromadb_dir=chromadb_dir,
        )
        assert result.returncode != 0
