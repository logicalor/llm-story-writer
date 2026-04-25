"""Verification tests for Issue #103 - OutlineGenerator RAG null guard."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = str(PROJECT_ROOT / "src")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


from application.strategies.outline_chapter.outline_generator import OutlineGenerator
from domain.value_objects.generation_settings import GenerationSettings


def _make_outline_generator() -> OutlineGenerator:
    return OutlineGenerator(
        model_provider=MagicMock(),
        config={},
        prompt_handler=MagicMock(),
        system_message="",
        savepoint_manager=MagicMock(),
    )


def test_index_story_analysis_chunk_returns_early_when_rag_integration_is_none() -> (
    None
):
    generator = _make_outline_generator()
    settings = GenerationSettings()

    assert generator.rag_integration is None

    result = asyncio.run(
        generator._index_story_analysis_chunk(
            "content",
            "plot_structure",
            settings,
        )
    )

    assert result is None


def test_index_story_analysis_chunk_calls_index_outline_when_rag_integration_present() -> (
    None
):
    generator = _make_outline_generator()
    settings = GenerationSettings()
    rag_integration = MagicMock()
    rag_integration.index_outline = AsyncMock()
    generator.rag_integration = rag_integration

    result = asyncio.run(
        generator._index_story_analysis_chunk(
            "content",
            "plot_structure",
            settings,
        )
    )

    assert result is None
    rag_integration.index_outline.assert_awaited_once_with(
        outline_content="content",
        metadata={
            "content_type": "story_analysis_chunk",
            "chunk_type": "plot_structure",
            "generation_stage": "story_analysis",
        },
    )
