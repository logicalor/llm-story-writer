"""Integration tests for outline_generator expand-to-scenes savepoint flow."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import tools._io as tool_io
import tools.outline_generator as og


SCENE_TEMPLATE = {
    "title": "Scene Title",
    "description": "A pivotal story beat unfolds.",
    "characters": ["Character 1"],
    "setting": "Observation deck",
    "conflict": "Conflicting goals collide.",
    "tone": "tense",
    "key_events": ["Event 1"],
    "dialogue": "sample dialogue",
    "ending": "A new complication emerges.",
    "lead_in_to_next_scene": "Pressure carries into the next scene.",
    "literary_devices": "Foreshadowing",
}


def _make_scene(index: int) -> dict[str, object]:
    return {
        **SCENE_TEMPLATE,
        "title": f"Scene {index}",
        "description": f"Scene {index} description.",
        "characters": [f"Character {index}"],
        "setting": f"Location {index}",
        "conflict": f"Conflict {index}",
        "key_events": [f"Event {index}"],
        "dialogue": f"Dialogue {index}",
        "ending": f"Ending {index}",
        "lead_in_to_next_scene": f"Lead in {index}",
        "literary_devices": f"Device {index}",
    }


def _write_savepoint(
    stories_dir: Path, story_name: str, step_name: str, data: str
) -> None:
    savepoint_dir = stories_dir / story_name / "savepoints"
    if "/" in step_name:
        parts = step_name.split("/")
        filename = parts[-1]
        target_dir = savepoint_dir.joinpath(*parts[:-1])
        target_dir.mkdir(parents=True, exist_ok=True)
        filepath = target_dir / f"{filename}.md"
    else:
        filepath = savepoint_dir / f"{step_name}.md"
    filepath.write_text(f"# Savepoint: {step_name}\n\n{data}", encoding="utf-8")


@pytest.fixture()
def patched_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str]:
    stories_dir = tmp_path / "stories"
    story_name = "test-story"
    (stories_dir / story_name / "savepoints").mkdir(parents=True)

    monkeypatch.setattr(og, "STORIES_DIR", stories_dir)
    monkeypatch.setattr(tool_io, "STORIES_DIR", stories_dir)
    monkeypatch.setattr(og, "_load_prompt", lambda *_a, **_kw: "mock prompt text")

    return stories_dir, story_name


def test_phase7a_expand_to_scenes_writes_valid_savepoints(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two chapter scene-expansion runs persist bounded validated scene lists."""
    stories_dir, name = patched_env
    chapter_1_scenes = [_make_scene(index) for index in range(1, 11)]
    chapter_2_scenes = [_make_scene(index) for index in range(1, 10)]
    responses = [json.dumps(chapter_1_scenes), json.dumps(chapter_2_scenes)]

    _write_savepoint(stories_dir, name, "story_elements", "Story elements content")
    _write_savepoint(stories_dir, name, "base_context", "Base context content")

    def fake_call_llm(*_args: object, **_kwargs: object) -> str:
        assert responses
        return responses.pop(0)

    monkeypatch.setattr(og, "_call_llm", fake_call_llm)

    og.cmd_expand_to_scenes(
        name,
        1,
        "Chapter 1 synopsis",
        8,
        16,
        next_chapter_synopsis="Chapter 2 synopsis",
        model="test-model",
    )
    og.cmd_expand_to_scenes(
        name,
        2,
        "Chapter 2 synopsis",
        8,
        16,
        previous_recap="Chapter 1 recap",
        next_chapter_synopsis="Chapter 3 synopsis",
        model="test-model",
    )

    repo = og._make_repo(name)
    saved_chapter_1 = og._load_savepoint(repo, "chapter_1/scene_definitions")
    saved_chapter_2 = og._load_savepoint(repo, "chapter_2/scene_definitions")

    assert isinstance(saved_chapter_1, str)
    assert isinstance(saved_chapter_2, str)

    chapter_1_data = json.loads(saved_chapter_1)
    chapter_2_data = json.loads(saved_chapter_2)

    assert len(chapter_1_data) == 10
    assert len(chapter_2_data) == 9
    assert 8 <= len(chapter_1_data) <= 16
    assert 8 <= len(chapter_2_data) <= 16
    assert all(set(SCENE_TEMPLATE) <= set(scene) for scene in chapter_1_data)
    assert all(set(SCENE_TEMPLATE) <= set(scene) for scene in chapter_2_data)
