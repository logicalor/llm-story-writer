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

    run_p = sub.add_parser("run", help="Run the full pipeline headlessly.")
    run_p.add_argument("--story", required=True, metavar="NAME", help="Story name.")
    run_p.add_argument(
        "--batch",
        action="store_true",
        help="Run headlessly (non-interactive). NOTE: story-writer run is always headless; this flag is reserved for future interactive mode.",
    )

    resume_p = sub.add_parser("resume", help="Resume from latest savepoint.")
    resume_p.add_argument("--story", required=True, metavar="NAME", help="Story name.")
    resume_p.add_argument(
        "--savepoint",
        default=None,
        metavar="NAME",
        help="Savepoint name to validate. Resume always continues from the latest savepoint; this argument only verifies the story reached at least the specified phase.",
    )

    return parser
