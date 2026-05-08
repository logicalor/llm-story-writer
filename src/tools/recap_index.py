"""ChromaDB recap index helpers for per-story aggregate recap retrieval."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src = str(Path(__file__).resolve().parents[1])
if _src not in sys.path:
    sys.path.insert(0, _src)

from tools._chroma_sync import upsert_from_source  # noqa: E402
from tools._io import _validate_story_name  # noqa: E402

CHROMADB_DIR = os.environ.get("CHROMADB_DIR", str(PROJECT_ROOT / ".chromadb"))


def _split_pipe(s: str) -> list[str]:
    """Split a pipe-joined string into non-empty parts."""
    return [part for part in s.split("|") if part]


def _normalize_story_name(story_name: str) -> str:
    """Validate story name and return the canonical collection slug."""
    return _validate_story_name(story_name).name


def _get_or_create_collection(story_name: str) -> Any:
    """Get or create the per-story recap collection."""
    import chromadb  # type: ignore[import-not-found]

    client = chromadb.PersistentClient(path=CHROMADB_DIR)
    collection_name = f"recaps-{_normalize_story_name(story_name)}"
    return client.get_or_create_collection(name=collection_name)


def upsert_recap(
    story_name: str,
    chapter: int,
    payload: dict,
    participants: list[str] | None = None,
    locations: list[str] | None = None,
) -> None:
    """Upsert one chapter aggregate recap into the story collection."""
    collection = _get_or_create_collection(story_name)
    doc_id = f"aggregate/{chapter}"
    pipe_p = "|".join(participants or [])
    pipe_l = "|".join(locations or [])
    body = (
        f"participants:{pipe_p}\n"
        f"locations:{pipe_l}\n\n"
        f"{payload.get('compact', '')}\n\n"
        f"{payload.get('sanitised', '')}"
    )
    metadata = {
        "chapter": chapter,
        "kind": "chapter_aggregate",
        "story": _normalize_story_name(story_name),
        "participants": pipe_p,
        "locations": pipe_l,
    }

    upsert_from_source(
        collection,
        doc_id,
        source_path="",
        extra_metadata=metadata,
        body=body,
    )


def delete_chapter_events(story_name: str, chapter: int) -> None:
    """Delete all recap event docs for a chapter from the story collection."""
    collection = _get_or_create_collection(story_name)
    collection.delete(where={"chapter": chapter})


def clear_recap_index(story_name: str) -> None:
    """Drop and recreate the story recap collection (clean slate on restart)."""
    import chromadb  # type: ignore[import-not-found]

    client = chromadb.PersistentClient(path=CHROMADB_DIR)
    collection_name = f"recaps-{_normalize_story_name(story_name)}"
    client.delete_collection(collection_name)
    client.get_or_create_collection(name=collection_name)


def upsert_recap_events(
    story_name: str,
    chapter: int,
    events: list[dict],
) -> None:
    """Upsert each event as its own Chroma document (flat storage)."""
    collection = _get_or_create_collection(story_name)
    story_slug = _normalize_story_name(story_name)
    delete_chapter_events(story_name, chapter)
    for i, event in enumerate(events, start=1):
        doc_id = f"event/{chapter}/{i}"
        raw_participants = event.get("participants") or event.get("characters") or []
        raw_locations = event.get("locations") or []
        pipe_participants = "|".join(str(p) for p in raw_participants if p)
        pipe_locations = "|".join(str(loc) for loc in raw_locations if loc)
        narrative_fields: dict = {}
        for key in (
            "summary",
            "key_events",
            "character_development",
            "symbols_motifs",
            "impact",
        ):
            if key in event:
                narrative_fields[key] = event[key]
        body = (
            f"participants:{pipe_participants}\n"
            f"locations:{pipe_locations}\n\n"
            f"{json.dumps(narrative_fields, ensure_ascii=False)}"
        )
        metadata = {
            "chapter": chapter,
            "kind": "event",
            "story": story_slug,
            "participants": pipe_participants,
            "locations": pipe_locations,
            "date_start": str(event.get("date_start", "")),
            "date_end": str(event.get("date_end", "")),
            "importance": str(event.get("importance", "medium")),
        }
        upsert_from_source(
            collection,
            doc_id,
            source_path="",
            extra_metadata=metadata,
            body=body,
        )


def _build_where_clause(
    chapter: int | None,
    chapter_range: tuple[int, int] | None,
) -> dict[str, Any] | None:
    if chapter is not None:
        return {"chapter": chapter}
    if chapter_range is not None:
        lo, hi = chapter_range
        return {
            "$and": [
                {"chapter": {"$gte": lo}},
                {"chapter": {"$lte": hi}},
            ]
        }
    return None


def _build_where_document_clause(
    character: str | None,
    location: str | None,
) -> dict[str, Any] | None:
    if character and location:
        return {"$and": [{"$contains": character}, {"$contains": location}]}
    if character:
        return {"$contains": character}
    if location:
        return {"$contains": location}
    return None


def _flatten_query_results(result: dict[str, Any]) -> list[dict[str, Any]]:
    ids = result.get("ids") or []
    documents = result.get("documents") or []
    metadatas = result.get("metadatas") or []

    flat_ids = ids[0] if ids else []
    flat_documents = documents[0] if documents else []
    flat_metadatas = metadatas[0] if metadatas else []

    rows: list[dict[str, Any]] = []
    for index, doc_id in enumerate(flat_ids):
        rows.append(
            {
                "id": doc_id,
                "document": flat_documents[index]
                if index < len(flat_documents)
                else None,
                "metadata": flat_metadatas[index]
                if index < len(flat_metadatas)
                else None,
            }
        )
    return rows


def _flatten_get_results(result: dict[str, Any]) -> list[dict[str, Any]]:
    ids = result.get("ids") or []
    documents = result.get("documents") or []
    metadatas = result.get("metadatas") or []

    rows: list[dict[str, Any]] = []
    for index, doc_id in enumerate(ids):
        rows.append(
            {
                "id": doc_id,
                "document": documents[index] if index < len(documents) else None,
                "metadata": metadatas[index] if index < len(metadatas) else None,
            }
        )
    return rows


def query_recap(
    story_name: str,
    *,
    character: str | None = None,
    location: str | None = None,
    query_text: str | None = None,
    chapter: int | None = None,
    chapter_range: tuple[int, int] | None = None,
    n_results: int = 10,
) -> list[dict]:
    """Query recap entries by chapter filters and optional semantic search."""
    collection = _get_or_create_collection(story_name)
    where_clause = _build_where_clause(chapter, chapter_range)
    where_doc_clause = _build_where_document_clause(character, location)

    if query_text:
        count = collection.count()
        if count == 0:
            return []
        result = collection.query(
            query_texts=[query_text],
            n_results=min(n_results, max(1, count)),
            where=where_clause,
            where_document=where_doc_clause,
        )
        return _flatten_query_results(result)

    if chapter is not None and where_doc_clause is None and chapter_range is None:
        result = collection.get(
            where={"chapter": chapter},
            include=["documents", "metadatas"],
        )
        return _flatten_get_results(result)

    get_kwargs: dict[str, Any] = {"include": ["documents", "metadatas"]}
    if where_clause is not None:
        get_kwargs["where"] = where_clause
    if where_doc_clause is not None:
        get_kwargs["where_document"] = where_doc_clause

    result = collection.get(**get_kwargs)
    return _flatten_get_results(result)
