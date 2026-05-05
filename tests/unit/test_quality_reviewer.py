from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from presentation.agents.quality_reviewer import QualityReviewerAgent
from presentation.pipeline_primitives import TokenStreamBus, WikiContextBus


async def _stream_tokens(tokens: list[str]):
    for token in tokens:
        yield token


class _ProviderStub:
    def __init__(self, tokens: list[str] | None = None) -> None:
        self.tokens = tokens or ["critique"]

    def stream_text(self, messages, model_config, seed=None):
        return _stream_tokens(self.tokens)


@pytest.mark.asyncio
async def test_run_calls_assemble_context_with_consistency_scope() -> None:
    chapter_content = "A" * 800
    agent = QualityReviewerAgent(
        _ProviderStub(), {}, TokenStreamBus(), WikiContextBus()
    )

    with (
        patch(
            "presentation.agents.quality_reviewer.assemble_context",
            return_value={"wiki_snapshot": "wiki", "recap_snippets": ["recap"]},
        ) as mock_assemble_context,
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            return_value="mocked prompt",
        ),
    ):
        await agent.run("test-story", 7, chapter_content)

    mock_assemble_context.assert_called_once_with(
        "test-story",
        scope="consistency",
        focus=chapter_content[:500],
        chapter=7,
        recap_window=("chapter", 3),
    )


@pytest.mark.asyncio
async def test_run_passes_wiki_and_recap_to_prompts() -> None:
    agent = QualityReviewerAgent(
        _ProviderStub(), {}, TokenStreamBus(), WikiContextBus()
    )
    captured_variables: list[dict[str, str]] = []

    def capture_prompt(name: str, variables: dict | None = None) -> str:
        assert variables is not None
        captured_variables.append(dict(variables))
        return "mocked prompt"

    with (
        patch(
            "presentation.agents.quality_reviewer.assemble_context",
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
        await agent.run("test-story", 2, "chapter content")

    assert len(captured_variables) == 4
    assert all(item["wiki_context"] == "wiki snapshot" for item in captured_variables)
    assert all(
        item["recap_context"] == "recap one\n\nrecap two" for item in captured_variables
    )


@pytest.mark.asyncio
async def test_run_returns_list_of_critiques() -> None:
    agent = QualityReviewerAgent(
        _ProviderStub(["review text"]), {}, TokenStreamBus(), WikiContextBus()
    )

    with (
        patch(
            "presentation.agents.quality_reviewer.assemble_context",
            return_value={"wiki_snapshot": "wiki", "recap_snippets": []},
        ),
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            return_value="mocked prompt",
        ),
    ):
        result = await agent.run("test-story", 2, "chapter content")

    assert len(result) == 4
    assert all("critique_type" in item for item in result)
    assert all("text" in item for item in result)


@pytest.mark.asyncio
async def test_run_degrades_gracefully_when_assemble_context_raises() -> None:
    agent = QualityReviewerAgent(
        _ProviderStub(["review text"]), {}, TokenStreamBus(), WikiContextBus()
    )
    captured_variables: list[dict[str, str]] = []

    def capture_prompt(name: str, variables: dict | None = None) -> str:
        assert variables is not None
        captured_variables.append(dict(variables))
        return "mocked prompt"

    with (
        patch(
            "presentation.agents.quality_reviewer.assemble_context",
            side_effect=RuntimeError("boom"),
        ),
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=capture_prompt,
        ),
    ):
        result = await agent.run("test-story", 2, "chapter content")

    assert len(result) == 4
    assert all(item["wiki_context"] == "" for item in captured_variables)
    assert all(item["recap_context"] == "" for item in captured_variables)
