"""Verification tests for extract_paragraph_tail paragraph-boundary trimming."""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from tools._llm import extract_paragraph_tail


class TestExtractParagraphTail:
    def test_result_starts_at_paragraph_boundary(self) -> None:
        first = "alpha " * 40
        second = "beta " * 40
        third = "gamma " * 40
        text = f"{first.strip()}\n\n{second.strip()}\n\n{third.strip()}"

        result = extract_paragraph_tail(text, token_budget=120)

        assert result == f"{second.strip()}\n\n{third.strip()}"
        assert result.startswith(second.strip())
        assert not result.startswith("...")
        assert not result.startswith("…")

    def test_short_prose_returns_full_text(self) -> None:
        text = "Short opening.\n\nShort middle.\n\nShort ending."

        result = extract_paragraph_tail(text, token_budget=200)

        assert result == text

    def test_single_paragraph_returns_full_paragraph(self) -> None:
        text = "single paragraph " * 200

        result = extract_paragraph_tail(text.strip(), token_budget=10)

        assert result == text.strip()

    def test_empty_string_returns_empty(self) -> None:
        assert extract_paragraph_tail("") == ""

    def test_multiple_paragraphs_fit_within_budget(self) -> None:
        paragraphs = [
            "One short paragraph.",
            "Two short paragraph.",
            "Three short paragraph.",
        ]
        text = "\n\n".join(paragraphs)

        result = extract_paragraph_tail(text, token_budget=50)

        assert result == text

    def test_budget_exceeded_returns_last_paragraphs_only(self) -> None:
        paragraphs = [
            "intro " * 60,
            "setup " * 60,
            "turn " * 60,
            "climax " * 20,
            "ending " * 20,
        ]
        normalized = [paragraph.strip() for paragraph in paragraphs]
        text = "\n\n".join(normalized)

        result = extract_paragraph_tail(text, token_budget=70)

        expected = "\n\n".join(normalized[-2:])
        assert result == expected
        assert not result.startswith("...")
        assert not result.startswith("…")
