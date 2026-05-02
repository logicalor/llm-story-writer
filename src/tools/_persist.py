"""Markdown persistence helpers for the pointer-based storage convention."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src = str(Path(__file__).resolve().parents[1])
if _src not in sys.path:
    sys.path.insert(0, _src)

from tools._io import _atomic_write  # noqa: E402


def _validate_relative_path(relative_path: str) -> Path:
    path = Path(relative_path)
    if path.is_absolute():
        raise ValueError("relative_path must not be absolute")
    if ".." in path.parts:
        raise ValueError("relative_path must not contain '..'")
    return path


def persist_markdown(story_root: Path, relative_path: str, body: str) -> dict[str, str]:
    _validate_relative_path(relative_path)
    target_path = story_root / relative_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(target_path, body)
    return {"$ref": relative_path}


def read_markdown_ref(story_root: Path, ref: dict[str, str] | str) -> str:
    if isinstance(ref, str):
        return ref
    if not isinstance(ref, dict):
        raise TypeError("ref must be a dict with '$ref' or a string")

    relative_path = ref.get("$ref")
    if not isinstance(relative_path, str):
        raise ValueError("ref dict must contain a string '$ref'")

    _validate_relative_path(relative_path)
    return (story_root / relative_path).read_text(encoding="utf-8")
