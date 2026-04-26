"""Regression tests for ADR 008 phased application-service retirement."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICES_DIR = PROJECT_ROOT / "src" / "application" / "services"


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


def test_adr_008_retains_active_critique_parser() -> None:
    assert (SERVICES_DIR / "critique_parser.py").is_file()
