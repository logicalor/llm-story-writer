"""Verification tests for Issue #53 — _validate_story_name extraction.

Confirms _validate_story_name() in src/tools/_io.py correctly validates
story names and rejects path traversal attempts.
"""

from pathlib import Path

import pytest

from src.tools._io import _validate_story_name


@pytest.fixture()
def stories_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide a temp stories directory and patch STORIES_DIR."""
    d = tmp_path / "stories"
    d.mkdir()
    monkeypatch.setattr("src.tools._io.STORIES_DIR", d)
    return d


class TestValidateStoryName:
    def test_validate_story_name_valid(self, stories_dir: Path) -> None:
        result = _validate_story_name("my-story")
        assert result == stories_dir / "my-story"

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
