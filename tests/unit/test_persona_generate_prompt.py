"""Verification tests for issue #403 persona generation prompt template."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
PERSONA_PROMPT = PROMPTS_DIR / "persona" / "generate.md"
PERSONA_SCHEMA = PROMPTS_DIR / "persona" / "_schema.md"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from infrastructure.prompts.prompt_loader import PromptLoader


def _loader() -> PromptLoader:
    return PromptLoader(prompts_dir=str(PROMPTS_DIR))


class TestPersonaGeneratePrompt:
    def test_prompt_file_exists(self) -> None:
        assert PERSONA_PROMPT.is_file()

    def test_schema_file_exists(self) -> None:
        assert PERSONA_SCHEMA.is_file()

    def test_prompt_loads_without_error(self) -> None:
        content = _loader().load_prompt("persona/generate")

        assert content

    def test_prompt_renders_all_variables(self) -> None:
        content = _loader().load_prompt(
            "persona/generate",
            {
                "core_story_foundation": "CF",
                "tone_style": "TS",
                "theme_message": "TM",
                "story_elements": "SE",
                "word_budget": 225,
            },
        )

        assert "CF" in content
        assert "TS" in content
        assert "TM" in content
        assert "SE" in content
        assert "225" in content
        assert "{{core_story_foundation}}" not in content

    def test_prompt_contains_required_sections(self) -> None:
        content = PERSONA_PROMPT.read_text(encoding="utf-8")

        assert "## Identity" in content
        assert "## Prose Texture" in content
        assert "## Dialogue Style" in content
        assert "## Pacing Philosophy" in content
        assert "## Thematic Sensibility" in content
        assert "## Narrative Philosophy" in content
        assert "## Anti-Patterns" in content

    def test_prompt_contains_word_budget_variable(self) -> None:
        content = PERSONA_PROMPT.read_text(encoding="utf-8")

        assert "{{word_budget}}" in content

    def test_schema_documents_all_sections(self) -> None:
        content = PERSONA_SCHEMA.read_text(encoding="utf-8")

        assert "genre" in content
        assert "subgenre" in content
        assert "pov" in content
        assert "tense" in content
        assert "created_at" in content
        assert "Identity" in content
        assert "Prose Texture" in content
        assert "Dialogue Style" in content
        assert "Pacing Philosophy" in content
        assert "Thematic Sensibility" in content
        assert "Narrative Philosophy" in content
        assert "Anti-Patterns" in content
