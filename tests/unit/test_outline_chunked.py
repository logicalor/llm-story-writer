from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from application.pipeline.handoffs import OutlineResult
from domain.value_objects.generation_settings import GenerationSettings
from presentation.agents.outline_planner import OutlinePlannerAgent


async def _async_gen(tokens: list[str]):
    for token in tokens:
        yield token


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


def _make_agent(provider: MagicMock) -> OutlinePlannerAgent:
    return OutlinePlannerAgent(provider, {}, _StubBus(), _StubWikiBus())


def _chunk_outline(start: int, end: int) -> str:
    return "\n\n".join(
        f"### Chapter {chapter}: Title {chapter}\nSummary {chapter}\n"
        for chapter in range(start, end + 1)
    )


def _chapter_detail(chapter: int) -> str:
    return f"## Chapter {chapter}: Title {chapter}\n### Opening\nDetail {chapter}\n"


@pytest.mark.asyncio
async def test_chunked_exact_call_counts(tmp_path: Path) -> None:
    provider = MagicMock()
    provider.stream_text = MagicMock(
        side_effect=[
            _async_gen([_chunk_outline(1, 5)]),
            _async_gen(["Continuity 1-5"]),
            _async_gen([_chunk_outline(6, 10)]),
            _async_gen(["Continuity 6-10"]),
            _async_gen([_chunk_outline(11, 15)]),
            _async_gen(["Continuity 11-15"]),
            _async_gen([_chunk_outline(16, 20)]),
            _async_gen(["Continuity 16-20"]),
            _async_gen([_chunk_outline(21, 25)]),
            _async_gen(["Enrichment suggestions"]),
        ]
    )
    agent = _make_agent(provider)

    with (
        patch("presentation.agents.outline_planner.STORIES_DIR", tmp_path),
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=lambda name, variables=None: f"prompt::{name}",
        ) as mock_load_prompt,
    ):
        result = await agent.run(
            "test-story",
            "a prompt",
            GenerationSettings.from_dict(
                {
                    "use_chunked_outline_generation": True,
                    "outline_chunk_size": 5,
                    "wanted_chapters": 25,
                    "expand_outline": True,
                }
            ),
        )

    prompt_names = [call.args[0] for call in mock_load_prompt.call_args_list]

    assert isinstance(result, OutlineResult)
    assert provider.stream_text.call_count == 10
    assert prompt_names.count("outline/create_chunk") == 5
    assert prompt_names.count("outline/analyze_continuity") == 4
    assert prompt_names.count("outline/analyze_enrichment") == 1


@pytest.mark.asyncio
async def test_chunked_enrichment_suggestions_non_empty(tmp_path: Path) -> None:
    provider = MagicMock()
    provider.stream_text = MagicMock(
        side_effect=[
            _async_gen([_chunk_outline(1, 5)]),
            _async_gen(["Continuity 1-5"]),
            _async_gen([_chunk_outline(6, 10)]),
            _async_gen(["Add more interpersonal conflict."]),
        ]
    )
    agent = _make_agent(provider)

    with (
        patch("presentation.agents.outline_planner.STORIES_DIR", tmp_path),
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=lambda name, variables=None: f"prompt::{name}",
        ),
    ):
        result = await agent.run(
            "test-story",
            "a prompt",
            GenerationSettings.from_dict(
                {
                    "use_chunked_outline_generation": True,
                    "outline_chunk_size": 5,
                    "wanted_chapters": 10,
                    "expand_outline": True,
                }
            ),
        )

    assert result.enrichment_suggestions != ""


@pytest.mark.asyncio
async def test_chunked_enrichment_md_written_to_disk(tmp_path: Path) -> None:
    provider = MagicMock()
    provider.stream_text = MagicMock(
        side_effect=[
            _async_gen([_chunk_outline(1, 5)]),
            _async_gen(["Continuity 1-5"]),
            _async_gen([_chunk_outline(6, 10)]),
            _async_gen(["Add a stronger midpoint reversal."]),
        ]
    )
    agent = _make_agent(provider)

    with (
        patch("presentation.agents.outline_planner.STORIES_DIR", tmp_path),
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=lambda name, variables=None: f"prompt::{name}",
        ),
    ):
        await agent.run(
            "test-story",
            "a prompt",
            GenerationSettings.from_dict(
                {
                    "use_chunked_outline_generation": True,
                    "outline_chunk_size": 5,
                    "wanted_chapters": 10,
                    "expand_outline": True,
                }
            ),
        )

    assert (tmp_path / "test-story" / "outline" / "enrichment.md").exists()


@pytest.mark.asyncio
async def test_chunked_flag_disabled_uses_per_chapter_path(tmp_path: Path) -> None:
    provider = MagicMock()
    provider.stream_text = MagicMock(
        side_effect=[
            _async_gen([_chunk_outline(1, 10)]),
            _async_gen([_chapter_detail(1)]),
            _async_gen([_chapter_detail(2)]),
            _async_gen([_chapter_detail(3)]),
            _async_gen([_chapter_detail(4)]),
            _async_gen([_chapter_detail(5)]),
            _async_gen([_chapter_detail(6)]),
            _async_gen([_chapter_detail(7)]),
            _async_gen([_chapter_detail(8)]),
            _async_gen([_chapter_detail(9)]),
            _async_gen([_chapter_detail(10)]),
            _async_gen(["stripped content"]),
        ]
    )
    agent = _make_agent(provider)

    with (
        patch("presentation.agents.outline_planner.STORIES_DIR", tmp_path),
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=lambda name, variables=None: f"prompt::{name}",
        ) as mock_load_prompt,
    ):
        await agent.run(
            "test-story",
            "a prompt",
            GenerationSettings.from_dict(
                {
                    "use_chunked_outline_generation": False,
                    "outline_chunk_size": 5,
                    "wanted_chapters": 10,
                    "expand_outline": True,
                }
            ),
        )

    prompt_names = [call.args[0] for call in mock_load_prompt.call_args_list]

    assert "outline/create_chunk" not in prompt_names
    assert "outline/create_skeleton" in prompt_names


@pytest.mark.asyncio
async def test_chunked_below_chunk_size_uses_per_chapter_path(tmp_path: Path) -> None:
    provider = MagicMock()
    provider.stream_text = MagicMock(
        side_effect=[
            _async_gen([_chunk_outline(1, 3)]),
            _async_gen([_chapter_detail(1)]),
            _async_gen([_chapter_detail(2)]),
            _async_gen([_chapter_detail(3)]),
            _async_gen(["stripped content"]),
        ]
    )
    agent = _make_agent(provider)

    with (
        patch("presentation.agents.outline_planner.STORIES_DIR", tmp_path),
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=lambda name, variables=None: f"prompt::{name}",
        ) as mock_load_prompt,
    ):
        await agent.run(
            "test-story",
            "a prompt",
            GenerationSettings.from_dict(
                {
                    "use_chunked_outline_generation": True,
                    "outline_chunk_size": 5,
                    "wanted_chapters": 3,
                    "expand_outline": True,
                }
            ),
        )

    prompt_names = [call.args[0] for call in mock_load_prompt.call_args_list]

    assert "outline/create_chunk" not in prompt_names
    assert "outline/create_skeleton" in prompt_names
