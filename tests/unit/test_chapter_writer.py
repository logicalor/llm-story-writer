"""Verification tests for iterative scene critique loop (#416)."""

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
from domain.exceptions import ValidationError
from domain.value_objects.generation_settings import GenerationSettings
from presentation.agents.chapter_writer import ChapterWriterAgent
from presentation.pipeline_primitives import TokenStreamBus, WikiContextBus


@pytest.fixture(autouse=True)
def stub_assemble_context(monkeypatch, tmp_path: Path):
    wiki_dir = tmp_path / "test-story" / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "presentation.agents.chapter_writer.assemble_context",
        lambda *args, **kwargs: {
            "wiki_snapshot": "## Wiki",
            "recap_snippets": [],
        },
    )


def _outline_result() -> OutlineResult:
    return OutlineResult(
        story_name="test-story",
        chapter_outlines=[
            {"chapter_number": 1, "title": "Ch 1", "summary": "Chapter 1 summary"},
        ],
        summary="Story summary",
        genre="fantasy",
        themes=["courage"],
    )


def _settings(**overrides: object) -> GenerationSettings:
    base = {
        "wanted_chapters": 1,
        "seed": 42,
        "scene_generation_pipeline": True,
        "scenes_per_chapter_min": 1,
        "scenes_per_chapter_max": 2,
        "enable_scene_critique": True,
        "enable_scene_critique_loop": True,
        "scene_critique_score_threshold": 80.0,
        "scene_critique_max_iterations": 3,
        "enable_scrubbing": False,
        "enable_decomposition_critique": False,
        "enable_beat_sheet": False,
        "enable_living_scene_plan": False,
        "enable_outline_critique": False,
        "enable_author_persona": False,
        "expand_outline": False,
    }
    base.update(overrides)
    return GenerationSettings(**base)


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


def _one_scene() -> list[dict[str, object]]:
    return [
        {
            "title": "Scene A",
            "description": "First scene.",
            "characters": ["Alice"],
            "setting": "Forest",
            "key_events": ["Alice arrives"],
            "ending": "Alice rests",
        }
    ]


def _render_prompt(prompt_key: str, *, variables: dict[str, object]) -> str:
    return (
        f"PROMPT::{prompt_key}\n"
        f"{json.dumps(variables, sort_keys=True, ensure_ascii=False)}"
    )


async def _run_agent(
    tmp_path: Path,
    responses: list[str],
    settings: GenerationSettings,
) -> object:
    provider = _make_provider(responses)
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
        return await agent.run(
            story_name="test-story",
            chapter_number=1,
            outline_result=_outline_result(),
            settings=settings,
        )


@pytest.mark.asyncio
async def test_scene_critique_loop_exits_when_score_reaches_threshold(
    tmp_path: Path,
) -> None:
    scenes_json = json.dumps(_one_scene())
    crit_60 = json.dumps(
        {
            "outline_adherence": ["missing beat A", "missing beat B"],
            "pov_consistency": ["POV shift at para 3"],
            "continuity": ["break at opening"],
            "style_violations": ["purple prose"],
        }
    )
    crit_76 = json.dumps(
        {
            "outline_adherence": ["missing beat A"],
            "pov_consistency": ["POV shift"],
            "continuity": ["minor break"],
        }
    )
    crit_84 = json.dumps(
        {
            "outline_adherence": ["minor issue"],
            "pov_consistency": ["slight drift"],
        }
    )

    draft = await _run_agent(
        tmp_path,
        [
            "Expanded synopsis.",
            scenes_json,
            "Scene prose draft.",
            crit_60,
            "Revised scene v1.",
            crit_76,
            "Revised scene v2.",
            crit_84,
            "Scene ending recap.",
        ],
        _settings(),
    )

    assert "Revised scene v2." in draft.content
    assert (
        tmp_path
        / "test-story"
        / "chapters"
        / "chapter_1"
        / "scene_1_critique_iter_1.txt"
    ).exists()
    assert (
        tmp_path
        / "test-story"
        / "chapters"
        / "chapter_1"
        / "scene_1_critique_iter_2.md"
    ).exists()


@pytest.mark.asyncio
async def test_scene_critique_loop_disabled_runs_no_revision(tmp_path: Path) -> None:
    scenes_json = json.dumps(_one_scene())
    crit_below = json.dumps({"outline_adherence": ["missing beat A", "missing beat B"]})

    draft = await _run_agent(
        tmp_path,
        [
            "Expanded synopsis.",
            scenes_json,
            "Scene prose draft.",
            crit_below,
            "Scene ending recap.",
        ],
        _settings(enable_scene_critique_loop=False),
    )

    assert "Scene prose draft." in draft.content
    assert "Revised scene" not in draft.content


@pytest.mark.asyncio
async def test_scene_critique_loop_exits_immediately_when_score_passes(
    tmp_path: Path,
) -> None:
    scenes_json = json.dumps(_one_scene())

    draft = await _run_agent(
        tmp_path,
        [
            "Expanded synopsis.",
            scenes_json,
            "Scene prose draft.",
            json.dumps({}),
            "Scene ending recap.",
        ],
        _settings(),
    )

    assert "Scene prose draft." in draft.content
    assert not (
        tmp_path
        / "test-story"
        / "chapters"
        / "chapter_1"
        / "scene_1_critique_iter_1.txt"
    ).exists()


def test_generation_settings_scene_critique_loop_defaults() -> None:
    settings = GenerationSettings()

    assert settings.enable_scene_critique_loop is True
    assert settings.scene_critique_score_threshold == 80.0
    assert settings.scene_critique_max_iterations == 3
    assert settings.to_dict()["scene_critique_score_threshold"] == 80.0


def test_generation_settings_critique_threshold_validation() -> None:
    with pytest.raises(ValidationError):
        GenerationSettings(scene_critique_score_threshold=101.0)

    with pytest.raises(ValidationError):
        GenerationSettings(scene_critique_score_threshold=-1.0)


def test_generation_settings_critique_max_iterations_validation() -> None:
    with pytest.raises(ValidationError):
        GenerationSettings(scene_critique_max_iterations=0)

    with pytest.raises(ValidationError):
        GenerationSettings(scene_critique_max_iterations=11)
