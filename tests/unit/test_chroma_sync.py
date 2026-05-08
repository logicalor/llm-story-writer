"""Verification tests for ChromaDB source-sync helpers."""

import os
import re
import sys
from pathlib import Path

import chromadb
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

import tools._chroma_sync as chroma_sync_module
from tools._chroma_sync import (
    ReconcileReport,
    compute_fingerprint,
    is_stale,
    reconcile_collection,
    refresh_if_stale,
    upsert_from_source,
)


@pytest.fixture()
def source_project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    project_root = tmp_path / "project"
    project_root.mkdir()
    monkeypatch.setattr(chroma_sync_module, "PROJECT_ROOT", project_root)
    return project_root


@pytest.fixture()
def collection(tmp_path: Path):
    client = chromadb.PersistentClient(path=str(tmp_path / "chromadb"))
    return client.get_or_create_collection(name="test-chroma-sync")


def _write_source(project_root: Path, relative_path: str, content: str) -> Path:
    path = project_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def _set_mtime(path: Path, mtime: float) -> None:
    os.utime(path, (mtime, mtime))


def test_compute_fingerprint_returns_mtime_and_sha(tmp_path: Path) -> None:
    source_path = tmp_path / "fingerprint.md"
    source_path.write_text("fingerprint body")

    mtime, sha256_hex = compute_fingerprint(source_path)

    assert mtime == source_path.stat().st_mtime
    assert re.fullmatch(r"[0-9a-f]{64}", sha256_hex)


def test_upsert_from_source_round_trip(collection, source_project_root: Path) -> None:
    source_path = _write_source(source_project_root, "wiki/entry.md", "hello sync")
    relative_path = str(source_path.relative_to(source_project_root))

    upsert_from_source(
        collection,
        doc_id="entry",
        source_path=relative_path,
        extra_metadata={"type": "wiki", "ignored": ["x"]},
    )

    result = collection.get(ids=["entry"], include=["documents", "metadatas"])
    metadata = result["metadatas"][0]

    assert result["documents"][0] == "hello sync"
    assert metadata["type"] == "wiki"
    assert metadata["source_path"] == relative_path
    assert metadata["source_mtime"] == source_path.stat().st_mtime
    assert metadata["source_sha256"] == compute_fingerprint(source_path)[1]
    assert "ignored" not in metadata


def test_is_stale_false_when_content_unchanged(
    collection, source_project_root: Path
) -> None:
    source_path = _write_source(source_project_root, "wiki/stable.md", "stable")

    upsert_from_source(
        collection,
        doc_id="stable",
        source_path=str(source_path.relative_to(source_project_root)),
        extra_metadata={},
    )

    assert is_stale(collection, "stable") is False


def test_is_stale_true_when_mtime_changes(
    collection, source_project_root: Path
) -> None:
    source_path = _write_source(source_project_root, "wiki/changed.md", "before")
    relative_path = str(source_path.relative_to(source_project_root))

    upsert_from_source(
        collection,
        doc_id="changed",
        source_path=relative_path,
        extra_metadata={},
    )

    original_mtime = source_path.stat().st_mtime
    source_path.write_text("after")
    _set_mtime(source_path, original_mtime + 10)

    assert is_stale(collection, "changed") is True


def test_is_stale_sha256_fallback_same_mtime(
    collection, source_project_root: Path
) -> None:
    source_path = _write_source(source_project_root, "wiki/fallback.md", "content A")
    relative_path = str(source_path.relative_to(source_project_root))

    upsert_from_source(
        collection,
        doc_id="fallback",
        source_path=relative_path,
        extra_metadata={},
    )

    stored_mtime = source_path.stat().st_mtime
    source_path.write_text("content B")
    _set_mtime(source_path, stored_mtime + 10)
    assert is_stale(collection, "fallback") is True

    source_path.write_text("content A")
    _set_mtime(source_path, stored_mtime + 20)

    assert is_stale(collection, "fallback") is False


def test_is_stale_no_source_never_stale(collection) -> None:
    upsert_from_source(
        collection,
        doc_id="inline",
        source_path="",
        extra_metadata={"type": "inline"},
        body="inline body",
    )

    assert is_stale(collection, "inline") is False


def test_path_traversal_raises_value_error(
    collection, source_project_root: Path
) -> None:
    with pytest.raises(ValueError, match="escapes project root"):
        upsert_from_source(
            collection,
            doc_id="x",
            source_path="../../../etc/passwd",
            extra_metadata={},
        )


def test_refresh_if_stale_returns_true_and_updates_doc(
    collection, source_project_root: Path
) -> None:
    source_path = _write_source(source_project_root, "wiki/refresh.md", "old")
    relative_path = str(source_path.relative_to(source_project_root))

    upsert_from_source(
        collection,
        doc_id="refresh",
        source_path=relative_path,
        extra_metadata={"type": "wiki"},
    )

    original_mtime = source_path.stat().st_mtime
    source_path.write_text("new")
    _set_mtime(source_path, original_mtime + 10)

    assert refresh_if_stale(collection, "refresh") is True

    result = collection.get(ids=["refresh"], include=["documents", "metadatas"])
    metadata = result["metadatas"][0]
    assert result["documents"][0] == "new"
    assert metadata["source_mtime"] == pytest.approx(source_path.stat().st_mtime)
    assert metadata["source_sha256"] == compute_fingerprint(source_path)[1]


def test_refresh_if_stale_returns_false_when_not_stale(
    collection, source_project_root: Path
) -> None:
    source_path = _write_source(source_project_root, "wiki/fresh.md", "fresh")

    upsert_from_source(
        collection,
        doc_id="fresh",
        source_path=str(source_path.relative_to(source_project_root)),
        extra_metadata={},
    )

    assert refresh_if_stale(collection, "fresh") is False


def test_refresh_if_stale_deletes_row_when_source_missing(
    collection, source_project_root: Path
) -> None:
    """When the source file has been renamed/deleted on disk, the stale row
    should be removed from the collection rather than crashing the pipeline.
    """
    source_path = _write_source(source_project_root, "wiki/gone.md", "content")
    relative_path = str(source_path.relative_to(source_project_root))

    upsert_from_source(
        collection,
        doc_id="gone",
        source_path=relative_path,
        extra_metadata={"type": "wiki"},
    )

    source_path.unlink()

    assert refresh_if_stale(collection, "gone") is True
    result = collection.get(ids=["gone"])
    assert result["ids"] == []


def test_reconcile_adds_new_files(collection, source_project_root: Path) -> None:
    source_root = source_project_root / "wiki"
    _write_source(source_project_root, "wiki/alpha.md", "alpha")
    _write_source(source_project_root, "wiki/beta.md", "beta")

    report = reconcile_collection(
        collection,
        source_root=source_root,
        glob_pattern="*.md",
        doc_id_from_path=lambda path: path.stem,
    )

    assert isinstance(report, ReconcileReport)
    assert report.added == 2
    assert report.updated == 0
    assert report.deleted == 0
    assert report.unchanged == 0


def test_reconcile_updates_stale_files(collection, source_project_root: Path) -> None:
    source_root = source_project_root / "wiki"
    source_path = _write_source(source_project_root, "wiki/stale.md", "before")
    relative_path = str(source_path.relative_to(source_project_root))

    upsert_from_source(
        collection,
        doc_id="stale",
        source_path=relative_path,
        extra_metadata={},
    )

    original_mtime = source_path.stat().st_mtime
    source_path.write_text("after")
    _set_mtime(source_path, original_mtime + 10)

    report = reconcile_collection(
        collection,
        source_root=source_root,
        glob_pattern="*.md",
        doc_id_from_path=lambda path: path.stem,
    )

    result = collection.get(ids=["stale"], include=["documents"])
    assert report.updated == 1
    assert result["documents"][0] == "after"


def test_reconcile_deletes_orphaned_entries(
    collection, source_project_root: Path
) -> None:
    source_root = source_project_root / "wiki"
    source_root.mkdir(parents=True, exist_ok=True)
    collection.upsert(
        ids=["orphan"],
        documents=["orphaned"],
        metadatas=[{"source_path": ""}],
    )

    report = reconcile_collection(
        collection,
        source_root=source_root,
        glob_pattern="*.md",
        doc_id_from_path=lambda path: path.stem,
    )

    assert report.deleted == 1
    assert collection.get(ids=["orphan"])["ids"] == []


def test_reconcile_unchanged_when_not_stale(
    collection, source_project_root: Path
) -> None:
    source_root = source_project_root / "wiki"
    _write_source(source_project_root, "wiki/steady.md", "steady")

    first_report = reconcile_collection(
        collection,
        source_root=source_root,
        glob_pattern="*.md",
        doc_id_from_path=lambda path: path.stem,
    )
    second_report = reconcile_collection(
        collection,
        source_root=source_root,
        glob_pattern="*.md",
        doc_id_from_path=lambda path: path.stem,
    )

    assert first_report.added == 1
    assert second_report.unchanged == 1
