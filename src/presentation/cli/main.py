"""CLI entry point for story-writer."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
_src_dir = _project_root / "src"

if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))


def _apply_prompt(story: str, prompt_path: str) -> None:
    """Read a prompt file, initialise the story if needed, and write the prompt to state."""
    from tools._io import STORIES_DIR
    from tools._persist import persist_markdown
    from tools.story_state import cmd_init, cmd_write

    prompt_file = Path(prompt_path)
    if not prompt_file.exists():
        print(f"Error: prompt file not found: {prompt_path}", file=sys.stderr)
        raise SystemExit(1)

    story_text = prompt_file.read_text(encoding="utf-8")
    story_dir = Path("stories") / story

    # Auto-init if the story does not yet exist
    if not (story_dir / "state.json").exists():
        try:
            cmd_init(story)
        except SystemExit:
            # If init failed for a reason other than "already exists", re-raise
            if (story_dir / "state.json").exists():
                pass
            else:
                raise

    story_root = STORIES_DIR / story
    pointer = persist_markdown(story_root, "prompt.md", story_text)
    cmd_write(story, "story_prompt", json.dumps(pointer))


def _cmd_tui(
    story: str,
    *,
    resume: bool = False,
    savepoint: str | None = None,
    prompt: str | None = None,
) -> None:
    if prompt:
        _apply_prompt(story, prompt)

    # Auto-resume when a pipeline savepoint already exists, so users don't
    # accidentally restart from scratch and lose progress.
    state_path = Path("stories") / story / "savepoints" / "pipeline_state.json"
    if not resume and state_path.exists():
        resume = True
        print(
            "[story-writer] Found existing pipeline state — resuming.",
            file=sys.stderr,
        )

    try:
        from presentation.tui.app import StoryWriterApp  # type: ignore[import-not-found]
    except ImportError:
        print(
            "textual is not installed. Install it with:\n"
            "  pip install 'textual>=6.0,<7.0'\n",
            file=sys.stderr,
        )
        raise SystemExit(1)

    app = StoryWriterApp(story_name=story, resume=resume, savepoint_name=savepoint)
    app.run()
    # Force-terminate any lingering pipeline worker threads.
    # Python won't exit on its own if non-daemon threads are still running.
    os._exit(0)


def _cmd_run(story: str, *, batch: bool = False, prompt: str | None = None) -> None:
    if prompt:
        _apply_prompt(story, prompt)

    from presentation.orchestrator import run_pipeline
    from presentation.pipeline_primitives import (
        NullApprovalGate,
        TokenStreamBus,
        WikiContextBus,
    )

    if not batch:
        print(
            "Note: story-writer run is always headless. "
            "Interactive approval mode is not yet implemented."
        )
    gate = NullApprovalGate()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    state = asyncio.run(run_pipeline(story, gate, bus, wiki_bus))
    print(f"Pipeline complete: status={state.status}")


def _cmd_resume(story: str, savepoint: str | None, prompt: str | None = None) -> None:
    if prompt:
        _apply_prompt(story, prompt)

    from presentation.orchestrator import resume_pipeline
    from presentation.pipeline_primitives import (
        NullApprovalGate,
        TokenStreamBus,
        WikiContextBus,
    )

    gate = NullApprovalGate()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    state = asyncio.run(resume_pipeline(story, savepoint, gate, bus, wiki_bus))
    print(f"Pipeline resumed: status={state.status}")


def _cmd_rag_reconcile(args: argparse.Namespace) -> None:
    from tools._io import STORIES_DIR, _validate_story_name
    from tools.rag_reconcile import format_reports, reconcile_story

    if not args.all and not args.story:
        print("Error: --story or --all is required", file=sys.stderr)
        raise SystemExit(2)

    chromadb_dir = os.environ.get(
        "CHROMADB_DIR",
        str(Path(__file__).resolve().parents[3] / ".chromadb"),
    )

    stories: list[str] = []
    if args.all:
        stories = [d.name for d in sorted(STORIES_DIR.iterdir()) if d.is_dir()]
    else:
        stories = [_validate_story_name(args.story).name]

    all_ok = True
    for story_name in stories:
        try:
            reports = reconcile_story(
                story_name=story_name,
                collection_filter=args.collection,
                dry_run=args.dry_run,
                chromadb_dir=chromadb_dir,
            )
            if getattr(args, "output_json", False):
                out = {
                    "story": story_name,
                    **{
                        key: {
                            "added": value.added,
                            "updated": value.updated,
                            "deleted": value.deleted,
                            "unchanged": value.unchanged,
                            "log": value.log,
                        }
                        for key, value in reports.items()
                    },
                }
                print(json.dumps(out, indent=2))
            else:
                print(format_reports(story_name, reports))
        except Exception as exc:
            print(f"Error reconciling {story_name}: {exc}", file=sys.stderr)
            all_ok = False

    if not all_ok:
        raise SystemExit(1)


def main() -> None:
    from presentation.cli.argument_parser import build_parser

    parser = build_parser()
    args = parser.parse_args()

    if args.subcommand == "tui":
        if getattr(args, "savepoint", None) and not args.resume:
            parser.error("--savepoint requires --resume")
        _cmd_tui(
            args.story,
            resume=args.resume,
            savepoint=args.savepoint,
            prompt=args.prompt,
        )
    elif args.subcommand == "run":
        _cmd_run(args.story, batch=args.batch, prompt=args.prompt)
    elif args.subcommand == "resume":
        _cmd_resume(args.story, args.savepoint, prompt=args.prompt)
    elif args.subcommand == "rag":
        if args.rag_subcommand == "reconcile":
            _cmd_rag_reconcile(args)
        else:
            parser.print_help()
            raise SystemExit(1)
    else:
        parser.print_help()
        raise SystemExit(1)


if __name__ == "__main__":
    main()
