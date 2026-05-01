"""Unit tests for FinalEditorAgent prior-summary scoping."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from application.pipeline.handoffs import ChapterDraft
from domain.value_objects.generation_settings import GenerationSettings
from presentation.agents.final_editor import FinalEditorAgent
from presentation.pipeline_primitives import TokenStreamBus, WikiContextBus


async def _stream_tokens(tokens: list[str]):
    for token in tokens:
        yield token


class _ProviderStub:
    def __init__(self, response: str) -> None:
        self.response = response

    def stream_text(self, messages, model_config, seed=None):
        return _stream_tokens([self.response])


def _draft(n: int, content: str = "") -> ChapterDraft:
    return ChapterDraft(
        story_name="s",
        chapter_number=n,
        title=f"Chapter {n}",
        content=content or f"Chapter {n} body content",
        word_count=4,
    )


@pytest.mark.asyncio
async def test_prior_chapters_summary_excludes_future_chapters() -> None:
    """Chapter N must only see chapters 1..N-1 in prior_chapters_summary."""
    captured: list[dict] = []

    def capture_prompt(name: str, variables: dict | None = None) -> str:
        captured.append(dict(variables or {}))
        return "system"

    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    agent = FinalEditorAgent(
        provider=_ProviderStub("polished"),
        config={},
        bus=bus,
        wiki_bus=wiki_bus,
    )
    drafts = [_draft(1), _draft(2), _draft(3)]

    with patch(
        "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
        side_effect=capture_prompt,
    ):
        await agent.run("s", drafts, GenerationSettings.from_dict({}))

    bus.close()

    # Chapter 1: no prior summaries.
    assert captured[0]["prior_chapters_summary"] == ""
    # Chapter 2: only chapter 1.
    assert "Chapter 1:" in captured[1]["prior_chapters_summary"]
    assert "Chapter 3:" not in captured[1]["prior_chapters_summary"]
    # Chapter 3: chapters 1 and 2 only.
    assert "Chapter 1:" in captured[2]["prior_chapters_summary"]
    assert "Chapter 2:" in captured[2]["prior_chapters_summary"]
    assert "Chapter 3:" not in captured[2]["prior_chapters_summary"]
