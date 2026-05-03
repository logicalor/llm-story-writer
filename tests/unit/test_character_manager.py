"""Verification tests for character_manager markdown pointer storage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import src.tools._io as io_module
import tools.character_manager as character_manager
from tools._persist import persist_markdown
from tools.character_manager import (
    cmd_generate_chunks,
    cmd_generate_sheet,
    cmd_generate_summary,
    cmd_load_sheet,
)


@pytest.fixture()
def character_story(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[str, Path]:
    story_name = "test-story"
    story_root = tmp_path / story_name
    story_root.mkdir(parents=True)
    monkeypatch.setattr(io_module, "STORIES_DIR", tmp_path)
    monkeypatch.setattr(character_manager, "STORIES_DIR", tmp_path)
    return story_name, story_root


def _character_args(**overrides: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "name": "test-story",
        "character": "Alice",
        "data": None,
        "additional_context": None,
        "model": None,
        "abridged": False,
        "chunk": None,
        "budget": 500,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _character_path(story_root: Path, character_name: str = "Alice") -> Path:
    return story_root / "characters" / f"{character_name.lower()}.json"


def _write_character_json(story_root: Path, payload: dict[str, object]) -> Path:
    char_path = story_root / "characters" / "alice.json"
    char_path.parent.mkdir(parents=True, exist_ok=True)
    char_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return char_path


class TestCharacterManagerPointerFormat:
    def test_generate_sheet_writes_pointer_json(
        self, character_story: tuple[str, Path]
    ) -> None:
        story_name, story_root = character_story
        sheet_body = "# Alice\nA brave hero."
        args = _character_args(
            name=story_name,
            data=json.dumps(
                {
                    "sheet": sheet_body,
                    "chunks": {},
                    "summary": "Alice summary",
                    "abridged": "Alice abridged",
                }
            ),
        )

        cmd_generate_sheet(args)

        stored = json.loads(_character_path(story_root).read_text(encoding="utf-8"))
        assert stored["sheet"] == {"$ref": "characters/alice/sheet.md"}
        assert (story_root / "characters" / "alice" / "sheet.md").read_text(
            encoding="utf-8"
        ) == sheet_body

    def test_generate_sheet_no_markdown_body_in_json(
        self, character_story: tuple[str, Path]
    ) -> None:
        story_name, story_root = character_story
        args = _character_args(
            name=story_name,
            data=json.dumps(
                {
                    "sheet": "# Alice\nDetailed sheet body.",
                    "chunks": {},
                    "summary": "# Summary\nBrave hero summary.",
                    "abridged": "# Abridged\nBrave hero.",
                }
            ),
        )

        cmd_generate_sheet(args)

        stored = json.loads(_character_path(story_root).read_text(encoding="utf-8"))
        for field in ("sheet", "summary", "abridged"):
            value = stored[field]
            assert isinstance(value, dict)
            assert "$ref" in value

    def test_load_sheet_resolves_pointer(
        self, character_story: tuple[str, Path], capsys: pytest.CaptureFixture[str]
    ) -> None:
        story_name, story_root = character_story
        sheet_body = "# Alice\nResolved markdown body."
        sheet_ref = persist_markdown(story_root, "characters/alice/sheet.md", sheet_body)
        _write_character_json(
            story_root,
            {
                "name": "Alice",
                "sheet": sheet_ref,
                "chunks": {},
                "summary": "",
                "abridged": "",
                "updated_at": "2026-05-03T00:00:00+00:00",
            },
        )

        cmd_load_sheet(_character_args(name=story_name))

        loaded = json.loads(capsys.readouterr().out)
        assert loaded["sheet"] == sheet_body
        assert isinstance(loaded["sheet"], str)

    def test_load_sheet_legacy_string_passthrough(
        self, character_story: tuple[str, Path], capsys: pytest.CaptureFixture[str]
    ) -> None:
        story_name, story_root = character_story
        legacy_sheet = "Legacy inline character sheet"
        _write_character_json(
            story_root,
            {
                "name": "Alice",
                "sheet": legacy_sheet,
                "chunks": {},
                "summary": "",
                "abridged": "",
                "updated_at": "2026-05-03T00:00:00+00:00",
            },
        )

        cmd_load_sheet(_character_args(name=story_name))

        loaded = json.loads(capsys.readouterr().out)
        assert loaded["sheet"] == legacy_sheet

    def test_generate_chunks_writes_pointer_chunks(
        self, character_story: tuple[str, Path]
    ) -> None:
        story_name, story_root = character_story
        sheet_ref = persist_markdown(
            story_root,
            "characters/alice/sheet.md",
            "# Alice\nHeroic sheet body.",
        )
        _write_character_json(
            story_root,
            {
                "name": "Alice",
                "sheet": sheet_ref,
                "chunks": {},
                "summary": "",
                "abridged": "",
                "updated_at": "2026-05-03T00:00:00+00:00",
            },
        )

        with patch(
            "tools.character_manager._load_prompt",
            side_effect=lambda prompt_id, variables=None: str(
                (variables or {}).get("character_sheet", "")
            ),
        ), patch(
            "tools.character_manager._call_llm",
            return_value="<output>chunk content here</output>",
        ):
            cmd_generate_chunks(_character_args(name=story_name))

        stored = json.loads(_character_path(story_root).read_text(encoding="utf-8"))
        expected_keys = {
            "backstory",
            "personality",
            "motivation",
            "relationships",
            "skills",
            "arc",
            "current_state",
        }
        # Independent expected value — intentional test design.
        assert set(stored["chunks"]) == expected_keys
        for key, value in stored["chunks"].items():
            assert isinstance(value, dict)
            assert value == {"$ref": f"characters/alice/chunks/{key}.md"}
            assert (story_root / value["$ref"]).read_text(encoding="utf-8") == (
                "chunk content here"
            )

    def test_generate_summary_resolves_chunks_for_prompt(
        self, character_story: tuple[str, Path]
    ) -> None:
        story_name, story_root = character_story
        chunks = {
            "backstory": persist_markdown(
                story_root,
                "characters/alice/chunks/backstory.md",
                "Former knight from the north.",
            ),
            "skills": persist_markdown(
                story_root,
                "characters/alice/chunks/skills.md",
                "Expert tracker.",
            ),
        }
        _write_character_json(
            story_root,
            {
                "name": "Alice",
                "sheet": "legacy sheet",
                "chunks": chunks,
                "summary": "",
                "abridged": "",
                "updated_at": "2026-05-03T00:00:00+00:00",
            },
        )
        mock_llm = MagicMock(return_value="<output>great summary</output>")

        with patch(
            "tools.character_manager._load_prompt",
            side_effect=lambda prompt_id, variables=None: str(
                (variables or {}).get("character_info", "")
            ),
        ), patch("tools.character_manager._call_llm", mock_llm):
            cmd_generate_summary(_character_args(name=story_name))

        prompt = mock_llm.call_args.args[0]
        assert "Former knight from the north." in prompt
        assert "Expert tracker." in prompt
        assert '"$ref"' not in prompt