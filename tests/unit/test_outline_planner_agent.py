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


@pytest.mark.asyncio
async def test_expand_outline_false_uses_create_direct() -> None:
    provider = MagicMock()
    provider.stream_text = MagicMock(
        return_value=_async_gen(["### Chapter 1: Title\nSummary text\n"])
    )
    agent = _make_agent(provider)

    with patch(
        "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
        side_effect=lambda name, variables=None: f"prompt::{name}",
    ) as mock_load_prompt:
        result = await agent.run(
            "test-story",
            "a prompt",
            GenerationSettings.from_dict(
                {"expand_outline": False, "wanted_chapters": 3}
            ),
        )

    prompt_names = [call.args[0] for call in mock_load_prompt.call_args_list]

    assert "outline/create_direct" in prompt_names
    assert isinstance(result, OutlineResult)
    assert result.story_name == "test-story"


@pytest.mark.asyncio
async def test_expand_outline_false_passes_base_context_and_story_elements() -> None:
    provider = MagicMock()
    provider.stream_text = MagicMock(
        return_value=_async_gen(["### Chapter 1: Title\nSummary text\n"])
    )
    agent = _make_agent(provider)
    captured_direct_variables: dict[str, str] = {}

    def _capture_prompt(name: str, variables: dict[str, str] | None = None) -> str:
        if name == "outline/create_direct":
            captured_direct_variables.update(variables or {})
        return f"prompt::{name}"

    with patch(
        "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
        side_effect=_capture_prompt,
    ) as mock_load_prompt:
        await agent.run(
            "test-story",
            "a prompt",
            GenerationSettings.from_dict(
                {"expand_outline": False, "wanted_chapters": 3}
            ),
            base_context="myctx",
            story_elements="myelems",
        )

    prompt_names = [call.args[0] for call in mock_load_prompt.call_args_list]

    assert "outline/create_direct" in prompt_names
    assert captured_direct_variables["base_context"] == "myctx"
    assert captured_direct_variables["story_elements"] == "myelems"


@pytest.mark.asyncio
async def test_expand_outline_true_populates_chapter_details(tmp_path: Path) -> None:
    provider = MagicMock()
    provider.stream_text = MagicMock(
        side_effect=[
            _async_gen(["### Chapter 1: A\nbody\n\n### Chapter 2: B\nbody2\n"]),
            _async_gen(["## Chapter 1: A\n### Opening\nfoo\n"]),
            _async_gen(["## Chapter 2: B\n### Opening\nbar\n"]),
            _async_gen(["stripped content"]),
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
                {"expand_outline": True, "wanted_chapters": 2}
            ),
            base_context="ctx",
            story_elements="elems",
        )

    assert len(result.chapter_details) == 2
    assert result.chapter_details[0]["chapter_number"] == 1
    assert result.chapter_details[1]["chapter_number"] == 2
    assert len(result.chapter_skeletons) == 2


@pytest.mark.asyncio
async def test_expand_outline_true_writes_detail_files_to_disk(tmp_path: Path) -> None:
    provider = MagicMock()
    provider.stream_text = MagicMock(
        side_effect=[
            _async_gen(["### Chapter 1: A\nbody\n\n### Chapter 2: B\nbody2\n"]),
            _async_gen(["## Chapter 1: A\n### Opening\nfoo\n"]),
            _async_gen(["## Chapter 2: B\n### Opening\nbar\n"]),
            _async_gen(["stripped content"]),
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
                {"expand_outline": True, "wanted_chapters": 2}
            ),
            base_context="ctx",
            story_elements="elems",
        )

    assert (tmp_path / "test-story" / "outline" / "details" / "chapter_1.md").exists()
    assert (tmp_path / "test-story" / "outline" / "details" / "chapter_2.md").exists()


@pytest.mark.asyncio
async def test_expand_outline_true_skips_already_expanded_chapters(
    tmp_path: Path,
) -> None:
    details_dir = tmp_path / "test-story" / "outline" / "details"
    details_dir.mkdir(parents=True, exist_ok=True)
    (details_dir / "chapter_1.md").write_text("existing detail", encoding="utf-8")

    provider = MagicMock()
    provider.stream_text = MagicMock(
        side_effect=[
            _async_gen(["### Chapter 1: A\nbody\n\n### Chapter 2: B\nbody2\n"]),
            _async_gen(["## Chapter 2: B\n### Opening\nbar\n"]),
            _async_gen(["stripped content"]),
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
                {"expand_outline": True, "wanted_chapters": 2}
            ),
        )

    assert result.chapter_details[0]["detail"] == "existing detail"
    assert provider.stream_text.call_count == 3


@pytest.mark.asyncio
async def test_expand_outline_true_calls_skeleton_and_strip_prompts(
    tmp_path: Path,
) -> None:
    provider = MagicMock()
    provider.stream_text = MagicMock(
        side_effect=[
            _async_gen(["### Chapter 1: A\nbody\n\n### Chapter 2: B\nbody2\n"]),
            _async_gen(["## Chapter 1: A\n### Opening\nfoo\n"]),
            _async_gen(["## Chapter 2: B\n### Opening\nbar\n"]),
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
                {"expand_outline": True, "wanted_chapters": 2}
            ),
            base_context="ctx",
            story_elements="elems",
        )

    prompt_names = [call.args[0] for call in mock_load_prompt.call_args_list]

    assert "outline/create_skeleton" in prompt_names
    assert "outline/strip_elements" in prompt_names
    assert prompt_names.count("outline/expand_chapter_detail") == 2
