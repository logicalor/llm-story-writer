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

import pytest

import src.tools.scene_writer as sw

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
    assert out["data"] == scene_text

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
    assert "Cached scene content" in str(out["data"])


# ---------------------------------------------------------------------------
# 6. test_revise_scene_success
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
    assert out["data"] == revised_text

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

    sw.cmd_assemble_chapter(name, 1, 3, chapter_title="The Beginning")

    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out["status"] == "success"
    assert out["operation"] == "assemble-chapter"

    assembled = out["data"]
    assert "# The Beginning" in assembled
    assert "## The Arrival" in assembled
    assert "## The Battle" in assembled
    assert "## The Aftermath" in assembled
    assert "Content of scene one." in assembled
    assert "Content of scene two." in assembled
    assert "Content of scene three." in assembled
    assert "---" in assembled


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
    from src.tools._llm import count_tokens

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

    sw.cmd_voice_analyze(name, 1, "Chapter text", prior_chapters_summary="", model="test")

    out = json.loads(capsys.readouterr().out)
    assert out["data"]["issues_found"] == 0
    assert out["data"]["issues"] == []


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
