"""Shared I/O utilities for tool scripts."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STORIES_DIR = Path(os.environ.get("STORIES_DIR", str(PROJECT_ROOT / "stories")))


def _validate_story_name(name: str) -> Path:
    """Validate story name does not escape the stories directory."""
    story_dir = (STORIES_DIR / name).resolve()
    if not story_dir.is_relative_to(STORIES_DIR.resolve()):
        print(
            f"Error: story name escapes stories directory: {name}",
            file=sys.stderr,
        )
        sys.exit(1)
    return story_dir


def _atomic_write(path: Path, content: str) -> None:
    """Write content atomically using tempfile + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    fd_closed = False
    try:
        os.write(fd, content.encode())
        os.close(fd)
        fd_closed = True
        os.replace(tmp, str(path))
    except BaseException:
        if not fd_closed:
            os.close(fd)
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
