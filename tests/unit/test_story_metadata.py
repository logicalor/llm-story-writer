from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from domain.value_objects.generation_settings import GenerationSettings
from presentation.agents.story_metadata import StoryMetadataAgent, _parse_tags


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


class _ProviderStub:
    def __init__(self, side_effect: object) -> None:
        self.generate_text = AsyncMock(side_effect=side_effect)


@pytest.mark.asyncio
async def test_run_phase1_no_chapter_content() -> None:
    provider = _ProviderStub(
        ["My Title", "A great summary.", '["fantasy", "adventure"]']
    )
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = StoryMetadataAgent(provider, {}, bus, wiki_bus)

    with (
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=lambda name, variables=None: f"prompt::{name}",
        ),
        patch(
            "presentation.agents.story_metadata.assemble_context",
            return_value={"wiki_snapshot": "", "recap_snippets": []},
        ),
    ):
        result = await agent.run(
            "my-story",
            "outline text",
            "",
            GenerationSettings.from_dict({}),
        )

    assert result.title == "My Title"
    assert result.summary == "A great summary."
    assert result.tags == ["fantasy", "adventure"]
    assert result.story_name == "my-story"
    assert provider.generate_text.call_count == 3


@pytest.mark.asyncio
async def test_run_phase2_with_chapter_content() -> None:
    provider = _ProviderStub(
        ["Better Title", "Better summary.", '["sci-fi", "thriller"]']
    )
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = StoryMetadataAgent(provider, {}, bus, wiki_bus)

    with (
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=lambda name, variables=None: f"prompt::{name}",
        ),
        patch(
            "presentation.agents.story_metadata.assemble_context",
            return_value={"wiki_snapshot": "", "recap_snippets": []},
        ),
    ):
        result = await agent.run(
            "my-story",
            "outline text",
            "Chapter 1 prose here...",
            GenerationSettings.from_dict({}),
        )

    assert result.title == "Better Title"
    assert result.summary == "Better summary."
    assert result.tags == ["sci-fi", "thriller"]
    assert provider.generate_text.call_count == 3


@pytest.mark.asyncio
async def test_run_graceful_degradation_title_fails() -> None:
    provider = _ProviderStub([Exception("boom"), "Good summary.", '["tag1"]'])
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = StoryMetadataAgent(provider, {}, bus, wiki_bus)

    with (
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=lambda name, variables=None: f"prompt::{name}",
        ),
        patch(
            "presentation.agents.story_metadata.assemble_context",
            return_value={"wiki_snapshot": "", "recap_snippets": []},
        ),
    ):
        result = await agent.run(
            "my-story",
            "outline text",
            "",
            GenerationSettings.from_dict({}),
        )

    assert result.title == ""
    assert result.summary == "Good summary."
    assert result.tags == ["tag1"]


@pytest.mark.asyncio
async def test_run_graceful_degradation_all_fail() -> None:
    provider = _ProviderStub(Exception("boom"))
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = StoryMetadataAgent(provider, {}, bus, wiki_bus)

    with (
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=lambda name, variables=None: f"prompt::{name}",
        ),
        patch(
            "presentation.agents.story_metadata.assemble_context",
            return_value={"wiki_snapshot": "", "recap_snippets": []},
        ),
    ):
        result = await agent.run(
            "my-story",
            "outline text",
            "",
            GenerationSettings.from_dict({}),
        )

    assert result.title == ""
    assert result.summary == ""
    assert result.tags == []


def test_parse_tags_plain_json() -> None:
    assert _parse_tags('["a", "b", "c"]') == ["a", "b", "c"]


def test_parse_tags_with_code_fence() -> None:
    assert _parse_tags('```json\n["x", "y"]\n```') == ["x", "y"]


def test_parse_tags_invalid_returns_empty() -> None:
    assert _parse_tags("not json at all") == []


@pytest.mark.asyncio
async def test_run_emits_phase_messages() -> None:
    provider = _ProviderStub(["T", "S", '["t"]'])
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = StoryMetadataAgent(provider, {}, bus, wiki_bus)

    with (
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=lambda name, variables=None: f"prompt::{name}",
        ),
        patch(
            "presentation.agents.story_metadata.assemble_context",
            return_value={"wiki_snapshot": "", "recap_snippets": []},
        ),
    ):
        await agent.run(
            "my-story",
            "outline text",
            "",
            GenerationSettings.from_dict({}),
        )

    assert any("[Metadata]" in message for message in bus.messages)


@pytest.mark.asyncio
async def test_run_calls_assemble_context_with_metadata_scope() -> None:
    """StoryMetadataAgent.run() calls assemble_context with scope='metadata'."""
    provider = _ProviderStub(["T", "S", '["t"]'])
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = StoryMetadataAgent(provider, {}, bus, wiki_bus)

    with (
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=lambda name, variables=None: f"prompt::{name}",
        ),
        patch(
            "presentation.agents.story_metadata.assemble_context",
            return_value={"wiki_snapshot": "wiki data", "recap_snippets": ["recap 1"]},
        ) as mock_ctx,
    ):
        await agent.run(
            "my-story",
            "outline text",
            "",
            GenerationSettings.from_dict({}),
        )

    mock_ctx.assert_called_once()
    call_kwargs = mock_ctx.call_args
    assert call_kwargs.args[0] == "my-story"
    assert call_kwargs.kwargs["scope"] == "metadata"
    assert call_kwargs.kwargs["recap_window"] == ("chapter", 20)


@pytest.mark.asyncio
async def test_run_passes_wiki_and_recap_context_to_prompts() -> None:
    """wiki_context and recap_context from assemble_context are passed to load_prompt."""
    provider = _ProviderStub(["T", "S", '["t"]'])
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = StoryMetadataAgent(provider, {}, bus, wiki_bus)

    captured_variables: list[dict] = []

    def capture_prompt(name: str, variables: dict | None = None) -> str:
        if variables:
            captured_variables.append(dict(variables))
        return f"prompt::{name}"

    with (
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=capture_prompt,
        ),
        patch(
            "presentation.agents.story_metadata.assemble_context",
            return_value={"wiki_snapshot": "wiki data", "recap_snippets": ["recap 1"]},
        ),
    ):
        await agent.run(
            "my-story",
            "outline text",
            "",
            GenerationSettings.from_dict({}),
        )

    assert all("wiki_context" in v for v in captured_variables)
    assert all("recap_context" in v for v in captured_variables)
    assert all(v["wiki_context"] == "wiki data" for v in captured_variables)
