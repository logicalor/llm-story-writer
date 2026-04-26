"""Verification tests for critique prompts and parser support.

Confirms that:
- All 6 outline review prompt files exist at prompts/outline_review/
- PromptLoader resolves outline_review paths without error
- CritiqueParser supports character voice consistency checks
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)


OUTLINE_REVIEW_PROMPTS = [
    "audiobook-producer.md",
    "book-club-moderator.md",
    "commercial-fiction-editor.md",
    "literary-fiction-reviewer.md",
    "publishing-acquisitions-editor.md",
    "subject-expert.md",
]


def test_outline_review_prompts_exist():
    """Verify all 6 outline review prompt files exist at prompts/outline_review/."""
    outline_dir = PROJECT_ROOT / "prompts" / "outline_review"
    assert outline_dir.is_dir(), (
        f"prompts/outline_review/ directory missing: {outline_dir}"
    )

    for filename in OUTLINE_REVIEW_PROMPTS:
        path = outline_dir / filename
        assert path.is_file(), f"Missing prompt file: {filename}"


def test_prompt_loader_resolves_outline_review():
    """PromptLoader loads outline_review/audiobook-producer without ConfigurationError."""
    from infrastructure.prompts.prompt_loader import PromptLoader

    loader = PromptLoader(str(PROJECT_ROOT / "prompts"))
    # Should not raise ConfigurationError
    content = loader.load_prompt("outline_review/audiobook-producer")
    assert len(content) > 0, "Prompt content should not be empty"


# ---------------------------------------------------------------------------
# Issue #125: character-voice-consistency in CritiqueParser
# ---------------------------------------------------------------------------


def test_character_voice_consistency_in_critic_criteria() -> None:
    """CritiqueParser knows 'character-voice-consistency' with correct criteria."""
    from src.tools.critique_parser import CritiqueParser

    parser = CritiqueParser()

    assert "character-voice-consistency" in parser.critic_criteria

    criteria = parser.critic_criteria["character-voice-consistency"]
    expected_keys = {
        "Pacing",
        "Details",
        "Flow",
        "Genre",
        "Consistency",
        "Character Arc & Theme",
        "Structure",
    }
    assert expected_keys == set(criteria.keys())
    assert sum(criteria.values()) == 100
