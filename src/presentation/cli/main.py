"""CLI entry point for story-writer."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
_src_dir = _project_root / "src"

if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))


def _cmd_tui(story: str) -> None:
    try:
        from presentation.tui.app import StoryWriterApp  # type: ignore[import-not-found]
    except ImportError:
        print(
            "textual is not installed. Install it with:\n"
            "  pip install 'textual>=0.85.0,<1.0.0'\n",
            file=sys.stderr,
        )
        raise SystemExit(1)

    app = StoryWriterApp(story_name=story)
    app.run()


def _cmd_run(story: str, *, batch: bool = False) -> None:
    from presentation.orchestrator import run_pipeline
    from presentation.pipeline_primitives import (
        NullApprovalGate,
        TokenStreamBus,
        WikiContextBus,
    )

    _ = batch
    gate = NullApprovalGate()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    state = asyncio.run(run_pipeline(story, gate, bus, wiki_bus))
    print(f"Pipeline complete: status={state.status}")


def _cmd_resume(story: str, savepoint: str | None) -> None:
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


def main() -> None:
    from presentation.cli.argument_parser import build_parser

    parser = build_parser()
    args = parser.parse_args()

    if args.subcommand == "tui":
        _cmd_tui(args.story)
    elif args.subcommand == "run":
        _cmd_run(args.story, batch=args.batch)
    elif args.subcommand == "resume":
        _cmd_resume(args.story, args.savepoint)
    else:
        parser.print_help()
        raise SystemExit(1)


if __name__ == "__main__":
    main()
