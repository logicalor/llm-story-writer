"""Reconcile story ChromaDB collections against on-disk markdown sources."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src = str(Path(__file__).resolve().parents[1])
if _src not in sys.path:
    sys.path.insert(0, _src)

from tools._chroma_sync import (  # noqa: E402
    PROJECT_ROOT as CHROMA_PROJECT_ROOT,
    ReconcileReport,
    is_stale,
    reconcile_collection,
    upsert_from_source,
)
from tools._io import STORIES_DIR, _validate_story_name  # noqa: E402
from tools._wiki import get_wiki_dir  # noqa: E402


def _get_client(chromadb_dir: str) -> Any:
    import chromadb  # type: ignore[import-not-found]

    return chromadb.PersistentClient(path=chromadb_dir)


def _get_collection(chromadb_dir: str, collection_name: str) -> Any | None:
    from chromadb.errors import NotFoundError  # type: ignore[import-not-found]

    client = _get_client(chromadb_dir)
    try:
        return client.get_collection(name=collection_name)
    except NotFoundError:
        return None


def _get_or_create_collection(chromadb_dir: str, collection_name: str) -> Any:
    client = _get_client(chromadb_dir)
    return client.get_or_create_collection(name=collection_name)


def _report_to_dict(report: ReconcileReport) -> dict[str, Any]:
    return {
        "added": report.added,
        "updated": report.updated,
        "deleted": report.deleted,
        "unchanged": report.unchanged,
        "log": report.log,
    }


def _dry_run_wiki_collection(
    collection: Any | None,
    wiki_dir: Path,
) -> ReconcileReport:
    report = ReconcileReport()
    source_files = sorted(path for path in wiki_dir.glob("**/*.md") if path.is_file())
    source_ids: set[str] = set()

    existing_ids: set[str] = set()
    if collection is not None:
        existing = collection.get(include=["metadatas"])
        existing_ids = set(existing.get("ids") or [])

    for path in source_files:
        doc_id = path.stem
        source_ids.add(doc_id)
        if collection is None or doc_id not in existing_ids:
            report.added += 1
            report.log.append(f"added {doc_id}")
            continue

        if is_stale(collection, doc_id):
            report.updated += 1
            report.log.append(f"updated {doc_id}")
            continue

        report.unchanged += 1
        report.log.append(f"unchanged {doc_id}")

    for doc_id in sorted(existing_ids - source_ids):
        report.deleted += 1
        report.log.append(f"deleted {doc_id}")

    return report


def _reconcile_stories_collection(
    story_name: str,
    collection: Any | None,
    dry_run: bool,
) -> ReconcileReport:
    report = ReconcileReport()
    if collection is None:
        return report

    result = collection.get(include=["metadatas"])
    ids = result.get("ids") or []
    metadatas = result.get("metadatas") or []

    for index, doc_id in enumerate(ids):
        metadata = metadatas[index] if index < len(metadatas) else {}
        if not isinstance(metadata, dict):
            metadata = {}

        source_path = metadata.get("source_path")
        if not isinstance(source_path, str) or not source_path:
            report.unchanged += 1
            report.log.append(f"unchanged {doc_id}")
            continue

        source_file = (CHROMA_PROJECT_ROOT / source_path).resolve()
        if not source_file.is_relative_to(CHROMA_PROJECT_ROOT.resolve()):
            report.deleted += 1
            report.log.append(f"deleted {doc_id}")
            if not dry_run:
                collection.delete(ids=[doc_id])
            continue

        if not source_file.exists():
            report.deleted += 1
            report.log.append(f"deleted {doc_id}")
            if not dry_run:
                collection.delete(ids=[doc_id])
            continue

        if is_stale(collection, doc_id):
            report.updated += 1
            report.log.append(f"updated {doc_id}")
            if not dry_run:
                extra_metadata: dict[str, str | int | float | bool] = {
                    key: value
                    for key, value in metadata.items()
                    if isinstance(value, (str, int, float, bool))
                    and key not in {"source_path", "source_mtime", "source_sha256"}
                }
                extra_metadata.setdefault("story", story_name)
                extra_metadata.setdefault("doc_id", doc_id)
                upsert_from_source(
                    collection,
                    doc_id=doc_id,
                    source_path=source_path,
                    extra_metadata=extra_metadata,
                )
            continue

        report.unchanged += 1
        report.log.append(f"unchanged {doc_id}")

    return report


def reconcile_story(
    story_name: str,
    collection_filter: str | None,
    dry_run: bool,
    chromadb_dir: str,
) -> dict[str, ReconcileReport]:
    story_dir = STORIES_DIR / story_name
    reports: dict[str, ReconcileReport] = {}

    if collection_filter in (None, "wiki"):
        wiki_dir = get_wiki_dir(story_dir)
        if not wiki_dir.exists():
            reports["wiki"] = ReconcileReport()
        else:
            wiki_collection_name = f"wiki-{story_name}"
            if dry_run:
                wiki_collection = _get_collection(chromadb_dir, wiki_collection_name)
                reports["wiki"] = _dry_run_wiki_collection(wiki_collection, wiki_dir)
            else:
                wiki_collection = _get_or_create_collection(
                    chromadb_dir, wiki_collection_name
                )
                reports["wiki"] = reconcile_collection(
                    wiki_collection,
                    source_root=wiki_dir,
                    glob_pattern="**/*.md",
                    doc_id_from_path=lambda path: path.stem,
                )

    if collection_filter in (None, "stories"):
        stories_collection = _get_collection(chromadb_dir, f"stories-{story_name}")
        reports["stories"] = _reconcile_stories_collection(
            story_name=story_name,
            collection=stories_collection,
            dry_run=dry_run,
        )

    return reports


def format_reports(story_name: str, reports: dict[str, ReconcileReport]) -> str:
    lines = [f"Story: {story_name}"]
    ordered_names = [name for name in ["wiki", "stories"] if name in reports]
    for collection_name in ordered_names:
        report = reports[collection_name]
        lines.extend(
            [
                f"  Collection: {collection_name}",
                f"    Added:     {report.added}",
                f"    Updated:   {report.updated}",
                f"    Deleted:   {report.deleted}",
                f"    Unchanged: {report.unchanged}",
            ]
        )
        if report.log:
            lines.append("    Log:")
            lines.extend(f"      {entry}" for entry in report.log)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reconcile story ChromaDB collections against markdown sources."
    )
    parser.add_argument(
        "--story",
        metavar="NAME",
        help="Story name to reconcile. Required unless --all is set.",
    )
    parser.add_argument(
        "--collection",
        choices=["wiki", "stories"],
        default=None,
        metavar="COLLECTION",
        help="Collection to reconcile: 'wiki' or 'stories' (default: both).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without writing to ChromaDB.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Reconcile all stories under stories/.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output results as JSON only.",
    )

    args = parser.parse_args()

    if not args.all and not args.story:
        print("Error: --story is required unless --all is set", file=sys.stderr)
        sys.exit(2)

    chromadb_dir = os.environ.get("CHROMADB_DIR", str(PROJECT_ROOT / ".chromadb"))

    if args.all:
        story_names = [
            path.name for path in sorted(STORIES_DIR.iterdir()) if path.is_dir()
        ]
    else:
        story_names = [_validate_story_name(args.story).name]

    outputs: list[str] = []
    json_outputs: list[dict[str, Any]] = []

    for story_name in story_names:
        reports = reconcile_story(
            story_name=story_name,
            collection_filter=args.collection,
            dry_run=args.dry_run,
            chromadb_dir=chromadb_dir,
        )
        if args.output_json:
            json_outputs.append(
                {
                    "story": story_name,
                    **{
                        name: _report_to_dict(report)
                        for name, report in reports.items()
                    },
                }
            )
        else:
            outputs.append(format_reports(story_name, reports))

    if args.output_json:
        payload: Any
        if args.all:
            payload = json_outputs
        else:
            payload = json_outputs[0] if json_outputs else {}
        print(json.dumps(payload, indent=2))
        return

    print("\n\n".join(outputs))


if __name__ == "__main__":
    main()
