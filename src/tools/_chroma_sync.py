"""ChromaDB source-sync helpers — ADR 012.

Enforces the source-pointer + fingerprint metadata contract:
  source_path   — relative path from PROJECT_ROOT to the source .md file
  source_mtime  — float mtime at index time
  source_sha256 — SHA-256 hex of file contents at index time
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class ReconcileReport:
    added: int = 0
    updated: int = 0
    deleted: int = 0
    unchanged: int = 0
    log: list[str] = field(default_factory=list)


def _check_source_path(source_path: str) -> Path:
    if not source_path:
        return Path()
    resolved = (PROJECT_ROOT / source_path).resolve()
    if not str(resolved).startswith(str(PROJECT_ROOT)):
        raise ValueError(f"source_path escapes project root: {source_path}")
    return resolved


def _get_existing_entry(
    collection: Any, doc_id: str
) -> tuple[str | None, dict[str, Any]]:
    result = collection.get(ids=[doc_id], include=["metadatas"])
    ids = result.get("ids") or []
    metadatas = result.get("metadatas") or []

    if not ids:
        return None, {}

    existing_id = ids[0]
    metadata = metadatas[0] if metadatas else {}
    if not isinstance(metadata, dict):
        metadata = {}
    return existing_id, metadata


def compute_fingerprint(path: Path) -> tuple[float, str]:
    mtime = path.stat().st_mtime
    sha256_hex = hashlib.sha256(path.read_bytes()).hexdigest()
    return mtime, sha256_hex


def upsert_from_source(
    collection: Any,
    doc_id: str,
    source_path: str,
    extra_metadata: dict,
    body: str | None = None,
) -> None:
    resolved = _check_source_path(source_path)

    if source_path and body is None:
        body = resolved.read_text()

    chroma_meta: dict[str, str | int | float | bool] = {}
    for key, value in extra_metadata.items():
        if isinstance(value, (str, int, float, bool)):
            chroma_meta[key] = value

    if source_path:
        source_mtime, source_sha256 = compute_fingerprint(resolved)
        chroma_meta["source_path"] = source_path
        chroma_meta["source_mtime"] = source_mtime
        chroma_meta["source_sha256"] = source_sha256
    else:
        chroma_meta["source_path"] = ""

    collection.upsert(
        ids=[doc_id],
        documents=[body or ""],
        metadatas=[chroma_meta],
    )


def is_stale(collection: Any, doc_id: str) -> bool:
    _, metadata = _get_existing_entry(collection, doc_id)

    source_path = metadata.get("source_path")
    if not isinstance(source_path, str) or not source_path:
        return False

    stored_mtime = metadata.get("source_mtime")
    stored_sha256 = metadata.get("source_sha256")
    if not isinstance(stored_mtime, (int, float)) or not isinstance(stored_sha256, str):
        return True

    resolved = _check_source_path(source_path)
    if not resolved.exists():
        return True

    current_mtime = resolved.stat().st_mtime
    if current_mtime == float(stored_mtime):
        return False

    _, current_sha256 = compute_fingerprint(resolved)
    return current_sha256 != stored_sha256


def refresh_if_stale(collection: Any, doc_id: str) -> bool:
    existing_id, metadata = _get_existing_entry(collection, doc_id)
    if existing_id is None:
        return False
    if not is_stale(collection, doc_id):
        return False

    source_path = metadata.get("source_path")
    if not isinstance(source_path, str):
        source_path = ""

    # If the source file no longer exists (e.g. page renamed/deleted on disk),
    # drop the stale row rather than crashing trying to re-read it.
    if source_path:
        resolved = _check_source_path(source_path)
        if not resolved.exists():
            collection.delete(ids=[doc_id])
            return True

    upsert_from_source(
        collection,
        doc_id=doc_id,
        source_path=source_path,
        extra_metadata=metadata,
    )
    return True


def reconcile_collection(
    collection: Any,
    source_root: Path,
    glob_pattern: str,
    doc_id_from_path: Callable[[Path], str],
) -> ReconcileReport:
    report = ReconcileReport()
    source_files = sorted(
        path for path in source_root.glob(glob_pattern) if path.is_file()
    )
    source_ids: set[str] = set()

    for path in source_files:
        doc_id = doc_id_from_path(path)
        source_ids.add(doc_id)
        source_path = str(path.relative_to(PROJECT_ROOT))

        existing_id, _ = _get_existing_entry(collection, doc_id)
        if existing_id is None:
            upsert_from_source(
                collection,
                doc_id=doc_id,
                source_path=source_path,
                extra_metadata={},
            )
            report.added += 1
            report.log.append(f"added {doc_id}")
            continue

        if is_stale(collection, doc_id):
            upsert_from_source(
                collection,
                doc_id=doc_id,
                source_path=source_path,
                extra_metadata={},
            )
            report.updated += 1
            report.log.append(f"updated {doc_id}")
            continue

        report.unchanged += 1
        report.log.append(f"unchanged {doc_id}")

    all_docs = collection.get(include=["metadatas"])
    indexed_ids = all_docs.get("ids") or []
    orphaned_ids = [doc_id for doc_id in indexed_ids if doc_id not in source_ids]
    if orphaned_ids:
        collection.delete(ids=orphaned_ids)
        report.deleted += len(orphaned_ids)
        for doc_id in orphaned_ids:
            report.log.append(f"deleted {doc_id}")

    return report
