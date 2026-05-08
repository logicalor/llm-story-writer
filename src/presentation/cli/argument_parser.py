"""Argument parser for the story-writer CLI."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="story-writer",
        description="AI-powered long-form story generation system.",
    )
    sub = parser.add_subparsers(dest="subcommand", metavar="<subcommand>")
    sub.required = True

    tui_p = sub.add_parser("tui", help="Launch the interactive Textual TUI.")
    tui_p.add_argument("--story", required=True, metavar="NAME", help="Story name.")
    tui_p.add_argument(
        "--prompt",
        default=None,
        metavar="PATH",
        help="Path to a prompt file (.txt or .md). If the story does not exist it is auto-initialised and the prompt is written to story state.",
    )
    tui_p.add_argument(
        "--resume",
        action="store_true",
        default=False,
        help="Resume pipeline from the latest savepoint.",
    )
    tui_p.add_argument(
        "--savepoint",
        default=None,
        metavar="NAME",
        help="Savepoint name to validate. Resume always continues from the latest savepoint; this argument only verifies the story reached at least the specified phase.",
    )
    tui_p.add_argument(
        "--debug-log",
        default=None,
        metavar="PATH",
        help="Write a JSONL debug log of every LLM request and response to PATH.",
    )
    tui_p.add_argument(
        "--auto-approve",
        action="store_true",
        default=False,
        help="Automatically approve outline and chapter gates without waiting for user input.",
    )

    run_p = sub.add_parser("run", help="Run the full pipeline headlessly.")
    run_p.add_argument("--story", required=True, metavar="NAME", help="Story name.")
    run_p.add_argument(
        "--prompt",
        default=None,
        metavar="PATH",
        help="Path to a prompt file (.txt or .md). If the story does not exist it is auto-initialised and the prompt is written to story state.",
    )
    run_p.add_argument(
        "--batch",
        action="store_true",
        help="Run headlessly (non-interactive). NOTE: story-writer run is always headless; this flag is reserved for future interactive mode.",
    )
    run_p.add_argument(
        "--debug-log",
        default=None,
        metavar="PATH",
        help="Write a JSONL debug log of every LLM request and response to PATH.",
    )

    resume_p = sub.add_parser("resume", help="Resume from latest savepoint.")
    resume_p.add_argument("--story", required=True, metavar="NAME", help="Story name.")
    resume_p.add_argument(
        "--prompt",
        default=None,
        metavar="PATH",
        help="Path to a prompt file (.txt or .md). Overwrites the existing story prompt in state.",
    )
    resume_p.add_argument(
        "--savepoint",
        default=None,
        metavar="NAME",
        help="Savepoint name to validate. Resume always continues from the latest savepoint; this argument only verifies the story reached at least the specified phase.",
    )
    resume_p.add_argument(
        "--debug-log",
        default=None,
        metavar="PATH",
        help="Write a JSONL debug log of every LLM request and response to PATH.",
    )

    reset_recaps_p = sub.add_parser(
        "reset-recaps",
        help="Drop and recreate the ChromaDB recap collection for a story.",
    )
    reset_recaps_p.add_argument(
        "--story", required=True, metavar="NAME", help="Story name."
    )

    return parser
