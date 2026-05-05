from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from presentation.agents.chapter_outline_expander import ChapterOutlineExpanderAgent
from presentation.pipeline_primitives import TokenStreamBus, WikiContextBus


async def _stream_tokens(tokens: list[str]):
    for token in tokens:
        yield token


class _ProviderStub:
    def __init__(self, tokens: list[str] | None = None) -> None:
        self.tokens = tokens or ["expanded ", "outline"]

    def stream_text(self, messages, model_config, seed=None):
        return _stream_tokens(self.tokens)


@pytest.mark.asyncio
async def test_run_calls_assemble_context_with_outline_scope() -> None:
    chapter_outline = "B" * 900
    agent = ChapterOutlineExpanderAgent(
        _ProviderStub(), {}, TokenStreamBus(), WikiContextBus()
    )

    with (
        patch(
            "presentation.agents.chapter_outline_expander.assemble_context",
            return_value={"wiki_snapshot": "wiki", "recap_snippets": ["recap"]},
        ) as mock_assemble_context,
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            return_value="mocked prompt",
        ),
    ):
        await agent.run(
            "test-story",
            3,
            chapter_outline,
            protagonist="Mira",
        )

    mock_assemble_context.assert_called_once_with(
        "test-story",
        scope="outline",
        focus=chapter_outline[:500],
        chapter=3,
        pov_character="Mira",
        recap_window=("character", 3),
    )


@pytest.mark.asyncio
async def test_run_passes_wiki_and_recap_to_prompt() -> None:
    agent = ChapterOutlineExpanderAgent(
        _ProviderStub(), {}, TokenStreamBus(), WikiContextBus()
    )
    captured: dict[str, str] = {}

    def capture_prompt(name: str, variables: dict | None = None) -> str:
        assert variables is not None
        captured.update(variables)
        return "mocked prompt"

    with (
        patch(
            "presentation.agents.chapter_outline_expander.assemble_context",
            return_value={
                "wiki_snapshot": "wiki snapshot",
                "recap_snippets": ["recap one", "recap two"],
            },
        ),
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=capture_prompt,
        ),
    ):
        await agent.run("test-story", 3, "chapter outline")

    assert captured["wiki_context"] == "wiki snapshot"
    assert captured["recap_context"] == "recap one\n\nrecap two"


@pytest.mark.asyncio
async def test_run_returns_expanded_text() -> None:
    agent = ChapterOutlineExpanderAgent(
        _ProviderStub(["expanded ", "outline"]),
        {},
        TokenStreamBus(),
        WikiContextBus(),
    )

    with (
        patch(
            "presentation.agents.chapter_outline_expander.assemble_context",
            return_value={"wiki_snapshot": "wiki", "recap_snippets": []},
        ),
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            return_value="mocked prompt",
        ),
    ):
        result = await agent.run("test-story", 3, "chapter outline")

    assert isinstance(result, str)
    assert result == "expanded outline"


@pytest.mark.asyncio
async def test_run_degrades_gracefully_when_assemble_context_raises() -> None:
    agent = ChapterOutlineExpanderAgent(
        _ProviderStub(["expanded outline"]),
        {},
        TokenStreamBus(),
        WikiContextBus(),
    )
    captured: dict[str, str] = {}

    def capture_prompt(name: str, variables: dict | None = None) -> str:
        assert variables is not None
        captured.update(variables)
        return "mocked prompt"

    with (
        patch(
            "presentation.agents.chapter_outline_expander.assemble_context",
            side_effect=RuntimeError("boom"),
        ),
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=capture_prompt,
        ),
    ):
        result = await agent.run("test-story", 3, "chapter outline")

    assert captured["wiki_context"] == ""
    assert captured["recap_context"] == ""
    assert isinstance(result, str)
    assert result == "expanded outline"
