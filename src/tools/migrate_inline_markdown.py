"""One-shot migration: move legacy inline markdown/text out of story JSON files.

Usage::

    python3 src/tools/migrate_inline_markdown.py --name <story>
    python3 src/tools/migrate_inline_markdown.py --all
    python3 src/tools/migrate_inline_markdown.py --name <story> --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_path = str(PROJECT_ROOT / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.tools._io import STORIES_DIR, _atomic_write, _validate_story_name  # noqa: E402


FENCED_JSON_RE = re.compile(r"```json\s*(.*?)```", re.DOTALL)


def _is_ref(value: object) -> bool:
    return isinstance(value, dict) and isinstance(value.get("$ref"), str)


def _dump_json(data: object) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _write_json(path: Path, data: object, *, dry_run: bool) -> None:
    if dry_run:
        return
    _atomic_write(path, _dump_json(data))


def _write_text(path: Path, content: str, *, dry_run: bool) -> None:
    if dry_run:
        return
    _atomic_write(path, content)


def _backup_path(path: Path) -> Path:
    return Path(f"{path}.premigrate")


def _ensure_backup(path: Path, original_text: str, *, dry_run: bool) -> None:
    backup_path = _backup_path(path)
    if dry_run or backup_path.exists():
        return
    _atomic_write(backup_path, original_text)


class StoryMigration:
    def __init__(self, story_dir: Path, *, dry_run: bool) -> None:
        self.story_dir = story_dir
        self.dry_run = dry_run
        self.fields_migrated = 0
        self.actions: list[str] = []

    def _record(self, message: str) -> None:
        self.actions.append(message)

    def _migrate_ref_field(
        self,
        container: dict[str, Any],
        key: str,
        relative_path: str,
        *,
        json_mode: bool = False,
        value: object | None = None,
    ) -> bool:
        current = container.get(key) if value is None else value
        if _is_ref(current) or not isinstance(current, str):
            return False
        target_path = self.story_dir / relative_path
        if json_mode:
            parsed = json.loads(current)
            _write_json(target_path, parsed, dry_run=self.dry_run)
        else:
            _write_text(target_path, current, dry_run=self.dry_run)
        container[key] = {"$ref": relative_path}
        self.fields_migrated += 1
        self._record(f"[{self.story_dir.name}] migrate {key} -> {relative_path}")
        return True

    def _migrate_state_json(self) -> None:
        state_path = self.story_dir / "state.json"
        if not state_path.exists():
            return
        original_text = state_path.read_text(encoding="utf-8")
        data = json.loads(original_text)
        if not isinstance(data, dict):
            return

        changed = self._migrate_ref_field(data, "story_prompt", "prompt.md")
        if changed:
            _ensure_backup(state_path, original_text, dry_run=self.dry_run)
            _write_json(state_path, data, dry_run=self.dry_run)

    def _migrate_outline_summary(self, chapter: dict[str, Any], index: int) -> bool:
        summary = chapter.get("summary")
        if _is_ref(summary) or not isinstance(summary, str):
            return False
        relative_path = f"outline/chapter_{index}_summary.md"
        _write_text(self.story_dir / relative_path, summary, dry_run=self.dry_run)
        chapter["summary"] = {"$ref": relative_path}
        self.fields_migrated += 1
        self._record(
            f"[{self.story_dir.name}] migrate outline_result.chapter_outlines[{index - 1}].summary -> {relative_path}"
        )
        return True

    def _migrate_enrichment_suggestions(self, outline_result: dict[str, Any]) -> bool:
        value = outline_result.get("enrichment_suggestions")
        if _is_ref(value) or not isinstance(value, str) or not value.strip():
            return False

        match = FENCED_JSON_RE.search(value)
        relative_path: str
        if match:
            parsed = json.loads(match.group(1).strip())
            relative_path = "outline/enrichment_suggestions.json"
            _write_json(self.story_dir / relative_path, parsed, dry_run=self.dry_run)
        else:
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                relative_path = "outline/enrichment_suggestions.txt"
                _write_text(self.story_dir / relative_path, value, dry_run=self.dry_run)
            else:
                relative_path = "outline/enrichment_suggestions.json"
                _write_json(
                    self.story_dir / relative_path, parsed, dry_run=self.dry_run
                )

        outline_result["enrichment_suggestions"] = {"$ref": relative_path}
        self.fields_migrated += 1
        self._record(
            f"[{self.story_dir.name}] migrate outline_result.enrichment_suggestions -> {relative_path}"
        )
        return True

    def _migrate_recap_dict(self, recaps: dict[str, Any]) -> bool:
        changed = False
        for chapter_key, recap_data in recaps.items():
            chapter_dir = f"chapters/chapter_{chapter_key}"
            if isinstance(recap_data, str):
                relative_path = f"{chapter_dir}/recap_events.md"
                _write_text(
                    self.story_dir / relative_path, recap_data, dry_run=self.dry_run
                )
                recaps[chapter_key] = {"events": {"$ref": relative_path}}
                self.fields_migrated += 1
                self._record(
                    f"[{self.story_dir.name}] migrate recaps.{chapter_key} -> {relative_path}"
                )
                changed = True
                continue
            if not isinstance(recap_data, dict):
                continue
            if all(
                _is_ref(value) for value in recap_data.values() if value is not None
            ):
                continue
            for field_name in ("events", "compact", "sanitised"):
                field_value = recap_data.get(field_name)
                if (
                    _is_ref(field_value)
                    or not isinstance(field_value, str)
                    or not field_value
                ):
                    continue
                relative_path = f"{chapter_dir}/recap_{field_name}.md"
                _write_text(
                    self.story_dir / relative_path,
                    field_value,
                    dry_run=self.dry_run,
                )
                recap_data[field_name] = {"$ref": relative_path}
                self.fields_migrated += 1
                self._record(
                    f"[{self.story_dir.name}] migrate recaps.{chapter_key}.{field_name} -> {relative_path}"
                )
                changed = True
        return changed

    def _migrate_entity_jsons(self, folder_name: str) -> None:
        entity_dir = self.story_dir / folder_name
        if not entity_dir.exists():
            return

        for json_path in sorted(entity_dir.glob("*.json")):
            original_text = json_path.read_text(encoding="utf-8")
            data = json.loads(original_text)
            if not isinstance(data, dict):
                continue

            slug = json_path.stem
            changed = False
            for field_name in ("sheet", "summary", "abridged"):
                current = data.get(field_name)
                if _is_ref(current) or not isinstance(current, str):
                    continue
                relative_path = f"{folder_name}/{slug}/{field_name}.md"
                _write_text(
                    self.story_dir / relative_path, current, dry_run=self.dry_run
                )
                data[field_name] = {"$ref": relative_path}
                self.fields_migrated += 1
                self._record(
                    f"[{self.story_dir.name}] migrate {folder_name}/{slug}.json::{field_name} -> {relative_path}"
                )
                changed = True

            chunks = data.get("chunks")
            if isinstance(chunks, dict):
                for chunk_key, chunk_value in chunks.items():
                    if _is_ref(chunk_value) or not isinstance(chunk_value, str):
                        continue
                    relative_path = f"{folder_name}/{slug}/chunks/{chunk_key}.md"
                    _write_text(
                        self.story_dir / relative_path,
                        chunk_value,
                        dry_run=self.dry_run,
                    )
                    chunks[chunk_key] = {"$ref": relative_path}
                    self.fields_migrated += 1
                    self._record(
                        f"[{self.story_dir.name}] migrate {folder_name}/{slug}.json::chunks.{chunk_key} -> {relative_path}"
                    )
                    changed = True

            if changed:
                _ensure_backup(json_path, original_text, dry_run=self.dry_run)
                _write_json(json_path, data, dry_run=self.dry_run)

    def _migrate_chapter_recaps(self) -> None:
        chapters_dir = self.story_dir / "chapters"
        if not chapters_dir.exists():
            return

        for json_path in sorted(chapters_dir.glob("chapter_*_recap.json")):
            original_text = json_path.read_text(encoding="utf-8")
            data = json.loads(original_text)
            if not isinstance(data, dict):
                continue
            match = re.match(r"chapter_(\d+)_recap\.json$", json_path.name)
            if match is None:
                continue
            chapter_num = match.group(1)
            changed = False
            for field_name in ("events", "compact", "sanitised"):
                field_value = data.get(field_name)
                if _is_ref(field_value) or not isinstance(field_value, str):
                    continue
                relative_path = f"chapters/chapter_{chapter_num}/recap_{field_name}.md"
                _write_text(
                    self.story_dir / relative_path, field_value, dry_run=self.dry_run
                )
                data[field_name] = {"$ref": relative_path}
                self.fields_migrated += 1
                self._record(
                    f"[{self.story_dir.name}] migrate {json_path.name}::{field_name} -> {relative_path}"
                )
                changed = True
            if changed:
                _ensure_backup(json_path, original_text, dry_run=self.dry_run)
                _write_json(json_path, data, dry_run=self.dry_run)

    def _migrate_pipeline_state(self) -> None:
        pipeline_state_path = self.story_dir / "savepoints" / "pipeline_state.json"
        if not pipeline_state_path.exists():
            return
        original_text = pipeline_state_path.read_text(encoding="utf-8")
        data = json.loads(original_text)
        if not isinstance(data, dict):
            return

        changed = False
        outline_result = data.get("outline_result")
        if isinstance(outline_result, dict):
            chapter_outlines = outline_result.get("chapter_outlines")
            if isinstance(chapter_outlines, list):
                for index, chapter in enumerate(chapter_outlines, start=1):
                    if isinstance(chapter, dict):
                        changed = (
                            self._migrate_outline_summary(chapter, index) or changed
                        )
            changed = self._migrate_enrichment_suggestions(outline_result) or changed

        recaps = data.get("recaps")
        if isinstance(recaps, dict):
            changed = self._migrate_recap_dict(recaps) or changed

        if changed:
            _ensure_backup(pipeline_state_path, original_text, dry_run=self.dry_run)
            _write_json(pipeline_state_path, data, dry_run=self.dry_run)

    def run(self) -> None:
        self._migrate_state_json()
        self._migrate_pipeline_state()
        self._migrate_entity_jsons("characters")
        self._migrate_entity_jsons("settings")
        self._migrate_chapter_recaps()


def _iter_story_dirs() -> list[Path]:
    if not STORIES_DIR.exists():
        return []
    return sorted(path for path in STORIES_DIR.iterdir() if path.is_dir())


def migrate_story(story_dir: Path, *, dry_run: bool = False) -> int:
    migration = StoryMigration(story_dir, dry_run=dry_run)
    migration.run()
    for action in migration.actions:
        print(action)
    print(f"[{story_dir.name}] {migration.fields_migrated} fields migrated")
    return migration.fields_migrated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", help="Story name to migrate")
    parser.add_argument("--all", action="store_true", help="Migrate all stories")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes without writing files",
    )
    args = parser.parse_args()

    if args.all == bool(args.name):
        parser.error("Provide exactly one of --name <story> or --all")

    story_dirs = [_validate_story_name(args.name)] if args.name else _iter_story_dirs()
    for story_dir in story_dirs:
        migrate_story(story_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
