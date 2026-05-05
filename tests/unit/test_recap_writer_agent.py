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
from presentation.agents.recap_writer import RecapWriterAgent


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
async def test_run_full_path_returns_events_compact_sanitised() -> None:
    provider = _ProviderStub(
        [
            "events text",
            "timed events",
            "enriched events",
            '{"events": ["formatted"]}',
            "compact recap",
            "sanitised recap",
        ]
    )
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = RecapWriterAgent(provider, {}, bus, wiki_bus)

    with patch(
        "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
        side_effect=lambda name, variables=None: f"prompt::{name}",
    ):
        result = await agent.run(
            "my-story",
            3,
            "chapter body",
            "previous recap",
            "2024-01-15",
            GenerationSettings.from_dict({}),
        )

    assert result == {
        "events": "events text",
        "compact": "compact recap",
        "sanitised": "sanitised recap",
    }
    assert provider.generate_text.call_count == 6


@pytest.mark.asyncio
async def test_run_short_path_two_calls() -> None:
    provider = _ProviderStub(["events text", '{"events": ["formatted"]}'])
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = RecapWriterAgent(provider, {}, bus, wiki_bus)

    with patch(
        "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
        side_effect=lambda name, variables=None: f"prompt::{name}",
    ):
        result = await agent.run(
            "my-story",
            3,
            "chapter body",
            "previous recap",
            "2024-01-15",
            GenerationSettings.from_dict(
                {
                    "use_multi_stage_recap_sanitizer": False,
                }
            ),
        )

    assert provider.generate_text.call_count == 2
    assert result["events"] == "events text"
    assert result["compact"] == '{"events": ["formatted"]}'
    assert result["sanitised"] == result["compact"]


@pytest.mark.asyncio
async def test_run_skip_sanitizer_five_calls() -> None:
    provider = _ProviderStub(
        [
            "events text",
            "timed events",
            "enriched events",
            '{"events": ["formatted"]}',
            "compact recap",
        ]
    )
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = RecapWriterAgent(provider, {}, bus, wiki_bus)

    with patch(
        "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
        side_effect=lambda name, variables=None: f"prompt::{name}",
    ):
        result = await agent.run(
            "my-story",
            3,
            "chapter body",
            "previous recap",
            "2024-01-15",
            GenerationSettings.from_dict(
                {
                    "use_improved_recap_sanitizer": False,
                }
            ),
        )

    assert provider.generate_text.call_count == 5
    assert result["events"] == "events text"
    assert result["compact"] == "compact recap"
    assert result["sanitised"] == result["compact"]


@pytest.mark.asyncio
async def test_run_stage1_failure_returns_empty_dict() -> None:
    provider = _ProviderStub(Exception("boom"))
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = RecapWriterAgent(provider, {}, bus, wiki_bus)

    with patch(
        "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
        side_effect=lambda name, variables=None: f"prompt::{name}",
    ):
        result = await agent.run(
            "my-story",
            3,
            "chapter body",
            "previous recap",
            "2024-01-15",
            GenerationSettings.from_dict({}),
        )

    assert result == {
        "events": "",
        "compact": "",
        "sanitised": "",
    }


@pytest.mark.asyncio
async def test_run_emits_stage_messages_to_bus() -> None:
    provider = _ProviderStub(
        [
            "events text",
            "timed events",
            "enriched events",
            '{"events": ["formatted"]}',
            "compact recap",
            "sanitised recap",
        ]
    )
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = RecapWriterAgent(provider, {}, bus, wiki_bus)

    with patch(
        "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
        side_effect=lambda name, variables=None: f"prompt::{name}",
    ):
        await agent.run(
            "my-story",
            3,
            "chapter body",
            "previous recap",
            "2024-01-15",
            GenerationSettings.from_dict({}),
        )

    assert any("[Recap]" in message for message in bus.messages)


@pytest.mark.asyncio
async def test_run_accepts_empty_previous_recap_and_start_date() -> None:
    provider = _ProviderStub(
        [
            "events text",
            "timed events",
            "enriched events",
            '{"events": ["formatted"]}',
            "compact recap",
            "sanitised recap",
        ]
    )
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = RecapWriterAgent(provider, {}, bus, wiki_bus)

    with patch(
        "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
        side_effect=lambda name, variables=None: f"prompt::{name}",
    ):
        result = await agent.run(
            "my-story",
            3,
            "chapter body",
            "",
            "",
            GenerationSettings.from_dict({}),
        )

    assert isinstance(result, dict)
    assert result["events"] == "events text"


@pytest.mark.asyncio
async def test_assemble_context_called_with_recap_scope(tmp_path: Path) -> None:
    provider = _ProviderStub(
        [
            "events text",
            "timed events",
            "enriched events",
            '{"events": ["formatted"]}',
            "compact recap",
            "sanitised recap",
        ]
    )
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = RecapWriterAgent(provider, {}, bus, wiki_bus)
    settings = GenerationSettings.from_dict({})

    with (
        patch(
            "presentation.agents.recap_writer.assemble_context",
            return_value={
                "wiki_snapshot": "wiki text",
                "recap_snippets": ["recap A", "recap B"],
            },
        ) as assemble_mock,
        patch(
            "presentation.agents.recap_writer.read_index",
            return_value=[
                {
                    "name": "Alice",
                    "slug": "alice",
                    "type": "character",
                    "aliases": [],
                }
            ],
        ),
        patch(
            "presentation.agents.recap_writer.match_entities_in_text",
            return_value=[
                {
                    "name": "Alice",
                    "slug": "alice",
                    "type": "character",
                    "aliases": [],
                }
            ],
        ),
        patch("presentation.agents.recap_writer.STORIES_DIR", tmp_path),
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=lambda name, variables=None: f"prompt::{name}",
        ),
    ):
        await agent.run(
            "my-story",
            3,
            "Alice appeared in the chapter",
            "prev recap",
            "2024-01-15",
            settings,
        )

    assemble_mock.assert_called_once_with(
        "my-story",
        scope="recap",
        focus="Alice appeared in the chapter",
        chapter=3,
        characters=("alice",),
        recap_window=("character", 5),
    )


@pytest.mark.asyncio
async def test_related_recap_history_injected_in_extract_events_prompt() -> None:
    provider = _ProviderStub(
        [
            "events text",
            "timed events",
            "enriched events",
            '{"events": ["formatted"]}',
            "compact recap",
            "sanitised recap",
        ]
    )
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = RecapWriterAgent(provider, {}, bus, wiki_bus)
    captured_variables: dict[str, object] = {}

    def capture_prompt(name: str, variables: dict[str, object] | None = None) -> str:
        if name == "extract_chapter_events":
            captured_variables.update(variables or {})
        return f"prompt::{name}"

    with (
        patch(
            "presentation.agents.recap_writer.assemble_context",
            return_value={
                "wiki_snapshot": "",
                "recap_snippets": ["prior event 1", "prior event 2"],
            },
        ),
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=capture_prompt,
        ),
    ):
        await agent.run(
            "my-story",
            3,
            "chapter body",
            "prev recap",
            "2024-01-15",
            GenerationSettings.from_dict({}),
        )

    assert captured_variables["related_recap_history"] == "prior event 1\n\nprior event 2"


@pytest.mark.asyncio
async def test_related_recap_history_injected_in_sanitize_prompt() -> None:
    provider = _ProviderStub(
        [
            "events text",
            "timed events",
            "enriched events",
            '{"events": ["formatted"]}',
            "compact recap",
            "sanitised recap",
        ]
    )
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = RecapWriterAgent(provider, {}, bus, wiki_bus)
    captured_variables: dict[str, object] = {}

    def capture_prompt(name: str, variables: dict[str, object] | None = None) -> str:
        if name == "recap/sanitize":
            captured_variables.update(variables or {})
        return f"prompt::{name}"

    with (
        patch(
            "presentation.agents.recap_writer.assemble_context",
            return_value={
                "wiki_snapshot": "",
                "recap_snippets": ["prior event"],
            },
        ),
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=capture_prompt,
        ),
    ):
        await agent.run(
            "my-story",
            3,
            "chapter body",
            "prev recap",
            "2024-01-15",
            GenerationSettings.from_dict(
                {
                    "use_multi_stage_recap_sanitizer": True,
                    "use_improved_recap_sanitizer": True,
                }
            ),
        )

    assert "prior event" in str(captured_variables["related_recap_history"])
