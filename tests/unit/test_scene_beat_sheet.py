import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from application.pipeline.handoffs import OutlineResult
from domain.value_objects.generation_settings import GenerationSettings
from presentation.agents.chapter_writer import ChapterWriterAgent
from presentation.pipeline_primitives import TokenStreamBus, WikiContextBus


def _make_provider(responses: list[str]) -> tuple[object, list[str]]:
    captured: list[str] = []

    class _Prov:
        async def stream_text(self, messages, model_config, seed=None):
            captured.append(messages[0]["content"])
            yield responses.pop(0)

    return _Prov(), captured


def _settings(**kwargs: object) -> GenerationSettings:
    base = {
        "wanted_chapters": 1,
        "seed": 1,
        "scene_generation_pipeline": True,
        "scenes_per_chapter_min": 2,
        "scenes_per_chapter_max": 2,
        "enable_outline_critique": False,
        "enable_scene_critique": False,
        "enable_decomposition_critique": False,
        "enable_scrubbing": False,
    }
    base.update(kwargs)
    return GenerationSettings(**base)


def _outline_result() -> OutlineResult:
    return OutlineResult(
        story_name="test-story",
        chapter_outlines=[
            {
                "chapter_number": 1,
                "title": "Ch1",
                "summary": "summary",
            }
        ],
        summary="Story summary",
        genre="fantasy",
        themes=["courage"],
    )


def _render_prompt(prompt_key: str, *, variables: dict[str, object]) -> str:
    return json.dumps(
        {"prompt_key": prompt_key, "variables": variables},
        ensure_ascii=False,
        sort_keys=True,
    )


def _two_scenes() -> list[dict[str, object]]:
    return [
        {
            "title": "S1",
            "description": "d1",
            "key_events": ["e1"],
            "ending": "end1",
            "literary_devices": [],
            "characters": [],
            "setting": "loc",
        },
        {
            "title": "S2",
            "description": "d2",
            "key_events": ["e2"],
            "ending": "end2",
            "literary_devices": [],
            "characters": [],
            "setting": "loc",
        },
    ]


@pytest.fixture(autouse=True)
def _stub_wiki(monkeypatch):
    monkeypatch.setattr(
        "presentation.agents.chapter_writer.assemble_context",
        lambda *a, **kw: {
            "wiki_snapshot": "## Stub Wiki Context",
            "recap_snippets": [],
        },
    )


@pytest.mark.asyncio
async def test_beat_sheet_disabled_default(tmp_path: Path) -> None:
    provider, captured = _make_provider(
        [
            "synopsis text",
            json.dumps(_two_scenes()),
            "scene one prose",
            "Scene 1 recap.",
            "scene two prose",
            "Scene 2 recap.",
        ]
    )
    with (
        patch("presentation.agents.chapter_writer.PromptLoader") as loader_cls,
        patch("presentation.agents.chapter_writer.STORIES_DIR", tmp_path),
    ):
        loader_cls.return_value.load_prompt.side_effect = _render_prompt
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
        draft = await agent.run("test-story", 1, _outline_result(), _settings())

    parsed_prompts = [json.loads(prompt) for prompt in captured]
    prose_prompts = [
        prompt
        for prompt in parsed_prompts
        if prompt["prompt_key"].startswith("multistep/scene/create_content")
    ]

    assert "scene one prose" in draft.content
    assert "scene two prose" in draft.content
    assert len(captured) == 6
    assert all(
        prompt["prompt_key"] != "multistep/scene/create_beat_sheet"
        for prompt in parsed_prompts
    )
    assert prose_prompts
    assert all(
        prompt["variables"]["beat_sheet_section"] == "" for prompt in prose_prompts
    )


@pytest.mark.asyncio
async def test_beat_sheet_enabled_makes_extra_calls(tmp_path: Path) -> None:
    provider, captured = _make_provider(
        [
            "synopsis text",
            json.dumps(_two_scenes()),
            "beat sheet one",
            "scene one prose",
            "Scene 1 recap.",
            "beat sheet two",
            "scene two prose",
            "Scene 2 recap.",
        ]
    )

    with (
        patch("presentation.agents.chapter_writer.PromptLoader") as loader_cls,
        patch("presentation.agents.chapter_writer.STORIES_DIR", tmp_path),
    ):
        loader_cls.return_value.load_prompt.side_effect = _render_prompt
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
        draft = await agent.run(
            "test-story",
            1,
            _outline_result(),
            _settings(enable_beat_sheet=True),
        )

    parsed_prompts = [json.loads(prompt) for prompt in captured]
    prompt_keys = [prompt["prompt_key"] for prompt in parsed_prompts]
    prose_prompts = [
        prompt
        for prompt in parsed_prompts
        if prompt["prompt_key"].startswith("multistep/scene/create_content")
    ]

    assert "scene one prose" in draft.content
    assert "scene two prose" in draft.content
    assert len(captured) == 8
    assert prompt_keys == [
        "chapters/create_synopsis",
        "chapters/expand_to_scenes",
        "multistep/scene/create_beat_sheet",
        "multistep/scene/create_content_first",
        "scenes/summarise_for_continuity",
        "multistep/scene/create_beat_sheet",
        "multistep/scene/create_content_final",
        "scenes/summarise_for_continuity",
    ]
    assert (
        prose_prompts[0]["variables"]["beat_sheet_section"].count("<BEAT_SHEET>") == 1
    )
    assert "beat sheet one" in prose_prompts[0]["variables"]["beat_sheet_section"]
    assert (
        prose_prompts[1]["variables"]["beat_sheet_section"].count("<BEAT_SHEET>") == 1
    )
    assert "beat sheet two" in prose_prompts[1]["variables"]["beat_sheet_section"]


@pytest.mark.asyncio
async def test_beat_sheet_error_does_not_abort_scene(tmp_path: Path) -> None:
    captured: list[str] = []
    responses = [
        "synopsis text",
        json.dumps(_two_scenes()),
        "scene one prose",
        "Scene 1 recap.",
        "scene two prose",
        "Scene 2 recap.",
    ]

    class _Prov:
        def __init__(self) -> None:
            self._call_count = 0

        async def stream_text(self, messages, model_config, seed=None):
            self._call_count += 1
            captured.append(messages[0]["content"])
            if self._call_count in {3, 6}:
                raise RuntimeError("beat sheet failed")
            yield responses.pop(0)

    with (
        patch("presentation.agents.chapter_writer.PromptLoader") as loader_cls,
        patch("presentation.agents.chapter_writer.STORIES_DIR", tmp_path),
    ):
        loader_cls.return_value.load_prompt.side_effect = _render_prompt
        agent = ChapterWriterAgent(
            _Prov(),
            {
                "models": {
                    "chapter_outline_writer": "openai-compat://test",
                    "scene_writer": "openai-compat://test",
                }
            },
            TokenStreamBus(),
            WikiContextBus(),
        )
        draft = await agent.run(
            "test-story",
            1,
            _outline_result(),
            _settings(enable_beat_sheet=True),
        )

    parsed_prompts = [json.loads(prompt) for prompt in captured]
    prose_prompts = [
        prompt
        for prompt in parsed_prompts
        if prompt["prompt_key"].startswith("multistep/scene/create_content")
    ]

    assert "scene one prose" in draft.content
    assert "scene two prose" in draft.content
    assert len(captured) == 8
    assert all(
        prompt["variables"]["beat_sheet_section"] == "" for prompt in prose_prompts
    )
