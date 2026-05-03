"""Verification tests for story_assembler generate-handoff."""

import json
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from domain.exceptions import ConfigurationError

import tools._io as _io_module
import tools.story_assembler as sa


@pytest.fixture
def patched_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    stories_dir = tmp_path / "stories"
    stories_dir.mkdir(parents=True)
    monkeypatch.setattr(_io_module, "STORIES_DIR", stories_dir)
    monkeypatch.setattr(sa, "STORIES_DIR", stories_dir)
    return stories_dir


def _write_story_state(
    stories_dir: Path, story_name: str, state: dict[str, Any]
) -> Path:
    story_dir = stories_dir / story_name
    (story_dir / "savepoints").mkdir(parents=True, exist_ok=True)
    state_path = story_dir / "state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    return state_path


def _valid_handoff_payload() -> dict[str, Any]:
    return {
        "resolved_beats": ["beat1"],
        "obligations": [],
        "active_tensions": [],
        "timeline": {"start": "day 1", "end": "day 2"},
    }


def _state_with_outline() -> dict[str, Any]:
    return {
        "story_context": {"title": "My Story"},
        "chapters": {
            "3": {
                "title": "Chapter Three",
                "expanded_outline": "Outline text",
            }
        },
    }


class TestStripJsonFences:
    def test_strip_json_fences_removes_code_block_markers(self) -> None:
        result = sa._strip_json_fences('```json\n{"key": "val"}\n```')

        assert result == '{"key": "val"}'

    def test_strip_json_fences_leaves_plain_json_unchanged(self) -> None:
        result = sa._strip_json_fences('{"key": "val"}')

        assert result == '{"key": "val"}'


class TestCmdGenerateHandoff:
    def test_generate_handoff_writes_handoff_to_state(
        self, patched_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state_path = _write_story_state(
            patched_env, "test-story", _state_with_outline()
        )
        monkeypatch.setattr(
            sa, "_load_prompt", lambda prompt_id, variables: "mock prompt"
        )
        monkeypatch.setattr(
            sa,
            "_call_llm",
            lambda prompt, model=None: json.dumps(_valid_handoff_payload()),
        )

        sa.cmd_generate_handoff("test-story", 3)

        updated_state = json.loads(state_path.read_text(encoding="utf-8"))
        assert updated_state["chapters"]["3"]["handoff"]["resolved_beats"] == ["beat1"]

    def test_generate_handoff_prints_success_json(
        self,
        patched_env: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _write_story_state(patched_env, "test-story", _state_with_outline())
        monkeypatch.setattr(
            sa, "_load_prompt", lambda prompt_id, variables: "mock prompt"
        )
        monkeypatch.setattr(
            sa,
            "_call_llm",
            lambda prompt, model=None: json.dumps(_valid_handoff_payload()),
        )

        sa.cmd_generate_handoff("test-story", 3)

        result = json.loads(capsys.readouterr().out)
        assert result["status"] == "success"
        assert result["chapter_num"] == 3
        assert "resolved_beats" in result["handoff_keys"]

    def test_generate_handoff_errors_on_missing_expanded_outline(
        self, patched_env: Path
    ) -> None:
        _write_story_state(
            patched_env,
            "test-story",
            {
                "story_context": {"title": "My Story"},
                "chapters": {"3": {"title": "Chapter Three"}},
            },
        )

        with pytest.raises(SystemExit) as exc_info:
            sa.cmd_generate_handoff("test-story", 3)

        assert exc_info.value.code == 1

    def test_generate_handoff_errors_when_prompt_is_missing(
        self, patched_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_story_state(patched_env, "test-story", _state_with_outline())

        def _raise_missing_prompt(prompt_id: str, variables: dict[str, Any]) -> str:
            raise ConfigurationError("Prompt file not found: chapters/generate_handoff")

        monkeypatch.setattr(sa, "_load_prompt", _raise_missing_prompt)

        with pytest.raises(SystemExit) as exc_info:
            sa.cmd_generate_handoff("test-story", 3)

        assert exc_info.value.code == 1

    def test_generate_handoff_passes_model_to_llm(
        self, patched_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_story_state(patched_env, "test-story", _state_with_outline())
        spy: dict[str, Any] = {}

        monkeypatch.setattr(
            sa, "_load_prompt", lambda prompt_id, variables: "mock prompt"
        )

        def _spy_call_llm(prompt: str, *, model: str | None = None) -> str:
            spy["prompt"] = prompt
            spy["model"] = model
            return json.dumps(_valid_handoff_payload())

        monkeypatch.setattr(sa, "_call_llm", _spy_call_llm)

        sa.cmd_generate_handoff("test-story", 3, model="test-model")

        assert spy["prompt"] == "mock prompt"
        assert spy["model"] == "test-model"

    def test_generate_handoff_handles_fenced_json_response(
        self, patched_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state_path = _write_story_state(
            patched_env, "test-story", _state_with_outline()
        )
        monkeypatch.setattr(
            sa, "_load_prompt", lambda prompt_id, variables: "mock prompt"
        )
        monkeypatch.setattr(
            sa,
            "_call_llm",
            lambda prompt, model=None: (
                "```json\n" + json.dumps(_valid_handoff_payload()) + "\n```"
            ),
        )

        sa.cmd_generate_handoff("test-story", 3)

        updated_state = json.loads(state_path.read_text(encoding="utf-8"))
        assert updated_state["chapters"]["3"]["handoff"]["timeline"] == {
            "start": "day 1",
            "end": "day 2",
        }

    def test_generate_handoff_errors_on_invalid_json_response(
        self, patched_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_story_state(patched_env, "test-story", _state_with_outline())
        monkeypatch.setattr(
            sa, "_load_prompt", lambda prompt_id, variables: "mock prompt"
        )
        monkeypatch.setattr(sa, "_call_llm", lambda prompt, model=None: "not json")

        with pytest.raises(SystemExit) as exc_info:
            sa.cmd_generate_handoff("test-story", 3)

        assert exc_info.value.code == 1
