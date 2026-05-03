"""CLI tool for searching wiki pages via ChromaDB."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src = str(Path(__file__).resolve().parents[1])
if _src not in sys.path:
    sys.path.insert(0, _src)

from src.tools._io import _validate_story_name  # noqa: E402
from tools._chroma_sync import refresh_if_stale  # noqa: E402

CHROMADB_DIR = os.environ.get("CHROMADB_DIR", str(PROJECT_ROOT / ".chromadb"))


def _get_collection(story_name: str):  # type: ignore[no-untyped-def]
    """Get ChromaDB collection for a story wiki.

    Returns None if collection does not exist.
    """
    import chromadb  # type: ignore[import-not-found]
    from chromadb.errors import NotFoundError  # type: ignore[import-not-found]

    client = chromadb.PersistentClient(path=CHROMADB_DIR)
    collection_name = f"wiki-{story_name}"

    try:
        return client.get_collection(name=collection_name)
    except NotFoundError:
        return None


def cmd_semantic(args: argparse.Namespace) -> None:
    """Perform semantic search over wiki pages."""
    if not args.query:
        print("Error: --query is required for semantic", file=sys.stderr)
        sys.exit(2)

    story_dir = _validate_story_name(args.name)
    collection = _get_collection(story_dir.name)

    if collection is None or collection.count() == 0:
        print(json.dumps({"status": "ok", "results": []}))
        return

    n_results = args.n_results or 10

    try:
        query_result = collection.query(
            query_texts=[args.query],
            n_results=min(n_results, collection.count()),
        )
    except Exception as exc:
        print(f"Error: ChromaDB query failed: {exc}", file=sys.stderr)
        sys.exit(1)

    results: list[dict] = []
    if query_result and query_result.get("ids"):
        ids = query_result["ids"][0] if query_result["ids"] else []
        documents = (
            query_result["documents"][0] if query_result.get("documents") else []
        )
        distances = (
            query_result["distances"][0] if query_result.get("distances") else []
        )
        metadatas = (
            query_result["metadatas"][0] if query_result.get("metadatas") else []
        )
        refreshed_map: dict = {}
        refreshed_ids = [
            doc_id for doc_id in ids if refresh_if_stale(collection, doc_id)
        ]
        if refreshed_ids:
            re_fetch = collection.get(
                ids=refreshed_ids,
                include=["documents", "metadatas"],
            )
            refreshed_map = {
                re_fetch["ids"][i]: {
                    "document": (re_fetch.get("documents") or [])[i]
                    if i < len(re_fetch.get("documents") or [])
                    else "",
                    "metadata": (re_fetch.get("metadatas") or [])[i]
                    if i < len(re_fetch.get("metadatas") or [])
                    else {},
                }
                for i in range(len(re_fetch["ids"]))
            }

        for i, doc_id in enumerate(ids):
            fresh = refreshed_map.get(doc_id)
            entry: dict = {
                "slug": doc_id,
                "score": round(1.0 / (1.0 + distances[i]), 4)
                if i < len(distances)
                else 0.0,
                "excerpt": (fresh["document"] if fresh else documents[i])[:500]
                if (fresh or i < len(documents))
                else "",
                "metadata": fresh["metadata"]
                if fresh
                else (metadatas[i] if i < len(metadatas) else {}),
            }
            results.append(entry)

    print(json.dumps({"status": "ok", "results": results}, indent=2))


def cmd_metadata(args: argparse.Namespace) -> None:
    """Query wiki pages by metadata filters."""
    if not args.where:
        print("Error: --where is required for metadata", file=sys.stderr)
        sys.exit(2)

    story_dir = _validate_story_name(args.name)

    try:
        where_filter = json.loads(args.where)
    except json.JSONDecodeError:
        print("Error: --where is not valid JSON", file=sys.stderr)
        sys.exit(2)

    if not isinstance(where_filter, dict):
        print("Error: --where must be a JSON object", file=sys.stderr)
        sys.exit(2)

    collection = _get_collection(story_dir.name)

    if collection is None or collection.count() == 0:
        print(json.dumps({"status": "ok", "results": []}))
        return

    n_results = args.n_results or 10

    try:
        get_result = collection.get(
            where=where_filter,
            limit=n_results,
        )
    except Exception as exc:
        print(f"Error: ChromaDB query failed: {exc}", file=sys.stderr)
        sys.exit(1)

    results: list[dict] = []
    if get_result and get_result.get("ids"):
        ids = get_result["ids"]
        documents = get_result.get("documents") or []
        metadatas = get_result.get("metadatas") or []
        refreshed_map: dict = {}
        refreshed_ids = [
            doc_id for doc_id in ids if refresh_if_stale(collection, doc_id)
        ]
        if refreshed_ids:
            re_fetch = collection.get(
                ids=refreshed_ids,
                include=["documents", "metadatas"],
            )
            refreshed_map = {
                re_fetch["ids"][i]: {
                    "document": (re_fetch.get("documents") or [])[i]
                    if i < len(re_fetch.get("documents") or [])
                    else "",
                    "metadata": (re_fetch.get("metadatas") or [])[i]
                    if i < len(re_fetch.get("metadatas") or [])
                    else {},
                }
                for i in range(len(re_fetch["ids"]))
            }

        for i, doc_id in enumerate(ids):
            fresh = refreshed_map.get(doc_id)
            entry: dict = {
                "slug": doc_id,
                "score": 1.0,
                "excerpt": (
                    fresh["document"]
                    if fresh
                    else (documents[i] if i < len(documents) else "")
                )[:500],
                "metadata": fresh["metadata"]
                if fresh
                else (metadatas[i] if i < len(metadatas) else {}),
            }
            results.append(entry)

    print(json.dumps({"status": "ok", "results": results}, indent=2))


def main() -> None:
    """Parse arguments and dispatch to the appropriate command."""
    parser = argparse.ArgumentParser(description="Wiki search tool")
    parser.add_argument(
        "--operation",
        required=True,
        choices=["semantic", "metadata"],
        help="Operation to perform",
    )
    parser.add_argument("--name", required=True, help="Story name")
    parser.add_argument("--query", help="Search query text (for semantic)")
    parser.add_argument("--where", help="JSON metadata filter (for metadata)")
    parser.add_argument(
        "--n-results",
        type=int,
        default=10,
        help="Number of results to return",
    )

    args = parser.parse_args()

    if args.operation == "semantic":
        cmd_semantic(args)
    elif args.operation == "metadata":
        cmd_metadata(args)


if __name__ == "__main__":
    main()
