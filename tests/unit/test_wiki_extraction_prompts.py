"""Verification tests for wiki extraction prompt templates."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
WIKI_PROMPTS_DIR = PROMPTS_DIR / "wiki"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from infrastructure.prompts.prompt_loader import PromptLoader


PROMPT_IDS = [
    "wiki/extract_factions_from_chapter",
    "wiki/extract_items_from_chapter",
    "wiki/extract_plot_threads_from_chapter",
    "wiki/extract_world_rules_from_chapter",
    "wiki/extract_themes_from_chapter",
    "wiki/extract_relationships_from_chapter",
]

PROMPT_FILES = [
    "extract_factions_from_chapter.md",
    "extract_items_from_chapter.md",
    "extract_plot_threads_from_chapter.md",
    "extract_world_rules_from_chapter.md",
    "extract_themes_from_chapter.md",
    "extract_relationships_from_chapter.md",
]

SAMPLE_CHAPTER_TEXT = "Sample chapter text. Mara finds the key at dawn."
SAMPLE_EXISTING_PAGES_INDEX = '[{"name": "Mara", "type": "character"}]'


def _loader() -> PromptLoader:
    return PromptLoader(prompts_dir=str(PROMPTS_DIR))


def _load_prompt(prompt_id: str) -> str:
    return _loader().load_prompt(
        prompt_id,
        {
            "chapter_text": SAMPLE_CHAPTER_TEXT,
            "existing_pages_index": SAMPLE_EXISTING_PAGES_INDEX,
        },
    )


class TestWikiExtractionPrompts:
    def test_extract_factions_loads_without_error(self) -> None:
        content = _load_prompt("wiki/extract_factions_from_chapter")

        assert len(content) > 0
        assert "{chapter_text}" not in content
        assert "{existing_pages_index}" not in content

    def test_extract_items_loads_without_error(self) -> None:
        content = _load_prompt("wiki/extract_items_from_chapter")

        assert len(content) > 0
        assert "{chapter_text}" not in content
        assert "{existing_pages_index}" not in content

    def test_extract_plot_threads_loads_without_error(self) -> None:
        content = _load_prompt("wiki/extract_plot_threads_from_chapter")

        assert len(content) > 0
        assert "{chapter_text}" not in content
        assert "{existing_pages_index}" not in content

    def test_extract_world_rules_loads_without_error(self) -> None:
        content = _load_prompt("wiki/extract_world_rules_from_chapter")

        assert len(content) > 0
        assert "{chapter_text}" not in content
        assert "{existing_pages_index}" not in content

    def test_extract_themes_loads_without_error(self) -> None:
        content = _load_prompt("wiki/extract_themes_from_chapter")

        assert len(content) > 0
        assert "{chapter_text}" not in content
        assert "{existing_pages_index}" not in content

    def test_extract_relationships_loads_without_error(self) -> None:
        content = _load_prompt("wiki/extract_relationships_from_chapter")

        assert len(content) > 0
        assert "{chapter_text}" not in content
        assert "{existing_pages_index}" not in content

    def test_all_prompts_contain_chapter_text_placeholder(self) -> None:
        for prompt_file in PROMPT_FILES:
            content = (WIKI_PROMPTS_DIR / prompt_file).read_text(encoding="utf-8")
            assert "{chapter_text}" in content, f"Missing chapter_text in {prompt_file}"

    def test_all_prompts_contain_existing_pages_index_placeholder(self) -> None:
        for prompt_file in PROMPT_FILES:
            content = (WIKI_PROMPTS_DIR / prompt_file).read_text(encoding="utf-8")
            assert "{existing_pages_index}" in content, (
                f"Missing existing_pages_index in {prompt_file}"
            )

    def test_chapter_text_variable_is_substituted(self) -> None:
        for prompt_id in PROMPT_IDS:
            content = _load_prompt(prompt_id)
            assert SAMPLE_CHAPTER_TEXT in content
            assert "{chapter_text}" not in content

    def test_existing_pages_index_variable_is_substituted(self) -> None:
        for prompt_id in PROMPT_IDS:
            content = _load_prompt(prompt_id)
            assert SAMPLE_EXISTING_PAGES_INDEX in content
            assert "{existing_pages_index}" not in content
