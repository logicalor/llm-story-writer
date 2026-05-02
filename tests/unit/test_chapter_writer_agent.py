"""Verification tests for ChapterWriterAgent recap, outline, and scene prompts."""

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


def _outline_result(
    *,
    chapters: int = 3,
    chapter_summaries: list[str] | None = None,
    chapter_details: list[dict[str, object]] | None = None,
) -> OutlineResult:
    summaries = chapter_summaries or [f"Chapter {index} summary" for index in range(1, chapters + 1)]
    return OutlineResult(
        story_name="test-story",
        chapter_outlines=[
            {
                "chapter_number": index,
                "title": f"Chapter {index}",
                "summary": summaries[index - 1],
            }
            for index in range(1, chapters + 1)
        ],
        summary="Story summary",
        genre="fantasy",
        themes=["courage"],
        chapter_details=chapter_details or [],
    )


def _settings(**overrides: object) -> GenerationSettings:
    base = {
        "wanted_chapters": 3,
        "seed": 42,
        "scene_generation_pipeline": True,
        "scenes_per_chapter_min": 2,
        "scenes_per_chapter_max": 4,
    }
    base.update(overrides)
    return GenerationSettings(**base)


def _scene_payload(scene_count: int) -> str:
    return json.dumps(
        [
            {
                "title": f"Scene {index}",
                "description": f"Beat {index}",
            }
            for index in range(1, scene_count + 1)
        ]
    )


def _scene_pipeline_responses(scene_count: int) -> list[str]:
    return [
        "Expanded synopsis for chapter.",
        _scene_payload(scene_count),
        *[f"Scene {index} prose." for index in range(1, scene_count + 1)],
    ]


def _make_provider(responses: list[str]) -> tuple[MagicMock, list[str]]:
    provider = MagicMock()
    captured_systems: list[str] = []
    response_iter = iter(responses)

    async def fake_stream(messages, model_config, seed=None):
        captured_systems.append(
            next(message["content"] for message in messages if message["role"] == "system")
        )
        try:
            text = next(response_iter)
        except StopIteration:
            text = ""
        yield text

    provider.stream_text = fake_stream
    return provider, captured_systems


def _render_prompt(prompt_key: str, *, variables: dict[str, object]) -> str:
    return f"PROMPT::{prompt_key}\n{json.dumps(variables, sort_keys=True, ensure_ascii=False)}"


async def _run_agent(
    tmp_path: Path,
    *,
    chapter_number: int,
    outline_result: OutlineResult,
    responses: list[str],
    recaps: dict[str, object] | None = None,
    settings: GenerationSettings | None = None,
) -> tuple[object, list[str], list[str]]:
    provider, captured_systems = _make_provider(responses)
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    config = {
        "models": {
            "chapter_writer": "openai-compat://test",
            "chapter_outline_writer": "openai-compat://test",
            "scene_writer": "openai-compat://test",
        }
    }

    with (
        patch("presentation.agents.chapter_writer.PromptLoader") as loader_cls,
        patch("presentation.agents.chapter_writer.STORIES_DIR", tmp_path),
    ):
        loader = loader_cls.return_value
        loader.load_prompt.side_effect = _render_prompt
        agent = ChapterWriterAgent(provider, config, bus, wiki_bus)
        draft = await agent.run(
            story_name="test-story",
            chapter_number=chapter_number,
            outline_result=outline_result,
            settings=settings or _settings(),
            recaps=recaps,
        )

    prompt_keys = [call.args[0] for call in loader.load_prompt.call_args_list]
    return draft, captured_systems, prompt_keys


@pytest.mark.asyncio
async def test_real_recap_injected_for_chapter_2(tmp_path: Path) -> None:
    recaps = {"1": {"compact": "Chapter 1 compact recap", "events": "ignored"}}

    _, captured_systems, _ = await _run_agent(
        tmp_path,
        chapter_number=2,
        outline_result=_outline_result(),
        responses=_scene_pipeline_responses(scene_count=2),
        recaps=recaps,
    )

    assert any("Chapter 1 compact recap" in prompt for prompt in captured_systems)


@pytest.mark.asyncio
async def test_empty_recap_for_chapter_1(tmp_path: Path) -> None:
    _, captured_systems, _ = await _run_agent(
        tmp_path,
        chapter_number=1,
        outline_result=_outline_result(),
        responses=_scene_pipeline_responses(scene_count=2),
        recaps={"1": {"compact": "Should not appear"}},
    )

    assert all("Should not appear" not in prompt for prompt in captured_systems)


@pytest.mark.asyncio
async def test_detailed_outline_preferred_over_blurb(tmp_path: Path) -> None:
    outline_result = _outline_result(
        chapters=1,
        chapter_summaries=["short blurb"],
        chapter_details=[
            {
                "chapter_number": 1,
                "detail": "DETAILED_BLOCK_MARKER full detail beats block here",
            }
        ],
    )

    _, captured_systems, _ = await _run_agent(
        tmp_path,
        chapter_number=1,
        outline_result=outline_result,
        responses=_scene_pipeline_responses(scene_count=2),
    )

    assert any("DETAILED_BLOCK_MARKER" in prompt for prompt in captured_systems)
    assert all("short blurb" not in prompt for prompt in captured_systems)


@pytest.mark.asyncio
async def test_falls_back_to_blurb_when_no_chapter_details(tmp_path: Path) -> None:
    outline_result = _outline_result(
        chapters=1,
        chapter_summaries=["SKELETON_BLURB_MARKER"],
        chapter_details=[],
    )

    _, captured_systems, _ = await _run_agent(
        tmp_path,
        chapter_number=1,
        outline_result=outline_result,
        responses=_scene_pipeline_responses(scene_count=2),
    )

    assert any("SKELETON_BLURB_MARKER" in prompt for prompt in captured_systems)


@pytest.mark.asyncio
async def test_first_chapter_uses_first_scene_prompt(tmp_path: Path) -> None:
    _, _, prompt_keys = await _run_agent(
        tmp_path,
        chapter_number=1,
        outline_result=_outline_result(chapters=3),
        responses=_scene_pipeline_responses(scene_count=1),
    )

    assert "multistep/scene/create_content_first" in prompt_keys
    assert "multistep/scene/create_content_middle" not in prompt_keys
    assert "multistep/scene/create_content_final" not in prompt_keys


@pytest.mark.asyncio
async def test_final_chapter_uses_final_scene_prompt(tmp_path: Path) -> None:
    _, _, prompt_keys = await _run_agent(
        tmp_path,
        chapter_number=3,
        outline_result=_outline_result(chapters=3),
        responses=_scene_pipeline_responses(scene_count=2),
    )

    assert "multistep/scene/create_content_final" in prompt_keys
    assert "multistep/scene/create_content_middle" not in prompt_keys


@pytest.mark.asyncio
async def test_middle_chapter_uses_middle_scene_prompt(tmp_path: Path) -> None:
    _, _, prompt_keys = await _run_agent(
        tmp_path,
        chapter_number=2,
        outline_result=_outline_result(chapters=3),
        responses=_scene_pipeline_responses(scene_count=3),
    )

    assert "multistep/scene/create_content_middle" in prompt_keys


@pytest.mark.asyncio
async def test_scene_pipeline_false_uses_direct_path(tmp_path: Path) -> None:
    draft, _, prompt_keys = await _run_agent(
        tmp_path,
        chapter_number=1,
        outline_result=_outline_result(chapters=1),
        responses=["Direct chapter prose."],
        settings=_settings(scene_generation_pipeline=False),
    )

    assert prompt_keys == ["chapters/write_chapter_direct"]
    assert draft.content == "Direct chapter prose."