"""Verification tests for PR #118 workflow improvement fixes."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
OUTLINE_GENERATOR_SCRIPT = PROJECT_ROOT / "src" / "tools" / "outline_generator.py"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import src.tools.critique_runner as critique_runner
import src.tools.story_assembler as story_assembler
import src.tools.story_state as story_state
import src.tools.wiki_snapshot as wiki_snapshot


CHUNK_TYPES = (
    "core_story_foundation",
    "character_foundation",
    "setting_foundation",
    "plot_structure",
    "theme_message",
    "tone_style",
    "conflict_stakes",
    "world_rules_logic",
)


def _run_outline_generator(
    *args: str, stories_dir: Path | None = None
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
    if stories_dir is not None:
        env["STORIES_DIR"] = str(stories_dir)
    return subprocess.run(
        [sys.executable, str(OUTLINE_GENERATOR_SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
    )


def _write_markdown_savepoint(
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
        savepoint_dir.mkdir(parents=True, exist_ok=True)
        filepath = savepoint_dir / f"{step_name}.md"
    filepath.write_text(f"# Savepoint: {step_name}\n\n{data}", encoding="utf-8")


class TestWikiSnapshotTokenBudget:
    def test_enforce_token_budget_drops_lowest_relevance_pages_after_demotions(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            wiki_snapshot,
            "_get_page_content_at_level",
            lambda page, level: str(page["token_map"][level]),
        )
        monkeypatch.setattr(wiki_snapshot, "count_tokens", lambda content: int(content))

        pages = {
            "alpha": {
                "detail_level": "L3",
                "relevance_score": 0.9,
                "token_map": {"L1": 5, "L2": 15, "L3": 30},
            },
            "gamma": {
                "detail_level": "L3",
                "relevance_score": 0.4,
                "token_map": {"L1": 5, "L2": 20, "L3": 40},
            },
            "beta": {
                "detail_level": "L3",
                "relevance_score": 0.2,
                "token_map": {"L1": 5, "L2": 20, "L3": 40},
            },
        }
        sorted_slugs = ["alpha", "gamma", "beta"]

        wiki_snapshot._enforce_token_budget(
            pages,
            sorted_slugs,
            pov_character=None,
            primary_location=None,
            budget=11,
        )

        assert sorted_slugs == ["alpha", "gamma"]
        assert set(pages) == {"alpha", "gamma"}
        assert "beta" not in pages
        assert pages["alpha"]["detail_level"] == "L1"
        assert pages["gamma"]["detail_level"] == "L1"


class TestStoryStateDefaults:
    def test_ensure_state_defaults_adds_missing_pipeline_state(self) -> None:
        data = {"story_context": {}, "chapters": {}}

        result = story_state._ensure_state_defaults(data)

        assert result["pipeline_state"] == {
            "phase": None,
            "step": None,
            "chapter": None,
        }

    def test_ensure_state_defaults_preserves_valid_pipeline_state(self) -> None:
        data = {
            "story_context": {},
            "pipeline_state": {"phase": "outline", "step": "draft", "chapter": 3},
        }

        result = story_state._ensure_state_defaults(data)

        assert result["pipeline_state"] == {
            "phase": "outline",
            "step": "draft",
            "chapter": 3,
        }

    def test_ensure_state_defaults_replaces_invalid_pipeline_state(self) -> None:
        data = {"story_context": {}, "pipeline_state": "broken"}

        result = story_state._ensure_state_defaults(data)

        assert result["pipeline_state"] == {
            "phase": None,
            "step": None,
            "chapter": None,
        }


class TestOutlineGeneratorCliOutput:
    def test_generate_elements_stdout_returns_savepoint_only(
        self, tmp_path: Path
    ) -> None:
        stories_dir = tmp_path / "stories"
        story_name = "test-story"
        (stories_dir / story_name / "savepoints").mkdir(parents=True)

        for chunk_type in CHUNK_TYPES:
            _write_markdown_savepoint(
                stories_dir,
                story_name,
                f"story_analysis/{chunk_type}_chunk",
                f"Chunk content for {chunk_type}.",
            )

        result = _run_outline_generator(
            "--operation",
            "generate-elements",
            "--name",
            story_name,
            stories_dir=stories_dir,
        )

        assert result.returncode == 0, result.stderr
        output = json.loads(result.stdout)
        assert output["status"] == "success"
        assert output["operation"] == "generate-elements"
        assert output["data"] == {"savepoint": "story_elements"}
        assert (stories_dir / story_name / "savepoints" / "story_elements.md").exists()


class TestCritiqueRunnerModeHelpers:
    def test_critique_results_step_namespaces_outline_and_chapter(self) -> None:
        assert (
            critique_runner._critique_results_step("outline", 1)
            == "outline_critique_results_iteration_1"
        )
        assert (
            critique_runner._critique_results_step("chapter", 2)
            == "chapter_critique_results_iteration_2"
        )

    def test_prompt_prefix_matches_mode(self) -> None:
        assert critique_runner._prompt_prefix("outline") == "outline_review"
        assert critique_runner._prompt_prefix("chapter") == "chapter_review"

    def test_critic_types_for_mode_returns_expected_sets(self) -> None:
        expected_outline = [
            "audiobook-producer",
            "book-club-moderator",
            "commercial-fiction-editor",
            "literary-fiction-reviewer",
            "publishing-acquisitions-editor",
            "subject-expert",
        ]
        expected_chapter = [
            "commercial-fiction-editor",
            "chapter-pacing",
            "chapter-character-consistency",
        ]

        assert critique_runner._critic_types_for_mode("outline") == expected_outline
        assert critique_runner._critic_types_for_mode("chapter") == expected_chapter


class TestStoryAssemblerHelpers:
    def test_extract_state_chapter_text_reads_supported_fields(self) -> None:
        chapters = {"2": {"assembled": "Chapter two text"}}

        result = story_assembler._extract_state_chapter_text(chapters, 2)

        assert result == "Chapter two text"

    def test_load_chapter_content_falls_back_to_story_state(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(story_assembler, "_has_savepoint", lambda repo, step: False)

        result = story_assembler._load_chapter_content(
            repo=object(),
            story_state={"chapters": {"3": {"content": "Chapter three"}}},
            chapter_num=3,
        )

        assert result == "Chapter three"

    def test_discover_chapter_numbers_merges_savepoints_and_story_state(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            story_assembler,
            "_list_savepoint_names",
            lambda repo: [
                "chapter_2_complete",
                "chapter_10/complete",
                "chapter_3",
                "outline",
            ],
        )

        chapter_numbers = story_assembler._discover_chapter_numbers(
            repo=object(),
            story_state={"chapters": {"1": {}, 4: {}}},
        )

        assert chapter_numbers == [1, 2, 3, 4, 10]
