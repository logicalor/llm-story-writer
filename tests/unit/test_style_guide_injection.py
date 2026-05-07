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
from presentation.agents.chapter_writer import ChapterWriterAgent
from presentation.pipeline_primitives import TokenStreamBus, WikiContextBus


def _settings(**overrides: object) -> GenerationSettings:
    base = {
        "wanted_chapters": 1,
        "seed": 42,
        "scene_generation_pipeline": True,
        "scenes_per_chapter_min": 1,
        "scenes_per_chapter_max": 1,
        "enable_scene_critique": False,
        "enable_decomposition_critique": False,
        "enable_scrubbing": False,
    }
    base.update(overrides)
    return GenerationSettings(**base)


def _outline_result() -> OutlineResult:
    return OutlineResult(
        story_name="test-story",
        chapter_outlines=[
            {
                "chapter_number": 1,
                "title": "Chapter 1",
                "summary": "Chapter 1 summary",
            }
        ],
        summary="Story summary",
        genre="fantasy",
        themes=["courage"],
    )


def _make_provider(responses: list[str]) -> MagicMock:
    provider = MagicMock()
    response_iter = iter(responses)

    async def fake_stream(messages, model_config, seed=None):
        try:
            text = next(response_iter)
        except StopIteration:
            text = ""
        yield text

    provider.stream_text = fake_stream
    return provider


@pytest.mark.asyncio
async def test_pipeline_state_style_guide_round_trip(tmp_path: Path) -> None:
    style_guide = "## Voice\n- First person only\n\n## Banned\n- Ellipsis"
    state = PipelineState(
        story_name="test-style-guide",
        current_phase="init",
        style_guide=style_guide,
    )

    with patch("tools._io.STORIES_DIR", tmp_path):
        payload = state.to_dict()
        round_tripped = PipelineState.from_dict(payload)

    assert payload["style_guide"] == {"$ref": "style_guide.md"}
    assert round_tripped.style_guide.startswith("## Voice")
    assert round_tripped.style_guide == style_guide


def test_pipeline_state_style_guide_defaults_to_empty() -> None:
    state = PipelineState.from_dict({"story_name": "test", "current_phase": "init"})

    assert state.style_guide == ""


def test_pipeline_state_style_guide_loads_from_dict() -> None:
    style_guide = "## Voice\n- First person only"
    state = PipelineState.from_dict(
        {
            "story_name": "test",
            "current_phase": "init",
            "style_guide": style_guide,
        }
    )

    assert state.style_guide == style_guide


@pytest.mark.asyncio
async def test_chapter_writer_injects_style_guide_into_scene_variables(
    tmp_path: Path,
) -> None:
    captured_calls: list[tuple[str, dict[str, object]]] = []

    def fake_load_prompt(prompt_key: str, variables: dict[str, object]) -> str:
        captured_calls.append((prompt_key, dict(variables)))
        return f"PROMPT::{prompt_key}"

    provider = _make_provider(
        [
            "Expanded synopsis.",
            json.dumps([{"title": "Scene 1", "description": "Opening beat"}]),
            "Scene 1 prose.",
            "Actual scene recap.",
        ]
    )
    agent = ChapterWriterAgent(
        provider,
        {
            "models": {
                "chapter_outline_writer": "openai-compat://test",
                "scene_writer": "openai-compat://test",
            }
        },
        TokenStreamBus(),
        WikiContextBus(),
    )
    agent._loader.load_prompt = fake_load_prompt
    state = PipelineState(
        story_name="test-story",
        current_phase="chapters",
        style_guide="## Voice\n- First person",
    )

    with (
        patch("presentation.agents.chapter_writer.STORIES_DIR", tmp_path),
        patch(
            "presentation.agents.chapter_writer.assemble_context",
            return_value={"wiki_snapshot": "", "recap_snippets": []},
        ),
    ):
        chapter_text = await agent._run_scene_pipeline(
            story_name="test-story",
            chapter_number=1,
            chapter_title="Chapter 1",
            chapter_summary="Chapter 1 summary",
            story_elements="Story elements",
            base_context="Base context",
            next_chapter_summary="",
            settings=_settings(),
            state=state,
        )

    scene_prompt_calls = [
        variables
        for prompt_key, variables in captured_calls
        if prompt_key.startswith("multistep/scene/create_content")
    ]
    assert chapter_text
    assert scene_prompt_calls
    assert any(
        variables.get("style_guide") == "## Voice\n- First person"
        for variables in scene_prompt_calls
    )


@pytest.mark.asyncio
async def test_chapter_writer_style_guide_empty_when_state_none(
    tmp_path: Path,
) -> None:
    captured_calls: list[tuple[str, dict[str, object]]] = []

    def fake_load_prompt(prompt_key: str, variables: dict[str, object]) -> str:
        captured_calls.append((prompt_key, dict(variables)))
        return f"PROMPT::{prompt_key}"

    provider = _make_provider(
        [
            "Expanded synopsis.",
            json.dumps([{"title": "Scene 1", "description": "Opening beat"}]),
            "Scene 1 prose.",
            "Actual scene recap.",
        ]
    )
    agent = ChapterWriterAgent(
        provider,
        {
            "models": {
                "chapter_outline_writer": "openai-compat://test",
                "scene_writer": "openai-compat://test",
            }
        },
        TokenStreamBus(),
        WikiContextBus(),
    )
    agent._loader.load_prompt = fake_load_prompt

    with (
        patch("presentation.agents.chapter_writer.STORIES_DIR", tmp_path),
        patch(
            "presentation.agents.chapter_writer.assemble_context",
            return_value={"wiki_snapshot": "", "recap_snippets": []},
        ),
    ):
        chapter_text = await agent._run_scene_pipeline(
            story_name="test-story",
            chapter_number=1,
            chapter_title="Chapter 1",
            chapter_summary="Chapter 1 summary",
            story_elements="Story elements",
            base_context="Base context",
            next_chapter_summary="",
            settings=_settings(),
            state=None,
        )

    scene_prompt_calls = [
        variables
        for prompt_key, variables in captured_calls
        if prompt_key.startswith("multistep/scene/create_content")
    ]
    assert chapter_text
    assert scene_prompt_calls
    assert any(variables.get("style_guide") == "" for variables in scene_prompt_calls)
