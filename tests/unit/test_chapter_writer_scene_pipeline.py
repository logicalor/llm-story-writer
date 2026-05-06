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

from application.pipeline.handoffs import OutlineResult, PipelineState
from domain.value_objects.generation_settings import GenerationSettings
from presentation.agents.chapter_writer import (
    ChapterWriterAgent,
    _extract_json_array,
)
from presentation.pipeline_primitives import TokenStreamBus, WikiContextBus


@pytest.fixture(autouse=True)
def stub_assemble_context(monkeypatch, tmp_path: Path):
    """Create wiki dir and stub assemble_context for all tests in this module.

    Tests that patch assemble_context explicitly will override this stub.
    """
    wiki_dir = tmp_path / "test-story" / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "presentation.agents.chapter_writer.assemble_context",
        lambda *args, **kwargs: {
            "wiki_snapshot": "## Stub Wiki Context",
            "recap_snippets": [],
        },
    )


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
async def test_scene_snapshot_appears_in_base_context(tmp_path: Path) -> None:
    provider = MagicMock()
    captured_messages: list[str] = []

    async def fake_stream(messages, model_config, seed=None):
        captured_messages.append(
            next(m["content"] for m in messages if m["role"] == "system")
        )
        yield "Direct chapter prose."

    provider.stream_text = fake_stream

    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    config = {"models": {"chapter_writer": "openai-compat://test"}}

    agent = ChapterWriterAgent(provider, config, bus, wiki_bus)
    captured_variables: list[dict[str, str]] = []

    def fake_load_prompt(prompt_key: str, variables: dict[str, str]) -> str:
        captured_variables.append(dict(variables))
        return json.dumps(
            {
                "prompt_key": prompt_key,
                "base_context": variables.get("base_context", ""),
            }
        )

    agent._loader.load_prompt = fake_load_prompt

    wiki_dir = tmp_path / "test-story" / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)

    with (
        patch("presentation.agents.chapter_writer.STORIES_DIR", tmp_path),
        patch(
            "presentation.agents.chapter_writer.assemble_context",
            return_value={
                "wiki_snapshot": "WIKI_SNAPSHOT_CONTENT",
                "recap_snippets": [],
            },
        ),
    ):
        draft = await agent.run(
            "test-story",
            1,
            _outline_result(),
            _settings(scene_generation_pipeline=False),
        )

    assert draft.content == "Direct chapter prose."
    assert captured_variables[0]["base_context"] == "WIKI_SNAPSHOT_CONTENT"
    assert "WIKI_SNAPSHOT_CONTENT" in captured_messages[0]


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


@pytest.mark.asyncio
async def test_scene_pipeline_skips_decomposition_when_ledger_done(
    tmp_path: Path,
) -> None:
    scenes = [
        {"title": "Opening", "description": "Hero arrives at the gate."},
        {"title": "Climax", "description": "Hero confronts the guard."},
    ]
    provider, captured = _make_provider(["Scene 1 prose body.", "Scene 2 prose body."])
    state = PipelineState(
        story_name="test-story",
        current_phase="chapters",
        completed_work_items={"chapter-1": ["scenes/decomposition"]},
    )

    scenes_file = tmp_path / "test-story" / "chapters" / "chapter_1_scenes.json"
    scenes_file.parent.mkdir(parents=True, exist_ok=True)
    scenes_file.write_text(json.dumps(scenes), encoding="utf-8")

    agent = ChapterWriterAgent(
        provider,
        {
            "models": {
                "chapter_writer": "openai-compat://test",
                "chapter_outline_writer": "openai-compat://test",
                "scene_writer": "openai-compat://test",
            }
        },
        TokenStreamBus(),
        WikiContextBus(),
    )

    with patch("presentation.agents.chapter_writer.STORIES_DIR", tmp_path):
        draft = await agent.run(
            "test-story", 1, _outline_result(), _settings(), state=state
        )

    assert draft.content
    assert len(captured) == 2
    assert "Scene 1 prose body." in draft.content
    assert "Scene 2 prose body." in draft.content


@pytest.mark.asyncio
async def test_scene_pipeline_skips_completed_scenes_on_resume(tmp_path: Path) -> None:
    scenes = [
        {"title": "Opening", "description": "Hero arrives at the gate."},
        {"title": "Climax", "description": "Hero confronts the guard."},
    ]
    provider, captured = _make_provider(["Scene 2 prose body."])
    state = PipelineState(
        story_name="test-story",
        current_phase="chapters",
        completed_work_items={"chapter-1": ["scenes/decomposition", "scene:1"]},
    )

    scenes_file = tmp_path / "test-story" / "chapters" / "chapter_1_scenes.json"
    scenes_file.parent.mkdir(parents=True, exist_ok=True)
    scenes_file.write_text(json.dumps(scenes), encoding="utf-8")
    scene_1_path = tmp_path / "test-story" / "chapters" / "chapter_1" / "scene_1.md"
    scene_1_path.parent.mkdir(parents=True, exist_ok=True)
    scene_1_path.write_text("Scene 1 prose from disk", encoding="utf-8")

    agent = ChapterWriterAgent(
        provider,
        {
            "models": {
                "chapter_writer": "openai-compat://test",
                "chapter_outline_writer": "openai-compat://test",
                "scene_writer": "openai-compat://test",
            }
        },
        TokenStreamBus(),
        WikiContextBus(),
    )

    with patch("presentation.agents.chapter_writer.STORIES_DIR", tmp_path):
        draft = await agent.run(
            "test-story", 1, _outline_result(), _settings(), state=state
        )

    assert "Scene 1 prose from disk" in draft.content
    assert "Scene 2 prose body." in draft.content
    assert len(captured) == 1
    assert "Climax" in captured[0]


@pytest.mark.asyncio
async def test_scene_pipeline_marks_work_items_done(tmp_path: Path) -> None:
    scenes_payload = json.dumps(
        [
            {"title": "Opening", "description": "Hero arrives at the gate."},
            {"title": "Climax", "description": "Hero confronts the guard."},
        ]
    )
    provider, captured = _make_provider(
        [
            "Detailed synopsis content for chapter 1.",
            f"```json\n{scenes_payload}\n```",
            "Scene 1 prose body.",
            "Scene 2 prose body.",
        ]
    )
    state = PipelineState(story_name="test-story", current_phase="chapters")

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    agent = ChapterWriterAgent(
        provider,
        {
            "models": {
                "chapter_writer": "openai-compat://test",
                "chapter_outline_writer": "openai-compat://test",
                "scene_writer": "openai-compat://test",
            }
        },
        TokenStreamBus(),
        WikiContextBus(),
    )

    with (
        patch("presentation.agents.chapter_writer.STORIES_DIR", tmp_path),
        patch(
            "presentation.agents.chapter_writer._savepoint_path",
            side_effect=fake_savepoint_path,
        ),
    ):
        draft = await agent.run(
            "test-story", 1, _outline_result(), _settings(), state=state
        )

    assert draft.content
    assert len(captured) == 4
    completed = state.completed_work_items.get("chapter-1", [])
    assert "scenes/decomposition" in completed
    assert "scene:1" in completed
    assert "scene:2" in completed


def test_extract_json_array_strips_fences() -> None:
    payload = '```json\n[{"title": "A"}, {"title": "B"}]\n```'
    scenes = _extract_json_array(payload)
    assert scenes == [{"title": "A"}, {"title": "B"}]


def test_extract_json_array_returns_empty_on_garbage() -> None:
    assert _extract_json_array("no json here") == []
    assert _extract_json_array("[malformed") == []


@pytest.mark.asyncio
async def test_scene_prompt_receives_scene_recap_context(tmp_path: Path) -> None:
    provider, captured = _make_provider(
        [
            "Detailed synopsis content for chapter 1.",
            json.dumps(
                [
                    {"title": "Opening", "description": "Hero arrives."},
                    {"title": "Climax", "description": "Hero wins."},
                ]
            ),
            "Scene 1 prose body.",
            "Scene 2 prose body.",
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

    def assemble_side_effect(*args, **kwargs):
        if kwargs.get("scope") == "scene":
            return {
                "wiki_snapshot": "scene wiki",
                "recap_snippets": ["scene recap A"],
            }
        return {
            "wiki_snapshot": "wiki",
            "recap_snippets": [],
        }

    agent = ChapterWriterAgent(provider, config, bus, wiki_bus)
    with (
        patch("presentation.agents.chapter_writer.STORIES_DIR", tmp_path),
        patch(
            "presentation.agents.chapter_writer.assemble_context",
            side_effect=assemble_side_effect,
        ),
    ):
        await agent.run("test-story", 1, _outline_result(), _settings())

    assert any("scene recap A" in prompt for prompt in captured)


def test_extract_json_array_filters_non_dict_entries() -> None:
    payload = '[{"title": "A"}, "stray string", 42, {"title": "B"}]'
    assert _extract_json_array(payload) == [{"title": "A"}, {"title": "B"}]


@pytest.mark.asyncio
async def test_scene_pipeline_calls_assemble_context_per_scene(tmp_path: Path) -> None:
    """assemble_context runs at chapter scope and again for each scene."""
    wiki_dir = tmp_path / "test-story" / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)

    scenes_payload = json.dumps(
        [
            {"title": "Scene A", "description": "First beat."},
            {"title": "Scene B", "description": "Second beat."},
        ]
    )
    provider, _ = _make_provider(
        [
            "Synopsis text.",
            f"```json\n{scenes_payload}\n```",
            "Scene A prose.",
            "Scene B prose.",
        ]
    )

    config = {
        "models": {
            "chapter_writer": "openai-compat://test",
            "chapter_outline_writer": "openai-compat://test",
            "scene_writer": "openai-compat://test",
        }
    }
    agent = ChapterWriterAgent(provider, config, TokenStreamBus(), WikiContextBus())

    call_count = 0

    def _assemble_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return {
            "wiki_snapshot": f"## Wiki snapshot {call_count}",
            "recap_snippets": [],
        }

    with (
        patch("presentation.agents.chapter_writer.STORIES_DIR", tmp_path),
        patch(
            "presentation.agents.chapter_writer.assemble_context",
            side_effect=_assemble_side_effect,
        ),
    ):
        draft = await agent.run("test-story", 1, _outline_result(), _settings())

    assert call_count == 3
    assert draft.content


@pytest.mark.asyncio
async def test_scene_pipeline_falls_back_per_scene_when_scene_context_unavailable(
    tmp_path: Path,
) -> None:
    """When scene-scope assembly fails, generation still produces output.

    The chapter-level context returns valid content; per-scene calls raise to
    exercise the graceful fallback path in the scene pipeline.
    """
    scenes_payload = json.dumps(
        [{"title": "Only Scene", "description": "The one and only beat."}]
    )
    provider, _ = _make_provider(
        [
            "Synopsis text.",
            f"```json\n{scenes_payload}\n```",
            "Scene prose content.",
        ]
    )

    config = {
        "models": {
            "chapter_writer": "openai-compat://test",
            "chapter_outline_writer": "openai-compat://test",
            "scene_writer": "openai-compat://test",
        }
    }
    agent = ChapterWriterAgent(provider, config, TokenStreamBus(), WikiContextBus())

    call_count = 0

    def _side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if kwargs.get("scope") == "chapter":
            return {
                "wiki_snapshot": "## Wiki Context\nChapter context",
                "recap_snippets": [],
            }
        raise RuntimeError("scene context unavailable")

    with (
        patch("presentation.agents.chapter_writer.STORIES_DIR", tmp_path),
        patch(
            "presentation.agents.chapter_writer.assemble_context",
            side_effect=_side_effect,
        ),
    ):
        draft = await agent.run(
            "test-story",
            1,
            _outline_result(),
            _settings(scenes_per_chapter_min=1),
        )

    assert draft.content
    assert "Scene prose content." in draft.content
