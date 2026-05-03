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

    rag_p = sub.add_parser("rag", help="RAG index management commands.")
    rag_sub = rag_p.add_subparsers(dest="rag_subcommand", metavar="<rag-subcommand>")
    rag_sub.required = True

    reconcile_p = rag_sub.add_parser(
        "reconcile",
        help="Reconcile ChromaDB collections against on-disk markdown sources.",
    )
    reconcile_p.add_argument(
        "--story",
        metavar="NAME",
        help="Story name to reconcile. Required unless --all is set.",
    )
    reconcile_p.add_argument(
        "--collection",
        choices=["wiki", "stories"],
        default=None,
        metavar="COLLECTION",
        help="Collection to reconcile: 'wiki' or 'stories' (default: both).",
    )
    reconcile_p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without writing to ChromaDB.",
    )
    reconcile_p.add_argument(
        "--all",
        action="store_true",
        help="Reconcile all stories under stories/.",
    )
    reconcile_p.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output results as JSON.",
    )

    return parser
