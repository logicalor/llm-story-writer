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
from application.interfaces.model_provider import StreamToken


def _make_provider(responses: list[str]) -> tuple[object, list[str]]:
    captured: list[str] = []

    class _Prov:
        async def stream_text(self, messages, model_config, seed=None):
            captured.append(messages[0]["content"])
            yield StreamToken(text=responses.pop(0), kind="content")

    return _Prov(), captured


def _settings(**kwargs: object) -> GenerationSettings:
    base = {
        "wanted_chapters": 1,
        "seed": 1,
        "scene_generation_pipeline": True,
        "scenes_per_chapter_min": 3,
        "scenes_per_chapter_max": 3,
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


def _three_scenes() -> list[dict[str, object]]:
    return [
        {
            "title": "S1",
            "description": "d1",
            "summary": "summary1",
            "key_events": ["e1"],
            "ending": "end1",
            "literary_devices": [],
            "characters": [],
            "setting": "loc1",
        },
        {
            "title": "S2",
            "description": "d2",
            "summary": "summary2",
            "key_events": ["e2"],
            "ending": "end2",
            "literary_devices": [],
            "characters": [],
            "setting": "loc2",
        },
        {
            "title": "S3",
            "description": "d3",
            "summary": "summary3",
            "key_events": ["e3"],
            "ending": "end3",
            "literary_devices": [],
            "characters": [],
            "setting": "loc3",
        },
    ]


def _two_scenes() -> list[dict[str, object]]:
    return _three_scenes()[:2]


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
async def test_living_plan_disabled_default(tmp_path: Path) -> None:
    original_scenes = _three_scenes()
    provider, captured = _make_provider(
        [
            "synopsis text",
            json.dumps(original_scenes),
            "scene one prose",
            "Scene 1 recap.",
            "scene two prose",
            "Scene 2 recap.",
            "scene three prose",
            "Scene 3 recap.",
        ]
    )
    scenes_json_path = tmp_path / "test-story" / "chapters" / "chapter_1_scenes.json"

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
    persisted_scenes = json.loads(scenes_json_path.read_text(encoding="utf-8"))

    assert "scene one prose" in draft.content
    assert "scene two prose" in draft.content
    assert "scene three prose" in draft.content
    assert len(captured) == 8
    assert all(
        prompt["prompt_key"] != "multistep/scene/update_remaining_scenes"
        for prompt in parsed_prompts
    )
    assert persisted_scenes == original_scenes


@pytest.mark.asyncio
async def test_living_plan_enabled_updates_remaining(tmp_path: Path) -> None:
    original_scenes = _three_scenes()
    updated_after_scene_1 = [
        {
            "title": "S2",
            "description": "d2 revised after scene 1",
            "summary": "summary2 revised after scene 1",
            "key_events": ["e2 revised"],
            "ending": "end2 revised after scene 1",
            "literary_devices": [],
            "characters": [],
            "setting": "loc2",
        },
        {
            "title": "S3",
            "description": "d3 revised after scene 1",
            "summary": "summary3 revised after scene 1",
            "key_events": ["e3 revised after scene 1"],
            "ending": "end3 revised after scene 1",
            "literary_devices": [],
            "characters": [],
            "setting": "loc3",
        },
    ]
    updated_after_scene_2 = [
        {
            "title": "S3",
            "description": "d3 revised after scene 2",
            "summary": "summary3 revised after scene 2",
            "key_events": ["e3 revised after scene 2"],
            "ending": "end3 revised after scene 2",
            "literary_devices": [],
            "characters": [],
            "setting": "loc3",
        }
    ]
    provider, captured = _make_provider(
        [
            "synopsis text",
            json.dumps(original_scenes),
            "scene one prose",
            "Scene 1 recap.",
            json.dumps(updated_after_scene_1),
            "scene two prose",
            "Scene 2 recap.",
            json.dumps(updated_after_scene_2),
            "scene three prose",
            "Scene 3 recap.",
        ]
    )
    scenes_json_path = tmp_path / "test-story" / "chapters" / "chapter_1_scenes.json"

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
            _settings(enable_living_scene_plan=True),
        )

    parsed_prompts = [json.loads(prompt) for prompt in captured]
    prompt_keys = [prompt["prompt_key"] for prompt in parsed_prompts]
    persisted_scenes = json.loads(scenes_json_path.read_text(encoding="utf-8"))

    assert "scene one prose" in draft.content
    assert "scene two prose" in draft.content
    assert "scene three prose" in draft.content
    assert len(captured) == 10
    assert prompt_keys == [
        "chapters/create_synopsis",
        "chapters/expand_to_scenes",
        "multistep/scene/create_content_first",
        "scenes/summarise_for_continuity",
        "multistep/scene/update_remaining_scenes",
        "multistep/scene/create_content_middle",
        "scenes/summarise_for_continuity",
        "multistep/scene/update_remaining_scenes",
        "multistep/scene/create_content_final",
        "scenes/summarise_for_continuity",
    ]
    assert persisted_scenes[0] == original_scenes[0]
    assert persisted_scenes[1] == updated_after_scene_1[0]
    assert persisted_scenes[2] == updated_after_scene_2[0]


@pytest.mark.asyncio
async def test_living_plan_bad_json_does_not_abort(tmp_path: Path) -> None:
    original_scenes = _two_scenes()
    provider, captured = _make_provider(
        [
            "synopsis text",
            json.dumps(original_scenes),
            "scene one prose",
            "Scene 1 recap.",
            "not json at all",
            "scene two prose",
            "Scene 2 recap.",
        ]
    )
    scenes_json_path = tmp_path / "test-story" / "chapters" / "chapter_1_scenes.json"

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
            _settings(
                enable_living_scene_plan=True,
                scenes_per_chapter_min=2,
                scenes_per_chapter_max=2,
            ),
        )

    parsed_prompts = [json.loads(prompt) for prompt in captured]
    persisted_scenes = json.loads(scenes_json_path.read_text(encoding="utf-8"))

    assert "scene one prose" in draft.content
    assert "scene two prose" in draft.content
    assert len(captured) == 7
    assert (
        sum(
            1
            for prompt in parsed_prompts
            if prompt["prompt_key"] == "multistep/scene/update_remaining_scenes"
        )
        == 1
    )
    assert persisted_scenes == original_scenes
