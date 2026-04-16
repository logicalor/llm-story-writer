"""CLI tool for indexing and querying story content via ChromaDB."""

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

CHROMADB_DIR = os.environ.get("CHROMADB_DIR", str(PROJECT_ROOT / ".chromadb"))

# Valid content types that can be indexed
CONTENT_TYPES = frozenset(
    ["outline", "chapter", "character", "setting", "wiki", "recap"]
)


def _get_or_create_collection(story_name: str):  # type: ignore[no-untyped-def]
    """Get or create a per-story ChromaDB collection for RAG content."""
    import chromadb  # type: ignore[import-not-found]

    client = chromadb.PersistentClient(path=CHROMADB_DIR)
    collection_name = f"stories-{story_name}"
    return client.get_or_create_collection(name=collection_name)


def _get_collection(story_name: str):  # type: ignore[no-untyped-def]
    """Get an existing per-story ChromaDB collection. Returns None if not found."""
    import chromadb  # type: ignore[import-not-found]
    from chromadb.errors import NotFoundError  # type: ignore[import-not-found]

    client = chromadb.PersistentClient(path=CHROMADB_DIR)
    collection_name = f"stories-{story_name}"
    try:
        return client.get_collection(name=collection_name)
    except NotFoundError:
        return None


def cmd_index(args: argparse.Namespace) -> None:
    """Index a piece of content into the story's ChromaDB collection."""
    _validate_story_name(args.name)

    if not args.doc_id:
        print("Error: --doc-id is required for index", file=sys.stderr)
        sys.exit(2)
    if not args.content:
        print("Error: --content is required for index", file=sys.stderr)
        sys.exit(2)
    if args.content_type and args.content_type not in CONTENT_TYPES:
        print(
            f"Error: --content-type must be one of: {', '.join(sorted(CONTENT_TYPES))}",
            file=sys.stderr,
        )
        sys.exit(2)

    content_type = args.content_type or "outline"

    try:
        collection = _get_or_create_collection(args.name)

        metadata: dict[str, str | int | float | bool] = {
            "story": args.name,
            "content_type": content_type,
            "doc_id": args.doc_id,
        }
        if args.chapter_num is not None:
            metadata["chapter_num"] = args.chapter_num

        collection.upsert(
            ids=[args.doc_id],
            documents=[args.content],
            metadatas=[metadata],
        )
    except Exception as exc:
        print(f"Error: ChromaDB index failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print(
        json.dumps(
            {
                "status": "ok",
                "indexed": args.doc_id,
                "content_type": content_type,
                "story": args.name,
            }
        )
    )


def cmd_query(args: argparse.Namespace) -> None:
    """Query the story's ChromaDB collection for relevant chunks."""
    _validate_story_name(args.name)

    if not args.query:
        print("Error: --query is required for query", file=sys.stderr)
        sys.exit(2)

    collection = _get_collection(args.name)

    if collection is None or collection.count() == 0:
        print(json.dumps({"status": "ok", "results": []}))
        return

    n_results = args.n_results or 10
    where_filter: dict | None = None

    if args.content_type:
        if args.content_type not in CONTENT_TYPES:
            print(
                f"Error: --content-type must be one of: {', '.join(sorted(CONTENT_TYPES))}",
                file=sys.stderr,
            )
            sys.exit(2)
        where_filter = {"content_type": args.content_type}

    try:
        query_kwargs: dict = {
            "query_texts": [args.query],
            "n_results": min(n_results, collection.count()),
        }
        if where_filter:
            query_kwargs["where"] = where_filter

        query_result = collection.query(**query_kwargs)
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

        for i, doc_id in enumerate(ids):
            entry: dict = {
                "doc_id": doc_id,
                "score": round(1.0 / (1.0 + distances[i]), 4)
                if i < len(distances)
                else 0.0,
                "excerpt": documents[i][:1000] if i < len(documents) else "",
                "metadata": metadatas[i] if i < len(metadatas) else {},
            }
            results.append(entry)

    print(json.dumps({"status": "ok", "results": results}, indent=2))


def main() -> None:
    """Parse arguments and dispatch to the appropriate command."""
    parser = argparse.ArgumentParser(
        description="RAG query tool — index and query story content via ChromaDB"
    )
    parser.add_argument(
        "--operation",
        required=True,
        choices=["index", "query"],
        help="Operation to perform",
    )
    parser.add_argument("--name", required=True, help="Story name")
    parser.add_argument(
        "--doc-id",
        help="Stable document ID (required for index, e.g. 'outline', 'chapter-1')",
    )
    parser.add_argument(
        "--content",
        help="Text content to index (required for index)",
    )
    parser.add_argument(
        "--content-type",
        help=f"Content type: {', '.join(sorted(CONTENT_TYPES))} (default: outline)",
    )
    parser.add_argument(
        "--chapter-num",
        type=int,
        help="Chapter number (optional, stored as metadata for chapters)",
    )
    parser.add_argument(
        "--query",
        help="Search query text (required for query)",
    )
    parser.add_argument(
        "--n-results",
        type=int,
        default=10,
        help="Number of results to return (default: 10)",
    )

    args = parser.parse_args()

    if args.operation == "index":
        cmd_index(args)
    elif args.operation == "query":
        cmd_query(args)
    else:
        print(f"Error: Unknown operation: {args.operation}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
