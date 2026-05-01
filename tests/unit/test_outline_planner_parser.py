"""Tests for the OutlinePlannerAgent chapter outline parser."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from presentation.agents.outline_planner import _parse_chapter_outlines


def test_parse_markdown_heading_chapters() -> None:
    text = (
        "### Chapter 1: The Zero Hour\n"
        "SABLE wakes Yara to report a strange signal.\n"
        "She suspects it is real.\n"
        "\n"
        "### Chapter 2: Echoes of Earth\n"
        "Emre opposes any course deviation.\n"
        "\n"
        "### Chapter 3: Linguistic Shadows\n"
        "Dr. Nair finds mathematical constants in the signal.\n"
    )

    parsed = _parse_chapter_outlines(text, wanted_chapters=25)

    assert len(parsed) == 3
    assert parsed[0]["chapter_number"] == 1
    assert parsed[0]["title"] == "Chapter 1: The Zero Hour"
    assert "SABLE wakes Yara" in parsed[0]["summary"]
    assert "She suspects it is real." in parsed[0]["summary"]
    assert parsed[1]["chapter_number"] == 2
    assert parsed[1]["title"] == "Chapter 2: Echoes of Earth"
    assert "Emre opposes" in parsed[1]["summary"]
    assert parsed[2]["chapter_number"] == 3


def test_parse_plain_chapter_headings() -> None:
    text = (
        "Chapter 1: Opening\nThe hero arrives.\n\n"
        "Chapter 2 - Conflict\nA rival appears.\n"
    )

    parsed = _parse_chapter_outlines(text, wanted_chapters=10)

    assert len(parsed) == 2
    assert parsed[0]["chapter_number"] == 1
    assert "The hero arrives." in parsed[0]["summary"]
    assert parsed[1]["chapter_number"] == 2
    assert parsed[1]["title"] == "Chapter 2: Conflict"


def test_parse_trims_to_wanted_chapters() -> None:
    text = "\n".join(f"### Chapter {n}: T{n}\nbody {n}" for n in range(1, 6))

    parsed = _parse_chapter_outlines(text, wanted_chapters=3)

    assert len(parsed) == 3
    assert [c["chapter_number"] for c in parsed] == [1, 2, 3]


def test_parse_json_payload_still_supported() -> None:
    text = (
        '{"chapter_outlines": ['
        '{"chapter_number": 1, "title": "A", "summary": "s1"},'
        '{"chapter_number": 2, "title": "B", "summary": "s2"}'
        "]}"
    )

    parsed = _parse_chapter_outlines(text, wanted_chapters=5)

    assert len(parsed) == 2
    assert parsed[0]["title"] == "A"


def test_parse_fallback_on_unstructured_text() -> None:
    text = "Just some prose with no chapter headings at all."

    parsed = _parse_chapter_outlines(text, wanted_chapters=5)

    assert len(parsed) == 1
    assert parsed[0]["chapter_number"] == 1
    assert parsed[0]["summary"].startswith("Just some prose")


def test_parse_empty_text_returns_empty_list() -> None:
    assert _parse_chapter_outlines("", wanted_chapters=3) == []
    assert _parse_chapter_outlines("   \n\n  ", wanted_chapters=3) == []
