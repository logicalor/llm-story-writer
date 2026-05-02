"""Tests for ChapterWriterAgent multi-stage scene pipeline."""

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
from presentation.agents.chapter_writer import (
    ChapterWriterAgent,
    _extract_json_array,
)
from presentation.pipeline_primitives import TokenStreamBus, WikiContextBus


def _outline_result() -> OutlineResult:
    return OutlineResult(
        story_name="test-story",
        chapter_outlines=[
            {"chapter_number": 1, "title": "Ch 1", "summary": "Chapter 1 summary"},
            {"chapter_number": 2, "title": "Ch 2", "summary": "Chapter 2 summary"},
        ],
        summary="Story summary",
        genre="fantasy",
        themes=["courage"],
    )


def _settings(**overrides) -> GenerationSettings:
    base = {
        "wanted_chapters": 2,
        "seed": 42,
        "scene_generation_pipeline": True,
        "scenes_per_chapter_min": 2,
        "scenes_per_chapter_max": 3,
    }
    base.update(overrides)
    return GenerationSettings(**base)


def _make_provider(responses: list[str]):
    """Build a provider whose `stream_text` returns each response in order.

    Captures the system prompt of every call so tests can assert call ordering.
    """
    provider = MagicMock()
    captured_systems: list[str] = []
    response_iter = iter(responses)

    async def fake_stream(messages, model_config, seed=None):
        captured_systems.append(
            next(m["content"] for m in messages if m["role"] == "system")
        )
        try:
            text = next(response_iter)
        except StopIteration:
            text = ""
        for token in [text]:
            yield token

    provider.stream_text = fake_stream
    return provider, captured_systems


@pytest.mark.asyncio
async def test_scene_pipeline_runs_three_stages_in_order(tmp_path: Path) -> None:
    """Synopsis → scene-array → per-scene calls happen in order with correct prompts."""
    scenes_payload = json.dumps(
        [
            {"title": "Opening", "description": "Hero arrives at the gate."},
            {"title": "Climax", "description": "Hero confronts the guard."},
        ]
    )
    provider, captured = _make_provider(
        [
            "Detailed synopsis content for chapter 1.",  # synopsis call
            f"```json\n{scenes_payload}\n```",  # scene decomposition call
            "Scene 1 prose body.",  # scene 1 drafting
            "Scene 2 prose body.",  # scene 2 drafting
        ]
    )

    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    config = {
        "models": {
            "chapter_writer": "openai-compat://test",
            "chapter_outline_writer": "openai-compat://test",
            "scene_writer": "openai-compat://test",
        },
        "model_api_base": "http://localhost/v1",
    }

    agent = ChapterWriterAgent(provider, config, bus, wiki_bus)
    with patch("presentation.agents.chapter_writer.STORIES_DIR", tmp_path):
        draft = await agent.run("test-story", 1, _outline_result(), _settings())

    # Four stream_text invocations: synopsis, scenes, scene1, scene2.
    assert len(captured) == 4
    assert "Create Chapter Synopsis" in captured[0]
    assert "scene" in captured[1].lower()
    assert "Opening" in captured[2]
    assert "Climax" in captured[3]

    # Final chapter content concatenates scene prose under the chapter title.
    assert "Scene 1 prose body." in draft.content
    assert "Scene 2 prose body." in draft.content
    assert draft.title in draft.content

    # Scene definitions are persisted to disk for downstream tooling.
    scenes_file = tmp_path / "test-story" / "chapters" / "chapter_1_scenes.json"
    assert scenes_file.exists()
    persisted = json.loads(scenes_file.read_text(encoding="utf-8"))
    assert len(persisted) == 2
    assert persisted[0]["title"] == "Opening"


@pytest.mark.asyncio
async def test_scene_pipeline_falls_back_when_json_unparseable(tmp_path: Path) -> None:
    """When scene decomposition returns no JSON array, agent falls back to direct."""
    provider, captured = _make_provider(
        [
            "Detailed synopsis text.",  # synopsis
            "I cannot produce JSON, sorry.",  # scenes (unparseable)
            "Direct chapter prose fallback.",  # direct draft
        ]
    )

    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    config = {
        "models": {
            "chapter_writer": "openai-compat://test",
            "chapter_outline_writer": "openai-compat://test",
            "scene_writer": "openai-compat://test",
        }
    }

    agent = ChapterWriterAgent(provider, config, bus, wiki_bus)
    with patch("presentation.agents.chapter_writer.STORIES_DIR", tmp_path):
        draft = await agent.run("test-story", 1, _outline_result(), _settings())

    # Three calls: synopsis, scenes (failed parse), direct draft fallback.
    assert len(captured) == 3
    # Fallback call must use the direct single-shot chapter prompt, which
    # carries the "Chapter Assignment" header (unique to write_chapter_direct).
    assert "Chapter Assignment" in captured[2]
    assert draft.content == "Direct chapter prose fallback."


@pytest.mark.asyncio
async def test_scene_pipeline_disabled_uses_direct_path(tmp_path: Path) -> None:
    """With `scene_generation_pipeline=False`, only one direct call is made."""
    provider, captured = _make_provider(["Direct chapter prose."])

    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    config = {"models": {"chapter_writer": "openai-compat://test"}}

    agent = ChapterWriterAgent(provider, config, bus, wiki_bus)
    settings = _settings(scene_generation_pipeline=False)
    with patch("presentation.agents.chapter_writer.STORIES_DIR", tmp_path):
        draft = await agent.run("test-story", 1, _outline_result(), settings)

    assert len(captured) == 1
    assert draft.content == "Direct chapter prose."


@pytest.mark.asyncio
async def test_revision_feedback_uses_direct_path(tmp_path: Path) -> None:
    """Revision feedback always routes through the single-shot direct path."""
    provider, captured = _make_provider(["Revised chapter prose."])

    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    config = {"models": {"chapter_writer": "openai-compat://test"}}

    agent = ChapterWriterAgent(provider, config, bus, wiki_bus)
    with patch("presentation.agents.chapter_writer.STORIES_DIR", tmp_path):
        draft = await agent.run(
            "test-story",
            1,
            _outline_result(),
            _settings(),  # pipeline enabled
            feedback="Fix pacing in scene 2.",
        )

    # Only one call — direct path — and it carries the feedback in the system prompt.
    assert len(captured) == 1
    assert "Fix pacing in scene 2." in captured[0]
    assert draft.content == "Revised chapter prose."


def test_extract_json_array_strips_fences() -> None:
    payload = '```json\n[{"title": "A"}, {"title": "B"}]\n```'
    scenes = _extract_json_array(payload)
    assert scenes == [{"title": "A"}, {"title": "B"}]


def test_extract_json_array_returns_empty_on_garbage() -> None:
    assert _extract_json_array("no json here") == []
    assert _extract_json_array("[malformed") == []


def test_extract_json_array_filters_non_dict_entries() -> None:
    payload = '[{"title": "A"}, "stray string", 42, {"title": "B"}]'
    assert _extract_json_array(payload) == [{"title": "A"}, {"title": "B"}]
