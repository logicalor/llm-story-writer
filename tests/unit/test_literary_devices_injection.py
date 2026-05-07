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
async def test_literary_devices_list_formats_as_bullets(tmp_path: Path) -> None:
    captured_calls: list[tuple[str, dict[str, object]]] = []

    def fake_load_prompt(prompt_key: str, variables: dict[str, object]) -> str:
        captured_calls.append((prompt_key, dict(variables)))
        return f"PROMPT::{prompt_key}"

    provider = _make_provider(
        [
            "Expanded synopsis.",
            json.dumps(
                [
                    {
                        "title": "Scene 1",
                        "description": "Opening beat",
                        "literary_devices": [
                            "dramatic irony",
                            "anaphora",
                            "unreliable narrator signal",
                        ],
                    }
                ]
            ),
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
    assert all(
        variables["literary_devices"]
        == "- dramatic irony\n- anaphora\n- unreliable narrator signal"
        for variables in scene_prompt_calls
    )
    assert all(
        "literary_devices" not in json.loads(str(variables["current_scene_summary"]))
        for variables in scene_prompt_calls
    )


@pytest.mark.asyncio
async def test_literary_devices_absent_produces_empty_string(tmp_path: Path) -> None:
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
    assert all(variables["literary_devices"] == "" for variables in scene_prompt_calls)
