"""Verification tests for issue #344 wiki consolidation behavior."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from application.pipeline.handoffs import OutlineResult
from domain.value_objects.generation_settings import GenerationSettings
from presentation.agents.chapter_writer import ChapterWriterAgent
from presentation.pipeline_primitives import TokenStreamBus, WikiContextBus
from presentation.orchestrator import _sync_recap_events_to_wiki
from tools import wiki_extract


def _outline_result() -> OutlineResult:
    return OutlineResult(
        story_name="test-story",
        chapter_outlines=[
            {"chapter_number": 1, "title": "Chapter 1", "summary": "Summary"}
        ],
        summary="Story summary",
        genre="fantasy",
        themes=["courage"],
    )


def _settings() -> GenerationSettings:
    return GenerationSettings(
        wanted_chapters=1,
        seed=42,
        scene_generation_pipeline=False,
    )


def test_list_wiki_entities_returns_entities_without_outline(tmp_path: Path) -> None:
    story_dir = tmp_path / "test-story"
    story_dir.mkdir()

    with (
        patch("tools.wiki_extract._validate_story_name", return_value=story_dir),
        patch("tools.wiki_extract._load_outline_savepoint", return_value=""),
        patch(
            "tools.wiki_extract._read_sheet_files",
            side_effect=[
                [
                    {
                        "name": "Alice",
                        "sheet_text": "...",
                        "path": story_dir / "characters" / "alice.json",
                    }
                ],
                [],
            ],
        ),
        patch(
            "tools.wiki_extract._extract_sheet_entities",
            return_value=[
                {
                    "name": "Alice",
                    "type": "character",
                    "description": "protagonist",
                }
            ],
        ) as extract_sheet_entities,
        patch(
            "tools.wiki_extract._extract_outline_entities"
        ) as extract_outline_entities,
    ):
        entities = wiki_extract._list_wiki_entities("test-story")

    assert extract_sheet_entities.called
    extract_outline_entities.assert_not_called()
    assert entities
    assert entities[0]["name"] == "Alice"


def test_list_wiki_entities_includes_outline_entities_when_outline_exists(
    tmp_path: Path,
) -> None:
    story_dir = tmp_path / "test-story"
    story_dir.mkdir()

    with (
        patch("tools.wiki_extract._validate_story_name", return_value=story_dir),
        patch(
            "tools.wiki_extract._load_outline_savepoint",
            return_value="Chapter 1 outline with Bob.",
        ),
        patch("tools.wiki_extract._read_sheet_files", side_effect=[[], []]),
        patch(
            "tools.wiki_extract._extract_outline_entities",
            return_value=[{"name": "Bob", "type": "character"}],
        ) as extract_outline_entities,
    ):
        entities = wiki_extract._list_wiki_entities("test-story")

    extract_outline_entities.assert_called_once()
    assert [entity["name"] for entity in entities] == ["Bob"]


@pytest.mark.asyncio
async def test_chapter_writer_skips_entity_context_when_wiki_snapshot_available(
    tmp_path: Path,
) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    config = {
        "models": {"chapter_writer": "openai-compat://test-model"},
        "model_api_base": "http://localhost:1234/v1",
    }
    story_dir = tmp_path / "test-story"
    (story_dir / "wiki").mkdir(parents=True)
    agent = ChapterWriterAgent(provider, config, bus, wiki_bus)

    with (
        patch("presentation.agents.chapter_writer.STORIES_DIR", tmp_path),
        patch(
            "presentation.agents.chapter_writer.get_snapshot",
            return_value="## Wiki Context\nAlice facts",
        ) as mock_get_snapshot,
        patch.object(
            agent,
            "_build_entity_context",
            return_value=("unused", "unused", "unused"),
        ) as build_entity_context,
        patch.object(
            agent,
            "_draft_direct",
            new=AsyncMock(return_value="Generated chapter content."),
        ),
    ):
        draft = await agent.run("test-story", 1, _outline_result(), _settings())

    mock_get_snapshot.assert_called_once()
    build_entity_context.assert_not_called()
    assert draft.content == "Generated chapter content."


def test_sync_recap_events_to_wiki_creates_event_pages(tmp_path: Path) -> None:
    story_dir = tmp_path / "test-story"
    (story_dir / "wiki").mkdir(parents=True)
    recap_events = [
        {
            "title": "Alice Confronts Captain Vale",
            "summary": "Alice forces the truth into the open.",
            "timestamp": "Day 2, dusk",
            "participants": ["Alice", "Captain Vale"],
            "importance": "high",
            "emotional_state": "furious",
            "causal_context": "Fallout from the failed courier run.",
        }
    ]

    with (
        patch("presentation.orchestrator._validate_story_name", return_value=story_dir),
        patch("presentation.orchestrator.find_pages", return_value=[]),
        patch(
            "presentation.orchestrator.wiki_update_run_batch",
            return_value={
                "created": 1,
                "updated": 0,
                "timeline_events": 0,
                "entity_counts": {"event": 1},
            },
        ) as mock_run_batch,
    ):
        result = _sync_recap_events_to_wiki("test-story", 3, recap_events)

    payload = mock_run_batch.call_args.args[1]
    event_page = payload["creates"][0]

    assert result["created"] == 1
    assert payload["updates"] == []
    assert payload["timeline_events"] == []
    assert event_page["page_type"] == "event"
    assert event_page["chapter"] == 3
    assert event_page["frontmatter"]["timestamp"] == "Day 2, dusk"
    assert event_page["frontmatter"]["participants"] == ["alice", "captain-vale"]
    assert event_page["frontmatter"]["importance"] == "high"
    assert event_page["frontmatter"]["emotional_state"] == "furious"
    assert (
        event_page["frontmatter"]["causal_context"]
        == "Fallout from the failed courier run."
    )
    assert event_page["frontmatter"]["chapter_provenance"] == 3
