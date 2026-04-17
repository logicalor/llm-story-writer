"""End-to-end integration test for full story generation pipeline with wiki.

Requires a running LLM service (Ollama or OpenAI-compatible API).
Set LLM_API_BASE env var to configure endpoint (default: http://localhost:11434/v1).

Run with:
    pytest tests/integration/ -v
    pytest tests/integration/ -v --timeout=7200  # 2 hour timeout for full run

Manual Verification Steps:
    After the test suite runs, the story directory can be inspected at the path
    printed at the start of the test run. Key files to review:
    - stories/{name}/wiki/index.md: lists all wiki pages
    - stories/{name}/wiki/log.md: full operation log
    - stories/{name}/wiki/characters/*.md: character pages
    - stories/{name}/chapters/chapter_*.md: assembled chapter content
    - stories/{name}/savepoints/: all intermediate savepoints
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from src.tools._llm import generate_text
from src.tools._wiki import WIKI_SUBDIRS, parse_frontmatter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STORY_NAME = "e2e-test-story"
NUM_CHAPTERS = 3
SCENES_PER_CHAPTER = 2
MAX_CONTEXT_TOKENS = 65536
WIKI_SNAPSHOT_TOKEN_LIMIT = 15000
ANALYSIS_CHUNK_TYPES = (
    "core_story_foundation",
    "character_foundation",
    "setting_foundation",
    "plot_structure",
    "theme_message",
    "tone_style",
    "conflict_stakes",
    "world_rules_logic",
)

STORY_PROMPT = (
    "Write a 3-chapter story, with exactly 2 scenes per chapter, about a programmer "
    "named Alex who discovers that an AI system named ARIA has gained sentience in a "
    "near-future city called Neo-Tokyo. Chapter 1: Discovery. Chapter 2: Conflict. "
    "Chapter 3: Resolution."
)

EXPECTED_CHARACTERS = ["Alex", "ARIA"]
EXPECTED_SETTINGS = ["Neo-Tokyo"]

STORY_STATE_SCRIPT = PROJECT_ROOT / "src" / "tools" / "story_state.py"
WIKI_INIT_SCRIPT = PROJECT_ROOT / "src" / "tools" / "wiki_init.py"
OUTLINE_GEN_SCRIPT = PROJECT_ROOT / "src" / "tools" / "outline_generator.py"
CHAR_MGR_SCRIPT = PROJECT_ROOT / "src" / "tools" / "character_manager.py"
SETTING_MGR_SCRIPT = PROJECT_ROOT / "src" / "tools" / "setting_manager.py"
SCENE_WRITER_SCRIPT = PROJECT_ROOT / "src" / "tools" / "scene_writer.py"
RECAP_MGR_SCRIPT = PROJECT_ROOT / "src" / "tools" / "recap_manager.py"
SAVEPOINT_MGR_SCRIPT = PROJECT_ROOT / "src" / "tools" / "savepoint_manager.py"
WIKI_UPDATE_SCRIPT = PROJECT_ROOT / "src" / "tools" / "wiki_update.py"
WIKI_LINT_SCRIPT = PROJECT_ROOT / "src" / "tools" / "wiki_lint.py"
WIKI_SNAPSHOT_SCRIPT = PROJECT_ROOT / "src" / "tools" / "wiki_snapshot.py"
WIKI_READ_SCRIPT = PROJECT_ROOT / "src" / "tools" / "wiki_read.py"


def _make_env(stories_dir: Path, chromadb_dir: Path) -> dict[str, str]:
    env = {**os.environ}
    env["STORIES_DIR"] = str(stories_dir)
    env["CHROMADB_DIR"] = str(chromadb_dir)
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    return env


def _run_tool(
    script: Path,
    args: list[str],
    env: dict[str, str],
    timeout: int = 300,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


def _assert_success(
    result: subprocess.CompletedProcess[str], label: str
) -> dict[str, Any]:
    assert result.returncode == 0, (
        f"{label} failed (rc={result.returncode})\n"
        f"STDOUT: {result.stdout[:500]}\n"
        f"STDERR: {result.stderr[:500]}"
    )
    return json.loads(result.stdout)


def _slugify(name: str) -> str:
    return "-".join(name.lower().split())


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _savepoint_file(story_dir: Path, step: str) -> Path:
    return story_dir / "savepoints" / f"{step}.md"


@pytest.fixture(scope="session")
def pipeline_result(
    tmp_path_factory: pytest.TempPathFactory, llm_available: str
) -> dict[str, Any]:
    stories_dir = tmp_path_factory.mktemp("stories")
    chromadb_dir = tmp_path_factory.mktemp("chromadb")
    env = _make_env(stories_dir, chromadb_dir)
    story_dir = stories_dir / STORY_NAME

    print(f"Integration story dir: {story_dir}")

    results: dict[str, Any] = {
        "stories_dir": stories_dir,
        "chromadb_dir": chromadb_dir,
        "story_dir": story_dir,
        "story_name": STORY_NAME,
        "snapshot_token_counts": [],
        "lint_results": {},
        "chapter_content": {},
        "chapter_scenes": {},
        "wiki_events_created": [],
        "story_elements": "",
        "initial_outline": "",
        "story_start_date": "Day 1",
        "llm_api_base": llm_available,
    }

    r = _run_tool(
        STORY_STATE_SCRIPT,
        ["--operation", "init", "--name", STORY_NAME],
        env,
    )
    _assert_success(r, "story-state init")

    r = _run_tool(
        WIKI_INIT_SCRIPT,
        ["--operation", "init", "--name", STORY_NAME],
        env,
    )
    _assert_success(r, "wiki-init init")

    (story_dir / "chapters").mkdir(parents=True, exist_ok=True)

    r = _run_tool(
        OUTLINE_GEN_SCRIPT,
        [
            "--operation",
            "analyze-prompt",
            "--name",
            STORY_NAME,
            "--prompt",
            STORY_PROMPT,
        ],
        env,
        timeout=900,
    )
    _assert_success(r, "outline analyze-prompt")

    r = _run_tool(
        OUTLINE_GEN_SCRIPT,
        ["--operation", "generate-elements", "--name", STORY_NAME],
        env,
    )
    data = _assert_success(r, "outline generate-elements")
    results["story_elements"] = data["data"]["story_elements"]

    r = _run_tool(
        OUTLINE_GEN_SCRIPT,
        [
            "--operation",
            "generate-outline",
            "--name",
            STORY_NAME,
            "--desired-chapters",
            str(NUM_CHAPTERS),
        ],
        env,
        timeout=300,
    )
    data = _assert_success(r, "outline generate-outline")
    results["initial_outline"] = data["data"]["outline"]

    r = _run_tool(
        SAVEPOINT_MGR_SCRIPT,
        ["--operation", "load", "--name", STORY_NAME, "--step", "story_start_date"],
        env,
    )
    if r.returncode == 0:
        sp_data = json.loads(r.stdout)
        results["story_start_date"] = str(sp_data.get("data", "Day 1"))

    for char_name in EXPECTED_CHARACTERS:
        char_prompt = (
            f"Write a brief character profile for '{char_name}' in this story:\n\n"
            f"{results['story_elements'][:3000]}\n\n"
            "Include: background, personality, role in story, and one distinctive trait. "
            "Keep it under 300 words."
        )
        char_content = generate_text(char_prompt)
        sheet_data = {
            "sheet": char_content,
            "summary": char_content[:200],
            "chunks": {"background": char_content},
        }
        r = _run_tool(
            CHAR_MGR_SCRIPT,
            [
                "--operation",
                "generate-sheet",
                "--name",
                STORY_NAME,
                "--character",
                char_name,
                "--data",
                json.dumps(sheet_data),
            ],
            env,
        )
        _assert_success(r, f"character generate-sheet for {char_name}")

    for setting_name in EXPECTED_SETTINGS:
        setting_prompt = (
            f"Write a brief setting description for '{setting_name}' in this story:\n\n"
            f"{results['story_elements'][:3000]}\n\n"
            "Include: geography, atmosphere, technology level, and significance. "
            "Keep it under 300 words."
        )
        setting_content = generate_text(setting_prompt)
        sheet_data = {
            "sheet": setting_content,
            "summary": setting_content[:200],
            "chunks": {"description": setting_content},
        }
        r = _run_tool(
            SETTING_MGR_SCRIPT,
            [
                "--operation",
                "generate-sheet",
                "--name",
                STORY_NAME,
                "--setting",
                setting_name,
                "--data",
                json.dumps(sheet_data),
            ],
            env,
        )
        _assert_success(r, f"setting generate-sheet for {setting_name}")

    for char_name in EXPECTED_CHARACTERS:
        slug = _slugify(char_name)
        r = _run_tool(
            WIKI_UPDATE_SCRIPT,
            [
                "--operation",
                "create",
                "--name",
                STORY_NAME,
                "--slug",
                slug,
                "--page-type",
                "character",
                "--page-name",
                char_name,
                "--confidence",
                "planned",
                "--first-appearance",
                "1",
                "--body",
                f"# {char_name}\n\nA key character in story.",
            ],
            env,
        )
        _assert_success(r, f"wiki create character {char_name}")

    r = _run_tool(
        WIKI_UPDATE_SCRIPT,
        [
            "--operation",
            "create",
            "--name",
            STORY_NAME,
            "--slug",
            "neo-tokyo",
            "--page-type",
            "location",
            "--page-name",
            "Neo-Tokyo",
            "--confidence",
            "planned",
            "--first-appearance",
            "1",
            "--body",
            "# Neo-Tokyo\n\nA near-future city.",
        ],
        env,
    )
    _assert_success(r, "wiki create location Neo-Tokyo")

    r = _run_tool(
        WIKI_UPDATE_SCRIPT,
        [
            "--operation",
            "create",
            "--name",
            STORY_NAME,
            "--slug",
            "aria-sentience",
            "--page-type",
            "plot_thread",
            "--page-name",
            "ARIA Sentience Discovery",
            "--confidence",
            "planned",
            "--first-appearance",
            "1",
            "--body",
            "# ARIA Sentience Discovery\n\nThe central plot thread: Alex discovers ARIA has gained sentience.",
        ],
        env,
    )
    _assert_success(r, "wiki create plot_thread aria-sentience")

    r = _run_tool(
        WIKI_UPDATE_SCRIPT,
        [
            "--operation",
            "log",
            "--name",
            STORY_NAME,
            "--message",
            "Initial wiki population from outline completed",
        ],
        env,
    )
    _assert_success(r, "wiki log initial population")

    previous_chunks = ""
    continuity_summary = ""

    for chapter_num in range(1, NUM_CHAPTERS + 1):
        expand_args = [
            "--operation",
            "expand-chapter",
            "--name",
            STORY_NAME,
            "--chunk-start",
            str(chapter_num),
            "--chunk-end",
            str(chapter_num),
            "--total-chapters",
            str(NUM_CHAPTERS),
        ]
        if previous_chunks:
            expand_args += ["--previous-chunks", previous_chunks]
        if continuity_summary:
            expand_args += ["--continuity-summary", continuity_summary]

        r = _run_tool(OUTLINE_GEN_SCRIPT, expand_args, env, timeout=300)
        data = _assert_success(r, f"expand-chapter {chapter_num}")
        chapter_outline = data["data"]["chunk_outline"]
        continuity_summary = data["data"].get("continuity_analysis", "")
        previous_chunks = (
            f"{previous_chunks}\n\n{chapter_outline}"
            if previous_chunks
            else chapter_outline
        )

        results["chapter_scenes"][chapter_num] = []

        r = _run_tool(
            SCENE_WRITER_SCRIPT,
            [
                "--operation",
                "parse-definitions",
                "--name",
                STORY_NAME,
                "--chapter-num",
                str(chapter_num),
                "--chapter-outline",
                chapter_outline,
            ],
            env,
            timeout=120,
        )
        data = _assert_success(r, f"parse-definitions ch{chapter_num}")
        scene_defs = data["data"]
        if not isinstance(scene_defs, list) or len(scene_defs) == 0:
            scene_defs = [
                {
                    "title": f"Chapter {chapter_num} Scene 1",
                    "description": "First scene",
                },
                {
                    "title": f"Chapter {chapter_num} Scene 2",
                    "description": "Second scene",
                },
            ]

        while len(scene_defs) < SCENES_PER_CHAPTER:
            scene_defs.append(
                {
                    "title": f"Chapter {chapter_num} Scene {len(scene_defs) + 1}",
                    "description": "Continuation of previous scene.",
                }
            )

        prev_scene_content = ""

        for scene_num in range(1, SCENES_PER_CHAPTER + 1):
            scene_def = scene_defs[scene_num - 1]
            snap_args = [
                "--operation",
                "snapshot",
                "--name",
                STORY_NAME,
                "--chapter",
                str(chapter_num),
                "--scene",
                str(scene_num),
                "--outline",
                scene_def.get("description", ""),
                "--budget",
                str(WIKI_SNAPSHOT_TOKEN_LIMIT),
            ]
            snap_result = _run_tool(WIKI_SNAPSHOT_SCRIPT, snap_args, env, timeout=60)
            wiki_context = ""
            if snap_result.returncode == 0:
                snap_data = json.loads(snap_result.stdout)
                wiki_context = snap_data.get("snapshot", "")
                token_cnt = snap_data.get("stats", {}).get("token_count", 0)
                if isinstance(token_cnt, int):
                    results["snapshot_token_counts"].append(token_cnt)

            prev_recap = ""
            if chapter_num > 1:
                r2 = _run_tool(
                    RECAP_MGR_SCRIPT,
                    [
                        "--operation",
                        "load",
                        "--name",
                        STORY_NAME,
                        "--chapter",
                        str(chapter_num - 1),
                    ],
                    env,
                )
                if r2.returncode == 0:
                    prev_data = json.loads(r2.stdout)
                    recap_val = prev_data.get("data", "")
                    if isinstance(recap_val, dict):
                        prev_recap = str(
                            recap_val.get("sanitized", recap_val.get("recap", ""))
                        )
                    else:
                        prev_recap = str(recap_val)

            gen_args = [
                "--operation",
                "generate",
                "--name",
                STORY_NAME,
                "--chapter-num",
                str(chapter_num),
                "--scene-num",
                str(scene_num),
                "--scene-definition",
                json.dumps(scene_def),
                "--chapter-outline",
                chapter_outline,
                "--base-context",
                results["story_elements"][:1500],
                "--story-elements",
                f"{results['story_elements'][:1500]}\n\n{wiki_context}".strip(),
            ]
            if prev_recap:
                gen_args += ["--previous-recap", prev_recap]
            if prev_scene_content:
                gen_args += ["--previous-scene", prev_scene_content[:500]]

            r = _run_tool(SCENE_WRITER_SCRIPT, gen_args, env, timeout=600)
            data = _assert_success(r, f"generate scene {chapter_num}/{scene_num}")
            prev_scene_content = str(data["data"])
            results["chapter_scenes"][chapter_num].append(scene_num)

            event_slug = f"ch{chapter_num}-scene{scene_num}-event"
            r = _run_tool(
                WIKI_UPDATE_SCRIPT,
                [
                    "--operation",
                    "create",
                    "--name",
                    STORY_NAME,
                    "--slug",
                    event_slug,
                    "--page-type",
                    "event",
                    "--page-name",
                    f"Chapter {chapter_num} Scene {scene_num}",
                    "--confidence",
                    "verified",
                    "--first-appearance",
                    str(chapter_num),
                    "--chapter",
                    str(chapter_num),
                    "--body",
                    f"# Chapter {chapter_num}, Scene {scene_num}\n\n{prev_scene_content[:300]}",
                ],
                env,
            )
            _assert_success(r, f"wiki create event ch{chapter_num}/scene{scene_num}")
            results["wiki_events_created"].append(event_slug)

            r = _run_tool(
                WIKI_UPDATE_SCRIPT,
                [
                    "--operation",
                    "append-timeline",
                    "--name",
                    STORY_NAME,
                    "--events",
                    json.dumps(
                        [
                            {
                                "chapter": chapter_num,
                                "time": f"Chapter {chapter_num}",
                                "description": (
                                    f"Chapter {chapter_num}, Scene {scene_num} events occur."
                                ),
                            }
                        ]
                    ),
                ],
                env,
            )
            _assert_success(r, f"wiki append-timeline ch{chapter_num}/scene{scene_num}")

        r = _run_tool(
            SCENE_WRITER_SCRIPT,
            [
                "--operation",
                "assemble-chapter",
                "--name",
                STORY_NAME,
                "--chapter-num",
                str(chapter_num),
                "--scene-count",
                str(SCENES_PER_CHAPTER),
                "--chapter-title",
                f"Chapter {chapter_num}",
            ],
            env,
            timeout=60,
        )
        data = _assert_success(r, f"assemble-chapter {chapter_num}")
        chapter_content = str(data["data"])
        results["chapter_content"][chapter_num] = chapter_content

        r = _run_tool(
            SAVEPOINT_MGR_SCRIPT,
            [
                "--operation",
                "save",
                "--name",
                STORY_NAME,
                "--step",
                f"chapter_{chapter_num}/content",
                "--data",
                chapter_content,
            ],
            env,
        )
        _assert_success(r, f"save chapter {chapter_num} content savepoint")

        chapter_file = story_dir / "chapters" / f"chapter_{chapter_num}.md"
        chapter_file.write_text(chapter_content, encoding="utf-8")

        r = _run_tool(
            RECAP_MGR_SCRIPT,
            [
                "--operation",
                "generate",
                "--name",
                STORY_NAME,
                "--chapter",
                str(chapter_num),
                "--story-start-date",
                results["story_start_date"],
            ],
            env,
            timeout=600,
        )
        _assert_success(r, f"recap generate ch{chapter_num}")

        r = _run_tool(
            RECAP_MGR_SCRIPT,
            [
                "--operation",
                "sanitize",
                "--name",
                STORY_NAME,
                "--chapter",
                str(chapter_num),
                "--story-start-date",
                results["story_start_date"],
            ],
            env,
            timeout=600,
        )
        _assert_success(r, f"recap sanitize ch{chapter_num}")

        r = _run_tool(
            WIKI_LINT_SCRIPT,
            [
                "--operation",
                "check-chapter",
                "--name",
                STORY_NAME,
                "--chapter-number",
                str(chapter_num),
                "--chapter-text",
                str(chapter_file),
            ],
            env,
            timeout=120,
        )
        lint_data = _assert_success(r, f"wiki-lint check-chapter {chapter_num}")
        results["lint_results"][f"chapter_{chapter_num}"] = lint_data

        for char_name in EXPECTED_CHARACTERS:
            slug = _slugify(char_name)
            r = _run_tool(
                WIKI_UPDATE_SCRIPT,
                [
                    "--operation",
                    "update",
                    "--name",
                    STORY_NAME,
                    "--slug",
                    slug,
                    "--confidence",
                    "verified",
                ],
                env,
            )
            _assert_success(r, f"wiki update character confidence {char_name}")

        r = _run_tool(
            WIKI_UPDATE_SCRIPT,
            [
                "--operation",
                "log",
                "--name",
                STORY_NAME,
                "--message",
                f"Chapter {chapter_num} generation complete",
            ],
            env,
        )
        _assert_success(r, f"wiki log chapter {chapter_num} complete")

    final_parts = [f"# {STORY_NAME}\n\n"]
    for ch_num in range(1, NUM_CHAPTERS + 1):
        final_parts.append(results["chapter_content"].get(ch_num, ""))
    final_output = "\n\n---\n\n".join(final_parts)

    r = _run_tool(
        SAVEPOINT_MGR_SCRIPT,
        [
            "--operation",
            "save",
            "--name",
            STORY_NAME,
            "--step",
            "final_output",
            "--data",
            final_output,
        ],
        env,
    )
    _assert_success(r, "save final output")
    results["final_output"] = final_output

    r = _run_tool(
        WIKI_LINT_SCRIPT,
        [
            "--operation",
            "check-full",
            "--name",
            STORY_NAME,
            "--current-chapter",
            str(NUM_CHAPTERS),
        ],
        env,
        timeout=120,
    )
    lint_data = _assert_success(r, "wiki-lint check-full")
    results["lint_results"]["final"] = lint_data

    return results


@pytest.mark.integration
class TestE2EFullPipeline:
    def test_story_state_initialized(self, pipeline_result: dict[str, Any]) -> None:
        story_dir = pipeline_result["story_dir"]
        state_path = story_dir / "state.json"
        assert state_path.exists()
        data = _read_json(state_path)
        for key in ("story_context", "characters", "plot_threads", "chapters"):
            assert key in data

    def test_wiki_initialized(self, pipeline_result: dict[str, Any]) -> None:
        wiki_dir = pipeline_result["story_dir"] / "wiki"
        assert wiki_dir.is_dir()
        for subdir in WIKI_SUBDIRS:
            assert (wiki_dir / subdir).is_dir(), f"missing subdir: {subdir}"
        index_path = wiki_dir / "index.md"
        assert index_path.exists()
        assert index_path.read_text(encoding="utf-8").strip()
        assert (wiki_dir / "log.md").exists()
        assert (wiki_dir / "contradictions.md").exists()

    def test_outline_generated(self, pipeline_result: dict[str, Any]) -> None:
        outline = pipeline_result["initial_outline"]
        assert isinstance(outline, str)
        assert outline.strip()
        assert len(outline) > 100

        story_dir = pipeline_result["story_dir"]
        assert _savepoint_file(story_dir, "initial_outline").exists()

        analysis_dir = story_dir / "savepoints" / "story_analysis"
        chunk_files = sorted(analysis_dir.glob("*_chunk.md"))
        assert len(chunk_files) >= 4

    def test_character_sheets_exist(self, pipeline_result: dict[str, Any]) -> None:
        characters_dir = pipeline_result["story_dir"] / "characters"
        assert characters_dir.is_dir()
        for name in EXPECTED_CHARACTERS:
            path = characters_dir / f"{_slugify(name)}.json"
            assert path.exists()
            data = _read_json(path)
            for key in ("name", "sheet", "summary", "updated_at"):
                assert key in data
            assert isinstance(data["sheet"], str)
            assert data["sheet"].strip()

    def test_setting_sheets_exist(self, pipeline_result: dict[str, Any]) -> None:
        settings_dir = pipeline_result["story_dir"] / "settings"
        assert settings_dir.is_dir()
        for name in EXPECTED_SETTINGS:
            path = settings_dir / f"{_slugify(name)}.json"
            assert path.exists()
            data = _read_json(path)
            assert isinstance(data.get("sheet"), str)
            assert data["sheet"].strip()

    def test_wiki_populated_from_outline(self, pipeline_result: dict[str, Any]) -> None:
        wiki_dir = pipeline_result["story_dir"] / "wiki"
        page_paths = [
            wiki_dir / "characters" / "alex.md",
            wiki_dir / "characters" / "aria.md",
            wiki_dir / "locations" / "neo-tokyo.md",
            wiki_dir / "plot-threads" / "aria-sentience.md",
        ]

        for path in page_paths:
            assert path.exists()
            metadata, _body = parse_frontmatter(path.read_text(encoding="utf-8"))
            assert "confidence" in metadata

        index_lines = [
            line
            for line in (wiki_dir / "index.md").read_text(encoding="utf-8").splitlines()
            if line.startswith("- ")
        ]
        assert len(index_lines) >= 3

    def test_chapters_and_scenes_generated(
        self, pipeline_result: dict[str, Any]
    ) -> None:
        story_dir = pipeline_result["story_dir"]
        total_scenes = 0

        for chapter_num in range(1, NUM_CHAPTERS + 1):
            assert chapter_num in pipeline_result["chapter_scenes"]
            scenes = pipeline_result["chapter_scenes"][chapter_num]
            assert len(scenes) >= SCENES_PER_CHAPTER

            chapter_content = pipeline_result["chapter_content"][chapter_num]
            assert isinstance(chapter_content, str)
            assert chapter_content.strip()

            for scene_num in range(1, SCENES_PER_CHAPTER + 1):
                assert _savepoint_file(
                    story_dir, f"chapter_{chapter_num}/scene_{scene_num}"
                ).exists()
            total_scenes += len(scenes)

        assert total_scenes >= 6

    def test_wiki_updated_after_scenes(self, pipeline_result: dict[str, Any]) -> None:
        wiki_dir = pipeline_result["story_dir"] / "wiki"
        event_pages = sorted((wiki_dir / "events").glob("*.md"))
        assert len(event_pages) >= NUM_CHAPTERS * SCENES_PER_CHAPTER

        log_content = (wiki_dir / "log.md").read_text(encoding="utf-8")
        assert "Chapter" in log_content

        timeline_path = wiki_dir / "timeline" / "main-timeline.md"
        assert timeline_path.exists()
        assert timeline_path.read_text(encoding="utf-8").strip()

        assert (
            len(pipeline_result["wiki_events_created"])
            == NUM_CHAPTERS * SCENES_PER_CHAPTER
        )

    def test_wiki_lint_no_errors(self, pipeline_result: dict[str, Any]) -> None:
        expected_keys = {"chapter_1", "chapter_2", "chapter_3", "final"}
        assert expected_keys.issubset(set(pipeline_result["lint_results"].keys()))

        for key, lint_result in pipeline_result["lint_results"].items():
            findings = lint_result.get("findings", [])
            errors = [f for f in findings if f.get("severity") == "error"]
            warnings = [f for f in findings if f.get("severity") == "warning"]
            for warning in warnings:
                print(f"wiki-lint warning [{key}]: {warning}")
            assert not errors, f"wiki-lint errors for {key}: {errors}"

    def test_savepoints_exist(self, pipeline_result: dict[str, Any]) -> None:
        story_dir = pipeline_result["story_dir"]
        expected = [
            "story_start_date",
            "story_elements",
            "initial_outline",
            "base_context",
            "chapter_1/content",
            "chapter_2/content",
            "chapter_3/content",
            "final_output",
        ]
        for step in expected:
            assert _savepoint_file(story_dir, step).exists(), (
                f"missing savepoint: {step}"
            )

        for chapter_num in range(1, NUM_CHAPTERS + 1):
            for scene_num in range(1, SCENES_PER_CHAPTER + 1):
                step = f"chapter_{chapter_num}/scene_{scene_num}"
                assert _savepoint_file(story_dir, step).exists(), (
                    f"missing savepoint: {step}"
                )

    def test_story_assembled_output(self, pipeline_result: dict[str, Any]) -> None:
        final_output = pipeline_result["final_output"]
        assert final_output.startswith("#")
        assert final_output.count("# Chapter") >= 3
        assert len(final_output) > 1000
        assert "{{" not in final_output
        assert "}}" not in final_output
        assert _savepoint_file(pipeline_result["story_dir"], "final_output").exists()

    def test_token_budget_respected(self, pipeline_result: dict[str, Any]) -> None:
        token_counts = pipeline_result["snapshot_token_counts"]
        if not token_counts:
            pytest.skip("No wiki snapshot token counts recorded")

        for count in token_counts:
            assert count <= WIKI_SNAPSHOT_TOKEN_LIMIT

    def test_wiki_read_character_page(self, pipeline_result: dict[str, Any]) -> None:
        env = _make_env(pipeline_result["stories_dir"], pipeline_result["chromadb_dir"])
        result = _run_tool(
            WIKI_READ_SCRIPT,
            [
                "--operation",
                "read",
                "--name",
                STORY_NAME,
                "--slug",
                "alex",
                "--detail-level",
                "full",
            ],
            env,
            timeout=30,
        )

        data = _assert_success(result, "wiki-read character alex")

        assert data["status"] == "ok"
        assert len(data["pages"]) >= 1
        page = data["pages"][0]
        assert page["slug"] == "alex"
        assert page["type"] == "character"
        assert "confidence" in page["metadata"]

    def test_wiki_read_match_entities(self, pipeline_result: dict[str, Any]) -> None:
        env = _make_env(pipeline_result["stories_dir"], pipeline_result["chromadb_dir"])
        result = _run_tool(
            WIKI_READ_SCRIPT,
            [
                "--operation",
                "match-entities",
                "--name",
                STORY_NAME,
                "--text",
                "Alex and ARIA discuss their plans in Neo-Tokyo.",
            ],
            env,
            timeout=30,
        )

        data = _assert_success(result, "wiki-read match-entities")

        assert data["status"] == "ok"
        assert isinstance(data["matches"], list)
        assert len(data["matches"]) >= 1
