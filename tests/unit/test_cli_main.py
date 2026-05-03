"""Verification tests for Issue #162 - CLI entry points."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from src.presentation.cli.argument_parser import build_parser  # noqa: E402
from src.presentation.cli.main import _apply_prompt  # noqa: E402
from src.presentation.cli.main import _cmd_run  # noqa: E402
from src.presentation.cli.main import _cmd_tui  # noqa: E402
from src.presentation.cli.main import main  # noqa: E402
from presentation.orchestrator import _load_story_prompt  # noqa: E402


class TestBuildParser:
    def test_tui_subcommand_parses_story_name(self) -> None:
        parser = build_parser()

        args = parser.parse_args(["tui", "--story", "my_story"])

        assert args.subcommand == "tui"
        assert args.story == "my_story"

    def test_tui_subcommand_parses_resume_flag(self) -> None:
        parser = build_parser()

        args = parser.parse_args(["tui", "--story", "my_story", "--resume"])

        assert args.resume is True

    def test_tui_subcommand_resume_defaults_false(self) -> None:
        parser = build_parser()

        args = parser.parse_args(["tui", "--story", "my_story"])

        assert args.resume is False

    def test_tui_subcommand_parses_savepoint_flag(self) -> None:
        parser = build_parser()

        args = parser.parse_args(
            ["tui", "--story", "my_story", "--resume", "--savepoint", "chapter-3"]
        )

        assert args.savepoint == "chapter-3"

    def test_tui_subcommand_savepoint_defaults_none(self) -> None:
        parser = build_parser()

        args = parser.parse_args(["tui", "--story", "my_story"])

        assert args.savepoint is None

    def test_run_subcommand_parses_story_name(self) -> None:
        parser = build_parser()

        args = parser.parse_args(["run", "--story", "my_story"])

        assert args.subcommand == "run"
        assert args.story == "my_story"
        assert args.batch is False

    def test_run_subcommand_batch_flag(self) -> None:
        parser = build_parser()

        args = parser.parse_args(["run", "--story", "my_story", "--batch"])

        assert args.batch is True

    def test_resume_subcommand_parses_story_name(self) -> None:
        parser = build_parser()

        args = parser.parse_args(["resume", "--story", "my_story"])

        assert args.subcommand == "resume"
        assert args.story == "my_story"
        assert args.savepoint is None

    def test_resume_subcommand_parses_savepoint(self) -> None:
        parser = build_parser()

        args = parser.parse_args(
            ["resume", "--story", "my_story", "--savepoint", "chapter-3"]
        )

        assert args.savepoint == "chapter-3"

    def test_missing_story_arg_exits(self, capsys: pytest.CaptureFixture[str]) -> None:
        parser = build_parser()

        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["run"])

        assert exc_info.value.code == 2
        assert "required" in capsys.readouterr().err


class TestMainDispatch:
    def test_run_dispatches_cmd_run(self) -> None:
        original_argv = sys.argv[:]

        try:
            sys.argv = ["story-writer", "run", "--story", "my_story"]
            with patch("src.presentation.cli.main._cmd_run") as mock_cmd_run:
                main()
        finally:
            sys.argv = original_argv

        mock_cmd_run.assert_called_once_with("my_story", batch=False, prompt=None)

    def test_run_with_prompt_dispatches_cmd_run_with_prompt(self) -> None:
        original_argv = sys.argv[:]

        try:
            sys.argv = [
                "story-writer",
                "run",
                "--story",
                "my_story",
                "--prompt",
                "prompts/sample-story.md",
            ]
            with patch("src.presentation.cli.main._cmd_run") as mock_cmd_run:
                main()
        finally:
            sys.argv = original_argv

        mock_cmd_run.assert_called_once_with(
            "my_story", batch=False, prompt="prompts/sample-story.md"
        )

    def test_tui_dispatches_cmd_tui(self) -> None:
        original_argv = sys.argv[:]

        try:
            sys.argv = ["story-writer", "tui", "--story", "my_story"]
            with patch("src.presentation.cli.main._cmd_tui") as mock_cmd_tui:
                main()
        finally:
            sys.argv = original_argv

        mock_cmd_tui.assert_called_once_with(
            "my_story", resume=False, savepoint=None, prompt=None
        )

    def test_tui_with_resume_dispatches_cmd_tui_with_resume(self) -> None:
        original_argv = sys.argv[:]

        try:
            sys.argv = ["story-writer", "tui", "--story", "my_story", "--resume"]
            with patch("src.presentation.cli.main._cmd_tui") as mock_cmd_tui:
                main()
        finally:
            sys.argv = original_argv

        mock_cmd_tui.assert_called_once_with(
            "my_story", resume=True, savepoint=None, prompt=None
        )

    def test_tui_with_resume_and_savepoint_dispatches_correctly(self) -> None:
        original_argv = sys.argv[:]

        try:
            sys.argv = [
                "story-writer",
                "tui",
                "--story",
                "my_story",
                "--resume",
                "--savepoint",
                "ch3",
            ]
            with patch("src.presentation.cli.main._cmd_tui") as mock_cmd_tui:
                main()
        finally:
            sys.argv = original_argv

        mock_cmd_tui.assert_called_once_with(
            "my_story", resume=True, savepoint="ch3", prompt=None
        )

    def test_resume_dispatches_cmd_resume(self) -> None:
        original_argv = sys.argv[:]

        try:
            sys.argv = ["story-writer", "resume", "--story", "my_story"]
            with patch("src.presentation.cli.main._cmd_resume") as mock_cmd_resume:
                main()
        finally:
            sys.argv = original_argv

        mock_cmd_resume.assert_called_once_with("my_story", None, prompt=None)


class TestCmdTui:
    def test_missing_textual_reports_install_instruction(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        real_import = __import__

        def fake_import(name: str, *args: object, **kwargs: object) -> object:
            if name == "presentation.tui.app":
                raise ImportError("textual missing")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            with pytest.raises(SystemExit) as exc_info:
                _cmd_tui("my_story")

        assert exc_info.value.code == 1
        assert capsys.readouterr().err == (
            "textual is not installed. Install it with:\n"
            "  pip install 'textual>=6.0,<7.0'\n\n"
        )


class TestCmdRun:
    def test_run_without_batch_prints_headless_notice(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with patch(
            "presentation.orchestrator.run_pipeline",
            new_callable=AsyncMock,
            return_value=SimpleNamespace(status="complete"),
        ):
            _cmd_run("my_story", batch=False)

        captured = capsys.readouterr()
        assert "story-writer run is always headless" in captured.out

    def test_run_with_batch_does_not_print_headless_notice(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with patch(
            "presentation.orchestrator.run_pipeline",
            new_callable=AsyncMock,
            return_value=SimpleNamespace(status="complete"),
        ):
            _cmd_run("my_story", batch=True)

        captured = capsys.readouterr()
        assert "headless" not in captured.out.lower()


class TestPromptPointer:
    def test_apply_prompt_writes_pointer_to_state_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stories_dir = tmp_path / "stories"
        story_root = stories_dir / "my-story"
        story_root.mkdir(parents=True, exist_ok=True)
        (story_root / "state.json").write_text("{}\n", encoding="utf-8")
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("Prompt body", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        with (
            patch("tools._io.STORIES_DIR", stories_dir),
            patch("src.tools._io.STORIES_DIR", stories_dir),
        ):
            _apply_prompt("my-story", str(prompt_file))

        state = json.loads((story_root / "state.json").read_text(encoding="utf-8"))
        assert state["story_prompt"] == {"$ref": "prompt.md"}
        assert (story_root / "prompt.md").read_text(encoding="utf-8") == "Prompt body"

    def test_apply_prompt_creates_prompt_md(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stories_dir = tmp_path / "stories"
        story_root = stories_dir / "my-story"
        story_root.mkdir(parents=True, exist_ok=True)
        (story_root / "state.json").write_text("{}\n", encoding="utf-8")
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("Prompt body", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        with (
            patch("tools._io.STORIES_DIR", stories_dir),
            patch("src.tools._io.STORIES_DIR", stories_dir),
        ):
            _apply_prompt("my-story", str(prompt_file))

        prompt_md = story_root / "prompt.md"
        assert prompt_md.exists()
        assert prompt_md.read_text(encoding="utf-8") == "Prompt body"

    def test_load_story_prompt_resolves_pointer(self, tmp_path: Path) -> None:
        story_root = tmp_path / "my-story"
        story_root.mkdir(parents=True, exist_ok=True)
        (story_root / "prompt.md").write_text("Once upon a time", encoding="utf-8")
        (story_root / "state.json").write_text(
            json.dumps({"story_prompt": {"$ref": "prompt.md"}}),
            encoding="utf-8",
        )

        assert _load_story_prompt("my-story", story_root) == "Once upon a time"

    def test_load_story_prompt_legacy_inline_string(self, tmp_path: Path) -> None:
        story_root = tmp_path / "my-story"
        story_root.mkdir(parents=True, exist_ok=True)
        (story_root / "state.json").write_text(
            json.dumps({"story_prompt": "Inline prompt text"}),
            encoding="utf-8",
        )

        assert _load_story_prompt("my-story", story_root) == "Inline prompt text"
