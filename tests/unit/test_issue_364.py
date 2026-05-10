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
from tools._wiki_api import _extract_type_candidates, update_wiki_full_pass
from application.interfaces.model_provider import StreamToken


async def _stream_tokens(tokens: list[str]):
    for token in tokens:
        yield StreamToken(text=token, kind="content")


def _make_draft(content: str = "Alice walked in.") -> ChapterDraft:
    return ChapterDraft(
        story_name="test-story",
        chapter_number=1,
        title="Chapter 1",
        content=content,
        word_count=len(content.split()),
    )


def _make_provider(responses: list[str]) -> MagicMock:
    provider = MagicMock()
    provider.stream_text = MagicMock(
        side_effect=[_stream_tokens([response]) for response in responses]
    )
    return provider


def _make_buses() -> tuple[MagicMock, MagicMock]:
    bus = MagicMock(spec=TokenStreamBus)
    bus.emit = AsyncMock()
    wiki_bus = MagicMock(spec=WikiContextBus)
    wiki_bus.emit = AsyncMock()
    return bus, wiki_bus


@pytest.mark.asyncio
async def test_prose_scrub_passes_character_aliases_to_prompt(tmp_path: Path) -> None:
    provider = _make_provider(['{"issues": []}', '{"issues": []}', "Alice walked in."])
    bus, wiki_bus = _make_buses()
    agent = FinalEditorAgent(provider=provider, config={}, bus=bus, wiki_bus=wiki_bus)
    draft = _make_draft()
    settings = GenerationSettings.from_dict({"enable_scrubbing": True})
    captured_prose_vars: dict[str, str] = {}

    def capture_prompt(name: str, variables: dict | None = None) -> str:
        if name == "final_edit/prose_scrub":
            assert variables is not None
            captured_prose_vars.update(variables)
        return "prompt"

    with (
        patch(
            "presentation.agents.final_editor.assemble_context",
            return_value={"wiki_snapshot": "", "recap_snippets": []},
        ),
        patch(
            "presentation.agents.final_editor._validate_story_name",
            return_value=tmp_path,
        ),
        patch(
            "presentation.agents.final_editor.get_wiki_dir",
            return_value=tmp_path,
        ),
        patch(
            "presentation.agents.final_editor.read_index",
            return_value=[
                {
                    "name": "Alice",
                    "slug": "alice",
                    "type": "character",
                    "aliases": ["Ali", "Ally"],
                },
                {
                    "name": "Bob",
                    "slug": "bob",
                    "type": "character",
                    "aliases": [],
                },
            ],
        ),
        patch(
            "presentation.agents.final_editor.match_entities_in_text",
            return_value=[{"slug": "alice"}],
        ),
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=capture_prompt,
        ),
    ):
        await agent.edit_single_chapter(
            draft,
            prior_summary="",
            chapter_number=1,
            settings=settings,
        )

    assert captured_prose_vars["character_aliases"] == "Alice (aliases: Ali, Ally)"
    assert "Bob" not in captured_prose_vars["character_aliases"]


@pytest.mark.asyncio
async def test_prose_scrub_degrades_gracefully_when_wiki_unavailable() -> None:
    provider = _make_provider(['{"issues": []}', '{"issues": []}', "Alice walked in."])
    bus, wiki_bus = _make_buses()
    agent = FinalEditorAgent(provider=provider, config={}, bus=bus, wiki_bus=wiki_bus)
    draft = _make_draft()
    settings = GenerationSettings.from_dict({"enable_scrubbing": True})
    prompt_names: list[str] = []
    captured_prose_vars: dict[str, str] = {}

    def capture_prompt(name: str, variables: dict | None = None) -> str:
        prompt_names.append(name)
        if name == "final_edit/prose_scrub":
            assert variables is not None
            captured_prose_vars.update(variables)
        return "prompt"

    with (
        patch(
            "presentation.agents.final_editor.assemble_context",
            return_value={"wiki_snapshot": "", "recap_snippets": []},
        ),
        patch(
            "presentation.agents.final_editor._validate_story_name",
            side_effect=Exception("no wiki"),
        ),
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=capture_prompt,
        ),
    ):
        await agent.edit_single_chapter(
            draft,
            prior_summary="",
            chapter_number=1,
            settings=settings,
        )

    assert any(
        call.args[0].event_type == "error"
        for call in wiki_bus.emit.await_args_list
        if call.args
    )
    assert "final_edit/prose_scrub" in prompt_names
    assert captured_prose_vars["character_aliases"] == ""


def test_extract_type_candidates_event_passes_prior_recap_context() -> None:
    captured_prompt_vars: dict[str, object] = {}

    def capture_prompt(prompt_id: str, variables: dict[str, object]) -> str:
        captured_prompt_vars.clear()
        captured_prompt_vars.update(variables)
        return "prompt"

    with (
        patch("tools._wiki_api._load_prompt", side_effect=capture_prompt),
        patch("tools._wiki_api._chat_completion", return_value="[]"),
    ):
        result = _extract_type_candidates(
            "story",
            "event",
            "chapter text",
            [],
            prior_recap_context="Prior recap here",
        )

    assert result == []
    assert captured_prompt_vars["prior_recap_context"] == "Prior recap here"


def test_extract_type_candidates_non_event_does_not_pass_recap_context() -> None:
    captured_prompt_vars: dict[str, object] = {}

    def capture_prompt(prompt_id: str, variables: dict[str, object]) -> str:
        captured_prompt_vars.clear()
        captured_prompt_vars.update(variables)
        return "prompt"

    with (
        patch("tools._wiki_api._load_prompt", side_effect=capture_prompt),
        patch("tools._wiki_api._chat_completion", return_value="[]"),
    ):
        result = _extract_type_candidates(
            "story",
            "character",
            "chapter text",
            [],
            prior_recap_context="Some recap",
        )

    assert result == []
    assert "prior_recap_context" not in captured_prompt_vars


def test_update_wiki_full_pass_fetches_recap_context_for_events(tmp_path: Path) -> None:
    captured_event_kwargs: list[dict[str, object]] = []

    def capture_extract(*args, **kwargs):
        if args[1] == "event":
            captured_event_kwargs.append(kwargs)
        return []

    with (
        patch("tools._wiki_api._validate_story_name", return_value=tmp_path),
        patch("tools._wiki_api.get_wiki_dir", return_value=tmp_path / "missing-wiki"),
        patch(
            "tools._wiki_api.query_recap",
            return_value=[
                {
                    "document": "Chapter 1 summary",
                    "id": "agg/1",
                    "metadata": {},
                }
            ],
        ) as mock_query_recap,
        patch("tools._wiki_api._extract_type_candidates", side_effect=capture_extract),
        patch("tools._wiki_api.match_entities_in_text", return_value=[]),
    ):
        result = update_wiki_full_pass("story", chapter=2, chapter_text="test chapter")

    assert result["per_type"]["event"] == {"created": 0, "updated": 0}
    mock_query_recap.assert_called_once_with(
        "story",
        query_text="test chapter",
        n_results=3,
    )
    assert captured_event_kwargs
    assert captured_event_kwargs[0]["prior_recap_context"] == "Chapter 1 summary"


def test_update_wiki_full_pass_degrades_when_recap_unavailable(tmp_path: Path) -> None:
    captured_event_kwargs: list[dict[str, object]] = []

    def capture_extract(*args, **kwargs):
        if args[1] == "event":
            captured_event_kwargs.append(kwargs)
        return []

    with (
        patch("tools._wiki_api._validate_story_name", return_value=tmp_path),
        patch("tools._wiki_api.get_wiki_dir", return_value=tmp_path / "missing-wiki"),
        patch(
            "tools._wiki_api.query_recap",
            side_effect=Exception("chromadb unavailable"),
        ),
        patch("tools._wiki_api._extract_type_candidates", side_effect=capture_extract),
        patch("tools._wiki_api.match_entities_in_text", return_value=[]),
    ):
        result = update_wiki_full_pass("story", chapter=1, chapter_text="test")

    assert result["per_type"]["event"] == {"created": 0, "updated": 0}
    assert captured_event_kwargs
    assert captured_event_kwargs[0]["prior_recap_context"] == ""
