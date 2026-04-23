"""Verification tests for Issue #144 — wiki-extract Tool."""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.tools import _io, wiki_extract  # noqa: E402


def _write_state(
    story_dir: Path,
    *,
    outline: str = "Captain Vale reaches the Ember Port.",
    characters: object | None = None,
    settings: object | None = None,
) -> None:
    state = {
        "outline": outline,
        "characters": {} if characters is None else characters,
        "settings": {} if settings is None else settings,
        "chapters": {},
        "plot_threads": {},
    }
    (story_dir / "state.json").write_text(json.dumps(state, indent=2))


def _write_character_sheet(story_dir: Path, name: str, sheet: str) -> None:
    slug = name.lower().replace(" ", "-")
    (story_dir / "characters").mkdir(parents=True, exist_ok=True)
    (story_dir / "characters" / f"{slug}.json").write_text(
        json.dumps({"name": name, "sheet": sheet}, indent=2)
    )


def _write_setting_sheet(story_dir: Path, name: str, sheet: str) -> None:
    slug = name.lower().replace(" ", "-")
    (story_dir / "settings").mkdir(parents=True, exist_ok=True)
    (story_dir / "settings" / f"{slug}.json").write_text(
        json.dumps({"name": name, "sheet": sheet}, indent=2)
    )


def _write_wiki_page(
    story_dir: Path,
    *,
    subdir: str,
    slug: str,
    content: str,
) -> None:
    page_path = story_dir / "wiki" / subdir / f"{slug}.md"
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_text(content)


def _write_wiki_index(story_dir: Path, entries: list[str]) -> None:
    wiki_dir = story_dir / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    (wiki_dir / "index.md").write_text(
        "# Wiki Index\n\n<!-- slug | type | name | aliases -->\n\n"
        + "\n".join(entries)
        + "\n"
    )


def _set_stories_dir(monkeypatch: pytest.MonkeyPatch, stories_dir: Path) -> None:
    monkeypatch.setattr(_io, "STORIES_DIR", stories_dir)


def _set_fake_llm(monkeypatch: pytest.MonkeyPatch, responses: list[str]) -> None:
    remaining = list(responses)

    def _fake_chat_completion(prompt: str, *, model: str | None = None) -> str:
        assert model in {None, "test-model"}
        assert remaining, f"Unexpected LLM prompt: {prompt[:200]}"
        return remaining.pop(0)

    monkeypatch.setattr(wiki_extract, "_chat_completion", _fake_chat_completion)


def _run_main(args: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, dict]:
    original_argv = sys.argv[:]
    try:
        sys.argv = ["wiki_extract.py", *args]
        with pytest.raises(SystemExit) as exc_info:
            wiki_extract.main()
        code = int(exc_info.value.code)
    except FailedToRaise:
        code = 0
    finally:
        sys.argv = original_argv
    output = capsys.readouterr().out.strip()
    return code, json.loads(output) if output else {}


class FailedToRaise(Exception):
    pass


def _invoke_main(
    args: list[str], capsys: pytest.CaptureFixture[str]
) -> tuple[int, dict]:
    original_argv = sys.argv[:]
    try:
        sys.argv = ["wiki_extract.py", *args]
        try:
            wiki_extract.main()
        except SystemExit as exc:
            code = int(exc.code)
        else:
            code = 0
    finally:
        sys.argv = original_argv
    output = capsys.readouterr().out.strip()
    return code, json.loads(output) if output else {}


@pytest.fixture()
def story_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    stories_dir = tmp_path / "stories"
    story_dir = stories_dir / "test-story"
    (story_dir / "characters").mkdir(parents=True)
    (story_dir / "settings").mkdir(parents=True)
    _set_stories_dir(monkeypatch, stories_dir)
    return story_dir


def test_argparse_operations_registered() -> None:
    parser = wiki_extract.build_parser()

    args = parser.parse_args(["initial-populate", "--name", "test-story", "--dry-run"])
    assert args.operation == "initial-populate"
    assert args.apply is False

    args = parser.parse_args(
        [
            "update-from-chapter",
            "--name",
            "test-story",
            "--chapter-number",
            "3",
            "--chapter-text-path",
            "chapters/ch03.md",
        ]
    )
    assert args.operation == "update-from-chapter"
    assert args.chapter_number == 3


def test_initial_populate_dry_run_returns_valid_batch_payload(
    story_env: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_state(
        story_env,
        outline="Captain Vale reaches Ember Port while the Red Signal conspiracy grows.",
        characters=["Captain Vale"],
        settings={"Ember Port": {"summary": "A storm-battered harbor."}},
    )
    _write_character_sheet(
        story_env, "Captain Vale", "Captain Vale leads the courier ship."
    )
    _write_setting_sheet(
        story_env, "Ember Port", "Ember Port shelters smugglers and dockworkers."
    )
    _set_fake_llm(
        monkeypatch,
        [
            json.dumps(
                [
                    {
                        "name": "Captain Vale",
                        "type": "character",
                        "aliases": ["Vale"],
                        "description": "A starship captain at the center of the outline.",
                        "confidence": "planned",
                    },
                    {
                        "name": "Red Signal",
                        "type": "plot_thread",
                        "aliases": [],
                        "description": "A conspiracy thread that drives the early plot.",
                        "confidence": "planned",
                    },
                ]
            ),
            json.dumps(
                {
                    "primary_entity": {
                        "name": "Captain Vale",
                        "type": "character",
                        "aliases": ["Captain"],
                        "description": "Leader of a courier crew operating beyond formal law.",
                        "confidence": "planned",
                        "frontmatter": {"role": "protagonist", "status": "alive"},
                    },
                    "related_entities": [
                        {
                            "name": "Vale and Jun",
                            "type": "relationship",
                            "aliases": [],
                            "description": "A tense captain-engineer partnership.",
                            "confidence": "planned",
                            "frontmatter": {},
                        }
                    ],
                }
            ),
            json.dumps(
                {
                    "primary_entity": {
                        "name": "Ember Port",
                        "type": "location",
                        "aliases": [],
                        "description": "A harbor city where smugglers, officials, and crews intersect.",
                        "confidence": "planned",
                        "frontmatter": {"region": "Outer Reach"},
                    },
                    "related_entities": [
                        {
                            "name": "Dock Lantern Union",
                            "type": "faction",
                            "aliases": [],
                            "description": "A labor faction controlling key docks.",
                            "confidence": "planned",
                            "frontmatter": {},
                        },
                        {
                            "name": "Ash Key",
                            "type": "item",
                            "aliases": [],
                            "description": "A coded key tied to the port conspiracy.",
                            "confidence": "planned",
                            "frontmatter": {},
                        },
                    ],
                }
            ),
            *[
                json.dumps(
                    {
                        "l1": "Short summary.",
                        "l2": "Medium factual summary.",
                        "l3": "Long factual summary.",
                    }
                )
                for _ in range(6)
            ],
        ],
    )

    code, output = _invoke_main(
        ["initial-populate", "--name", "test-story", "--dry-run"], capsys
    )

    assert code == 0
    assert output["status"] == "ok"
    assert output["applied"] is False
    assert set(output) >= {"creates", "updates", "timeline_events"}
    assert output["updates"] == []
    assert output["timeline_events"] == []
    assert len(output["creates"]) == 6
    create = output["creates"][0]
    assert set(create) >= {
        "page_type",
        "page_name",
        "slug",
        "body",
        "confidence",
        "first_appearance",
        "aliases",
        "detail_levels",
        "frontmatter",
    }
    assert set(create["detail_levels"]) == {"L1", "L2", "L3"}
    assert all(isinstance(value, str) for value in create["detail_levels"].values())


def test_initial_populate_apply_invokes_run_batch(
    story_env: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_state(
        story_env, outline="Captain Vale enters Ember Port.", characters={}, settings={}
    )
    captured: dict[str, object] = {}

    _set_fake_llm(
        monkeypatch,
        [
            json.dumps(
                [
                    {
                        "name": "Captain Vale",
                        "type": "character",
                        "aliases": [],
                        "description": "A courier captain.",
                        "confidence": "planned",
                    }
                ]
            ),
            json.dumps({"l1": "L1", "l2": "L2", "l3": "L3"}),
        ],
    )

    def _fake_run_batch(name: str, payload: dict) -> dict:
        captured["name"] = name
        captured["payload"] = payload
        return {
            "created": 1,
            "updated": 0,
            "timeline_events": 0,
            "entity_counts": {"character": 1},
        }

    monkeypatch.setattr(wiki_extract, "run_batch", _fake_run_batch)

    code, output = _invoke_main(["initial-populate", "--name", "test-story"], capsys)

    assert code == 0
    assert output["applied"] is True
    assert output["created"] == 1
    assert captured["name"] == "test-story"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["creates"][0]["page_name"] == "Captain Vale"


def test_update_from_chapter_reads_chapter_file_path(
    story_env: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    chapter_dir = story_env / "chapters"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    chapter_path = chapter_dir / "chapter-3.md"
    chapter_path.write_text("Captain Vale docks at Ember Port and meets Jun.")
    _write_wiki_index(story_env, ["- captain-vale | character | Captain Vale | Vale"])
    _write_wiki_page(
        story_env,
        subdir="characters",
        slug="captain-vale",
        content=(
            "---\n"
            "slug: captain-vale\n"
            "name: Captain Vale\n"
            "type: character\n"
            "first_appearance: 1\n"
            "---\n\n"
            "Captain Vale commands the courier ship."
        ),
    )

    def _fake_chat_completion(prompt: str, *, model: str | None = None) -> str:
        if "Captain Vale docks at Ember Port" in prompt:
            return json.dumps(
                {
                    "new_entities": [],
                    "state_changes": [],
                    "timeline_events": [],
                    "new_aliases": [],
                }
            )
        raise AssertionError(f"Unexpected prompt: {prompt[:200]}")

    monkeypatch.setattr(wiki_extract, "_chat_completion", _fake_chat_completion)

    code, output = _invoke_main(
        [
            "update-from-chapter",
            "--name",
            "test-story",
            "--chapter-number",
            "3",
            "--chapter-text-path",
            "chapters/chapter-3.md",
            "--dry-run",
        ],
        capsys,
    )

    assert code == 0
    assert output["status"] == "ok"


def test_update_from_chapter_dry_run_produces_creates_updates_and_timeline_entries(
    story_env: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    chapter_dir = story_env / "chapters"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    chapter_path = chapter_dir / "chapter-4.md"
    chapter_path.write_text("Captain Vale loses the fleet beacon at Nova Station.")
    _write_wiki_index(story_env, ["- captain-vale | character | Captain Vale | Vale"])
    _write_wiki_page(
        story_env,
        subdir="characters",
        slug="captain-vale",
        content=(
            "---\n"
            "slug: captain-vale\n"
            "name: Captain Vale\n"
            "type: character\n"
            "first_appearance: 1\n"
            "aliases:\n"
            "  - Vale\n"
            "---\n\n"
            "Captain Vale commands the courier ship."
        ),
    )
    _set_fake_llm(
        monkeypatch,
        [
            json.dumps(
                {
                    "new_entities": [
                        {
                            "name": "Nova Station",
                            "type": "location",
                            "aliases": [],
                            "description": "A station where the crew regroups after losing the beacon.",
                            "confidence": "verified",
                            "frontmatter": {"region": "Outer Reach"},
                        }
                    ],
                    "state_changes": [
                        {
                            "slug": "captain-vale",
                            "frontmatter": {"status": "alive"},
                            "merge_body": "[Ch.4, verified] Vale loses the fleet beacon at Nova Station.",
                        }
                    ],
                    "timeline_events": [
                        {
                            "time": "Day 4, night",
                            "description": "Captain Vale loses the fleet beacon at Nova Station.",
                            "chapter": 4,
                        }
                    ],
                    "new_aliases": [
                        {"slug": "captain-vale", "aliases": ["Commander Vale"]}
                    ],
                }
            ),
            json.dumps({"l1": "L1", "l2": "L2", "l3": "L3"}),
        ],
    )

    code, output = _invoke_main(
        [
            "update-from-chapter",
            "--name",
            "test-story",
            "--chapter-number",
            "4",
            "--chapter-text-path",
            "chapters/chapter-4.md",
            "--dry-run",
        ],
        capsys,
    )

    assert code == 0
    assert len(output["creates"]) == 1
    assert len(output["updates"]) == 1
    assert len(output["timeline_events"]) == 1
    create = output["creates"][0]
    assert create["slug"] == "nova-station"
    assert set(create["detail_levels"]) == {"L1", "L2", "L3"}
    update = output["updates"][0]
    assert update["slug"] == "captain-vale"
    assert update["aliases"] == ["Commander Vale"]


def test_update_from_chapter_missing_chapter_file_exits_non_zero_with_json_error(
    story_env: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, output = _invoke_main(
        [
            "update-from-chapter",
            "--name",
            "test-story",
            "--chapter-number",
            "4",
            "--chapter-text-path",
            "chapters/missing.md",
        ],
        capsys,
    )

    assert code == 1
    assert output["status"] == "error"
    assert "not found" in output["message"]


@pytest.mark.parametrize(
    ("characters", "settings"),
    [
        (["Captain Vale"], ["Ember Port"]),
        ({"Captain Vale": {"role": "lead"}}, {"Ember Port": {"region": "Outer Reach"}}),
    ],
)
def test_initial_populate_tolerates_state_character_and_setting_shapes(
    story_env: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    characters: object,
    settings: object,
) -> None:
    _write_state(story_env, characters=characters, settings=settings)
    _set_fake_llm(
        monkeypatch,
        [json.dumps([])],
    )

    code, output = _invoke_main(
        ["initial-populate", "--name", "test-story", "--dry-run"], capsys
    )

    assert code == 0
    assert output["creates"] == []


def test_detail_levels_present_for_new_entities(
    story_env: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    chapter_dir = story_env / "chapters"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (chapter_dir / "chapter-5.md").write_text(
        "Nova Station appears for the first time."
    )
    _write_wiki_index(story_env, [])
    _set_fake_llm(
        monkeypatch,
        [
            json.dumps(
                {
                    "new_entities": [
                        {
                            "name": "Nova Station",
                            "type": "location",
                            "aliases": [],
                            "description": "A newly introduced station.",
                            "confidence": "verified",
                            "frontmatter": {},
                        }
                    ],
                    "state_changes": [],
                    "timeline_events": [],
                    "new_aliases": [],
                }
            ),
            json.dumps(
                {
                    "l1": "Station headline.",
                    "l2": "Station brief summary.",
                    "l3": "Station long summary.",
                }
            ),
        ],
    )

    code, output = _invoke_main(
        [
            "update-from-chapter",
            "--name",
            "test-story",
            "--chapter-number",
            "5",
            "--chapter-text-path",
            "chapters/chapter-5.md",
            "--dry-run",
        ],
        capsys,
    )

    assert code == 0
    detail_levels = output["creates"][0]["detail_levels"]
    assert set(detail_levels) == {"L1", "L2", "L3"}
    assert all(isinstance(value, str) for value in detail_levels.values())
