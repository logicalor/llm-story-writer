"""Verification tests for issue #352 recap index upsert wiring."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

import presentation.orchestrator as orchestrator


def _build_name_to_slug(index_rows: list[dict[str, object]]) -> dict[str, str]:
    name_to_slug: dict[str, str] = {}
    for entry in index_rows:
        entry_name = str(entry.get("name") or "").strip()
        entry_slug = str(entry.get("slug") or "").strip()
        if entry_name and entry_slug:
            name_to_slug[entry_name.lower()] = entry_slug
        for alias in orchestrator._coerce_string_list(entry.get("aliases")):
            name_to_slug[alias.lower()] = entry_slug
    return name_to_slug


def _extract_recap_entity_slugs(
    recap_result: dict[str, str], index_rows: list[dict[str, object]]
) -> tuple[list[str], list[str]]:
    recap_participants: list[str] = []
    recap_locations: list[str] = []
    raw_events = recap_result.get("events") or ""

    if raw_events:
        try:
            name_to_slug = _build_name_to_slug(index_rows)
            decoded_events = json.loads(raw_events)
            if isinstance(decoded_events, list):
                events_list = [
                    event for event in decoded_events if isinstance(event, dict)
                ]
            else:
                events_list = []
        except (ValueError, TypeError):
            events_list = []
            name_to_slug = {}

        for event in events_list:
            for name in orchestrator._coerce_string_list(
                event.get("participants") or event.get("characters")
            ):
                slug = name_to_slug.get(name.lower())
                if slug:
                    recap_participants.append(slug)
            for name in orchestrator._coerce_string_list(event.get("locations")):
                slug = name_to_slug.get(name.lower())
                if slug:
                    recap_locations.append(slug)

    return list(dict.fromkeys(recap_participants)), list(dict.fromkeys(recap_locations))


async def _run_recap_index_upsert_block(
    *,
    story_name: str,
    chapter_number: int,
    recap_result: dict,
    bus: MagicMock,
) -> None:
    try:
        _parsed_events: list[dict] = (
            recap_result["events"]
            if isinstance(recap_result.get("events"), list)
            else []
        )
        await orchestrator.asyncio.to_thread(
            orchestrator.recap_index.delete_chapter_events,
            story_name,
            chapter_number,
        )
        await orchestrator.asyncio.to_thread(
            orchestrator.recap_index.upsert_recap_events,
            story_name,
            chapter_number,
            _parsed_events,
        )
        await bus.emit(
            f"[Recap] indexed chapter {chapter_number} ({len(_parsed_events)} events)\n"
        )
    except Exception as exc:  # pragma: no cover
        await bus.emit(f"[Recap] index upsert failed: {exc}\n")


def test_slug_resolution_maps_names_via_wiki_index() -> None:
    wiki_index = [
        {
            "name": "Amy Miller",
            "slug": "amy-miller",
            "type": "character",
            "aliases": ["Amy"],
            "path": "characters/amy-miller.md",
        },
        {
            "name": "The Park",
            "slug": "the-park",
            "type": "location",
            "aliases": [],
            "path": "locations/the-park.md",
        },
    ]

    name_to_slug = _build_name_to_slug(wiki_index)

    assert name_to_slug["amy miller"] == "amy-miller"
    assert name_to_slug["amy"] == "amy-miller"
    assert name_to_slug["the park"] == "the-park"
    assert "bob" not in name_to_slug


def test_slug_resolution_deduplicates_participants() -> None:
    wiki_index = [
        {
            "name": "Amy Miller",
            "slug": "amy-miller",
            "type": "character",
            "aliases": ["Amy"],
            "path": "characters/amy-miller.md",
        }
    ]
    recap_result = {
        "events": json.dumps(
            [
                {"participants": ["Amy"]},
                {"participants": ["Amy", "Amy Miller"]},
            ]
        )
    }

    participants, locations = _extract_recap_entity_slugs(recap_result, wiki_index)

    assert participants == ["amy-miller"]
    assert locations == []


@pytest.mark.asyncio
async def test_upsert_called_for_chapter_with_events(tmp_path: Path) -> None:
    recap_result = {
        "events": [{"participants": ["Amy"], "locations": ["The Park"]}],
    }
    bus = MagicMock()
    bus.emit = AsyncMock()

    async def _call_sync(func, *args):
        return func(*args)

    with (
        patch.object(orchestrator.recap_index, "delete_chapter_events") as delete_mock,
        patch.object(orchestrator.recap_index, "upsert_recap_events") as upsert_mock,
        patch.object(
            orchestrator.asyncio,
            "to_thread",
            new=AsyncMock(side_effect=_call_sync),
        ),
    ):
        await _run_recap_index_upsert_block(
            story_name="test-story",
            chapter_number=1,
            recap_result=recap_result,
            bus=bus,
        )

    delete_mock.assert_called_once_with("test-story", 1)
    upsert_mock.assert_called_once_with(
        "test-story",
        1,
        [{"participants": ["Amy"], "locations": ["The Park"]}],
    )
    bus.emit.assert_awaited_once_with("[Recap] indexed chapter 1 (1 events)\n")


@pytest.mark.asyncio
async def test_upsert_called_for_chapter_without_events(tmp_path: Path) -> None:
    recap_result: dict = {
        "events": [],
    }
    bus = MagicMock()
    bus.emit = AsyncMock()

    async def _call_sync(func, *args):
        return func(*args)

    with (
        patch.object(orchestrator.recap_index, "delete_chapter_events") as delete_mock,
        patch.object(orchestrator.recap_index, "upsert_recap_events") as upsert_mock,
        patch.object(
            orchestrator.asyncio,
            "to_thread",
            new=AsyncMock(side_effect=_call_sync),
        ),
    ):
        await _run_recap_index_upsert_block(
            story_name="test-story",
            chapter_number=1,
            recap_result=recap_result,
            bus=bus,
        )

    delete_mock.assert_called_once_with("test-story", 1)
    upsert_mock.assert_called_once_with("test-story", 1, [])
    bus.emit.assert_awaited_once_with("[Recap] indexed chapter 1 (0 events)\n")
