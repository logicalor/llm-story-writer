"""Integration verification for issue #350 recap event sync."""

import sys
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from tools import _io
from tools.wiki_init import _init_wiki_for_story
from presentation.orchestrator import _sync_recap_events_to_wiki


def test_fenced_events_create_wiki_pages(tmp_path: Path) -> None:
    story_name = "test-story"
    story_dir = tmp_path / story_name
    story_dir.mkdir()

    with patch.object(_io, "STORIES_DIR", tmp_path):
        init_result = _init_wiki_for_story(story_name, _io.STORIES_DIR)
        assert init_result["status"] == "ok"

        recap_events = (
            "LLM output follows:\n"
            "```json\n"
            '[{"name": "The Big Fight", "importance": "high", '
            '"participants": ["alice", "bob"]}]\n'
            "```\n"
            "End."
        )

        result = _sync_recap_events_to_wiki(
            story_name,
            chapter_number=1,
            recap_events=recap_events,
        )

    assert result["created"] >= 1
    assert (story_dir / "wiki" / "events" / "the-big-fight.md").exists()
