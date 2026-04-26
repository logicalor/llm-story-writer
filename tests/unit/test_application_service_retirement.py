"""Regression tests for ADR 008 phased application-service retirement."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICES_DIR = PROJECT_ROOT / "src" / "application" / "services"
TOOLS_DIR = PROJECT_ROOT / "src" / "tools"


def test_adr_008_phase_1_dead_services_removed() -> None:
    retired_files = {
        "chapter_service.py",
        "content_chunker.py",
        "rag_integration_service.py",
        "story_generation_service.py",
        "story_info_service.py",
    }

    for filename in retired_files:
        assert not (SERVICES_DIR / filename).exists()


def test_adr_008_phase_2_quality_services_removed() -> None:
    retired_files = {
        "critique_parser.py",
        "critique_service.py",
        "model_reranker_service.py",
        "outline_service.py",
        "reranker_service.py",
    }

    for filename in retired_files:
        assert not (SERVICES_DIR / filename).exists()


def test_adr_008_relocates_active_critique_parser_to_tools() -> None:
    assert (TOOLS_DIR / "critique_parser.py").is_file()
