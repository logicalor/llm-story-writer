from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from domain.value_objects.generation_settings import GenerationSettings
from presentation.agents.outline_planner import OutlinePlannerAgent
from application.interfaces.model_provider import StreamToken


async def _async_gen(tokens: list[str]):
    for token in tokens:
        yield StreamToken(text=token, kind="content")


class _StubBus:
    async def emit(self, msg):
        pass

    def close(self):
        pass


class _StubWikiBus:
    async def emit(self, event):
        pass

    def close(self):
        pass


def _make_agent() -> OutlinePlannerAgent:
    provider = MagicMock()
    provider.stream_text = MagicMock(
        return_value=_async_gen(["### Chapter 1: Title\nSummary text\n"])
    )
    return OutlinePlannerAgent(provider, {}, _StubBus(), _StubWikiBus())


def _settings() -> GenerationSettings:
    return GenerationSettings.from_dict({"expand_outline": False, "wanted_chapters": 5})


@pytest.mark.asyncio
async def test_run_calls_assemble_context_on_feedback_run() -> None:
    agent = _make_agent()

    with (
        patch(
            "presentation.agents.outline_planner.assemble_context",
            return_value={"wiki_snapshot": "wiki", "recap_snippets": []},
        ) as mock_assemble_context,
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            return_value="system prompt",
        ),
    ):
        await agent.run(
            "my-story",
            "story prompt",
            _settings(),
            feedback="please revise",
        )

    mock_assemble_context.assert_called_once_with(
        "my-story",
        scope="outline",
        focus="story prompt",
        recap_window=("chapter", 10),
    )


@pytest.mark.asyncio
async def test_run_calls_assemble_context_on_continuation() -> None:
    agent = _make_agent()

    with (
        patch(
            "presentation.agents.outline_planner._has_approved_chapters",
            return_value=True,
        ),
        patch(
            "presentation.agents.outline_planner.assemble_context",
            return_value={"wiki_snapshot": "wiki", "recap_snippets": []},
        ) as mock_assemble_context,
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            return_value="system prompt",
        ),
    ):
        await agent.run("my-story", "story prompt", _settings(), feedback=None)

    mock_assemble_context.assert_called_once_with(
        "my-story",
        scope="outline",
        focus="story prompt",
        recap_window=("chapter", 10),
    )


@pytest.mark.asyncio
async def test_run_skips_assemble_context_on_initial_run() -> None:
    agent = _make_agent()

    with (
        patch(
            "presentation.agents.outline_planner._has_approved_chapters",
            return_value=False,
        ),
        patch(
            "presentation.agents.outline_planner.assemble_context",
        ) as mock_assemble_context,
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            return_value="system prompt",
        ),
    ):
        await agent.run("my-story", "story prompt", _settings(), feedback=None)

    mock_assemble_context.assert_not_called()
