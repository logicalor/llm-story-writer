from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import tools._io as tool_io
import tools.persona_builder as persona_builder
from infrastructure.storage.savepoint_repository import FilesystemSavepointRepository

STORY_NAME = "test-story"
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
SAMPLE_PERSONA = VALID_PERSONA


def _patch_stories_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(persona_builder, "STORIES_DIR", tmp_path)
    monkeypatch.setattr(tool_io, "STORIES_DIR", tmp_path)


def _create_story_dir(tmp_path: Path, story_name: str = STORY_NAME) -> Path:
    story_dir = tmp_path / story_name
    story_dir.mkdir(parents=True, exist_ok=True)
    return story_dir


def _make_repo(story_dir: Path) -> FilesystemSavepointRepository:
    repo = FilesystemSavepointRepository(base_path=story_dir)
    repo.set_story_directory("savepoints")
    return repo


def _write_required_savepoints(story_dir: Path) -> FilesystemSavepointRepository:
    repo = _make_repo(story_dir)
    asyncio.run(repo.save_savepoint("core_story_foundation", "Foundation text"))
    asyncio.run(repo.save_savepoint("tone_style", "Tone text"))
    asyncio.run(repo.save_savepoint("theme_message", "Theme text"))
    asyncio.run(repo.save_savepoint("story_elements", "Elements text"))
    return repo


def _patch_generate_dependencies(
    monkeypatch: pytest.MonkeyPatch, response: str = VALID_PERSONA
) -> None:
    monkeypatch.setattr(
        persona_builder, "_load_prompt", lambda *_args, **_kwargs: "prompt"
    )
    monkeypatch.setattr(
        persona_builder,
        "_call_llm",
        lambda prompt, **kw: response,
    )


class TestValidatePersonaDoc:
    def test_valid_document_returns_no_errors(self) -> None:
        errors = persona_builder._validate_persona_doc(VALID_PERSONA)

        assert errors == []

    def test_missing_frontmatter_returns_error(self) -> None:
        document = VALID_PERSONA.removeprefix("---\n").split("---\n", maxsplit=1)[1]

        errors = persona_builder._validate_persona_doc(document)

        assert "Missing YAML frontmatter at document start" in errors

    def test_missing_section_returns_error(self) -> None:
        document = VALID_PERSONA.replace(
            "## Anti-Patterns\n- Avoid purple prose.\n- Avoid exposition dumps.\n", ""
        )

        errors = persona_builder._validate_persona_doc(document)

        assert "Missing required section: ## Anti-Patterns" in errors


class TestStripFrontmatter:
    def test_strips_frontmatter_block(self) -> None:
        document = "---\nkey: val\n---\nbody text"

        result = persona_builder._strip_frontmatter(document)

        assert result == "body text"

    def test_no_frontmatter_returns_original(self) -> None:
        document = "# Heading\n\nPlain markdown"

        result = persona_builder._strip_frontmatter(document)

        assert result == document


class TestExtractSections:
    def test_extracts_multiple_sections(self) -> None:
        body = "## Identity\ncontent1\n## Prose Texture\ncontent2"

        sections = persona_builder._extract_sections(body)

        assert sections["## Identity"] == "content1"
        assert sections["## Prose Texture"] == "content2"

    def test_section_content_stripped(self) -> None:
        body = "## Identity\n\n  content with space  \n\n## Prose Texture\nnext"

        sections = persona_builder._extract_sections(body)

        assert sections["## Identity"] == "content with space"


class TestGetPersonaDir:
    def test_creates_persona_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_stories_dir(monkeypatch, tmp_path)
        _create_story_dir(tmp_path)

        persona_dir = persona_builder._get_persona_dir(STORY_NAME)

        assert persona_dir == tmp_path / STORY_NAME / "persona"
        assert persona_dir.is_dir()


class TestCmdGenerate:
    def test_generate_writes_persona_md(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_stories_dir(monkeypatch, tmp_path)
        story_dir = _create_story_dir(tmp_path)
        _write_required_savepoints(story_dir)
        _patch_generate_dependencies(monkeypatch)

        persona_builder.cmd_generate(STORY_NAME)

        persona_path = story_dir / "persona" / "persona.md"
        assert persona_path.exists()
        assert persona_path.read_text(encoding="utf-8") == VALID_PERSONA

    def test_generate_writes_savepoint(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_stories_dir(monkeypatch, tmp_path)
        story_dir = _create_story_dir(tmp_path)
        repo = _write_required_savepoints(story_dir)
        _patch_generate_dependencies(monkeypatch)

        persona_builder.cmd_generate(STORY_NAME)

        savepoint = asyncio.run(repo.load_savepoint("persona"))
        assert isinstance(savepoint, dict)
        assert savepoint["persona_path"] == str(story_dir / "persona" / "persona.md")
        assert isinstance(savepoint["generation_timestamp"], str)
        assert "T" in savepoint["generation_timestamp"]

    def test_generate_outputs_success_json(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _patch_stories_dir(monkeypatch, tmp_path)
        story_dir = _create_story_dir(tmp_path)
        _write_required_savepoints(story_dir)
        _patch_generate_dependencies(monkeypatch)

        persona_builder.cmd_generate(STORY_NAME)

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["operation"] == "generate"
        assert output["data"]["word_count"] > 0

    def test_generate_word_budget_clamped_low(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, int] = {}

        def fake_load_prompt(
            prompt_id: str, variables: dict[str, object] | None = None
        ) -> str:
            assert prompt_id == "persona/generate"
            assert variables is not None
            captured["word_budget"] = int(variables["word_budget"])
            return "prompt"

        _patch_stories_dir(monkeypatch, tmp_path)
        story_dir = _create_story_dir(tmp_path)
        _write_required_savepoints(story_dir)
        monkeypatch.setattr(persona_builder, "_load_prompt", fake_load_prompt)
        monkeypatch.setattr(
            persona_builder, "_call_llm", lambda prompt, **kw: VALID_PERSONA
        )

        persona_builder.cmd_generate(STORY_NAME, word_budget=50)

        assert captured["word_budget"] == 100

    def test_generate_word_budget_clamped_high(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, int] = {}

        def fake_load_prompt(
            prompt_id: str, variables: dict[str, object] | None = None
        ) -> str:
            assert prompt_id == "persona/generate"
            assert variables is not None
            captured["word_budget"] = int(variables["word_budget"])
            return "prompt"

        _patch_stories_dir(monkeypatch, tmp_path)
        story_dir = _create_story_dir(tmp_path)
        _write_required_savepoints(story_dir)
        monkeypatch.setattr(persona_builder, "_load_prompt", fake_load_prompt)
        monkeypatch.setattr(
            persona_builder, "_call_llm", lambda prompt, **kw: VALID_PERSONA
        )

        persona_builder.cmd_generate(STORY_NAME, word_budget=600)

        assert captured["word_budget"] == 500

    def test_generate_missing_savepoint_exits_1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_stories_dir(monkeypatch, tmp_path)
        _create_story_dir(tmp_path)
        _patch_generate_dependencies(monkeypatch)

        with pytest.raises(SystemExit) as exc_info:
            persona_builder.cmd_generate(STORY_NAME)

        assert exc_info.value.code == 1

    def test_generate_validation_failure_writes_last_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        invalid_response = "## Identity\nNo frontmatter here."

        _patch_stories_dir(monkeypatch, tmp_path)
        story_dir = _create_story_dir(tmp_path)
        _write_required_savepoints(story_dir)
        _patch_generate_dependencies(monkeypatch, response=invalid_response)

        with pytest.raises(SystemExit) as exc_info:
            persona_builder.cmd_generate(STORY_NAME)

        failed_path = story_dir / "persona" / ".last-failed.md"
        assert exc_info.value.code == 1
        assert failed_path.exists()
        assert failed_path.read_text(encoding="utf-8") == invalid_response


class TestCmdGetView:
    @pytest.fixture()
    def persona_story_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> Path:
        _patch_stories_dir(monkeypatch, tmp_path)
        story_dir = _create_story_dir(tmp_path)
        persona_dir = story_dir / "persona"
        persona_dir.mkdir(parents=True, exist_ok=True)
        (persona_dir / "persona.md").write_text(SAMPLE_PERSONA, encoding="utf-8")
        return story_dir

    def test_get_view_outline(
        self, persona_story_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        persona_builder.cmd_get_view(STORY_NAME, "outline")

        output = capsys.readouterr().out
        assert "## Identity" in output
        assert "## Narrative Philosophy" in output
        assert "## Thematic Sensibility" in output
        assert "## Pacing Philosophy" in output
        assert "## Anti-Patterns" in output
        assert "## Prose Texture" not in output

    def test_get_view_chapter(
        self, persona_story_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        persona_builder.cmd_get_view(STORY_NAME, "chapter")

        output = capsys.readouterr().out
        assert "---" not in output
        assert "## Identity" in output
        assert "## Prose Texture" in output

    def test_get_view_scrubber(
        self, persona_story_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        persona_builder.cmd_get_view(STORY_NAME, "scrubber")

        output = capsys.readouterr().out
        assert "## Identity\nYou write haunted stories." in output
        assert "You favour intimate framing." not in output
        assert "## Prose Texture" in output
        assert "## Dialogue Style" in output
        assert "## Anti-Patterns" in output

    def test_get_view_editor(
        self, persona_story_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        persona_builder.cmd_get_view(STORY_NAME, "editor")

        output = capsys.readouterr().out
        assert "## Identity" in output
        assert "## Prose Texture" in output
        assert "## Dialogue Style" in output
        assert "## Narrative Philosophy" in output
        assert "## Anti-Patterns" in output
        assert "## Pacing Philosophy" not in output

    def test_get_view_missing_persona_exits_0(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_stories_dir(monkeypatch, tmp_path)
        _create_story_dir(tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            persona_builder.cmd_get_view(STORY_NAME, "outline")

        assert exc_info.value.code == 0

    def test_get_view_invalid_view_exits_1(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            persona_builder.cmd_get_view(STORY_NAME, "invalid_view")

        assert exc_info.value.code == 1

    def test_get_view_invalid_view_outputs_json(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit):
            persona_builder.cmd_get_view(STORY_NAME, "invalid_view")

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "error"


class TestCmdRegenerate:
    def test_regenerate_archives_existing_persona(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_stories_dir(monkeypatch, tmp_path)
        story_dir = _create_story_dir(tmp_path)
        _write_required_savepoints(story_dir)
        _patch_generate_dependencies(monkeypatch)
        persona_dir = story_dir / "persona"
        persona_dir.mkdir(parents=True, exist_ok=True)
        original_persona = "original persona"
        (persona_dir / "persona.md").write_text(original_persona, encoding="utf-8")

        persona_builder.cmd_regenerate(STORY_NAME)

        history_dir = persona_dir / "history"
        archived_files = list(history_dir.glob("persona-*.md"))
        assert history_dir.is_dir()
        assert len(archived_files) == 1
        assert archived_files[0].read_text(encoding="utf-8") == original_persona

    def test_regenerate_no_existing_persona_behaves_like_generate(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_stories_dir(monkeypatch, tmp_path)
        story_dir = _create_story_dir(tmp_path)
        _write_required_savepoints(story_dir)
        _patch_generate_dependencies(monkeypatch)

        persona_builder.cmd_regenerate(STORY_NAME)

        assert (story_dir / "persona" / "persona.md").exists()

    def test_regenerate_archive_filename_format(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_stories_dir(monkeypatch, tmp_path)
        story_dir = _create_story_dir(tmp_path)
        _write_required_savepoints(story_dir)
        _patch_generate_dependencies(monkeypatch)
        persona_dir = story_dir / "persona"
        persona_dir.mkdir(parents=True, exist_ok=True)
        (persona_dir / "persona.md").write_text("existing persona", encoding="utf-8")

        persona_builder.cmd_regenerate(STORY_NAME)

        archived_files = list((persona_dir / "history").glob("persona-*.md"))
        assert len(archived_files) == 1
        assert re.fullmatch(r"persona-\d{8}-\d{6}\.md", archived_files[0].name)
