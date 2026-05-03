from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from application.pipeline.handoffs import ChapterDraft
from domain.value_objects.generation_settings import GenerationSettings
from presentation.agents.character_evolver import CharacterEvolverAgent


class _StubBus:
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def emit(self, msg: str) -> None:
        self.messages.append(msg)

    def close(self) -> None:
        pass


class _StubWikiBus:
    async def emit(self, event: object) -> None:
        pass

    def close(self) -> None:
        pass


class _ProviderStub:
    def __init__(self, responses: list[str]) -> None:
        self.generate_text = AsyncMock(side_effect=responses)


def _chapter_draft() -> ChapterDraft:
    return ChapterDraft(
        story_name="my-story",
        chapter_number=1,
        title="Chapter 1",
        content="Alice meets the villain inside the ruined chapel.",
        word_count=8,
    )


def _settings() -> GenerationSettings:
    return GenerationSettings.from_dict({"seed": 7})


def _write_character_sheet(story_dir: Path, sheet_data: dict[str, object]) -> Path:
    character_path = story_dir / "characters" / "alice.json"
    character_path.parent.mkdir(parents=True)
    character_path.write_text(json.dumps(sheet_data), encoding="utf-8")
    return character_path


@pytest.mark.asyncio
async def test_character_evolver_updates_sheet_on_material_changes(
    tmp_path: Path,
) -> None:
    story_dir = tmp_path / "my-story"
    character_path = _write_character_sheet(
        story_dir,
        {
            "name": "Alice",
            "sheet": "A brave hero.",
            "abridged": "brave hero",
            "summary": "hero",
            "chunks": {},
        },
    )
    provider = _ProviderStub(
        [
            "Alice met the villain and was changed forever",
            "- Gained scar\n- Lost trust",
            '{"name": "Alice", "sheet": "Updated hero after meeting villain."}',
        ]
    )
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = CharacterEvolverAgent(provider, {}, bus, wiki_bus)

    with (
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.agents.character_evolver.STORIES_DIR", tmp_path),
        patch(
            "presentation.agents.character_evolver.PromptLoader.load_prompt",
            side_effect=lambda name, variables=None: f"prompt::{name}",
        ),
    ):
        result = await agent.run("my-story", _chapter_draft(), 1, _settings())

    assert result == {"Alice": "updated"}
    updated_data = json.loads(character_path.read_text(encoding="utf-8"))
    sheet_ref = updated_data["sheet"]
    assert isinstance(sheet_ref, dict) and "$ref" in sheet_ref
    sheet_content = (tmp_path / "my-story" / sheet_ref["$ref"]).read_text(encoding="utf-8")
    assert "Updated hero after meeting villain." in sheet_content
    assert provider.generate_text.call_count == 3


@pytest.mark.asyncio
async def test_character_evolver_no_update_when_no_material_changes(
    tmp_path: Path,
) -> None:
    story_dir = tmp_path / "my-story"
    _write_character_sheet(
        story_dir,
        {
            "name": "Alice",
            "sheet": "A brave hero.",
            "abridged": "brave hero",
            "summary": "hero",
            "chunks": {},
        },
    )
    provider = _ProviderStub(["No events found"])
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = CharacterEvolverAgent(provider, {}, bus, wiki_bus)

    with (
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.agents.character_evolver.STORIES_DIR", tmp_path),
        patch(
            "presentation.agents.character_evolver.PromptLoader.load_prompt",
            side_effect=lambda name, variables=None: f"prompt::{name}",
        ),
    ):
        result = await agent.run("my-story", _chapter_draft(), 1, _settings())

    assert result == {"Alice": "unchanged"}
    assert provider.generate_text.call_count == 1


@pytest.mark.asyncio
async def test_character_evolver_preserves_abridged_and_summary_on_update(
    tmp_path: Path,
) -> None:
    story_dir = tmp_path / "my-story"
    character_path = _write_character_sheet(
        story_dir,
        {
            "name": "Alice",
            "sheet": "A brave hero.",
            "abridged": "brave hero",
            "summary": "hero",
            "chunks": {"part1": "context"},
        },
    )
    provider = _ProviderStub(
        [
            "Alice met the villain and was changed forever",
            "- Gained scar\n- Lost trust",
            "Updated hero after meeting villain.",
        ]
    )
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = CharacterEvolverAgent(provider, {}, bus, wiki_bus)

    with (
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.agents.character_evolver.STORIES_DIR", tmp_path),
        patch(
            "presentation.agents.character_evolver.PromptLoader.load_prompt",
            side_effect=lambda name, variables=None: f"prompt::{name}",
        ),
    ):
        result = await agent.run("my-story", _chapter_draft(), 1, _settings())

    assert result == {"Alice": "updated"}
    updated_data = json.loads(character_path.read_text(encoding="utf-8"))
    assert updated_data["abridged"] == "brave hero"
    assert updated_data["summary"] == "hero"
    assert updated_data["chunks"] == {"part1": "context"}
