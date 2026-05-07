"""Verification tests for Issue #12 — scene-writer Tool.

Confirms the CLI tool (src/tools/scene_writer.py) correctly handles
parse-definitions, generate, revise, and assemble-chapter operations —
including savepoint resumability, LLM mocking, fallback paths, and
input validation.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import tools._llm as tool_llm
import tools.scene_writer as sw

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_SCRIPT = str(PROJECT_ROOT / "src" / "tools" / "scene_writer.py")


@pytest.fixture()
def story_env(tmp_path: Path) -> tuple[Path, str]:
    """Provide a temp stories directory with a pre-created story."""
    stories_dir = tmp_path / "stories"
    story_name = "test-story"
    (stories_dir / story_name / "savepoints").mkdir(parents=True)
    return stories_dir, story_name


@pytest.fixture()
def patched_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str]:
    """Redirect STORIES_DIR and stub _load_prompt for direct function calls."""
    stories_dir = tmp_path / "stories"
    story_name = "test-story"
    (stories_dir / story_name / "savepoints").mkdir(parents=True)

    monkeypatch.setattr(sw, "STORIES_DIR", stories_dir)
    monkeypatch.setattr(sw, "_load_prompt", lambda *_a, **_kw: "mock prompt text")

    return stories_dir, story_name


def test_call_llm_forwards_system_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_call_llm should forward system_message to the LLM helper."""
    received: dict[str, object] = {}

    def fake_generate_text(
        prompt: str,
        *,
        model: str | None = None,
        system_message: str | None = None,
    ) -> str:
        received["prompt"] = prompt
        received["model"] = model
        received["system_message"] = system_message
        return "ok"

    monkeypatch.setattr(tool_llm, "generate_text", fake_generate_text)

    assert sw._call_llm("prompt", system_message="sys") == "ok"
    assert received == {
        "prompt": "prompt",
        "model": None,
        "system_message": "sys",
    }


def test_fetch_persona_view_empty_stdout_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty persona-builder stdout should map to None."""
    monkeypatch.setattr(
        sw.subprocess,
        "run",
        lambda *_a, **_kw: subprocess.CompletedProcess(
            args=[], returncode=0, stdout=""
        ),
    )

    assert sw._fetch_persona_view("story", "scene") is None


def test_fetch_persona_view_non_empty_stdout_returns_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-empty persona-builder stdout should be stripped and returned."""
    monkeypatch.setattr(
        sw.subprocess,
        "run",
        lambda *_a, **_kw: subprocess.CompletedProcess(
            args=[], returncode=0, stdout="You are a writer.\n"
        ),
    )

    assert sw._fetch_persona_view("story", "scene") == "You are a writer."


def _run_tool(
    *args: str, stories_dir: Path | None = None
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ}
    if stories_dir is not None:
        env["STORIES_DIR"] = str(stories_dir)
    return subprocess.run(
        [sys.executable, TOOL_SCRIPT, *args],
        capture_output=True,
        text=True,
        env=env,
    )


# ---------------------------------------------------------------------------
# 1. test_parse_definitions_success
# ---------------------------------------------------------------------------


def test_parse_definitions_success(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Mock LLM to return valid JSON scene definitions. Verify parse + savepoint."""
    stories_dir, name = patched_env

    definitions = [
        {"title": "Opening", "description": "The hero arrives"},
        {"title": "Confrontation", "description": "The villain appears"},
    ]
    raw_llm = f"```json\n{json.dumps(definitions)}\n```"

    monkeypatch.setattr(sw, "_call_llm", lambda *_a, **_kw: raw_llm)

    sw.cmd_parse_definitions(name, 1, "Chapter outline text", model="test")

    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out["status"] == "success"
    assert out["operation"] == "parse-definitions"
    assert out["data"] == definitions

    # Verify savepoint written
    repo = sw._make_repo(name)
    assert sw._has_savepoint(repo, "chapter_1/scene_definitions")
    saved = sw._load_savepoint(repo, "chapter_1/scene_definitions")
    assert saved == definitions


# ---------------------------------------------------------------------------
# 2. test_parse_definitions_fallback
# ---------------------------------------------------------------------------


def test_parse_definitions_fallback(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Mock LLM to return unparseable response. Verify fallback single-scene definition."""
    _stories_dir, name = patched_env

    monkeypatch.setattr(sw, "_call_llm", lambda *_a, **_kw: "not valid json at all")

    sw.cmd_parse_definitions(name, 3, "My chapter outline", model="test")

    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out["status"] == "success"
    assert out["operation"] == "parse-definitions"
    assert len(out["data"]) == 1
    assert out["data"][0]["title"] == "Chapter 3 Scene"
    assert out["data"][0]["description"] == "My chapter outline"


# ---------------------------------------------------------------------------
# 3. test_parse_definitions_savepoint_resume
# ---------------------------------------------------------------------------


def test_parse_definitions_savepoint_resume(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Pre-populate savepoint. Verify returns cached data without LLM call."""
    stories_dir, name = patched_env

    cached_defs = [{"title": "Cached Scene", "description": "Already done"}]
    repo = sw._make_repo(name)
    sw._save_savepoint(repo, "chapter_1/scene_definitions", cached_defs)

    def llm_should_not_be_called(*_a: object, **_kw: object) -> str:
        raise AssertionError("_call_llm should not be called when savepoint exists")

    monkeypatch.setattr(sw, "_call_llm", llm_should_not_be_called)

    sw.cmd_parse_definitions(name, 1, "Ignored outline", model="test")

    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out["status"] == "success"
    assert out["data"] == cached_defs


# ---------------------------------------------------------------------------
# 4. test_generate_scene_success
# ---------------------------------------------------------------------------


def test_generate_scene_success(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Mock LLM to return scene content. Verify generate with full context params."""
    _stories_dir, name = patched_env

    scene_text = "The sun set over the ancient city as Elena stepped through the gate."
    monkeypatch.setattr(sw, "_call_llm", lambda *_a, **_kw: scene_text)

    sw.cmd_generate(
        name,
        chapter_num=2,
        scene_num=1,
        scene_definition="Elena arrives at the city",
        chapter_outline="Chapter 2 outline",
        base_context="Fantasy world context",
        story_elements="Key story elements",
        character_sheets="Elena: protagonist",
        setting_sheets="Ancient city setting",
        previous_recap="Chapter 1 recap",
        previous_scene="Previous scene text",
        next_scene_definition="Next scene def",
        next_chapter_synopsis="Chapter 3 synopsis",
        model="test",
    )

    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out["status"] == "success"
    assert out["operation"] == "generate"
    assert out["data"]["scene_ref"] == "chapter_2/scene_1"
    assert out["data"]["char_count"] == len(scene_text)
    assert "content" not in out["data"]

    # Verify savepoint
    repo = sw._make_repo(name)
    assert sw._has_savepoint(repo, "chapter_2/scene_1")
    saved = sw._load_savepoint(repo, "chapter_2/scene_1")
    assert scene_text in str(saved)


# ---------------------------------------------------------------------------
# 5. test_generate_scene_savepoint_resume
# ---------------------------------------------------------------------------


def test_generate_scene_savepoint_resume(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Pre-populate savepoint for scene. Verify returns cached content without LLM call."""
    _stories_dir, name = patched_env

    cached_content = "Cached scene content from previous run."
    repo = sw._make_repo(name)
    sw._save_savepoint(repo, "chapter_1/scene_2", cached_content)

    def llm_should_not_be_called(*_a: object, **_kw: object) -> str:
        raise AssertionError("_call_llm should not be called when savepoint exists")

    monkeypatch.setattr(sw, "_call_llm", llm_should_not_be_called)

    sw.cmd_generate(
        name,
        chapter_num=1,
        scene_num=2,
        scene_definition="Some definition",
        chapter_outline="Some outline",
        model="test",
    )

    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out["status"] == "success"
    assert out["operation"] == "generate"
    assert out["data"]["scene_ref"] == "chapter_1/scene_2"
    assert "content" not in out["data"]


# ---------------------------------------------------------------------------
# 6. TestCmdGenerateChapter
# ---------------------------------------------------------------------------


class TestCmdGenerateChapter:
    def test_generate_chapter_success(
        self,
        patched_env: tuple[Path, str],
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Generate full chapter, persist savepoint, and update state."""
        stories_dir, name = patched_env
        repo = sw._make_repo(name)

        state_path = stories_dir / name / "state.json"
        state_path.write_text(
            json.dumps({"chapters": {"1": {"expanded_outline": "Chapter outline"}}})
        )

        sw._save_savepoint(repo, "base_context", "Base context")
        sw._save_savepoint(repo, "initial_outline", "Initial outline")

        monkeypatch.setattr(
            sw, "_call_llm", lambda *_a, **_kw: "Generated chapter content"
        )

        sw.cmd_generate_chapter(name, 1)

        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "success"
        assert out["operation"] == "generate-chapter"
        assert out["data"]["chapter_ref"] == "chapter_1/chapter_content"
        assert out["data"]["char_count"] == len("Generated chapter content")
        assert "content" not in out["data"]

        assert sw._has_savepoint(repo, "chapter_1/chapter_content")
        assert (
            sw._load_savepoint(repo, "chapter_1/chapter_content")
            == "Generated chapter content"
        )

        updated_state = json.loads(state_path.read_text())
        assert updated_state["chapters"]["1"]["content"] == "Generated chapter content"

    def test_generate_chapter_savepoint_resume(
        self,
        patched_env: tuple[Path, str],
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Use cached chapter content when savepoint already exists."""
        _stories_dir, name = patched_env
        repo = sw._make_repo(name)
        sw._save_savepoint(repo, "chapter_1/chapter_content", "Cached content")

        def llm_should_not_be_called(*_a: object, **_kw: object) -> str:
            raise AssertionError("_call_llm should not be called when savepoint exists")

        monkeypatch.setattr(sw, "_call_llm", llm_should_not_be_called)

        sw.cmd_generate_chapter(name, 1)

        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "success"
        assert out["operation"] == "generate-chapter"
        assert out["data"]["chapter_ref"] == "chapter_1/chapter_content"
        assert "content" not in out["data"]

    def test_generate_chapter_previous_recap_included(
        self,
        patched_env: tuple[Path, str],
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Include prior chapter recap in prompt variables for later chapters."""
        stories_dir, name = patched_env
        repo = sw._make_repo(name)
        state_path = stories_dir / name / "state.json"
        state_path.write_text(
            json.dumps(
                {
                    "chapters": {
                        "1": {"expanded_outline": "Chapter 1 outline"},
                        "2": {"expanded_outline": "Chapter 2 outline"},
                    }
                }
            )
        )
        sw._save_savepoint(repo, "chapter_1/recap", "Prior recap")

        captured_variables: dict[str, object] = {}

        def capture_prompt(
            prompt_id: str, variables: dict[str, object] | None = None
        ) -> str:
            assert prompt_id == "chapters/create_content"
            if variables is not None:
                captured_variables.update(variables)
            return "mock prompt text"

        monkeypatch.setattr(sw, "_load_prompt", capture_prompt)
        monkeypatch.setattr(sw, "_call_llm", lambda *_a, **_kw: "Generated chapter 2")

        sw.cmd_generate_chapter(name, 2)

        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "success"
        assert captured_variables["previous_recap"] == "Prior recap"

    def test_generate_chapter_additional_context_appended(
        self,
        patched_env: tuple[Path, str],
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Append additional context to base_context before prompt render."""
        stories_dir, name = patched_env
        repo = sw._make_repo(name)
        state_path = stories_dir / name / "state.json"
        state_path.write_text(
            json.dumps({"chapters": {"1": {"expanded_outline": "Chapter outline"}}})
        )
        sw._save_savepoint(repo, "base_context", "Base info")

        captured_variables: dict[str, object] = {}

        def capture_prompt(
            _prompt_id: str, variables: dict[str, object] | None = None
        ) -> str:
            if variables is not None:
                captured_variables.update(variables)
            return "mock prompt text"

        monkeypatch.setattr(sw, "_load_prompt", capture_prompt)
        monkeypatch.setattr(sw, "_call_llm", lambda *_a, **_kw: "Generated chapter")

        sw.cmd_generate_chapter(name, 1, additional_context="Extra context")

        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "success"
        assert "Base info" in str(captured_variables["base_context"])
        assert "Extra context" in str(captured_variables["base_context"])

    def test_generate_chapter_missing_state_graceful(
        self,
        patched_env: tuple[Path, str],
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Missing story state and savepoints should not crash chapter generation."""
        stories_dir, name = patched_env
        state_path = stories_dir / name / "state.json"
        if state_path.exists():
            state_path.unlink()

        monkeypatch.setattr(sw, "_call_llm", lambda *_a, **_kw: "Content")

        sw.cmd_generate_chapter(name, 1)

        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "success"
        assert out["operation"] == "generate-chapter"
        assert out["data"]["chapter_ref"] == "chapter_1/chapter_content"
        assert out["data"]["char_count"] == len("Content")
        assert "content" not in out["data"]


# ---------------------------------------------------------------------------
# 7. test_revise_scene_success
# ---------------------------------------------------------------------------


def test_revise_scene_success(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Mock LLM to return revised content. Verify feedback appears in prompt."""
    _stories_dir, name = patched_env

    revised_text = "The revised scene with more tension."
    captured_prompts: list[str] = []

    def mock_load_prompt(prompt_id: str, variables: dict | None = None) -> str:
        # Build a fake prompt that includes the variable values so we can verify
        rendered = f"prompt:{prompt_id}"
        if variables:
            for k, v in variables.items():
                rendered += f" {k}={v}"
        captured_prompts.append(rendered)
        return rendered

    monkeypatch.setattr(sw, "_load_prompt", mock_load_prompt)
    monkeypatch.setattr(sw, "_call_llm", lambda *_a, **_kw: revised_text)

    feedback_text = "Add more tension in the dialogue"
    sw.cmd_revise(
        name,
        chapter_num=1,
        scene_num=1,
        scene_content="Original scene text",
        feedback=feedback_text,
        scene_definition="Scene def",
        chapter_outline="Chapter outline",
        model="test",
    )

    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out["status"] == "success"
    assert out["operation"] == "revise"
    assert out["data"]["scene_ref"] == "chapter_1/scene_1"
    assert out["data"]["char_count"] == len(revised_text)
    assert "content" not in out["data"]

    # CRITICAL: Verify feedback text appears in the LLM call arguments
    assert len(captured_prompts) == 1
    assert feedback_text in captured_prompts[0]

    # Verify savepoint overwritten
    repo = sw._make_repo(name)
    assert sw._has_savepoint(repo, "chapter_1/scene_1")


# ---------------------------------------------------------------------------
# 7. test_assemble_chapter_success
# ---------------------------------------------------------------------------


def test_assemble_chapter_success(
    patched_env: tuple[Path, str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Pre-populate scene savepoints. Verify assembly concatenates with headers."""
    _stories_dir, name = patched_env
    repo = sw._make_repo(name)

    # Save scene definitions with titles
    defs = [
        {"title": "The Arrival", "description": "Scene 1 desc"},
        {"title": "The Battle", "description": "Scene 2 desc"},
        {"title": "The Aftermath", "description": "Scene 3 desc"},
    ]
    sw._save_savepoint(repo, "chapter_1/scene_definitions", defs)

    # Save scene content
    sw._save_savepoint(repo, "chapter_1/scene_1", "Content of scene one.")
    sw._save_savepoint(repo, "chapter_1/scene_2", "Content of scene two.")
    sw._save_savepoint(repo, "chapter_1/scene_3", "Content of scene three.")

    sw.cmd_assemble_chapter(
        name, 1, 3, chapter_title="The Beginning", include_content=True
    )

    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out["status"] == "success"
    assert out["operation"] == "assemble-chapter"
    assert out["data"]["chapter_ref"] == "chapter_1/chapter_content"
    assert out["data"]["scene_count"] == 3

    assembled = out["data"]["content"]
    assert "# The Beginning" in assembled
    assert "## The Arrival" in assembled
    assert "## The Battle" in assembled
    assert "## The Aftermath" in assembled
    assert "Content of scene one." in assembled
    assert "Content of scene two." in assembled
    assert "Content of scene three." in assembled
    assert "---" in assembled
    assert sw._has_savepoint(repo, "chapter_1/chapter_content")


def test_generate_include_content_returns_content(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Include-content flag should restore legacy scene text in response."""
    _stories_dir, name = patched_env

    scene_text = "Scene text returned with include-content enabled."
    monkeypatch.setattr(sw, "_call_llm", lambda *_a, **_kw: scene_text)

    sw.cmd_generate(
        name,
        chapter_num=1,
        scene_num=1,
        scene_definition="Scene definition",
        chapter_outline="Chapter outline",
        include_content=True,
    )

    out = json.loads(capsys.readouterr().out)
    assert out["data"]["scene_ref"] == "chapter_1/scene_1"
    assert out["data"]["content"] == scene_text


def test_generate_persona_and_delta_forwarded(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """generate should forward persona text and append emphasis delta."""
    _stories_dir, name = patched_env

    received: dict[str, object] = {}

    def fake_call_llm(
        prompt: str,
        *,
        model: str | None = None,
        system_message: str | None = None,
    ) -> str:
        received["prompt"] = prompt
        received["model"] = model
        received["system_message"] = system_message
        return "Generated scene"

    monkeypatch.setattr(sw, "_call_llm", fake_call_llm)
    monkeypatch.setattr(sw, "_fetch_persona_view", lambda *_a, **_kw: "persona sys")

    sw.cmd_generate(
        name,
        chapter_num=1,
        scene_num=1,
        scene_definition="Scene definition",
        chapter_outline="Chapter outline",
        model="test",
        persona_view="scene",
        emphasis_delta="Lean harder into suspense.",
    )

    json.loads(capsys.readouterr().out)
    assert received["system_message"] == "persona sys"
    assert "## Chapter Emphasis" in str(received["prompt"])
    assert "Lean harder into suspense." in str(received["prompt"])


def test_generate_no_persona_no_delta(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """generate should omit persona system message and emphasis section when absent."""
    _stories_dir, name = patched_env

    received: dict[str, object] = {}

    def fake_call_llm(
        prompt: str,
        *,
        model: str | None = None,
        system_message: str | None = None,
    ) -> str:
        received["prompt"] = prompt
        received["model"] = model
        received["system_message"] = system_message
        return "Generated scene"

    monkeypatch.setattr(sw, "_call_llm", fake_call_llm)

    sw.cmd_generate(
        name,
        chapter_num=1,
        scene_num=1,
        scene_definition="Scene definition",
        chapter_outline="Chapter outline",
        model="test",
        persona_view=None,
        emphasis_delta=None,
    )

    json.loads(capsys.readouterr().out)
    assert received["system_message"] is None
    assert "## Chapter Emphasis" not in str(received["prompt"])


def test_generate_auto_loads_previous_scene(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Second scene should auto-load previous_scene from prior savepoint."""
    _stories_dir, name = patched_env
    repo = sw._make_repo(name)
    sw._save_savepoint(repo, "chapter_1/scene_1", "Previous scene content")

    captured_variables: dict[str, object] = {}

    def capture_prompt(
        _prompt_id: str, variables: dict[str, object] | None = None
    ) -> str:
        if variables is not None:
            captured_variables.update(variables)
        return "mock prompt text"

    monkeypatch.setattr(sw, "_load_prompt", capture_prompt)
    monkeypatch.setattr(sw, "_call_llm", lambda *_a, **_kw: "Generated scene")

    sw.cmd_generate(
        name,
        chapter_num=1,
        scene_num=2,
        scene_definition="Scene definition",
        chapter_outline="Chapter outline",
    )

    json.loads(capsys.readouterr().out)
    assert captured_variables["previous_scene"] == "Previous scene content"


def test_generate_explicit_previous_scene_overrides_savepoint(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Explicit previous_scene arg should win over auto-loaded savepoint text."""
    _stories_dir, name = patched_env
    repo = sw._make_repo(name)
    sw._save_savepoint(repo, "chapter_1/scene_1", "Savepoint scene content")

    captured_variables: dict[str, object] = {}

    def capture_prompt(
        _prompt_id: str, variables: dict[str, object] | None = None
    ) -> str:
        if variables is not None:
            captured_variables.update(variables)
        return "mock prompt text"

    monkeypatch.setattr(sw, "_load_prompt", capture_prompt)
    monkeypatch.setattr(sw, "_call_llm", lambda *_a, **_kw: "Generated scene")

    sw.cmd_generate(
        name,
        chapter_num=1,
        scene_num=2,
        scene_definition="Scene definition",
        chapter_outline="Chapter outline",
        previous_scene="Explicit content",
    )

    json.loads(capsys.readouterr().out)
    assert captured_variables["previous_scene"] == "Explicit content"


def test_generate_scene1_no_previous_scene_loaded(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """First scene in chapter should render empty previous_scene context."""
    _stories_dir, name = patched_env

    captured_variables: dict[str, object] = {}

    def capture_prompt(
        _prompt_id: str, variables: dict[str, object] | None = None
    ) -> str:
        if variables is not None:
            captured_variables.update(variables)
        return "mock prompt text"

    monkeypatch.setattr(sw, "_load_prompt", capture_prompt)
    monkeypatch.setattr(sw, "_call_llm", lambda *_a, **_kw: "Generated scene")

    sw.cmd_generate(
        name,
        chapter_num=1,
        scene_num=1,
        scene_definition="Scene definition",
        chapter_outline="Chapter outline",
    )

    json.loads(capsys.readouterr().out)
    assert captured_variables["previous_scene"] == ""


def test_revise_default_returns_scene_ref(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Revise should default to compact scene ref response when include-content off."""
    _stories_dir, name = patched_env
    repo = sw._make_repo(name)
    sw._save_savepoint(repo, "chapter_1/scene_1", "Original scene text")

    monkeypatch.setattr(sw, "_call_llm", lambda *_a, **_kw: "Revised scene text")

    sw.cmd_revise(name, chapter_num=1, scene_num=1, feedback="Make it darker")

    out = json.loads(capsys.readouterr().out)
    assert out["data"]["scene_ref"] == "chapter_1/scene_1"
    assert "content" not in out["data"]


def test_revise_auto_loads_scene_content(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Revise should auto-load scene_content from savepoint when omitted."""
    _stories_dir, name = patched_env
    repo = sw._make_repo(name)
    sw._save_savepoint(repo, "chapter_1/scene_1", "Original scene text")

    captured_variables: dict[str, object] = {}

    def capture_prompt(
        _prompt_id: str, variables: dict[str, object] | None = None
    ) -> str:
        if variables is not None:
            captured_variables.update(variables)
        return "mock prompt text"

    monkeypatch.setattr(sw, "_load_prompt", capture_prompt)
    monkeypatch.setattr(sw, "_call_llm", lambda *_a, **_kw: "Revised scene text")

    sw.cmd_revise(name, chapter_num=1, scene_num=1, feedback="Tighten prose")

    json.loads(capsys.readouterr().out)
    assert captured_variables["scene_content"] == "Original scene text"


def test_revise_include_content_returns_content(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Revise include-content flag should return revised scene text."""
    _stories_dir, name = patched_env
    repo = sw._make_repo(name)
    sw._save_savepoint(repo, "chapter_1/scene_1", "Original scene text")

    revised_text = "Revised scene text returned in payload"
    monkeypatch.setattr(sw, "_call_llm", lambda *_a, **_kw: revised_text)

    sw.cmd_revise(
        name,
        chapter_num=1,
        scene_num=1,
        feedback="Improve pacing",
        include_content=True,
    )

    out = json.loads(capsys.readouterr().out)
    assert out["data"]["content"] == revised_text


def test_revise_persona_and_delta_forwarded(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """revise should forward persona text and append emphasis delta."""
    _stories_dir, name = patched_env

    received: dict[str, object] = {}

    def fake_call_llm(
        prompt: str,
        *,
        model: str | None = None,
        system_message: str | None = None,
    ) -> str:
        received["prompt"] = prompt
        received["model"] = model
        received["system_message"] = system_message
        return "Revised scene"

    monkeypatch.setattr(sw, "_call_llm", fake_call_llm)
    monkeypatch.setattr(sw, "_fetch_persona_view", lambda *_a, **_kw: "persona sys")

    sw.cmd_revise(
        name,
        chapter_num=1,
        scene_num=1,
        feedback="Tighten prose",
        scene_content="Original scene",
        model="test",
        persona_view="scene",
        emphasis_delta="Keep the voice severe.",
    )

    json.loads(capsys.readouterr().out)
    assert received["system_message"] == "persona sys"
    assert "## Chapter Emphasis" in str(received["prompt"])
    assert "Keep the voice severe." in str(received["prompt"])


def test_assemble_chapter_default_returns_chapter_ref(
    patched_env: tuple[Path, str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Assemble should default to compact chapter ref response without content."""
    _stories_dir, name = patched_env
    repo = sw._make_repo(name)
    sw._save_savepoint(repo, "chapter_1/scene_1", "Scene one")
    sw._save_savepoint(repo, "chapter_1/scene_2", "Scene two")

    sw.cmd_assemble_chapter(name, 1, 2)

    out = json.loads(capsys.readouterr().out)
    assert out["data"]["chapter_ref"] == "chapter_1/chapter_content"
    assert out["data"]["scene_count"] == 2
    assert "content" not in out["data"]


# ---------------------------------------------------------------------------
# 8. test_assemble_chapter_missing_scenes
# ---------------------------------------------------------------------------


def test_assemble_chapter_missing_scenes(story_env: tuple[Path, str]) -> None:
    """Don't populate all savepoints. Verify error for missing scenes."""
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "assemble-chapter",
        "--name",
        name,
        "--chapter-num",
        "1",
        "--scene-count",
        "3",
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
    assert "missing scenes" in result.stderr.lower()


# ---------------------------------------------------------------------------
# 9. test_count_tokens
# ---------------------------------------------------------------------------


def test_count_tokens() -> None:
    """Verify count_tokens: 'hello world' -> int(2*1.33)=2, empty string -> 0."""
    from tools._llm import count_tokens

    assert count_tokens("hello world") == 2
    assert count_tokens("") == 0


# ---------------------------------------------------------------------------
# 10. test_invalid_story_name
# ---------------------------------------------------------------------------


def test_invalid_story_name(story_env: tuple[Path, str]) -> None:
    """Pass path traversal name (../hack). Verify error raised."""
    stories_dir, _ = story_env
    result = _run_tool(
        "--operation",
        "parse-definitions",
        "--name",
        "../hack",
        "--chapter-num",
        "1",
        "--chapter-outline",
        "Some outline",
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
    assert "escapes" in result.stderr.lower()


# ---------------------------------------------------------------------------
# 11. test_scrub_analyze_success
# ---------------------------------------------------------------------------


def test_scrub_analyze_success(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Mock LLM scrub analysis response. Verify issues returned and counted."""
    _stories_dir, name = patched_env

    issues = [
        {"type": "passive-voice", "excerpt": "was opened", "suggestion": "opened"},
        {
            "type": "wordiness",
            "excerpt": "in order to",
            "suggestion": "to",
        },
    ]
    raw_llm = f"```json\n{json.dumps({'issues': issues})}\n```"

    monkeypatch.setattr(sw, "_call_llm", lambda *_a, **_kw: raw_llm)

    sw.cmd_scrub_analyze(name, 1, "Chapter text", model="test")

    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "success"
    assert out["operation"] == "scrub-analyze"
    assert out["data"]["issues_found"] == 2
    assert issues == out["data"]["issues"]


# ---------------------------------------------------------------------------
# 12. test_scrub_analyze_empty_issues
# ---------------------------------------------------------------------------


def test_scrub_analyze_empty_issues(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Mock empty scrub issues response. Verify zero count and empty list."""
    _stories_dir, name = patched_env

    monkeypatch.setattr(sw, "_call_llm", lambda *_a, **_kw: '{"issues": []}')

    sw.cmd_scrub_analyze(name, 1, "Chapter text", model="test")

    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "success"
    assert out["data"]["issues_found"] == 0
    assert out["data"]["issues"] == []


# ---------------------------------------------------------------------------
# 13. test_scrub_analyze_json_parse_error_exits
# ---------------------------------------------------------------------------


def test_scrub_analyze_json_parse_error_exits(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mock invalid scrub response. Verify command exits on parse failure."""
    _stories_dir, name = patched_env

    monkeypatch.setattr(sw, "_call_llm", lambda *_a, **_kw: "not json")

    with pytest.raises(SystemExit):
        sw.cmd_scrub_analyze(name, 1, "Chapter text", model="test")


# ---------------------------------------------------------------------------
# 14. test_voice_analyze_success
# ---------------------------------------------------------------------------


def test_voice_analyze_success(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Mock voice analysis response. Verify issues and prior summary flow through."""
    _stories_dir, name = patched_env

    issues = [
        {"type": "voice", "excerpt": "slang spike", "suggestion": "match tone"},
        {"type": "pacing", "excerpt": "slow middle", "suggestion": "tighten"},
        {
            "type": "continuity",
            "excerpt": "shifted worldview",
            "suggestion": "align with prior chapters",
        },
    ]
    raw_llm = f"```json\n{json.dumps({'issues': issues})}\n```"
    captured_prompts: list[str] = []

    def mock_load_prompt(prompt_id: str, variables: dict | None = None) -> str:
        rendered = f"prompt:{prompt_id}"
        if variables:
            for key, value in variables.items():
                rendered += f" {key}={value}"
        captured_prompts.append(rendered)
        return rendered

    monkeypatch.setattr(sw, "_load_prompt", mock_load_prompt)
    monkeypatch.setattr(sw, "_call_llm", lambda *_a, **_kw: raw_llm)

    prior_summary = "Summary of prior events"
    sw.cmd_voice_analyze(
        name,
        1,
        "Chapter text",
        prior_chapters_summary=prior_summary,
        model="test",
    )

    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "success"
    assert out["operation"] == "voice-analyze"
    assert out["data"]["issues_found"] == 3
    assert issues == out["data"]["issues"]
    assert len(captured_prompts) == 1
    assert prior_summary in captured_prompts[0]


# ---------------------------------------------------------------------------
# 15. test_voice_analyze_empty_issues
# ---------------------------------------------------------------------------


def test_voice_analyze_empty_issues(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Mock empty voice issues response. Verify zero count and empty list."""
    _stories_dir, name = patched_env

    monkeypatch.setattr(sw, "_call_llm", lambda *_a, **_kw: '{"issues": []}')

    sw.cmd_voice_analyze(
        name, 1, "Chapter text", prior_chapters_summary="", model="test"
    )

    out = json.loads(capsys.readouterr().out)
    assert out["data"]["issues_found"] == 0
    assert out["data"]["issues"] == []


def test_voice_analyze_json_parse_error_exits(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mock invalid voice response. Verify command exits on parse failure."""
    _stories_dir, name = patched_env

    monkeypatch.setattr(sw, "_call_llm", lambda *_a, **_kw: "not json")

    with pytest.raises(SystemExit):
        sw.cmd_voice_analyze(name, 1, "Chapter text", model="test")


# ---------------------------------------------------------------------------
# 16. test_scrub_analyze_cli_missing_chapter_text
# ---------------------------------------------------------------------------


def test_scrub_analyze_cli_missing_chapter_text(
    story_env: tuple[Path, str],
) -> None:
    """Run scrub analyze via CLI without chapter text. Verify validation failure."""
    stories_dir, name = story_env

    result = _run_tool(
        "--operation",
        "scrub-analyze",
        "--name",
        name,
        "--chapter-num",
        "1",
        stories_dir=stories_dir,
    )

    assert result.returncode != 0
    assert "chapter-text is required" in result.stderr.lower()


# ---------------------------------------------------------------------------
# 17. test_voice_analyze_cli_missing_chapter_text
# ---------------------------------------------------------------------------


def test_voice_analyze_cli_missing_chapter_text(
    story_env: tuple[Path, str],
) -> None:
    """Run voice analyze via CLI without chapter text. Verify validation failure."""
    stories_dir, name = story_env

    result = _run_tool(
        "--operation",
        "voice-analyze",
        "--name",
        name,
        "--chapter-num",
        "1",
        stories_dir=stories_dir,
    )

    assert result.returncode != 0
    assert "chapter-text is required" in result.stderr.lower()
