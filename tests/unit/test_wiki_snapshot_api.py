"""Verification tests for the get_snapshot() public API.

Confirms the Python API at tools.wiki_snapshot.get_snapshot returns the right
value (or None) under the expected conditions without raising.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from tools.wiki_snapshot import get_snapshot


def _make_story_dir(tmp_path: Path, story_name: str = "test-story") -> Path:
    """Create a minimal story directory with a wiki subdirectory."""
    story_dir = tmp_path / story_name
    wiki_dir = story_dir / "wiki"
    wiki_dir.mkdir(parents=True)
    return story_dir


def test_get_snapshot_returns_none_when_no_collection(tmp_path: Path) -> None:
    story_dir = _make_story_dir(tmp_path)
    with (
        patch("tools.wiki_snapshot._validate_story_name", return_value=story_dir),
        patch("tools.wiki_snapshot.get_wiki_dir", return_value=story_dir / "wiki"),
        patch("tools.wiki_snapshot._get_collection", return_value=None),
    ):
        result = get_snapshot(
            story_name="test-story", chapter=1, scene=1, outline="test outline"
        )
    assert result is None


def test_get_snapshot_returns_none_when_collection_empty(tmp_path: Path) -> None:
    story_dir = _make_story_dir(tmp_path)
    mock_collection = MagicMock()
    mock_collection.count.return_value = 0
    with (
        patch("tools.wiki_snapshot._validate_story_name", return_value=story_dir),
        patch("tools.wiki_snapshot.get_wiki_dir", return_value=story_dir / "wiki"),
        patch("tools.wiki_snapshot._get_collection", return_value=mock_collection),
    ):
        result = get_snapshot(
            story_name="test-story", chapter=1, scene=1, outline="test outline"
        )
    assert result is None


def test_get_snapshot_returns_none_on_exception(tmp_path: Path) -> None:
    """Any exception inside get_snapshot must be swallowed; None returned."""
    with patch(
        "tools.wiki_snapshot._validate_story_name",
        side_effect=Exception("db error"),
    ):
        result = get_snapshot(
            story_name="test-story", chapter=1, scene=1, outline="test outline"
        )
    assert result is None


def test_get_snapshot_returns_string_when_pipeline_succeeds(tmp_path: Path) -> None:
    story_dir = _make_story_dir(tmp_path)
    mock_collection = MagicMock()
    mock_collection.count.return_value = 5
    with (
        patch("tools.wiki_snapshot._validate_story_name", return_value=story_dir),
        patch("tools.wiki_snapshot.get_wiki_dir", return_value=story_dir / "wiki"),
        patch("tools.wiki_snapshot._get_collection", return_value=mock_collection),
        patch(
            "tools.wiki_snapshot._build_snapshot",
            return_value=("## Scene Context\nsome content", {}),
        ),
    ):
        result = get_snapshot(
            story_name="test-story", chapter=1, scene=1, outline="test outline"
        )
    assert result is not None
    assert isinstance(result, str)
    assert "Scene Context" in result
