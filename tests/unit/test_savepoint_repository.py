"""Unit tests for FilesystemSavepointRepository extension-based storage."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from infrastructure.storage.savepoint_repository import FilesystemSavepointRepository


def _make_repo(tmp_path: Path) -> FilesystemSavepointRepository:
    repo = FilesystemSavepointRepository(base_path=tmp_path)
    repo.set_story_directory("savepoints")
    return repo


def test_save_string_uses_markdown_extension(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    asyncio.run(repo.save_savepoint("chapter_1/content", "hello world"))

    assert (tmp_path / "savepoints" / "chapter_1" / "content.md").exists()
    assert not (tmp_path / "savepoints" / "chapter_1" / "content.json").exists()
    assert asyncio.run(repo.load_savepoint("chapter_1/content")) == "hello world"


def test_save_structured_data_uses_json_extension(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    payload = {"title": "Chapter One", "word_count": 500}

    asyncio.run(repo.save_savepoint("chapter_meta", payload))

    path = tmp_path / "savepoints" / "chapter_meta.json"
    assert path.exists()
    assert not (tmp_path / "savepoints" / "chapter_meta.md").exists()
    assert json.loads(path.read_text(encoding="utf-8")) == payload
    assert asyncio.run(repo.load_savepoint("chapter_meta")) == payload


def test_json_load_takes_precedence_when_both_extensions_exist(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    base_path = tmp_path / "savepoints" / "shared_step"
    base_path.with_suffix(".md").write_text("markdown body", encoding="utf-8")
    base_path.with_suffix(".json").write_text('{"value": 7}', encoding="utf-8")

    assert asyncio.run(repo.load_savepoint("shared_step")) == {"value": 7}
    assert asyncio.run(repo.has_savepoint("shared_step")) is True


def test_list_delete_and_clear_handle_mixed_extensions(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    asyncio.run(repo.save_savepoint("alpha", "text"))
    asyncio.run(repo.save_savepoint("nested/beta", [1, 2, 3]))

    assert asyncio.run(repo.list_savepoint_names()) == ["alpha", "nested/beta"]
    assert asyncio.run(repo.list_savepoints()) == {
        "alpha": "text",
        "nested/beta": [1, 2, 3],
    }

    assert asyncio.run(repo.delete_savepoint("nested/beta")) is True
    assert asyncio.run(repo.has_savepoint("nested/beta")) is False

    asyncio.run(repo.clear_all_savepoints())
    assert asyncio.run(repo.list_savepoint_names()) == []


def test_load_savepoint_with_metadata_wraps_loaded_value(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    asyncio.run(repo.save_savepoint("flag", False))

    assert asyncio.run(repo.load_savepoint_with_metadata("flag")) == {
        "_frontmatter": {},
        "_body": False,
    }
