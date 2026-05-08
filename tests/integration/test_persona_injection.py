from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import tools._io as tool_io
import tools.critique_runner as critique_runner
import tools.outline_generator as og
import tools.persona_builder as pb
import tools.recap_manager as rm
import tools.scene_writer as sw


VALID_PERSONA = """---
genre: Fantasy
subgenre: Gothic
pov: Third person limited
tense: Past
created_at: 2026-05-08T12:00:00Z
---

## Identity
You write haunted stories. You favour intimate framing.

## Prose Texture
You use supple sentences.

## Dialogue Style
You write with restraint.

## Pacing Philosophy
You prefer dramatized scenes.

## Thematic Sensibility
You explore moral pressure.

## Narrative Philosophy
You stay close to character fear.

## Anti-Patterns
- Avoid purple prose.
- Avoid exposition dumps.
"""

LONG_VALID_PERSONA = """---
genre: Fantasy
subgenre: Gothic
pov: Third person limited
tense: Past
created_at: 2026-05-08T12:00:00Z
---

## Identity
You write haunted stories with intimate dread, precise sensory detail, close emotional pressure, and steady attention to choices, wounds, silence, memory, guilt, longing, ritual, omen, shadow, weather, and consequence in every paragraph.

## Prose Texture
You use supple sentences, tactile imagery, controlled rhythm, vivid nouns, restrained metaphor, lucid syntax, and deliberate repetition so each line feels musical, tense, legible, atmospheric, and emotionally exact without turning florid.

## Dialogue Style
You write with restraint, implication, interruption, subtext, hesitation, unfinished admissions, careful cadence, and pointed contrast so spoken language reveals desire, fear, history, class, intimacy, suspicion, and power without blunt explanation.

## Pacing Philosophy
You prefer dramatized scenes, accumulating pressure, incremental revelation, active choices, reactive consequences, and scene endings that bend the next beat forward with urgency, curiosity, dread, and irreversible movement.

## Thematic Sensibility
You explore moral pressure, inheritance, devotion, corruption, sacrifice, secrecy, grief, and the cost of love under strain, always tying abstract themes to concrete behavior, conflict, and image.

## Narrative Philosophy
You stay close to character fear, desire, bias, and misreading so viewpoint remains intimate, fallible, emotionally coherent, and rooted in the body, the room, the moment, and the price of action.

## Anti-Patterns
- Avoid purple prose, empty grandeur, vague abstraction, and decorative language without narrative function.
- Avoid exposition dumps, flat summary, detached explanation, and convenient emotional shortcuts.
"""


def _create_story_dir(
    tmp_path: Path, story_name: str = "test-story"
) -> tuple[Path, str, Path]:
    stories_dir = tmp_path / "stories"
    story_dir = stories_dir / story_name
    story_dir.mkdir(parents=True, exist_ok=True)
    return stories_dir, story_name, story_dir


def _patch_stories_dir(
    monkeypatch: pytest.MonkeyPatch,
    stories_dir: Path,
    *modules: object,
) -> None:
    monkeypatch.setenv("STORIES_DIR", str(stories_dir))
    monkeypatch.setattr(tool_io, "STORIES_DIR", stories_dir)
    for module in modules:
        if hasattr(module, "STORIES_DIR"):
            monkeypatch.setattr(module, "STORIES_DIR", stories_dir)


def _write_savepoint(story_dir: Path, step_name: str, data: str) -> None:
    savepoint_dir = story_dir / "savepoints"
    if "/" in step_name:
        parts = step_name.split("/")
        filename = parts[-1]
        target_dir = savepoint_dir.joinpath(*parts[:-1])
        target_dir.mkdir(parents=True, exist_ok=True)
        filepath = target_dir / f"{filename}.md"
    else:
        savepoint_dir.mkdir(parents=True, exist_ok=True)
        filepath = savepoint_dir / f"{step_name}.md"
    filepath.write_text(f"# Savepoint: {step_name}\n\n{data}", encoding="utf-8")


def _write_required_persona_builder_savepoints(story_dir: Path) -> None:
    _write_savepoint(story_dir, "core_story_foundation", "Foundation content")
    _write_savepoint(story_dir, "tone_style", "Tone content")
    _write_savepoint(story_dir, "theme_message", "Theme content")
    _write_savepoint(story_dir, "story_elements", "Story elements content")


def _write_persona_file(story_dir: Path, content: str = VALID_PERSONA) -> Path:
    persona_dir = story_dir / "persona"
    persona_dir.mkdir(parents=True, exist_ok=True)
    persona_path = persona_dir / "persona.md"
    persona_path.write_text(content, encoding="utf-8")
    return persona_path


class TestPersonaInjection:
    def test_persona_file_exists_after_generate(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stories_dir, story_name, story_dir = _create_story_dir(tmp_path)
        _patch_stories_dir(monkeypatch, stories_dir, pb)
        _write_required_persona_builder_savepoints(story_dir)
        monkeypatch.setattr(pb, "_load_prompt", lambda *_a, **_kw: "prompt text")
        monkeypatch.setattr(pb, "_call_llm", lambda *_a, **_kw: VALID_PERSONA)

        pb.cmd_generate(story_name, word_budget=225)

        persona_path = story_dir / "persona" / "persona.md"
        assert persona_path.exists()
        assert persona_path.read_text(encoding="utf-8").strip()

    def test_persona_word_count_within_budget(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stories_dir, story_name, story_dir = _create_story_dir(tmp_path)
        _patch_stories_dir(monkeypatch, stories_dir, pb)
        _write_required_persona_builder_savepoints(story_dir)
        monkeypatch.setattr(pb, "_load_prompt", lambda *_a, **_kw: "prompt text")
        monkeypatch.setattr(pb, "_call_llm", lambda *_a, **_kw: LONG_VALID_PERSONA)

        pb.cmd_generate(story_name, word_budget=225)

        content = (story_dir / "persona" / "persona.md").read_text(encoding="utf-8")
        word_count = len(content.split())
        assert 180 <= word_count <= 270

    def test_outline_generator_injects_persona_as_system_message(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stories_dir, story_name, story_dir = _create_story_dir(tmp_path)
        _patch_stories_dir(monkeypatch, stories_dir, og)
        _write_savepoint(story_dir, "story_elements", "Story elements content")
        _write_savepoint(story_dir, "base_context", "Base context content")
        _write_persona_file(story_dir)
        monkeypatch.setattr(og, "_load_prompt", lambda *_a, **_kw: "prompt text")

        calls: list[dict[str, object]] = []

        def recording_llm(
            *args: object, system_message: str | None = None, **kwargs: object
        ) -> str:
            calls.append(
                {
                    "args": args,
                    "kwargs": kwargs,
                    "system_message": system_message,
                }
            )
            return "outline text"

        monkeypatch.setattr(og, "_call_llm", recording_llm)
        monkeypatch.setattr(og, "_call_llm_messages", recording_llm)

        og.cmd_expand_chapter(
            story_name,
            1,
            1,
            5,
            phase="chapter",
            persona_view="outline",
        )

        assert any(call["system_message"] is not None for call in calls)
        assert any("## Identity" in str(call["system_message"]) for call in calls)
        assert any("haunted stories" in str(call["system_message"]) for call in calls)

    def test_scene_writer_injects_persona_and_emphasis_delta(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stories_dir, story_name, story_dir = _create_story_dir(tmp_path)
        _patch_stories_dir(monkeypatch, stories_dir, sw)
        _write_persona_file(story_dir)
        monkeypatch.setattr(sw, "_load_prompt", lambda *_a, **_kw: "prompt text")

        calls: list[dict[str, object]] = []

        def recording_llm(
            *args: object, system_message: str | None = None, **kwargs: object
        ) -> str:
            calls.append(
                {
                    "prompt": args[0] if args else "",
                    "kwargs": kwargs,
                    "system_message": system_message,
                }
            )
            return "scene content"

        monkeypatch.setattr(sw, "_call_llm", recording_llm)

        sw.cmd_generate(
            story_name,
            1,
            1,
            "scene def",
            "chapter outline",
            persona_view="chapter",
            emphasis_delta="feel tense",
        )

        assert any(call["system_message"] is not None for call in calls)
        assert any("## Chapter Emphasis" in str(call["prompt"]) for call in calls)
        assert any("feel tense" in str(call["prompt"]) for call in calls)

    def test_recap_manager_no_system_message(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stories_dir, story_name, story_dir = _create_story_dir(tmp_path)
        _patch_stories_dir(monkeypatch, stories_dir)
        _write_savepoint(story_dir, "chapter_1/content", "Chapter 1 text")
        monkeypatch.setattr(rm, "_load_prompt", lambda *_a, **_kw: "prompt text")

        calls: list[dict[str, object]] = []

        def recording_llm(*args: object, **kwargs: object) -> str:
            calls.append(kwargs)
            return "[]"

        monkeypatch.setattr(rm, "_call_llm", recording_llm)
        monkeypatch.setattr(rm, "_extract_json_from_response", lambda *_a, **_kw: "[]")

        rm.cmd_generate(story_name, 1, "2024-01-01")

        assert calls
        assert all("system_message" not in call for call in calls)

    def test_critique_runner_no_system_message(self) -> None:
        parameters = inspect.signature(critique_runner._call_llm_messages).parameters

        assert "system_message" not in parameters

    def test_no_persona_view_no_system_message_injection(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stories_dir, story_name, story_dir = _create_story_dir(tmp_path)
        _patch_stories_dir(monkeypatch, stories_dir, og)
        _write_savepoint(story_dir, "story_elements", "Story elements content")
        _write_savepoint(story_dir, "base_context", "Base context content")
        _write_persona_file(story_dir)
        monkeypatch.setattr(og, "_load_prompt", lambda *_a, **_kw: "prompt text")

        calls: list[dict[str, object]] = []

        def recording_llm(
            *args: object, system_message: str | None = None, **kwargs: object
        ) -> str:
            calls.append(
                {
                    "args": args,
                    "kwargs": kwargs,
                    "system_message": system_message,
                }
            )
            return "outline text"

        monkeypatch.setattr(og, "_call_llm", recording_llm)

        og.cmd_expand_chapter(story_name, 1, 1, 5, phase="chapter")

        assert calls
        assert all(call["system_message"] is None for call in calls)

    def test_no_emphasis_delta_no_delta_in_prompt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stories_dir, story_name, story_dir = _create_story_dir(tmp_path)
        _patch_stories_dir(monkeypatch, stories_dir, sw)
        _write_persona_file(story_dir)
        monkeypatch.setattr(sw, "_load_prompt", lambda *_a, **_kw: "prompt text")

        calls: list[dict[str, object]] = []

        def recording_llm(
            *args: object, system_message: str | None = None, **kwargs: object
        ) -> str:
            calls.append(
                {
                    "prompt": args[0] if args else "",
                    "kwargs": kwargs,
                    "system_message": system_message,
                }
            )
            return "scene content"

        monkeypatch.setattr(sw, "_call_llm", recording_llm)

        sw.cmd_generate(
            story_name,
            1,
            1,
            "scene def",
            "chapter outline",
            persona_view="chapter",
        )

        assert calls
        assert all("## Chapter Emphasis" not in str(call["prompt"]) for call in calls)
