"""Verification tests for Issue #53 — _validate_story_name extraction.

Confirms _validate_story_name() in src/tools/_io.py correctly validates
story names and rejects path traversal attempts, and normalizes to kebab-case.
"""

from pathlib import Path

import pytest

from src.tools._io import _slugify_story_name, _validate_story_name


@pytest.fixture()
def stories_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide a temp stories directory and patch STORIES_DIR."""
    d = tmp_path / "stories"
    d.mkdir()
    monkeypatch.setattr("src.tools._io.STORIES_DIR", d)
    return d


class TestSlugifyStoryName:
    def test_already_kebab_unchanged(self) -> None:
        assert _slugify_story_name("my-story") == "my-story"

    def test_spaces_to_hyphens(self) -> None:
        assert _slugify_story_name("The Silence Between Stars") == "the-silence-between-stars"

    def test_underscores_to_hyphens(self) -> None:
        assert _slugify_story_name("my_story_name") == "my-story-name"

    def test_mixed_case_lowercased(self) -> None:
        assert _slugify_story_name("My Great Story") == "my-great-story"

    def test_special_chars_stripped(self) -> None:
        assert _slugify_story_name("Story: The Beginning!") == "story-the-beginning"

    def test_consecutive_hyphens_collapsed(self) -> None:
        assert _slugify_story_name("story--name") == "story-name"

    def test_leading_trailing_hyphens_stripped(self) -> None:
        assert _slugify_story_name("-story-") == "story"


class TestValidateStoryName:
    def test_validate_story_name_valid(self, stories_dir: Path) -> None:
        result = _validate_story_name("my-story")
        assert result == stories_dir / "my-story"

    def test_validate_story_name_normalizes_to_kebab(self, stories_dir: Path) -> None:
        result = _validate_story_name("The Silence Between Stars")
        assert result == stories_dir / "the-silence-between-stars"

    def test_validate_story_name_path_traversal_rejected(
        self, stories_dir: Path
    ) -> None:
        with pytest.raises(SystemExit) as exc_info:
            _validate_story_name("../etc/passwd")
        assert exc_info.value.code == 1

    def test_validate_story_name_returns_resolved_path(self, stories_dir: Path) -> None:
        result = _validate_story_name("my-story")
        assert result.is_absolute()
        assert ".." not in result.parts
