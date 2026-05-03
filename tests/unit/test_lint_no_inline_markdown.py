from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "lint_no_inline_markdown.py"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_lint_no_inline_markdown_reports_violation(tmp_path: Path) -> None:
    stories_dir = tmp_path / "stories"
    _write_json(
        stories_dir / "story-a" / "state.json",
        {"story_prompt": "# Heading\n\nLong enough to flag."},
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--stories-dir", str(stories_dir)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "story_prompt" in result.stdout
    assert "contains markdown heading" in result.stdout


def test_lint_no_inline_markdown_skips_allowlisted_fields(tmp_path: Path) -> None:
    stories_dir = tmp_path / "stories"
    _write_json(
        stories_dir / "story-a" / "state.json",
        {"story_context": "# Context\n\nAllowed here."},
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--stories-dir", str(stories_dir)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout == ""


def test_lint_no_inline_markdown_uses_parent_field_for_list_items(
    tmp_path: Path,
) -> None:
    stories_dir = tmp_path / "stories"
    _write_json(
        stories_dir / "story-a" / "metadata.json",
        {"chapters": ["# Heading\n\nBody"]},
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--stories-dir", str(stories_dir)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "chapters[0]" in result.stdout
