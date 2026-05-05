"""Unit tests for FinalEditorAgent scrubbing flow."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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


class _SequentialProviderStub:
    def __init__(self, responses: list[str]) -> None:
        self._responses = responses
        self._index = 0

    def stream_text(self, messages, model_config, seed=None):
        response = self._responses[self._index]
        self._index += 1
        return _stream_tokens([response])


def _draft(n: int, content: str = "") -> ChapterDraft:
    return ChapterDraft(
        story_name="s",
        chapter_number=n,
        title=f"Chapter {n}",
        content=content or f"Chapter {n} body content",
        word_count=4,
    )


@pytest.mark.asyncio
async def test_scrubbing_enabled_invokes_prose_scrub_and_voice_pass() -> None:
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    agent = FinalEditorAgent(
        provider=_ProviderStub("polished"),
        config={},
        bus=bus,
        wiki_bus=wiki_bus,
    )

    with (
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            return_value="system",
        ) as mock_load_prompt,
        patch(
            "presentation.agents.final_editor.assemble_context",
            return_value={"wiki_snapshot": "", "recap_snippets": []},
        ),
    ):
        await agent.run(
            "s",
            [_draft(1)],
            GenerationSettings.from_dict({"enable_scrubbing": True}),
        )

    bus.close()

    prompt_names = [call.args[0] for call in mock_load_prompt.call_args_list]
    assert prompt_names.count("final_edit/prose_scrub") == 1
    assert prompt_names.count("final_edit/voice_consistency_pass") == 1
    assert prompt_names.count("final_edit/edit_chapter_direct") == 1


@pytest.mark.asyncio
async def test_scrubbing_enabled_passes_findings_to_edit_chapter_direct() -> None:
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    agent = FinalEditorAgent(
        provider=_SequentialProviderStub(
            [
                '{"issues":["prose finding"]}',
                '{"issues":["voice finding"]}',
                "polished",
            ]
        ),
        config={},
        bus=bus,
        wiki_bus=wiki_bus,
    )
    captured_edit_variables: dict[str, str] = {}

    def capture_prompt(name: str, variables: dict | None = None) -> str:
        if name == "final_edit/edit_chapter_direct":
            captured_edit_variables.update(variables or {})
        return "system"

    with (
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=capture_prompt,
        ),
        patch(
            "presentation.agents.final_editor.assemble_context",
            return_value={"wiki_snapshot": "", "recap_snippets": []},
        ),
    ):
        await agent.run(
            "s",
            [_draft(1)],
            GenerationSettings.from_dict({"enable_scrubbing": True}),
        )

    bus.close()

    assert captured_edit_variables["prose_findings"]
    assert captured_edit_variables["voice_findings"]


@pytest.mark.asyncio
async def test_scrubbing_disabled_skips_stage1_calls_only_edit_chapter_direct() -> None:
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    agent = FinalEditorAgent(
        provider=_ProviderStub("polished"),
        config={},
        bus=bus,
        wiki_bus=wiki_bus,
    )
    captured_edit_variables: dict[str, str] = {}

    def capture_prompt(name: str, variables: dict | None = None) -> str:
        if name == "final_edit/edit_chapter_direct":
            captured_edit_variables.update(variables or {})
        return "system"

    with (
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=capture_prompt,
        ) as mock_load_prompt,
        patch(
            "presentation.agents.final_editor.assemble_context",
            return_value={"wiki_snapshot": "", "recap_snippets": []},
        ),
    ):
        await agent.run(
            "s",
            [_draft(1)],
            GenerationSettings.from_dict({"enable_scrubbing": False}),
        )

    bus.close()

    prompt_names = [call.args[0] for call in mock_load_prompt.call_args_list]
    assert prompt_names.count("final_edit/edit_chapter_direct") == 1
    assert "final_edit/prose_scrub" not in prompt_names
    assert "final_edit/voice_consistency_pass" not in prompt_names
    assert captured_edit_variables["prose_findings"] == ""
    assert captured_edit_variables["voice_findings"] == ""


@pytest.mark.asyncio
async def test_edit_single_chapter_returns_chapter_draft() -> None:
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    provider = MagicMock()
    provider.stream_text.return_value = _stream_tokens(["Polished chapter text"])
    agent = FinalEditorAgent(
        provider=provider,
        config={},
        bus=bus,
        wiki_bus=wiki_bus,
    )

    with (
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            return_value="system",
        ),
        patch(
            "presentation.agents.final_editor.assemble_context",
            return_value={"wiki_snapshot": "", "recap_snippets": []},
        ),
    ):
        result = await agent.edit_single_chapter(
            _draft(1),
            prior_summary="prior",
            chapter_number=1,
            settings=GenerationSettings.from_dict({"enable_scrubbing": False}),
        )

    bus.close()
    wiki_bus.close()

    assert isinstance(result, ChapterDraft)
    assert result.content == "Polished chapter text"
    provider.stream_text.assert_called_once()


def test_build_prior_summaries_returns_list_of_strings() -> None:
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    agent = FinalEditorAgent(
        provider=_ProviderStub("ignored"),
        config={},
        bus=bus,
        wiki_bus=wiki_bus,
    )

    summaries = agent.build_prior_summaries([_draft(1), _draft(2)])

    assert isinstance(summaries, list)
    assert len(summaries) == 2
    assert all(isinstance(summary, str) for summary in summaries)


@pytest.mark.asyncio
async def test_run_delegates_to_edit_single_chapter() -> None:
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    agent = FinalEditorAgent(
        provider=_ProviderStub("ignored"),
        config={},
        bus=bus,
        wiki_bus=wiki_bus,
    )
    chapters = [_draft(1), _draft(2)]

    with (
        patch.object(
            agent,
            "edit_single_chapter",
            new=AsyncMock(side_effect=chapters),
        ) as edit_single,
        patch(
            "presentation.agents.final_editor.assemble_context",
            return_value={"wiki_snapshot": "", "recap_snippets": []},
        ),
    ):
        result = await agent.run(
            "s",
            chapters,
            GenerationSettings.from_dict({"enable_scrubbing": False}),
        )

    bus.close()
    wiki_bus.close()

    assert edit_single.await_count == 2
    assert result.edited_chapters == chapters


@pytest.mark.asyncio
async def test_edit_single_chapter_calls_assemble_context_with_final_edit_scope() -> (
    None
):
    """FinalEditorAgent calls assemble_context with scope='final_edit'."""
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    agent = FinalEditorAgent(
        provider=_ProviderStub("polished"),
        config={},
        bus=bus,
        wiki_bus=wiki_bus,
    )

    with (
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            return_value="system",
        ),
        patch(
            "presentation.agents.final_editor.assemble_context",
            return_value={"wiki_snapshot": "wiki data", "recap_snippets": ["recap 1"]},
        ) as mock_ctx,
    ):
        await agent.run(
            "s",
            [_draft(1)],
            GenerationSettings.from_dict({}),
        )

    bus.close()
    wiki_bus.close()

    mock_ctx.assert_called_once()
    call_kwargs = mock_ctx.call_args
    assert call_kwargs.args[0] == "s"
    assert call_kwargs.kwargs["scope"] == "final_edit"
    assert call_kwargs.kwargs["chapter"] == 1
    assert call_kwargs.kwargs["recap_window"] == ("chapter", 3)


@pytest.mark.asyncio
async def test_edit_single_chapter_passes_wiki_recap_to_edit_chapter_direct() -> None:
    """wiki_context and recap_context are passed to final_edit/edit_chapter_direct prompt."""
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    agent = FinalEditorAgent(
        provider=_ProviderStub("polished"),
        config={},
        bus=bus,
        wiki_bus=wiki_bus,
    )

    captured_edit_variables: dict[str, str] = {}

    def capture_prompt(name: str, variables: dict | None = None) -> str:
        if name == "final_edit/edit_chapter_direct":
            captured_edit_variables.update(variables or {})
        return "system"

    with (
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=capture_prompt,
        ),
        patch(
            "presentation.agents.final_editor.assemble_context",
            return_value={"wiki_snapshot": "wiki data", "recap_snippets": ["recap 1"]},
        ),
    ):
        await agent.run(
            "s",
            [_draft(1)],
            GenerationSettings.from_dict({}),
        )

    bus.close()
    wiki_bus.close()

    assert captured_edit_variables.get("wiki_context") == "wiki data"
    assert captured_edit_variables.get("recap_context") == "recap 1"
