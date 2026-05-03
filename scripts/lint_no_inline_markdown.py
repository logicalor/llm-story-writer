"""Lint story JSON files for bulky inline markdown content."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ALLOWLIST_FIELDS: frozenset[str] = frozenset(
    {
        "story_name",
        "title",
        "genre",
        "tags",
        "savepoint_id",
        "story_direction",
        "story_context",
    }
)

HEADING_RE = re.compile(r"(?m)^#{1,6} ")


def _violations_for_string(value: str) -> list[str]:
    reasons: list[str] = []
    if "\n\n" in value:
        reasons.append("contains paragraph break")
    if HEADING_RE.search(value):
        reasons.append("contains markdown heading")
    if "```" in value:
        reasons.append("contains fenced code block marker")
    if len(value) > 500:
        reasons.append("length > 500")
    return reasons


def _walk(
    value: Any,
    *,
    key_path: str,
    field_name: str | None,
    issues: list[str],
    file_path: Path,
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{key_path}.{key}" if key_path else key
            _walk(
                child,
                key_path=child_path,
                field_name=key,
                issues=issues,
                file_path=file_path,
            )
        return

    if isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{key_path}[{index}]"
            _walk(
                child,
                key_path=child_path,
                field_name=field_name,
                issues=issues,
                file_path=file_path,
            )
        return

    if isinstance(value, str) and field_name not in ALLOWLIST_FIELDS:
        reasons = _violations_for_string(value)
        if reasons:
            issues.append(f"{file_path}::{key_path}: {', '.join(reasons)}")


def lint_file(file_path: Path) -> list[str]:
    issues: list[str] = []
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{file_path}::<root>: invalid JSON ({exc})"]

    _walk(data, key_path="", field_name=None, issues=issues, file_path=file_path)
    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stories-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "stories",
        help="Root directory containing story folders",
    )
    args = parser.parse_args()

    stories_dir = args.stories_dir
    issues: list[str] = []
    for json_path in sorted(stories_dir.rglob("*.json")):
        issues.extend(lint_file(json_path))

    for issue in issues:
        print(issue)

    raise SystemExit(1 if issues else 0)


if __name__ == "__main__":
    main()
