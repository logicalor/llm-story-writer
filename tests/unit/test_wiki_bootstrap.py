"""Verification tests for Issue #294 — wiki bootstrap population."""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from src.tools import _io, wiki_extract  # noqa: E402
from src.tools.wiki_init import _init_wiki_for_story  # noqa: E402
from tools import _io as api_io  # noqa: E402
from tools import _wiki_api  # noqa: E402


def _set_stories_dir(monkeypatch: pytest.MonkeyPatch, stories_dir: Path) -> None:
    monkeypatch.setattr(_io, "STORIES_DIR", stories_dir)
    monkeypatch.setattr(api_io, "STORIES_DIR", stories_dir)


def _set_fake_llm(monkeypatch: pytest.MonkeyPatch, responses: list[str]) -> None:
    remaining = list(responses)

    def _fake_chat_completion(
        prompt: str, *, model: str | None = None, base_url: str | None = None
    ) -> str:
        assert model in {None, "test-model"}
        assert remaining, f"Unexpected LLM prompt: {prompt[:200]}"
        return remaining.pop(0)

    monkeypatch.setattr(wiki_extract, "_chat_completion", _fake_chat_completion)
    monkeypatch.setattr(_wiki_api, "_chat_completion", _fake_chat_completion)


def _write_character_sheet(story_dir: Path, name: str, sheet: str) -> None:
    slug = name.lower().replace(" ", "-")
    (story_dir / "characters" / f"{slug}.json").write_text(
        json.dumps({"name": name, "sheet": sheet}, indent=2)
    )


def _write_existing_character_page(story_dir: Path, slug: str, name: str) -> None:
    (story_dir / "wiki" / "characters" / f"{slug}.md").write_text(
        "---\n"
        f"name: {name}\n"
        f"slug: {slug}\n"
        "type: character\n"
        "first_appearance: 1\n"
        "---\n\n"
        f"Existing page for {name}.\n"
    )


def _outline_entity(name: str) -> dict[str, object]:
    return {
        "name": name,
        "type": "character",
        "aliases": [],
        "description": f"{name} drives the early story beats.",
        "confidence": "planned",
    }


def _sheet_response(name: str) -> dict[str, object]:
    return {
        "primary_entity": {
            "name": name,
            "type": "character",
            "aliases": [],
            "description": f"{name} sheet establishes core facts.",
            "confidence": "planned",
            "frontmatter": {"role": "lead"},
        },
        "related_entities": [],
    }


def _detail_levels() -> dict[str, str]:
    return {
        "l1": "Short summary.",
        "l2": "Medium summary.",
        "l3": "Long summary.",
    }


def _init_story_wiki(story_dir: Path) -> Path:
    result = _init_wiki_for_story(story_dir.name, _io.STORIES_DIR)
    assert result["status"] == "ok"
    return story_dir / "wiki"


@pytest.fixture()
def story_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    stories_dir = tmp_path / "stories"
    story_dir = stories_dir / "test-story"
    (story_dir / "characters").mkdir(parents=True)
    (story_dir / "settings").mkdir(parents=True)
    _set_stories_dir(monkeypatch, stories_dir)
    return story_dir


def test_bootstrap_creates_pages_from_outline(
    story_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wiki_dir = _init_story_wiki(story_env)
    monkeypatch.setattr(
        wiki_extract,
        "_load_outline_savepoint",
        lambda story_dir: "Chapter 1 outline with Captain Vale.",
    )
    _set_fake_llm(
        monkeypatch,
        [
            json.dumps([_outline_entity("Captain Vale")]),
            json.dumps(_detail_levels()),
        ],
    )

    result = wiki_extract.bootstrap_wiki_from_story("test-story")

    assert result["created"] == 1
    assert result["skipped"] == 0
    assert (wiki_dir / "characters" / "captain-vale.md").exists()


def test_bootstrap_creates_pages_from_character_sheet(
    story_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wiki_dir = _init_story_wiki(story_env)
    _write_character_sheet(
        story_env,
        "Captain Vale",
        "Captain Vale commands a courier ship through hostile space.",
    )
    monkeypatch.setattr(
        wiki_extract,
        "_load_outline_savepoint",
        lambda story_dir: "Minimal approved outline.",
    )
    _set_fake_llm(
        monkeypatch,
        [
            json.dumps([]),
            json.dumps(_sheet_response("Captain Vale")),
            json.dumps(_detail_levels()),
        ],
    )

    result = wiki_extract.bootstrap_wiki_from_story("test-story")

    assert result["created"] == 1
    assert result["skipped"] == 0
    assert (wiki_dir / "characters" / "captain-vale.md").exists()


def test_bootstrap_idempotent_skips_existing(
    story_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _init_story_wiki(story_env)
    _write_existing_character_page(story_env, "captain-vale", "Captain Vale")
    monkeypatch.setattr(
        wiki_extract,
        "_load_outline_savepoint",
        lambda story_dir: "Chapter 1 outline with Captain Vale.",
    )
    _set_fake_llm(
        monkeypatch,
        [
            json.dumps([_outline_entity("Captain Vale")]),
            json.dumps(_detail_levels()),
        ],
    )

    result = wiki_extract.bootstrap_wiki_from_story("test-story")

    assert result["created"] == 0
    assert result["skipped"] == 1


def test_bootstrap_returns_empty_when_no_outline(
    story_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _init_story_wiki(story_env)
    monkeypatch.setattr(wiki_extract, "_load_outline_savepoint", lambda story_dir: "")

    result = wiki_extract.bootstrap_wiki_from_story("test-story")

    assert result == {"created": 0, "skipped": 0, "entity_counts": {}}


def test_bootstrap_is_resumable_after_partial_run(
    story_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wiki_dir = _init_story_wiki(story_env)
    _write_existing_character_page(story_env, "captain-vale", "Captain Vale")
    monkeypatch.setattr(
        wiki_extract,
        "_load_outline_savepoint",
        lambda story_dir: "Chapter 1 outline with Captain Vale and Navigator Jun.",
    )
    _set_fake_llm(
        monkeypatch,
        [
            json.dumps(
                [
                    _outline_entity("Captain Vale"),
                    _outline_entity("Navigator Jun"),
                ]
            ),
            json.dumps(_detail_levels()),
            json.dumps(_detail_levels()),
        ],
    )

    result = wiki_extract.bootstrap_wiki_from_story("test-story")

    assert result["created"] == 1
    assert result["skipped"] == 1
    assert (wiki_dir / "characters" / "navigator-jun.md").exists()
