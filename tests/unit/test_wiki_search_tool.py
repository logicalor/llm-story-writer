"""Verification tests for Issue #16 — wiki-search Tool.

Confirms the CLI tool (src/tools/wiki_search.py) correctly performs
semantic and metadata search over wiki ChromaDB collections.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import chromadb
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_SCRIPT = str(PROJECT_ROOT / "src" / "tools" / "wiki_search.py")


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
def search_env(tmp_path: Path) -> tuple[Path, Path]:
    """Create a story dir and a temporary ChromaDB directory."""
    stories = tmp_path / "stories"
    (stories / "test-story").mkdir(parents=True)
    chroma_dir = tmp_path / "chromadb"
    chroma_dir.mkdir()
    return stories, chroma_dir


class TestSemantic:
    def test_semantic_empty_collection(self, search_env: tuple[Path, Path]) -> None:
        stories, chroma_dir = search_env
        result = _run_tool(
            "--operation",
            "semantic",
            "--name",
            "test-story",
            "--query",
            "some query",
            stories_dir=stories,
            chromadb_dir=chroma_dir,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"
        assert output["results"] == []

    def test_semantic_with_documents(self, search_env: tuple[Path, Path]) -> None:
        stories, chroma_dir = search_env
        # Seed ChromaDB with test documents
        client = chromadb.PersistentClient(path=str(chroma_dir))
        collection = client.create_collection(name="wiki-test-story")
        collection.add(
            ids=["alice", "bob"],
            documents=[
                "Alice is a brave warrior from the northern lands.",
                "Bob is a cunning thief from the southern deserts.",
            ],
            metadatas=[
                {"type": "character", "slug": "alice"},
                {"type": "character", "slug": "bob"},
            ],
        )
        del client  # release lock

        result = _run_tool(
            "--operation",
            "semantic",
            "--name",
            "test-story",
            "--query",
            "brave warrior",
            "--n-results",
            "2",
            stories_dir=stories,
            chromadb_dir=chroma_dir,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"
        assert len(output["results"]) > 0
        # First result should be Alice (closest match to "brave warrior")
        assert output["results"][0]["slug"] == "alice"
        assert "score" in output["results"][0]
        assert "excerpt" in output["results"][0]

    def test_semantic_scores_normalized_0_to_1(
        self, search_env: tuple[Path, Path]
    ) -> None:
        """Scores use 1/(1+distance), always in (0, 1] range."""
        stories, chroma_dir = search_env
        client = chromadb.PersistentClient(path=str(chroma_dir))
        collection = client.create_collection(name="wiki-test-story")
        collection.add(
            ids=["far-away"],
            documents=["Completely unrelated content about quantum physics."],
            metadatas=[{"type": "event", "slug": "far-away"}],
        )
        del client

        result = _run_tool(
            "--operation",
            "semantic",
            "--name",
            "test-story",
            "--query",
            "medieval sword battle",
            "--n-results",
            "1",
            stories_dir=stories,
            chromadb_dir=chroma_dir,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert len(output["results"]) == 1
        score = output["results"][0]["score"]
        assert 0 < score <= 1.0, f"Score {score} not in (0, 1]"


class TestMetadata:
    def test_metadata_empty_collection(self, search_env: tuple[Path, Path]) -> None:
        stories, chroma_dir = search_env
        result = _run_tool(
            "--operation",
            "metadata",
            "--name",
            "test-story",
            "--where",
            '{"type": "character"}',
            stories_dir=stories,
            chromadb_dir=chroma_dir,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"
        assert output["results"] == []

    def test_metadata_with_documents(self, search_env: tuple[Path, Path]) -> None:
        stories, chroma_dir = search_env
        # Seed ChromaDB with test documents
        client = chromadb.PersistentClient(path=str(chroma_dir))
        collection = client.create_collection(name="wiki-test-story")
        collection.add(
            ids=["castle", "forest"],
            documents=[
                "The grand castle overlooks the kingdom.",
                "The dark forest is home to many creatures.",
            ],
            metadatas=[
                {"type": "location", "slug": "castle"},
                {"type": "location", "slug": "forest"},
            ],
        )
        del client

        result = _run_tool(
            "--operation",
            "metadata",
            "--name",
            "test-story",
            "--where",
            '{"type": "location"}',
            stories_dir=stories,
            chromadb_dir=chroma_dir,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["status"] == "ok"
        assert len(output["results"]) == 2
        slugs = {r["slug"] for r in output["results"]}
        assert slugs == {"castle", "forest"}

    def test_search_path_traversal_blocked(self, search_env: tuple[Path, Path]) -> None:
        stories, chroma_dir = search_env
        result = _run_tool(
            "--operation",
            "semantic",
            "--name",
            "../evil",
            "--query",
            "test",
            stories_dir=stories,
            chromadb_dir=chroma_dir,
        )
        assert result.returncode == 1
        assert "escapes" in result.stderr

    def test_search_missing_operation(self) -> None:
        result = _run_tool("--name", "test-story", "--query", "test")
        assert result.returncode == 2
