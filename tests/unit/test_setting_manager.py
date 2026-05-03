"""Verification tests for setting_manager markdown pointer storage."""

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
import tools.setting_manager as setting_manager
from tools._persist import persist_markdown
from tools.setting_manager import (
    cmd_generate_chunks,
    cmd_generate_sheet,
    cmd_generate_summary,
    cmd_load_sheet,
)


@pytest.fixture()
def setting_story(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[str, Path]:
    story_name = "test-story"
    story_root = tmp_path / story_name
    story_root.mkdir(parents=True)
    monkeypatch.setattr(io_module, "STORIES_DIR", tmp_path)
    monkeypatch.setattr(setting_manager, "STORIES_DIR", tmp_path)
    return story_name, story_root


def _setting_args(**overrides: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "name": "test-story",
        "setting": "Moonlit Keep",
        "data": None,
        "additional_context": None,
        "model": None,
        "abridged": False,
        "chunk": None,
        "budget": 500,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _setting_path(story_root: Path, slug: str = "moonlit-keep") -> Path:
    return story_root / "settings" / f"{slug}.json"


def _write_setting_json(story_root: Path, payload: dict[str, object]) -> Path:
    setting_path = _setting_path(story_root)
    setting_path.parent.mkdir(parents=True, exist_ok=True)
    setting_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return setting_path


class TestSettingManagerPointerFormat:
    def test_generate_sheet_writes_pointer_json(
        self, setting_story: tuple[str, Path]
    ) -> None:
        story_name, story_root = setting_story
        sheet_body = "# Moonlit Keep\nAncient fortress above the cliffs."
        args = _setting_args(
            name=story_name,
            data=json.dumps(
                {
                    "sheet": sheet_body,
                    "chunks": {},
                    "summary": "Keep summary",
                    "abridged": "Keep abridged",
                }
            ),
        )

        cmd_generate_sheet(args)

        stored = json.loads(_setting_path(story_root).read_text(encoding="utf-8"))
        assert stored["sheet"] == {"$ref": "settings/moonlit-keep/sheet.md"}
        assert (story_root / "settings" / "moonlit-keep" / "sheet.md").read_text(
            encoding="utf-8"
        ) == sheet_body

    def test_generate_sheet_no_markdown_body_in_json(
        self, setting_story: tuple[str, Path]
    ) -> None:
        story_name, story_root = setting_story
        args = _setting_args(
            name=story_name,
            data=json.dumps(
                {
                    "sheet": "# Moonlit Keep\nDetailed setting body.",
                    "chunks": {},
                    "summary": "# Summary\nStorm-lashed fortress.",
                    "abridged": "# Abridged\nCliffside keep.",
                }
            ),
        )

        cmd_generate_sheet(args)

        stored = json.loads(_setting_path(story_root).read_text(encoding="utf-8"))
        for field in ("sheet", "summary", "abridged"):
            value = stored[field]
            assert isinstance(value, dict)
            assert "$ref" in value

    def test_load_sheet_resolves_pointer(
        self, setting_story: tuple[str, Path], capsys: pytest.CaptureFixture[str]
    ) -> None:
        story_name, story_root = setting_story
        sheet_body = "# Moonlit Keep\nResolved markdown body."
        sheet_ref = persist_markdown(
            story_root,
            "settings/moonlit-keep/sheet.md",
            sheet_body,
        )
        _write_setting_json(
            story_root,
            {
                "name": "Moonlit Keep",
                "sheet": sheet_ref,
                "chunks": {},
                "summary": "",
                "abridged": "",
                "updated_at": "2026-05-03T00:00:00+00:00",
            },
        )

        cmd_load_sheet(_setting_args(name=story_name))

        loaded = json.loads(capsys.readouterr().out)
        assert loaded["sheet"] == sheet_body
        assert isinstance(loaded["sheet"], str)

    def test_load_sheet_legacy_string_passthrough(
        self, setting_story: tuple[str, Path], capsys: pytest.CaptureFixture[str]
    ) -> None:
        story_name, story_root = setting_story
        legacy_sheet = "Legacy inline setting sheet"
        _write_setting_json(
            story_root,
            {
                "name": "Moonlit Keep",
                "sheet": legacy_sheet,
                "chunks": {},
                "summary": "",
                "abridged": "",
                "updated_at": "2026-05-03T00:00:00+00:00",
            },
        )

        cmd_load_sheet(_setting_args(name=story_name))

        loaded = json.loads(capsys.readouterr().out)
        assert loaded["sheet"] == legacy_sheet

    def test_generate_chunks_writes_pointer_chunks(
        self, setting_story: tuple[str, Path]
    ) -> None:
        story_name, story_root = setting_story
        sheet_ref = persist_markdown(
            story_root,
            "settings/moonlit-keep/sheet.md",
            "# Moonlit Keep\nStorm-lashed fortress.",
        )
        _write_setting_json(
            story_root,
            {
                "name": "Moonlit Keep",
                "sheet": sheet_ref,
                "chunks": {},
                "summary": "",
                "abridged": "",
                "updated_at": "2026-05-03T00:00:00+00:00",
            },
        )

        with patch(
            "tools.setting_manager._load_prompt",
            side_effect=lambda prompt_id, variables=None: str(
                (variables or {}).get("setting_sheet", "")
            ),
        ), patch(
            "tools.setting_manager._call_llm",
            return_value="<output>chunk content here</output>",
        ):
            cmd_generate_chunks(_setting_args(name=story_name))

        stored = json.loads(_setting_path(story_root).read_text(encoding="utf-8"))
        expected_keys = {
            "physical_description",
            "atmosphere_mood",
            "function_purpose",
            "history_background",
            "rules_constraints",
            "connections_relationships",
        }
        # Independent expected value — intentional test design.
        assert set(stored["chunks"]) == expected_keys
        for key, value in stored["chunks"].items():
            assert isinstance(value, dict)
            assert value == {"$ref": f"settings/moonlit-keep/chunks/{key}.md"}
            assert (story_root / value["$ref"]).read_text(encoding="utf-8") == (
                "chunk content here"
            )

    def test_generate_summary_resolves_chunks_for_prompt(
        self, setting_story: tuple[str, Path]
    ) -> None:
        story_name, story_root = setting_story
        chunks = {
            "physical_description": persist_markdown(
                story_root,
                "settings/moonlit-keep/chunks/physical_description.md",
                "Basalt towers rise over the sea.",
            ),
            "history_background": persist_markdown(
                story_root,
                "settings/moonlit-keep/chunks/history_background.md",
                "Built after the ash wars.",
            ),
        }
        _write_setting_json(
            story_root,
            {
                "name": "Moonlit Keep",
                "sheet": "legacy sheet",
                "chunks": chunks,
                "summary": "",
                "abridged": "",
                "updated_at": "2026-05-03T00:00:00+00:00",
            },
        )
        mock_llm = MagicMock(return_value="<output>great summary</output>")

        with patch(
            "tools.setting_manager._load_prompt",
            side_effect=lambda prompt_id, variables=None: str(
                (variables or {}).get("setting_info", "")
            ),
        ), patch("tools.setting_manager._call_llm", mock_llm):
            cmd_generate_summary(_setting_args(name=story_name))

        prompt = mock_llm.call_args.args[0]
        assert "Basalt towers rise over the sea." in prompt
        assert "Built after the ash wars." in prompt
        assert '"$ref"' not in prompt