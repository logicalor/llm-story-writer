"""Integration tests for update_wiki_full_pass."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools import _io, _wiki_api, wiki_update  # noqa: E402
from tools._wiki import render_frontmatter, write_index  # noqa: E402


def _init_wiki(story_dir: Path) -> None:
    wiki_dir = story_dir / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    for subdir in [
        "characters",
        "locations",
        "events",
        "factions",
        "items",
        "plot-threads",
        "world-rules",
        "themes",
        "relationships",
        "timeline",
        "chapters",
    ]:
        (wiki_dir / subdir).mkdir(exist_ok=True)
    (wiki_dir / "log.md").write_text("# Wiki Change Log\n", encoding="utf-8")
    (wiki_dir / "timeline" / "main-timeline.md").write_text(
        "# Main Timeline\n\n",
        encoding="utf-8",
    )
    write_index(wiki_dir, [])


def _write_page(
    story_dir: Path,
    *,
    subdir: str,
    slug: str,
    metadata: dict[str, object],
    body: str,
) -> None:
    page_path = story_dir / "wiki" / subdir / f"{slug}.md"
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_text(
        render_frontmatter(metadata, body),
        encoding="utf-8",
    )


def _fake_chat_completion_factory(
    *,
    character_candidates: list[dict[str, object]] | None = None,
    merge_patch: dict[str, object] | None = None,
    detail_levels: dict[str, str] | None = None,
):
    character_payload = json.dumps(character_candidates or [])
    merge_payload = json.dumps(merge_patch or {"no_change": True})
    detail_payload = json.dumps(
        detail_levels
        or {
            "l1": "Short detail",
            "l2": "Medium detail",
            "l3": "Long detail",
        }
    )

    def _fake_chat_completion(
        prompt: str,
        *,
        model: str | None = None,
        base_url: str | None = None,
    ) -> str:
        assert model is None
        assert base_url is None
        if "Extract Characters from Chapter" in prompt:
            return character_payload
        if "Merge Wiki Page Patch" in prompt:
            return merge_payload
        if "Generate Wiki Detail Levels" in prompt:
            return detail_payload
        if "Extract " in prompt and "from Chapter" in prompt:
            return "[]"
        raise AssertionError(f"Unexpected LLM prompt: {prompt[:200]}")

    return _fake_chat_completion


@pytest.fixture()
def story_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    stories_dir = tmp_path / "stories"
    chromadb_dir = tmp_path / "chromadb"
    story_dir = stories_dir / "test-story"
    story_dir.mkdir(parents=True)
    chromadb_dir.mkdir(parents=True)
    _init_wiki(story_dir)

    monkeypatch.setenv("STORIES_DIR", str(stories_dir))
    monkeypatch.setenv("CHROMADB_DIR", str(chromadb_dir))
    monkeypatch.setattr(_io, "STORIES_DIR", stories_dir)
    monkeypatch.setattr(wiki_update, "CHROMADB_DIR", str(chromadb_dir))
    return story_dir


class TestWikiFullPass:
    def test_full_pass_returns_per_type_stats(
        self,
        story_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            _wiki_api,
            "_chat_completion",
            _fake_chat_completion_factory(),
        )

        result = _wiki_api.update_wiki_full_pass(
            "test-story",
            1,
            "Some chapter text",
        )

        assert set(result) == {"per_type", "total_created", "total_updated"}
        assert result["total_created"] == 0
        assert result["total_updated"] == 0
        per_type = result["per_type"]
        expected_types = {"character", "location", "faction", "item"}
        assert expected_types <= set(per_type)
        for stats in per_type.values():
            assert stats == {"created": 0, "updated": 0}

    def test_full_pass_new_entity_creates_page(
        self,
        story_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            _wiki_api,
            "_chat_completion",
            _fake_chat_completion_factory(
                character_candidates=[
                    {
                        "name": "Alice",
                        "type": "character",
                        "aliases": [],
                        "description": "Alice leads the expedition.",
                        "confidence": "verified",
                        "frontmatter": {"role": "leader", "status": "active"},
                    }
                ],
                detail_levels={
                    "l1": "Alice leads the expedition.",
                    "l2": "Alice is the active expedition leader.",
                    "l3": "Alice is a verified character who leads the expedition.",
                },
            ),
        )

        result = _wiki_api.update_wiki_full_pass(
            "test-story",
            1,
            "Alice leads the team into the ruins.",
        )

        assert result["total_created"] >= 1
        assert result["total_updated"] == 0
        created_page = story_env / "wiki" / "characters" / "alice.md"
        assert created_page.exists()
        page_text = created_page.read_text(encoding="utf-8")
        assert "name: Alice" in page_text
        assert "Alice leads the expedition." in page_text

    def test_full_pass_existing_entity_uses_merge(
        self,
        story_env: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write_page(
            story_env,
            subdir="characters",
            slug="alice",
            metadata={
                "type": "character",
                "name": "Alice",
                "slug": "alice",
                "aliases": [],
                "confidence": "verified",
                "first_appearance": 1,
                "version": 1,
            },
            body="Alice already has a wiki page.",
        )
        write_index(
            story_env / "wiki",
            [
                {
                    "name": "Alice",
                    "slug": "alice",
                    "type": "character",
                    "aliases": [],
                }
            ],
        )
        monkeypatch.setattr(
            _wiki_api,
            "_chat_completion",
            _fake_chat_completion_factory(
                character_candidates=[
                    {
                        "name": "Alice",
                        "type": "character",
                        "aliases": [],
                        "description": "Alice appears again.",
                        "confidence": "verified",
                        "frontmatter": {"role": "leader"},
                    }
                ],
                merge_patch={"no_change": True},
            ),
        )

        result = _wiki_api.update_wiki_full_pass(
            "test-story",
            1,
            "Alice appears again in the chapter.",
        )

        assert result["total_created"] == 0
        assert result["total_updated"] == 0
        assert (story_env / "wiki" / "characters" / "alice.md").exists()

    def test_full_pass_zero_result_alias_warning(
        self,
        story_env: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        _write_page(
            story_env,
            subdir="characters",
            slug="alice",
            metadata={
                "type": "character",
                "name": "Alice",
                "slug": "alice",
                "aliases": ["Al"],
                "confidence": "verified",
                "first_appearance": 1,
                "version": 1,
            },
            body="Alice already has a wiki page.",
        )
        write_index(
            story_env / "wiki",
            [
                {
                    "name": "Alice",
                    "slug": "alice",
                    "type": "character",
                    "aliases": ["Al"],
                }
            ],
        )
        monkeypatch.setattr(
            _wiki_api,
            "_chat_completion",
            _fake_chat_completion_factory(),
        )
        caplog.set_level(logging.WARNING)

        result = _wiki_api.update_wiki_full_pass(
            "test-story",
            1,
            "Alice walks into the archive.",
        )

        assert result["total_created"] == 0
        assert result["total_updated"] == 0
        assert any(
            record.levelno == logging.WARNING
            and "WARNING" in record.message
            and "0 candidates" in record.message
            and "Alice" in record.message
            for record in caplog.records
        )
