from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from application.pipeline.handoffs import ChapterDraft, OutlineResult, PipelineState
from domain.value_objects.generation_settings import GenerationSettings
from presentation.agents.story_planner import StoryPlannerAgent
from presentation.pipeline_primitives import TokenStreamBus, WikiContextBus
from application.interfaces.model_provider import StreamToken


async def _stream_tokens(tokens: list[str]):
    for token in tokens:
        yield StreamToken(text=token, kind="content")


class _ProviderStub:
    def __init__(self, tokens: list[str] | None = None) -> None:
        self.tokens = tokens or ["arc ", "assessment"]

    def stream_text(self, messages, model_config, seed=None):
        return _stream_tokens(self.tokens)


def _make_state(*, approved_chapters: list[ChapterDraft]) -> PipelineState:
    return PipelineState(
        story_name="test-story",
        current_phase="arc",
        outline_result=OutlineResult(
            story_name="test-story",
            chapter_outlines=[{"chapter_number": 1, "title": "Ch 1", "summary": "..."}],
            summary="outline text",
            genre="fiction",
            themes=[],
            base_context="",
            story_elements="",
        ),
        approved_chapters=approved_chapters,
        critic_summary="critic summary",
        arc_distribution="arc distribution",
        promise_payoff="promise payoff",
    )


def _approved_chapter() -> ChapterDraft:
    return ChapterDraft(
        story_name="test-story",
        chapter_number=1,
        title="Chapter 1",
        content="approved content",
        word_count=1000,
    )


def _outline_text(state: PipelineState) -> str:
    outline = state.outline_result
    assert outline is not None
    text = outline.summary if isinstance(outline.summary, str) else ""
    if outline.chapter_outlines:
        text += "\n\n" + json.dumps(
            outline.chapter_outlines, ensure_ascii=False, indent=2
        )
    return text


@pytest.mark.asyncio
async def test_run_calls_assemble_context_on_continuation_run() -> None:
    state = _make_state(approved_chapters=[_approved_chapter()])
    agent = StoryPlannerAgent(_ProviderStub(), {}, TokenStreamBus(), WikiContextBus())

    with (
        patch(
            "presentation.agents.story_planner.assemble_context",
            return_value={"wiki_snapshot": "wiki", "recap_snippets": ["recap"]},
        ) as mock_assemble_context,
        patch(
            "presentation.agents.story_planner.render_recap_as_markdown",
            return_value="recap",
        ),
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            return_value="mocked prompt",
        ),
    ):
        await agent.run(state, GenerationSettings())

    mock_assemble_context.assert_called_once_with(
        state.story_name,
        scope="outline",
        focus=_outline_text(state)[:800],
        recap_window=("chapter", 5),
    )


@pytest.mark.asyncio
async def test_run_skips_assemble_context_on_initial_run() -> None:
    state = _make_state(approved_chapters=[])
    agent = StoryPlannerAgent(_ProviderStub(), {}, TokenStreamBus(), WikiContextBus())
    captured: dict[str, str] = {}

    def capture_prompt(name: str, variables: dict | None = None) -> str:
        assert variables is not None
        captured.update(variables)
        return "mocked prompt"

    with (
        patch(
            "presentation.agents.story_planner.assemble_context"
        ) as mock_assemble_context,
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=capture_prompt,
        ),
    ):
        await agent.run(state, GenerationSettings())

    mock_assemble_context.assert_not_called()
    assert captured["wiki_context"] == ""
    assert captured["recap_context"] == ""


@pytest.mark.asyncio
async def test_run_passes_wiki_and_recap_to_prompt_on_continuation() -> None:
    state = _make_state(approved_chapters=[_approved_chapter()])
    agent = StoryPlannerAgent(_ProviderStub(), {}, TokenStreamBus(), WikiContextBus())
    captured: dict[str, str] = {}

    def capture_prompt(name: str, variables: dict | None = None) -> str:
        assert variables is not None
        captured.update(variables)
        return "mocked prompt"

    with (
        patch(
            "presentation.agents.story_planner.assemble_context",
            return_value={
                "wiki_snapshot": "wiki snapshot",
                "recap_snippets": ["recap one", "recap two"],
            },
        ),
        patch(
            "presentation.agents.story_planner.render_recap_as_markdown",
            return_value="recap one\n\nrecap two",
        ),
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=capture_prompt,
        ),
    ):
        await agent.run(state, GenerationSettings())

    assert captured["wiki_context"] == "wiki snapshot"
    assert captured["recap_context"] == "recap one\n\nrecap two"


@pytest.mark.asyncio
async def test_run_degrades_gracefully_when_assemble_context_raises() -> None:
    state = _make_state(approved_chapters=[_approved_chapter()])
    agent = StoryPlannerAgent(
        _ProviderStub(["strong verdict"]), {}, TokenStreamBus(), WikiContextBus()
    )
    captured: dict[str, str] = {}

    def capture_prompt(name: str, variables: dict | None = None) -> str:
        assert variables is not None
        captured.update(variables)
        return "mocked prompt"

    with (
        patch(
            "presentation.agents.story_planner.assemble_context",
            side_effect=RuntimeError("boom"),
        ),
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=capture_prompt,
        ),
    ):
        result = await agent.run(state, GenerationSettings())

    assert captured["wiki_context"] == ""
    assert captured["recap_context"] == ""
    assert result.story_name == state.story_name
    assert result.arc_assessment == "strong verdict"
