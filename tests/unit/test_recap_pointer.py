from __future__ import annotations

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
from presentation.orchestrator import resume_pipeline, run_pipeline
from presentation.pipeline_primitives import (
    NullApprovalGate,
    TokenStreamBus,
    WikiContextBus,
)
from tools._persist import persist_markdown


def _config(wanted_chapters: int) -> dict[str, object]:
    return {
        "generation": {"wanted_chapters": wanted_chapters, "seed": 12},
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


def _outline_result(chapter_count: int) -> OutlineResult:
    return OutlineResult(
        story_name="test-story",
        chapter_outlines=[
            {
                "chapter_number": number,
                "title": f"Chapter {number}",
                "summary": f"Summary {number}",
            }
            for number in range(1, chapter_count + 1)
        ],
        summary="Story summary",
        genre="science fiction",
        themes=["memory"],
    )


def _chapter_draft(chapter_number: int) -> ChapterDraft:
    return ChapterDraft(
        story_name="test-story",
        chapter_number=chapter_number,
        title=f"Chapter {chapter_number}",
        content=f"Draft content {chapter_number}",
        word_count=3,
    )


def _fake_savepoint_path(tmp_path: Path, story_name: str) -> Path:
    return tmp_path / story_name / "savepoints" / "pipeline_state.json"


def _generated_character_paths() -> list[Path]:
    return [Path("characters/alice.json")]


def _wiki_batch(chapter_number: int) -> WikiUpdateBatch:
    return WikiUpdateBatch(
        story_name="test-story",
        chapter_number=chapter_number,
        updated_pages=[],
        new_pages=[],
    )


@pytest.mark.asyncio
async def test_recap_write_stores_pointer_dicts_in_state(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()

    with (
        patch(
            "presentation.orchestrator._savepoint_path",
            side_effect=lambda story_name: _fake_savepoint_path(tmp_path, story_name),
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch(
            "tools.wiki_generation.generate_character_pages",
            new=MagicMock(return_value={"generated": 2, "skipped": 0}),
        ),
        patch(
            "tools.wiki_generation.generate_location_pages",
            new=MagicMock(return_value={"generated": 3, "skipped": 0}),
        ),
        patch(
            "tools.wiki_generation.generate_outline_entity_pages",
            new=MagicMock(return_value={"generated": 0, "skipped": 0}),
        ),
        patch("presentation.agents.recap_writer.RecapWriterAgent") as recap_cls,
    ):
        outline_cls.return_value.run = AsyncMock(return_value=_outline_result(1))
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft(1))
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch(1))
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )
        recap_cls.return_value.run = AsyncMock(
            return_value={"events": "ev", "compact": "cp", "sanitised": "san"}
        )

        state = await run_pipeline(
            "test-story",
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=_config(1),
            provider=provider,
        )

    assert state.recaps["1"] == {
        "events": {"$ref": "chapters/chapter_1/recap_events.md"},
        "compact": {"$ref": "chapters/chapter_1/recap_compact.md"},
        "sanitised": {"$ref": "chapters/chapter_1/recap_sanitised.md"},
    }
    assert (
        tmp_path / "test-story" / "chapters" / "chapter_1" / "recap_events.md"
    ).exists()
    assert (
        tmp_path / "test-story" / "chapters" / "chapter_1" / "recap_compact.md"
    ).exists()
    assert (
        tmp_path / "test-story" / "chapters" / "chapter_1" / "recap_sanitised.md"
    ).exists()


@pytest.mark.asyncio
async def test_recap_md_files_contain_correct_content(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()

    with (
        patch(
            "presentation.orchestrator._savepoint_path",
            side_effect=lambda story_name: _fake_savepoint_path(tmp_path, story_name),
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch(
            "tools.wiki_generation.generate_character_pages",
            new=MagicMock(return_value={"generated": 2, "skipped": 0}),
        ),
        patch(
            "tools.wiki_generation.generate_location_pages",
            new=MagicMock(return_value={"generated": 3, "skipped": 0}),
        ),
        patch(
            "tools.wiki_generation.generate_outline_entity_pages",
            new=MagicMock(return_value={"generated": 0, "skipped": 0}),
        ),
        patch("presentation.agents.recap_writer.RecapWriterAgent") as recap_cls,
    ):
        outline_cls.return_value.run = AsyncMock(return_value=_outline_result(1))
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft(1))
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch(1))
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )
        recap_cls.return_value.run = AsyncMock(
            return_value={"events": "ev", "compact": "cp", "sanitised": "san"}
        )

        await run_pipeline(
            "test-story",
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=_config(1),
            provider=provider,
        )

    story_root = tmp_path / "test-story"
    assert (story_root / "chapters" / "chapter_1" / "recap_events.md").read_text(
        encoding="utf-8"
    ) == "ev"
    assert (story_root / "chapters" / "chapter_1" / "recap_compact.md").read_text(
        encoding="utf-8"
    ) == "cp"
    assert (story_root / "chapters" / "chapter_1" / "recap_sanitised.md").read_text(
        encoding="utf-8"
    ) == "san"


@pytest.mark.asyncio
async def test_recap_read_resolves_pointer_to_string(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    story_root = tmp_path / "test-story"
    story_root.mkdir(parents=True, exist_ok=True)
    pointer = persist_markdown(
        story_root,
        "chapters/chapter_1/recap_events.md",
        "previous events",
    )
    persist_markdown(story_root, "chapters/chapter_1/recap_compact.md", "")
    persist_markdown(story_root, "chapters/chapter_1/recap_sanitised.md", "")

    state = PipelineState(
        story_name="test-story",
        current_phase="chapter-1",
        completed_phases=["init", "outline", "chapter-1"],
        outline_result=_outline_result(2),
        approved_chapters=[_chapter_draft(1)],
        recaps={
            "1": {
                "events": pointer,
                "compact": {"$ref": "chapters/chapter_1/recap_compact.md"},
                "sanitised": {"$ref": "chapters/chapter_1/recap_sanitised.md"},
            }
        },
        savepoints=["init", "outline", "chapter-1"],
    )
    savepoint_path = _fake_savepoint_path(tmp_path, "test-story")
    savepoint_path.parent.mkdir(parents=True, exist_ok=True)
    with patch("tools._io.STORIES_DIR", tmp_path):
        savepoint_path.write_text(state.to_json(), encoding="utf-8")

    with (
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch(
            "tools.wiki_generation.generate_character_pages",
            new=MagicMock(return_value={"generated": 2, "skipped": 0}),
        ),
        patch(
            "tools.wiki_generation.generate_location_pages",
            new=MagicMock(return_value={"generated": 3, "skipped": 0}),
        ),
        patch(
            "tools.wiki_generation.generate_outline_entity_pages",
            new=MagicMock(return_value={"generated": 0, "skipped": 0}),
        ),
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch("presentation.agents.recap_writer.RecapWriterAgent") as recap_cls,
    ):
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft(2))
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch(2))
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )
        recap_cls.return_value.run = AsyncMock(
            return_value={"events": "ev2", "compact": "cp2", "sanitised": "san2"}
        )

        await resume_pipeline(
            "test-story",
            None,
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=_config(2),
            provider=provider,
        )

    assert (
        recap_cls.return_value.run.await_args.kwargs["previous_recap"]
        == "previous events"
    )


@pytest.mark.asyncio
async def test_recap_legacy_inline_dict_still_loads(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    story_root = tmp_path / "test-story"
    story_root.mkdir(parents=True, exist_ok=True)

    state = PipelineState(
        story_name="test-story",
        current_phase="chapter-1",
        completed_phases=["init", "outline", "chapter-1"],
        outline_result=_outline_result(2),
        approved_chapters=[_chapter_draft(1)],
        recaps={"1": {"sanitised": "old content"}},
        savepoints=["init", "outline", "chapter-1"],
    )
    savepoint_path = _fake_savepoint_path(tmp_path, "test-story")
    savepoint_path.parent.mkdir(parents=True, exist_ok=True)
    with patch("tools._io.STORIES_DIR", tmp_path):
        savepoint_path.write_text(state.to_json(), encoding="utf-8")

    with (
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch(
            "tools.wiki_generation.generate_character_pages",
            new=MagicMock(return_value={"generated": 2, "skipped": 0}),
        ),
        patch(
            "tools.wiki_generation.generate_location_pages",
            new=MagicMock(return_value={"generated": 3, "skipped": 0}),
        ),
        patch(
            "tools.wiki_generation.generate_outline_entity_pages",
            new=MagicMock(return_value={"generated": 0, "skipped": 0}),
        ),
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch("presentation.agents.recap_writer.RecapWriterAgent") as recap_cls,
    ):
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft(2))
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch(2))
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )
        recap_cls.return_value.run = AsyncMock(
            return_value={"events": "ev2", "compact": "cp2", "sanitised": "san2"}
        )

        await resume_pipeline(
            "test-story",
            None,
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=_config(2),
            provider=provider,
        )

    assert (
        recap_cls.return_value.run.await_args.kwargs["previous_recap"] == "old content"
    )
