"""Verification tests for markdown pointer persistence helpers."""

from __future__ import annotations

import pytest

from src.tools._persist import persist_markdown, read_markdown_ref


class TestPersistMarkdown:
    def test_writes_file_and_returns_pointer(self, tmp_path) -> None:
        result = persist_markdown(tmp_path, "foo/bar.md", "# Hello")

        assert result == {"$ref": "foo/bar.md"}
        assert (tmp_path / "foo/bar.md").read_text(encoding="utf-8") == "# Hello"

    def test_creates_parent_directories(self, tmp_path) -> None:
        persist_markdown(tmp_path, "a/b/c.md", "body")

        assert (tmp_path / "a/b/c.md").exists()

    def test_rejects_path_traversal(self, tmp_path) -> None:
        with pytest.raises(ValueError):
            persist_markdown(tmp_path, "../escape.md", "body")

    def test_rejects_absolute_path(self, tmp_path) -> None:
        with pytest.raises(ValueError):
            persist_markdown(tmp_path, "/etc/passwd", "body")


class TestReadMarkdownRef:
    def test_round_trip(self, tmp_path) -> None:
        pointer = persist_markdown(tmp_path, "foo/bar.md", "# Hello")

        assert read_markdown_ref(tmp_path, pointer) == "# Hello"

    def test_legacy_string_passthrough(self, tmp_path) -> None:
        assert read_markdown_ref(tmp_path, "some legacy string") == "some legacy string"

    def test_raises_on_invalid_type(self, tmp_path) -> None:
        with pytest.raises(TypeError):
            read_markdown_ref(tmp_path, 42)
