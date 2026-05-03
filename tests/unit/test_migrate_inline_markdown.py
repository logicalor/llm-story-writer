from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import src.tools._io as io_module
import tools.migrate_inline_markdown as migrate_inline_markdown


@pytest.fixture()
def story_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    stories_dir = tmp_path / "stories"
    story_root = stories_dir / "test-story"
    (story_root / "savepoints").mkdir(parents=True)
    monkeypatch.setattr(io_module, "STORIES_DIR", stories_dir)
    monkeypatch.setattr(migrate_inline_markdown, "STORIES_DIR", stories_dir)
    return story_root


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_migrate_story_moves_inline_fields(story_dir: Path) -> None:
    _write_json(
        story_dir / "state.json",
        {"story_prompt": "# Prompt\n\nLong prompt body."},
    )
    _write_json(
        story_dir / "savepoints" / "pipeline_state.json",
        {
            "outline_result": {
                "chapter_outlines": [
                    {"summary": "Chapter one summary"},
                    {"summary": {"$ref": "outline/chapter_2_summary.md"}},
                ],
                "enrichment_suggestions": '```json\n{"beats": ["a"]}\n```',
            },
            "recaps": {
                "1": "Event recap",
                "2": {
                    "events": "Detailed events",
                    "compact": "Compact recap",
                    "sanitised": {"$ref": "chapters/chapter_2/recap_sanitised.md"},
                },
            },
        },
    )
    _write_json(
        story_dir / "characters" / "alice.json",
        {
            "sheet": "# Alice\nBody",
            "summary": "Alice summary",
            "abridged": {"$ref": "characters/alice/abridged.md"},
            "chunks": {"skills": "Fast learner"},
        },
    )
    _write_json(
        story_dir / "settings" / "tower.json",
        {
            "sheet": "# Tower\nBody",
            "summary": "Tower summary",
            "abridged": "Tower abridged",
            "chunks": {"history": "Built long ago"},
        },
    )
    _write_json(
        story_dir / "chapters" / "chapter_3_recap.json",
        {
            "events": "Events",
            "compact": {"$ref": "chapters/chapter_3/recap_compact.md"},
            "sanitised": "Sanitised",
        },
    )

    migrated = migrate_inline_markdown.migrate_story(story_dir)

    assert migrated == 15
    state = json.loads((story_dir / "state.json").read_text(encoding="utf-8"))
    assert state["story_prompt"] == {"$ref": "prompt.md"}
    assert (story_dir / "prompt.md").read_text(encoding="utf-8").startswith("# Prompt")
    assert (story_dir / "state.json.premigrate").exists()

    pipeline_state = json.loads(
        (story_dir / "savepoints" / "pipeline_state.json").read_text(encoding="utf-8")
    )
    assert pipeline_state["outline_result"]["chapter_outlines"][0]["summary"] == {
        "$ref": "outline/chapter_1_summary.md"
    }
    enrichment_ref = pipeline_state["outline_result"]["enrichment_suggestions"]["$ref"]
    assert enrichment_ref == "outline/enrichment_suggestions.json"
    enrichment_data = json.loads(
        (story_dir / enrichment_ref).read_text(encoding="utf-8")
    )
    assert enrichment_data == {"beats": ["a"]}
    assert pipeline_state["recaps"]["1"] == {
        "events": {"$ref": "chapters/chapter_1/recap_events.md"}
    }
    assert pipeline_state["recaps"]["2"]["compact"] == {
        "$ref": "chapters/chapter_2/recap_compact.md"
    }

    character_data = json.loads(
        (story_dir / "characters" / "alice.json").read_text(encoding="utf-8")
    )
    assert character_data["sheet"] == {"$ref": "characters/alice/sheet.md"}
    assert character_data["chunks"]["skills"] == {
        "$ref": "characters/alice/chunks/skills.md"
    }

    setting_data = json.loads(
        (story_dir / "settings" / "tower.json").read_text(encoding="utf-8")
    )
    assert setting_data["summary"] == {"$ref": "settings/tower/summary.md"}
    assert setting_data["abridged"] == {"$ref": "settings/tower/abridged.md"}

    chapter_recap = json.loads(
        (story_dir / "chapters" / "chapter_3_recap.json").read_text(encoding="utf-8")
    )
    assert chapter_recap["events"] == {"$ref": "chapters/chapter_3/recap_events.md"}
    assert chapter_recap["sanitised"] == {
        "$ref": "chapters/chapter_3/recap_sanitised.md"
    }


def test_migrate_story_dry_run_writes_nothing(story_dir: Path) -> None:
    _write_json(story_dir / "state.json", {"story_prompt": "Prompt body"})

    migrated = migrate_inline_markdown.migrate_story(story_dir, dry_run=True)

    assert migrated == 1
    state = json.loads((story_dir / "state.json").read_text(encoding="utf-8"))
    assert state["story_prompt"] == "Prompt body"
    assert not (story_dir / "prompt.md").exists()
    assert not (story_dir / "state.json.premigrate").exists()


def test_migrate_story_writes_text_fallback_for_non_json_enrichment(
    story_dir: Path,
) -> None:
    _write_json(
        story_dir / "savepoints" / "pipeline_state.json",
        {
            "outline_result": {
                "chapter_outlines": [],
                "enrichment_suggestions": "plain suggestion text",
            }
        },
    )

    migrated = migrate_inline_markdown.migrate_story(story_dir)

    assert migrated == 1
    pipeline_state = json.loads(
        (story_dir / "savepoints" / "pipeline_state.json").read_text(encoding="utf-8")
    )
    assert pipeline_state["outline_result"]["enrichment_suggestions"] == {
        "$ref": "outline/enrichment_suggestions.txt"
    }
    assert (story_dir / "outline" / "enrichment_suggestions.txt").read_text(
        encoding="utf-8"
    ) == "plain suggestion text"
