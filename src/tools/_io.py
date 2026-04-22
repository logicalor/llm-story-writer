"""Shared I/O utilities for tool scripts."""

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STORIES_DIR = Path(os.environ.get("STORIES_DIR", str(PROJECT_ROOT / "stories")))


def _slugify_story_name(name: str) -> str:
    """Normalize a story name to kebab-case for use as a directory name."""
    slug = name.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)   # strip special chars except spaces/hyphens
    slug = re.sub(r"[\s_]+", "-", slug)    # spaces/underscores → hyphens
    slug = re.sub(r"-+", "-", slug)         # collapse consecutive hyphens
    slug = slug.strip("-")
    return slug


def _validate_story_name(name: str) -> Path:
    """Validate and normalize story name to kebab-case directory path."""
    # Reject traversal sequences before normalization
    if ".." in name:
        print(
            f"Error: story name escapes stories directory: {name}",
            file=sys.stderr,
        )
        sys.exit(1)
    name = _slugify_story_name(name)
    if not name:
        print(
            "Error: story name is empty or contains only special characters",
            file=sys.stderr,
        )
        sys.exit(1)
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
