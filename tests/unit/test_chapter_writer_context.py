"""Tests for ChapterWriterAgent character and setting context injection."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from application.pipeline.handoffs import OutlineResult
from domain.value_objects.generation_settings import GenerationSettings
from presentation.agents.chapter_writer import ChapterWriterAgent
from presentation.pipeline_primitives import TokenStreamBus, WikiContextBus


def _outline_result() -> OutlineResult:
    return OutlineResult(
        story_name="test-story",
        chapter_outlines=[{"chapter_number": 1, "title": "Ch 1", "summary": "Summary"}],
        summary="Story summary",
        genre="fantasy",
        themes=["courage"],
    )


def _settings() -> GenerationSettings:
    return GenerationSettings(wanted_chapters=1, seed=42)


@pytest.mark.asyncio
async def test_chapter_writer_includes_character_context(tmp_path: Path) -> None:
    """ChapterWriterAgent injects character sheet context into the prompt."""
    characters_dir = tmp_path / "test-story" / "characters"
    characters_dir.mkdir(parents=True)
    sheet_data = {
        "name": "Alice",
        "sheet": "# Alice\nThe protagonist.\nBrave and resourceful.",
        "chunks": {},
        "summary": "Brave protagonist",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    (characters_dir / "alice.json").write_text(json.dumps(sheet_data), encoding="utf-8")

    provider = MagicMock()
    captured_messages: list[dict[str, str]] = []

    async def fake_stream(messages, model_config, seed=None):
        captured_messages.extend(messages)
        yield "Generated chapter content."

    provider.stream_text = fake_stream
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    config = {
        "models": {"chapter_writer": "openai-compat://test-model"},
        "model_api_base": "http://localhost:1234/v1",
    }

    agent = ChapterWriterAgent(provider, config, bus, wiki_bus)
    with patch("presentation.agents.chapter_writer.STORIES_DIR", tmp_path):
        draft = await agent.run("test-story", 1, _outline_result(), _settings())

    assert draft is not None
    system_prompt = next(
        message["content"]
        for message in captured_messages
        if message["role"] == "system"
    )
    assert "Alice" in system_prompt
    assert "Brave protagonist" in system_prompt


@pytest.mark.asyncio
async def test_chapter_writer_includes_setting_context(tmp_path: Path) -> None:
    """ChapterWriterAgent injects setting sheet context into the prompt."""
    settings_dir = tmp_path / "test-story" / "settings"
    settings_dir.mkdir(parents=True)
    sheet_data = {
        "name": "The Citadel",
        "sheet": "# The Citadel\nA fortified city on the hill.",
        "chunks": {},
        "summary": "Fortified hilltop city",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    (settings_dir / "the-citadel.json").write_text(
        json.dumps(sheet_data), encoding="utf-8"
    )

    provider = MagicMock()
    captured_messages: list[dict[str, str]] = []

    async def fake_stream(messages, model_config, seed=None):
        captured_messages.extend(messages)
        yield "Generated chapter content."

    provider.stream_text = fake_stream
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    config = {
        "models": {"chapter_writer": "openai-compat://test-model"},
        "model_api_base": "http://localhost:1234/v1",
    }

    agent = ChapterWriterAgent(provider, config, bus, wiki_bus)
    with patch("presentation.agents.chapter_writer.STORIES_DIR", tmp_path):
        draft = await agent.run("test-story", 1, _outline_result(), _settings())

    assert draft is not None
    system_prompt = next(
        message["content"]
        for message in captured_messages
        if message["role"] == "system"
    )
    assert "The Citadel" in system_prompt
    assert "Fortified hilltop city" in system_prompt


@pytest.mark.asyncio
async def test_chapter_writer_no_context_when_no_sheets(tmp_path: Path) -> None:
    """ChapterWriterAgent runs normally when no character or setting dirs exist."""
    provider = MagicMock()
    captured_messages: list[dict[str, str]] = []

    async def fake_stream(messages, model_config, seed=None):
        captured_messages.extend(messages)
        yield "Generated content."

    provider.stream_text = fake_stream
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    config = {
        "models": {"chapter_writer": "openai-compat://test-model"},
        "model_api_base": "http://localhost:1234/v1",
    }

    agent = ChapterWriterAgent(provider, config, bus, wiki_bus)
    with patch("presentation.agents.chapter_writer.STORIES_DIR", tmp_path):
        draft = await agent.run("test-story", 1, _outline_result(), _settings())

    assert draft is not None
    system_prompt = next(
        message["content"]
        for message in captured_messages
        if message["role"] == "system"
    )
    assert "## Characters" not in system_prompt
    assert "## Settings" not in system_prompt
