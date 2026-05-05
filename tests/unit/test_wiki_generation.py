from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from application.pipeline.handoffs import OutlineResult
from tools.wiki_generation import (
    _build_pre_story_excerpt,
    generate_character_pages,
    generate_location_pages,
)


def _config() -> dict[str, object]:
    return {
        "generation": {"seed": 42, "wanted_chapters": 1},
        "models": {"chapter_writer": "openai-compat://test"},
        "randomize_seed": False,
    }


def _outline_result() -> OutlineResult:
    return OutlineResult(
        story_name="test-story",
        chapter_outlines=[
            {
                "chapter_number": 1,
                "title": "Chapter 1",
                "summary": "Alice arrives in Harbor Town.",
            }
        ],
        summary="Story summary",
        genre="fantasy",
        themes=["identity"],
        story_elements="Story elements",
    )


def _character_page_json() -> str:
    return json.dumps(
        {
            "slug": "alice",
            "page_name": "Alice",
            "aliases": [],
            "L1": "Alice is a protagonist.",
            "L2": "Alice arrives in Harbor Town.",
            "L3_background": "Raised far from the city.",
            "L3_personality": "Curious and guarded.",
            "L3_motivations": "Find the missing map.",
            "L3_relationships": "Suspicious of locals.",
            "L3_skills": "Navigation and observation.",
            "L3_growth_arc": "Learns to trust allies.",
            "L3_current_state": "Newly arrived and alert.",
        }
    )


def _location_page_json() -> str:
    return json.dumps(
        {
            "slug": "harbor-town",
            "page_name": "Harbor Town",
            "aliases": [],
            "L1": "Coastal trade settlement.",
            "L2": "Arrival point for the story.",
            "L3_geography": "Windy harbor ringed by cliffs.",
            "L3_history": "Built around an old lighthouse.",
            "L3_atmosphere": "Busy, salty, and tense.",
            "L3_inhabitants": "Fishers, traders, smugglers.",
            "L3_significance": "Entry point to the main mystery.",
            "L3_current_state": "Crowded after a recent storm.",
        }
    )


def _prompt_loader_side_effect(prompt_name: str, variables: dict[str, object]) -> str:
    return f"{prompt_name}:{sorted(variables)}"


class TestBuildPreStoryExcerpt:
    def test_returns_empty_string_when_both_fields_empty(self, tmp_path: Path) -> None:
        outline_result = OutlineResult(
            story_name="test-story",
            chapter_outlines=[],
            summary="Story summary",
            genre="fantasy",
            themes=["identity"],
            story_elements="",
            base_context="",
        )

        result = _build_pre_story_excerpt(outline_result, tmp_path)

        assert result == ""

    def test_returns_story_elements_only_when_base_context_absent(
        self, tmp_path: Path
    ) -> None:
        outline_result = OutlineResult(
            story_name="test-story",
            chapter_outlines=[],
            summary="Story summary",
            genre="fantasy",
            themes=["identity"],
            story_elements="Some elements text",
            base_context="",
        )

        result = _build_pre_story_excerpt(outline_result, tmp_path)

        assert result == "Some elements text"

    def test_returns_both_sections_joined_when_populated(self, tmp_path: Path) -> None:
        outline_result = OutlineResult(
            story_name="test-story",
            chapter_outlines=[],
            summary="Story summary",
            genre="fantasy",
            themes=["identity"],
            story_elements="Elements text",
            base_context="Base context text",
        )

        result = _build_pre_story_excerpt(outline_result, tmp_path)

        assert result == "Elements text\n\nBase context text"

    def test_excludes_summary_and_chapter_outlines(self, tmp_path: Path) -> None:
        outline_result = OutlineResult(
            story_name="test-story",
            chapter_outlines=[
                {
                    "chapter_number": 1,
                    "title": "Ch1",
                    "summary": "Alice dies.",
                }
            ],
            summary="The full story arc summary",
            genre="fantasy",
            themes=["identity"],
            story_elements="Elements",
            base_context="",
        )

        result = _build_pre_story_excerpt(outline_result, tmp_path)

        assert "full story arc" not in result
        assert "Alice dies" not in result
        assert result == "Elements"


class TestWikiGeneration:
    def test_generate_character_pages_happy_path(self, tmp_path: Path) -> None:
        story_name = "test-story"
        (tmp_path / story_name).mkdir(parents=True)
        provider = MagicMock()
        provider.generate_text = AsyncMock(
            side_effect=[
                json.dumps([{"name": "Alice", "type": "character", "aliases": []}]),
                _character_page_json(),
            ]
        )
        run_batch_mock = MagicMock(
            return_value={
                "created": 1,
                "updated": 0,
                "timeline_events": 0,
                "entity_counts": {},
            }
        )

        with (
            patch(
                "tools.wiki_generation._PROMPT_LOADER.load_prompt",
                side_effect=_prompt_loader_side_effect,
            ),
            patch("tools.wiki_generation.run_batch", run_batch_mock),
        ):
            result = generate_character_pages(
                story_name,
                _outline_result(),
                provider,
                _config(),
                tmp_path,
            )

        assert result == {"generated": 1, "skipped": 0}
        run_batch_mock.assert_called_once()

    def test_generate_character_pages_skips_existing(self, tmp_path: Path) -> None:
        story_name = "test-story"
        page_path = tmp_path / story_name / "wiki" / "characters" / "alice.md"
        page_path.parent.mkdir(parents=True)
        page_path.write_text("# Alice\n", encoding="utf-8")
        provider = MagicMock()
        provider.generate_text = AsyncMock(
            side_effect=[
                json.dumps([{"name": "Alice", "type": "character", "aliases": []}]),
                _character_page_json(),
            ]
        )
        run_batch_mock = MagicMock()

        with (
            patch(
                "tools.wiki_generation._PROMPT_LOADER.load_prompt",
                side_effect=_prompt_loader_side_effect,
            ),
            patch("tools.wiki_generation.run_batch", run_batch_mock),
        ):
            result = generate_character_pages(
                story_name,
                _outline_result(),
                provider,
                _config(),
                tmp_path,
            )

        assert result == {"generated": 0, "skipped": 1}
        run_batch_mock.assert_not_called()

    def test_generate_character_pages_retry_on_bad_schema(self, tmp_path: Path) -> None:
        story_name = "test-story"
        (tmp_path / story_name).mkdir(parents=True)
        provider = MagicMock()
        provider.generate_text = AsyncMock(
            side_effect=[
                json.dumps([{"name": "Alice", "type": "character", "aliases": []}]),
                "not valid json",
                _character_page_json(),
            ]
        )
        run_batch_mock = MagicMock(
            return_value={
                "created": 1,
                "updated": 0,
                "timeline_events": 0,
                "entity_counts": {},
            }
        )

        with (
            patch(
                "tools.wiki_generation._PROMPT_LOADER.load_prompt",
                side_effect=_prompt_loader_side_effect,
            ),
            patch("tools.wiki_generation.run_batch", run_batch_mock),
        ):
            result = generate_character_pages(
                story_name,
                _outline_result(),
                provider,
                _config(),
                tmp_path,
            )

        assert result == {"generated": 1, "skipped": 0}
        run_batch_mock.assert_called_once()

    def test_generate_character_pages_fails_after_retries(self, tmp_path: Path) -> None:
        story_name = "test-story"
        (tmp_path / story_name).mkdir(parents=True)
        provider = MagicMock()
        provider.generate_text = AsyncMock(
            side_effect=[
                json.dumps([{"name": "Alice", "type": "character", "aliases": []}]),
                "not valid json",
                "still not valid json",
            ]
        )
        run_batch_mock = MagicMock()

        with (
            patch(
                "tools.wiki_generation._PROMPT_LOADER.load_prompt",
                side_effect=_prompt_loader_side_effect,
            ),
            patch("tools.wiki_generation.run_batch", run_batch_mock),
        ):
            result = generate_character_pages(
                story_name,
                _outline_result(),
                provider,
                _config(),
                tmp_path,
            )

        assert result == {"generated": 0, "skipped": 0}
        run_batch_mock.assert_not_called()

    def test_generate_character_pages_uses_pre_story_context_for_page_generation(
        self, tmp_path: Path
    ) -> None:
        story_name = "test-story"
        (tmp_path / story_name).mkdir(parents=True)
        provider = MagicMock()
        provider.generate_text = AsyncMock(
            side_effect=[
                json.dumps([{"name": "Alice", "type": "character", "aliases": []}]),
                _character_page_json(),
            ]
        )
        run_batch_mock = MagicMock(
            return_value={
                "created": 1,
                "updated": 0,
                "timeline_events": 0,
                "entity_counts": {},
            }
        )
        prompt_loader_mock = MagicMock(side_effect=_prompt_loader_side_effect)
        outline_result = OutlineResult(
            story_name="test-story",
            chapter_outlines=[
                {
                    "chapter_number": 1,
                    "title": "Chapter 1",
                    "summary": "Alice arrives in Harbor Town.",
                }
            ],
            summary="Story summary",
            genre="fantasy",
            themes=["identity"],
            story_elements="Story elements",
            base_context="Base context text",
        )

        with (
            patch(
                "tools.wiki_generation._PROMPT_LOADER.load_prompt",
                prompt_loader_mock,
            ),
            patch("tools.wiki_generation.run_batch", run_batch_mock),
        ):
            result = generate_character_pages(
                story_name,
                outline_result,
                provider,
                _config(),
                tmp_path,
            )

        assert result == {"generated": 1, "skipped": 0}
        page_generation_calls = [
            call_args
            for call_args in prompt_loader_mock.call_args_list
            if call_args.args[0] == "wiki/generate_character_page"
        ]
        assert len(page_generation_calls) == 1
        variables = page_generation_calls[0].args[1]
        assert "pre_story_context" in variables
        assert variables["pre_story_context"] == "Story elements\n\nBase context text"
        assert "outline_excerpt" not in variables

    def test_generate_location_pages_happy_path(self, tmp_path: Path) -> None:
        story_name = "test-story"
        (tmp_path / story_name).mkdir(parents=True)
        provider = MagicMock()
        provider.generate_text = AsyncMock(
            side_effect=[
                json.dumps(
                    [
                        {
                            "name": "Harbor Town",
                            "type": "location",
                            "aliases": [],
                        }
                    ]
                ),
                _location_page_json(),
            ]
        )
        run_batch_mock = MagicMock(
            return_value={
                "created": 1,
                "updated": 0,
                "timeline_events": 0,
                "entity_counts": {},
            }
        )

        with (
            patch(
                "tools.wiki_generation._PROMPT_LOADER.load_prompt",
                side_effect=_prompt_loader_side_effect,
            ),
            patch("tools.wiki_generation.run_batch", run_batch_mock),
        ):
            result = generate_location_pages(
                story_name,
                _outline_result(),
                provider,
                _config(),
                tmp_path,
            )

        assert result == {"generated": 1, "skipped": 0}
        run_batch_mock.assert_called_once()
