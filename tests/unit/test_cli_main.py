"""Verification tests for Issue #162 - CLI entry points."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.presentation.cli.argument_parser import build_parser  # noqa: E402
from src.presentation.cli.main import main  # noqa: E402


class TestBuildParser:
    def test_tui_subcommand_parses_story_name(self) -> None:
        parser = build_parser()

        args = parser.parse_args(["tui", "--story", "my_story"])

        assert args.subcommand == "tui"
        assert args.story == "my_story"

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

        mock_cmd_run.assert_called_once_with("my_story", batch=False)

    def test_tui_dispatches_cmd_tui(self) -> None:
        original_argv = sys.argv[:]

        try:
            sys.argv = ["story-writer", "tui", "--story", "my_story"]
            with patch("src.presentation.cli.main._cmd_tui") as mock_cmd_tui:
                main()
        finally:
            sys.argv = original_argv

        mock_cmd_tui.assert_called_once_with("my_story")

    def test_resume_dispatches_cmd_resume(self) -> None:
        original_argv = sys.argv[:]

        try:
            sys.argv = ["story-writer", "resume", "--story", "my_story"]
            with patch("src.presentation.cli.main._cmd_resume") as mock_cmd_resume:
                main()
        finally:
            sys.argv = original_argv

        mock_cmd_resume.assert_called_once_with("my_story", None)
