"""Unit tests for quality telemetry persistence (issue #419).

Verifies _write_quality_report and the CLI `report` subcommand parser.
No LLM calls are made — pure file-system and argparse logic only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from application.pipeline.handoffs import PipelineState
from presentation.cli.argument_parser import build_parser
from presentation.orchestrator import _write_quality_report

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CHAPTER_ENTRY: dict = {
    "chapter_number": 1,
    "scenes": [
        {
            "final_score": 8,
            "iteration_count": 2,
            "residual_categories": [],
        }
    ],
    "consistency": {
        "passed": True,
        "critical_count": 0,
        "warning_count": 1,
        "final_status": "ok",
    },
}

_CONFIG: dict = {
    "models": {"chapter_writer": "test-model"},
    "generation": {
        "seed": 42,
        "wanted_chapters": 3,
        "min_scene_score": 7,
        "max_critique_iterations": 4,
    },
}


def _make_state(telemetry: list | None = None) -> PipelineState:
    return PipelineState(
        story_name="test-story",
        current_phase="done",
        quality_telemetry=telemetry if telemetry is not None else [_CHAPTER_ENTRY],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_write_quality_report_creates_file(tmp_path: Path) -> None:
    state = _make_state()
    _write_quality_report(state, tmp_path, _CONFIG)

    report_path = tmp_path / "quality_report.json"
    assert report_path.exists(), "quality_report.json was not created"

    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert len(data) == 1


def test_write_quality_report_structure(tmp_path: Path) -> None:
    state = _make_state()
    _write_quality_report(state, tmp_path, _CONFIG)

    data = json.loads((tmp_path / "quality_report.json").read_text(encoding="utf-8"))
    entry = data[0]

    assert "timestamp" in entry
    assert "model" in entry
    assert "settings_snapshot" in entry
    assert "chapters" in entry

    assert entry["model"] == "test-model"

    assert len(entry["chapters"]) == 1
    chapter = entry["chapters"][0]
    assert "chapter_number" in chapter
    assert "scenes" in chapter
    assert "consistency" in chapter


def test_write_quality_report_chapter_scene_fields(tmp_path: Path) -> None:
    state = _make_state()
    _write_quality_report(state, tmp_path, _CONFIG)

    data = json.loads((tmp_path / "quality_report.json").read_text(encoding="utf-8"))
    scene = data[0]["chapters"][0]["scenes"][0]
    assert "final_score" in scene
    assert "iteration_count" in scene
    assert "residual_categories" in scene


def test_write_quality_report_chapter_consistency_fields(tmp_path: Path) -> None:
    state = _make_state()
    _write_quality_report(state, tmp_path, _CONFIG)

    data = json.loads((tmp_path / "quality_report.json").read_text(encoding="utf-8"))
    consistency = data[0]["chapters"][0]["consistency"]
    assert "passed" in consistency
    assert "critical_count" in consistency
    assert "warning_count" in consistency
    assert "final_status" in consistency


def test_write_quality_report_appends(tmp_path: Path) -> None:
    entry_a = dict(_CHAPTER_ENTRY, chapter_number=1)
    entry_b = dict(_CHAPTER_ENTRY, chapter_number=2)

    _write_quality_report(_make_state([entry_a]), tmp_path, _CONFIG)
    _write_quality_report(_make_state([entry_b]), tmp_path, _CONFIG)

    data = json.loads((tmp_path / "quality_report.json").read_text(encoding="utf-8"))
    assert len(data) == 2
    assert data[0]["chapters"][0]["chapter_number"] == 1
    assert data[1]["chapters"][0]["chapter_number"] == 2


def test_write_quality_report_handles_malformed_json(tmp_path: Path) -> None:
    report_path = tmp_path / "quality_report.json"
    report_path.write_text("{not valid json!!!", encoding="utf-8")

    state = _make_state()
    # Must not raise even though the existing file is malformed
    _write_quality_report(state, tmp_path, _CONFIG)

    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) == 1


def test_write_quality_report_settings_snapshot(tmp_path: Path) -> None:
    state = _make_state()
    _write_quality_report(state, tmp_path, _CONFIG)

    data = json.loads((tmp_path / "quality_report.json").read_text(encoding="utf-8"))
    snap = data[0]["settings_snapshot"]
    assert snap.get("seed") == 42
    assert snap.get("wanted_chapters") == 3
    assert snap.get("min_scene_score") == 7
    assert snap.get("max_critique_iterations") == 4


def test_write_quality_report_model_fallback_default(tmp_path: Path) -> None:
    config = {"models": {"default": "fallback-model"}, "generation": {}}
    state = _make_state()
    _write_quality_report(state, tmp_path, config)

    data = json.loads((tmp_path / "quality_report.json").read_text(encoding="utf-8"))
    assert data[0]["model"] == "fallback-model"


def test_write_quality_report_model_unknown_when_missing(tmp_path: Path) -> None:
    config: dict = {}
    state = _make_state()
    _write_quality_report(state, tmp_path, config)

    data = json.loads((tmp_path / "quality_report.json").read_text(encoding="utf-8"))
    assert data[0]["model"] == "unknown"


# ---------------------------------------------------------------------------
# CLI parser tests
# ---------------------------------------------------------------------------


def test_report_subcommand_in_parser() -> None:
    parser = build_parser()
    args = parser.parse_args(["report", "my-story"])
    assert args.subcommand == "report"
    assert args.name == "my-story"
