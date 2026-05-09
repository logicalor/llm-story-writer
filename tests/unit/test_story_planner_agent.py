from __future__ import annotations

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
from presentation.agents.story_planner import StoryPlannerAgent
from application.interfaces.model_provider import StreamToken


async def _async_gen(tokens: list[str]):
    for token in tokens:
        yield StreamToken(text=token, kind="content")


class _StubBus:
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def emit(self, msg: str) -> None:
        self.messages.append(msg)

    def close(self) -> None:
        pass


class _StubWikiBus:
    def __init__(self) -> None:
        self.events: list[object] = []

    async def emit(self, event: object) -> None:
        self.events.append(event)

    def close(self) -> None:
        pass


def _outline_result() -> OutlineResult:
    return OutlineResult(
        story_name="test-story",
        chapter_outlines=[
            {"chapter_number": 1, "title": "Chapter 1", "summary": "Intro"}
        ],
        summary="Story summary",
        genre="science fiction",
        themes=["memory"],
    )


def _state(**updates: object) -> PipelineState:
    return PipelineState(
        story_name="test-story",
        current_phase="narrative-arc",
        outline_result=_outline_result(),
        **updates,
    )


def _make_agent(provider: MagicMock) -> StoryPlannerAgent:
    return StoryPlannerAgent(provider, {}, _StubBus(), _StubWikiBus())


@pytest.mark.asyncio
async def test_story_planner_consumes_critic_fields_from_state() -> None:
    provider = MagicMock()
    provider.stream_text = MagicMock(
        return_value=_async_gen(["Strong arc assessment."])
    )
    agent = _make_agent(provider)
    captured_variables: dict[str, str] = {}

    def _capture_prompt(name: str, variables: dict[str, str] | None = None) -> str:
        captured_variables.update(variables or {})
        return f"prompt::{name}"

    with patch(
        "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
        side_effect=_capture_prompt,
    ):
        result = await agent.run(
            _state(
                critic_summary="critic synthesis",
                arc_distribution="arc distribution",
                promise_payoff="promise payoff",
            ),
            GenerationSettings(),
        )

    assert captured_variables["critic_summary"] == "critic synthesis"
    assert captured_variables["arc_distribution"] == "arc distribution"
    assert captured_variables["promise_payoff"] == "promise payoff"
    assert result.story_name == "test-story"


@pytest.mark.asyncio
async def test_story_planner_handles_empty_critic_fields() -> None:
    provider = MagicMock()
    provider.stream_text = MagicMock(
        return_value=_async_gen(["Strong arc assessment."])
    )
    agent = _make_agent(provider)

    with patch(
        "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
        side_effect=lambda name, variables=None: f"prompt::{name}",
    ):
        result = await agent.run(_state(), GenerationSettings())

    assert result.story_name == "test-story"
    assert result.arc_assessment == "Strong arc assessment."
