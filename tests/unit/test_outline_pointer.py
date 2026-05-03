from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from application.pipeline.handoffs import (
    ChapterDraft,
    OutlineResult,
    PipelineState,
    WikiUpdateBatch,
)
from presentation.orchestrator import _build_story_elements, run_pipeline
from presentation.pipeline_primitives import NullApprovalGate, TokenStreamBus, WikiContextBus


def _config() -> dict[str, object]:
    return {
        "generation": {"wanted_chapters": 1, "seed": 12},
        "models": {
            "initial_outline_writer": "openai-compat://outline-model",
            "chapter_writer": "openai-compat://chapter-model",
            "checker_model": "openai-compat://checker-model",
            "eval_model": "openai-compat://wiki-model",
        },
        "model_api_base": "http://127.0.0.1:1234/v1",
        "context_length": 16384,
        "randomize_seed": False,
    }


def _outline_result(enrichment_suggestions: str | dict[str, str] = "") -> OutlineResult:
    return OutlineResult(
        story_name="test-story",
        chapter_outlines=[
            {
                "chapter_number": 1,
                "title": "Chapter 1",
                "summary": "Chapter 1 summary...",
            }
        ],
        summary="Story summary",
        genre="science fiction",
        themes=["memory"],
        enrichment_suggestions=enrichment_suggestions,
    )


def _chapter_draft() -> ChapterDraft:
    return ChapterDraft(
        story_name="test-story",
        chapter_number=1,
        title="Chapter 1",
        content="Draft content 1",
        word_count=3,
    )


def _wiki_batch() -> WikiUpdateBatch:
    return WikiUpdateBatch(
        story_name="test-story",
        chapter_number=1,
        updated_pages=[],
        new_pages=[],
    )


def _generated_character_paths() -> list[Path]:
    return [Path("characters/alice.json")]


async def _run_outline_pipeline(
    tmp_path: Path,
    outline_result: OutlineResult,
) -> PipelineState:
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    provider = MagicMock()

    with (
        patch(
            "presentation.orchestrator._savepoint_path",
            side_effect=lambda story_name: (
                tmp_path / story_name / "savepoints" / "pipeline_state.json"
            ),
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=_generated_character_paths()),
        ),
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
        patch("presentation.agents.recap_writer.RecapWriterAgent") as recap_cls,
    ):
        outline_cls.return_value.run = AsyncMock(return_value=outline_result)
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft())
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )
        recap_cls.return_value.run = AsyncMock(return_value={})

        return await run_pipeline(
            "test-story",
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=_config(),
            provider=provider,
        )


@pytest.mark.asyncio
async def test_outline_summary_pointer_written_to_disk(tmp_path: Path) -> None:
    state = await _run_outline_pipeline(tmp_path, _outline_result())

    assert state.outline_result is not None
    assert state.outline_result.chapter_outlines[0]["summary"] == {
        "$ref": "outline/chapter_1_summary.md"
    }
    assert (
        tmp_path / "test-story" / "outline" / "chapter_1_summary.md"
    ).read_text(encoding="utf-8") == "Chapter 1 summary..."


@pytest.mark.asyncio
async def test_enrichment_suggestions_parsed_and_stored_as_json(tmp_path: Path) -> None:
    state = await _run_outline_pipeline(
        tmp_path,
        _outline_result(
            '```json\n{"tone": "dark", "themes": ["loss"]}\n```'
        ),
    )

    assert state.outline_result is not None
    assert state.outline_result.enrichment_suggestions == {
        "$ref": "outline/enrichment_suggestions.json"
    }
    payload = json.loads(
        (
            tmp_path / "test-story" / "outline" / "enrichment_suggestions.json"
        ).read_text(encoding="utf-8")
    )
    assert payload == {"tone": "dark", "themes": ["loss"]}


def test_enrichment_suggestions_pointer_round_trip() -> None:
    state = PipelineState(
        story_name="test-story",
        current_phase="outline",
        outline_result=OutlineResult(
            story_name="test-story",
            chapter_outlines=[],
            summary="Story summary",
            genre="science fiction",
            themes=["memory"],
            enrichment_suggestions={"$ref": "outline/enrichment_suggestions.json"},
        ),
    )

    round_tripped = PipelineState.from_dict(state.to_dict())

    assert round_tripped.outline_result is not None
    assert round_tripped.outline_result.enrichment_suggestions == {
        "$ref": "outline/enrichment_suggestions.json"
    }


def test_build_story_elements_resolves_summary_pointers(tmp_path: Path) -> None:
    story_root = tmp_path / "test-story"
    story_root.mkdir(parents=True, exist_ok=True)
    (story_root / "outline").mkdir(parents=True, exist_ok=True)
    (story_root / "outline" / "chapter_1_summary.md").write_text(
        "Summary text",
        encoding="utf-8",
    )
    outline_result = OutlineResult(
        story_name="test-story",
        chapter_outlines=[
            {
                "chapter_number": 1,
                "title": "Chapter 1",
                "summary": {"$ref": "outline/chapter_1_summary.md"},
            }
        ],
        summary="Story summary",
        genre="science fiction",
        themes=["memory"],
    )

    story_elements = _build_story_elements(outline_result, story_root)
    resolved_outlines = json.loads(story_elements.split("\n\n", 1)[1])

    assert resolved_outlines[0]["summary"] == "Summary text"
    assert not isinstance(resolved_outlines[0]["summary"], dict)