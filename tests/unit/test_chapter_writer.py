"""Verification tests for iterative scene critique loop (#416) and cross-scene learning (#418)."""

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


# ---------------------------------------------------------------------------
# Issue #418 — cross-scene learning via recurring-finding memory
# ---------------------------------------------------------------------------


def test_generation_settings_critique_learning_defaults() -> None:
    settings = GenerationSettings()
    assert settings.enable_critique_learning is True
    assert settings.critique_learning_top_n == 3
    assert settings.to_dict()["enable_critique_learning"] is True
    assert settings.to_dict()["critique_learning_top_n"] == 3


def test_generation_settings_critique_learning_top_n_validation() -> None:
    with pytest.raises(ValidationError):
        GenerationSettings(critique_learning_top_n=0)
    with pytest.raises(ValidationError):
        GenerationSettings(critique_learning_top_n=11)


@pytest.mark.asyncio
async def test_cross_scene_lessons_injected_into_scene_3_prompt(
    tmp_path: Path,
) -> None:
    """style_violations flagged in scenes 1 and 2 appears in scene 3 lessons section."""

    def _three_scenes() -> list[dict]:
        return [
            {
                "title": f"Scene {i}",
                "description": f"Scene {i} description.",
                "characters": ["Alice"],
                "setting": "Forest",
                "key_events": [f"event {i}"],
                "ending": f"Scene {i} ends",
            }
            for i in range(1, 4)
        ]

    scenes_json = json.dumps(_three_scenes())
    # style_violations score = 25 - 8*1 = 17 (< 25) → buffer updated
    crit_with_violation = json.dumps({"style_violations": ["purple prose"]})
    # Clean critique: all scores = 25, total = 100 → passes threshold=0.0
    crit_clean = json.dumps({})

    # threshold=0.0 means every critique passes immediately (score >= 0 always)
    # so no revision loop runs, keeping exactly 3 LLM calls per scene.
    responses = [
        "Expanded synopsis.",  # chapter synopsis
        scenes_json,  # scenes JSON
        "Scene 1 prose.",  # scene 1 draft
        crit_with_violation,  # scene 1 critique (style_violations flagged)
        "Scene 1 recap.",  # scene 1 recap
        "Scene 2 prose.",  # scene 2 draft
        crit_with_violation,  # scene 2 critique (style_violations flagged)
        "Scene 2 recap.",  # scene 2 recap
        "Scene 3 prose.",  # scene 3 draft
        crit_clean,  # scene 3 critique (clean)
        "Scene 3 recap.",  # scene 3 recap
    ]

    captured_calls: list[tuple[str, dict]] = []

    def _capturing_render(prompt_key: str, *, variables: dict) -> str:
        captured_calls.append((prompt_key, dict(variables)))
        return _render_prompt(prompt_key, variables=variables)

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
    settings = _settings(
        scenes_per_chapter_min=3,
        scenes_per_chapter_max=3,
        enable_critique_learning=True,
        critique_learning_top_n=3,
        scene_critique_score_threshold=0.0,  # all critiques pass → no revisions
        scene_critique_max_iterations=1,
    )

    with (
        patch("presentation.agents.chapter_writer.PromptLoader") as loader_cls,
        patch("presentation.agents.chapter_writer.STORIES_DIR", tmp_path),
    ):
        loader = loader_cls.return_value
        loader.load_prompt.side_effect = _capturing_render
        agent = ChapterWriterAgent(provider, config, bus, wiki_bus)
        await agent.run(
            story_name="test-story",
            chapter_number=1,
            outline_result=_outline_result(),
            settings=settings,
        )

    scene_3_calls = [
        (key, vars_)
        for key, vars_ in captured_calls
        if key
        in (
            "multistep/scene/create_content_final",
            "multistep/scene/create_content_middle",
        )
        and vars_.get("scene_index") == "3"
    ]
    assert scene_3_calls, "Scene 3 create_content prompt not captured"
    _, scene_3_vars = scene_3_calls[0]
    lessons_section = scene_3_vars.get("critique_lessons_section", "")
    assert "style_violations" in lessons_section, (
        f"Expected 'style_violations' in scene 3 lessons section, got: {lessons_section!r}"
    )


@pytest.mark.asyncio
async def test_critique_learning_disabled_lessons_not_injected(
    tmp_path: Path,
) -> None:
    """When enable_critique_learning=False, scene 2 prompt has empty lessons section."""

    def _two_scenes() -> list[dict]:
        return [
            {
                "title": "Scene 1",
                "description": "s1",
                "characters": ["Alice"],
                "setting": "Forest",
                "key_events": ["e1"],
                "ending": "end1",
            },
            {
                "title": "Scene 2",
                "description": "s2",
                "characters": ["Alice"],
                "setting": "Forest",
                "key_events": ["e2"],
                "ending": "end2",
            },
        ]

    scenes_json = json.dumps(_two_scenes())
    crit_with_violation = json.dumps({"style_violations": ["purple prose"]})
    crit_clean = json.dumps({})

    responses = [
        "Expanded synopsis.",
        scenes_json,
        "Scene 1 prose.",
        crit_with_violation,
        "Scene 1 recap.",
        "Scene 2 prose.",
        crit_clean,
        "Scene 2 recap.",
    ]

    captured_calls: list[tuple[str, dict]] = []

    def _capturing_render(prompt_key: str, *, variables: dict) -> str:
        captured_calls.append((prompt_key, dict(variables)))
        return _render_prompt(prompt_key, variables=variables)

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
    settings = _settings(
        scenes_per_chapter_min=2,
        scenes_per_chapter_max=2,
        enable_critique_learning=False,
        scene_critique_score_threshold=0.0,
        scene_critique_max_iterations=1,
    )

    with (
        patch("presentation.agents.chapter_writer.PromptLoader") as loader_cls,
        patch("presentation.agents.chapter_writer.STORIES_DIR", tmp_path),
    ):
        loader = loader_cls.return_value
        loader.load_prompt.side_effect = _capturing_render
        agent = ChapterWriterAgent(provider, config, bus, wiki_bus)
        await agent.run(
            story_name="test-story",
            chapter_number=1,
            outline_result=_outline_result(),
            settings=settings,
        )

    scene_2_calls = [
        (key, vars_)
        for key, vars_ in captured_calls
        if key
        in (
            "multistep/scene/create_content_final",
            "multistep/scene/create_content_middle",
        )
        and vars_.get("scene_index") == "2"
    ]
    assert scene_2_calls, "Scene 2 create_content prompt not captured"
    _, scene_2_vars = scene_2_calls[0]
    lessons_section = scene_2_vars.get("critique_lessons_section", "")
    assert lessons_section == "", (
        f"Expected empty lessons section when learning disabled, got: {lessons_section!r}"
    )
