from __future__ import annotations

import sys
from pathlib import Path

import chromadb
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

import tools.recap_index as recap_index
from tools.recap_index import _split_pipe, query_recap, upsert_recap


@pytest.fixture()
def recap_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    chromadb_dir = tmp_path / "chromadb"
    chromadb_dir.mkdir()
    monkeypatch.setenv("CHROMADB_DIR", str(chromadb_dir))
    monkeypatch.setattr(recap_index, "CHROMADB_DIR", str(chromadb_dir))
    return chromadb_dir


@pytest.fixture()
def collection(recap_env: Path):
    client = chromadb.PersistentClient(path=str(recap_env))
    return client.get_or_create_collection(name="recaps-test-story")


def _payload(compact: str, sanitised: str) -> dict[str, str]:
    return {"compact": compact, "sanitised": sanitised}


def _chapters(rows: list[dict]) -> set[int]:
    return {
        row["metadata"]["chapter"]
        for row in rows
        if isinstance(row.get("metadata"), dict) and "chapter" in row["metadata"]
    }


def test_upsert_creates_single_aggregate_document(collection) -> None:
    upsert_recap(
        "test-story",
        1,
        _payload("ch1 compact text", "ch1 sanitised text"),
    )

    result = collection.get(ids=["aggregate/1"], include=["documents", "metadatas"])

    assert result["ids"] == ["aggregate/1"]
    assert len(result["documents"]) == 1
    assert result["metadatas"][0]["chapter"] == 1
    assert result["metadatas"][0]["kind"] == "chapter_aggregate"
    assert result["metadatas"][0]["story"] == "test-story"


def test_upsert_is_idempotent(collection) -> None:
    payload = _payload("ch1 compact text", "ch1 sanitised text")

    upsert_recap("test-story", 1, payload)
    upsert_recap("test-story", 1, payload)

    assert collection.count() == 1


def test_query_by_character(collection) -> None:
    upsert_recap(
        "test-story",
        1,
        _payload("Amy finds a clue", "Amy finds a clue"),
        participants=["amy"],
    )
    upsert_recap(
        "test-story",
        2,
        _payload("Morgan reviews evidence", "Morgan reviews evidence"),
        participants=["detective-morgan"],
    )

    result = query_recap("test-story", character="amy")

    assert _chapters(result) == {1}


def test_query_by_location(collection) -> None:
    upsert_recap(
        "test-story",
        1,
        _payload("Bathroom scene", "Bathroom scene"),
        locations=["the-bathroom"],
    )
    upsert_recap(
        "test-story",
        2,
        _payload("Precinct scene", "Precinct scene"),
        locations=["precinct"],
    )

    result = query_recap("test-story", location="the-bathroom")

    assert _chapters(result) == {1}


def test_query_by_chapter(collection) -> None:
    upsert_recap("test-story", 1, _payload("chapter one", "chapter one"))
    upsert_recap("test-story", 2, _payload("chapter two", "chapter two"))

    result = query_recap("test-story", chapter=2)

    assert len(result) == 1
    assert result[0]["id"] == "aggregate/2"
    assert result[0]["metadata"]["chapter"] == 2


def test_query_by_chapter_range(collection) -> None:
    upsert_recap("test-story", 1, _payload("chapter one", "chapter one"))
    upsert_recap("test-story", 2, _payload("chapter two", "chapter two"))
    upsert_recap("test-story", 3, _payload("chapter three", "chapter three"))

    result = query_recap("test-story", chapter_range=(1, 2))

    assert _chapters(result) == {1, 2}


def test_query_semantic(collection) -> None:
    upsert_recap(
        "test-story",
        1,
        _payload("Amy confronts Morgan in the basement", "Amy confronts Morgan"),
    )
    upsert_recap(
        "test-story",
        2,
        _payload("Quiet breakfast before the briefing", "Quiet breakfast"),
    )

    result = query_recap("test-story", query_text="confrontation", n_results=1)

    assert result
    assert result[0]["id"] == "aggregate/1"


def test_multiple_filters_compose_and(collection) -> None:
    upsert_recap(
        "test-story",
        1,
        _payload("Amy returns to the bathroom", "Amy returns to the bathroom"),
        participants=["amy"],
        locations=["the-bathroom"],
    )
    upsert_recap(
        "test-story",
        2,
        _payload("Amy checks the precinct board", "Amy checks the precinct board"),
        participants=["amy"],
        locations=["precinct"],
    )

    result = query_recap("test-story", character="amy", location="the-bathroom")

    assert _chapters(result) == {1}


def test_split_pipe_drops_empty_parts() -> None:
    assert _split_pipe("amy||the-bathroom|") == ["amy", "the-bathroom"]
    assert _split_pipe("") == []
