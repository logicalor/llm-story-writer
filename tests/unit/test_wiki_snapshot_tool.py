"""Verification tests for Issue #15 — wiki-snapshot Tool.

Confirms the CLI tool (src/tools/wiki_snapshot.py) correctly assembles
pre-generation scene context snapshots via the three-stage pipeline.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_SCRIPT = str(PROJECT_ROOT / "src" / "tools" / "wiki_snapshot.py")


def _run_tool(
    *args: str,
    stories_dir: Path | None = None,
    chromadb_dir: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ}
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    if stories_dir is not None:
        env["STORIES_DIR"] = str(stories_dir)
    if chromadb_dir is not None:
        env["CHROMADB_DIR"] = str(chromadb_dir)
    return subprocess.run(
        [sys.executable, TOOL_SCRIPT, *args],
        capture_output=True,
        text=True,
        env=env,
    )


def _write_wiki_page(wiki: Path, subdir: str, slug: str, content: str) -> Path:
    """Write a wiki page to the given subdirectory."""
    page = wiki / subdir / f"{slug}.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(content)
    return page


def _make_page_content(
    slug: str,
    page_type: str,
    name: str,
    body: str,
    *,
    aliases: list[str] | None = None,
    confidence: str = "verified",
    first_appearance: int = 1,
    version: int = 1,
    l1: str = "",
    l2: str = "",
    l3: str = "",
) -> str:
    """Build a wiki page with YAML frontmatter."""
    alias_str = json.dumps(aliases) if aliases else "[]"
    return (
        f"---\n"
        f"type: {page_type}\n"
        f'name: "{name}"\n'
        f"slug: {slug}\n"
        f"confidence: {confidence}\n"
        f"aliases: {alias_str}\n"
        f"first_appearance: {first_appearance}\n"
        f"version: {version}\n"
        f'last_updated: "2026-04-14T10:00:00Z"\n'
        f"detail_levels:\n"
        f'  L1: "{l1 or name}"\n'
        f'  L2: "{l2 or body.split(chr(10))[0]}"\n'
        f'  L3: "{l3 or body}"\n'
        f"---\n\n"
        f"{body}\n"
    )


def _make_index(*entries: tuple[str, str, str, str]) -> str:
    """Build index.md content.

    Each entry: (slug, type, name, aliases_csv)
    """
    lines = ["# Wiki Index", "", "<!-- slug | type | name | aliases -->", ""]
    for slug, page_type, name, aliases_csv in entries:
        lines.append(f"- {slug} | {page_type} | {name} | {aliases_csv}")
    lines.append("")
    return "\n".join(lines)


@pytest.fixture()
def wiki_env(tmp_path: Path) -> tuple[Path, Path]:
    """Create a story with an initialised wiki directory and subdirs."""
    stories = tmp_path / "stories"
    wiki = stories / "test-story" / "wiki"
    wiki.mkdir(parents=True)

    for subdir in [
        "characters",
        "locations",
        "events",
        "plot-threads",
        "world-rules",
    ]:
        (wiki / subdir).mkdir()

    return stories, wiki


# --- Common snapshot args builder ---
def _snapshot_args(
    *,
    outline: str = "Test scene outline",
    chapter: int = 1,
    scene: int = 1,
    pov_character: str | None = None,
    primary_location: str | None = None,
    budget: int | None = None,
    scene_type: str | None = None,
) -> list[str]:
    args = [
        "--operation",
        "snapshot",
        "--name",
        "test-story",
        "--chapter",
        str(chapter),
        "--scene",
        str(scene),
        "--outline",
        outline,
    ]
    if pov_character:
        args += ["--pov-character", pov_character]
    if primary_location:
        args += ["--primary-location", primary_location]
    if budget is not None:
        args += ["--budget", str(budget)]
    if scene_type:
        args += ["--scene-type", scene_type]
    return args


class TestSnapshotBasic:
    def test_snapshot_basic_output_structure(self, wiki_env: tuple[Path, Path]) -> None:
        stories, wiki = wiki_env

        # Write index
        (wiki / "index.md").write_text(
            _make_index(
                ("alice-smith", "character", "Alice Smith", "Alice, A. Smith"),
                ("old-library", "location", "Old Library", "Library"),
            )
        )

        # Write pages
        _write_wiki_page(
            wiki,
            "characters",
            "alice-smith",
            _make_page_content(
                "alice-smith",
                "character",
                "Alice Smith",
                "Alice Smith is the protagonist.",
                aliases=["Alice", "A. Smith"],
                l1="Alice Smith — protagonist",
                l2="Alice Smith is the protagonist detective.",
                l3="Alice Smith is the protagonist. Full backstory here.",
            ),
        )
        _write_wiki_page(
            wiki,
            "locations",
            "old-library",
            _make_page_content(
                "old-library",
                "location",
                "Old Library",
                "The Old Library is a grand building.",
                l1="Old Library — ancient building",
                l2="The Old Library is a grand building downtown.",
                l3="The Old Library is a grand building. Full description.",
            ),
        )

        result = _run_tool(
            *_snapshot_args(
                outline="Alice walked into the old library",
                pov_character="alice-smith",
                primary_location="old-library",
            ),
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert "snapshot" in output
        assert isinstance(output["snapshot"], str)
        assert "stats" in output
        stats = output["stats"]
        assert "pages_retrieved" in stats
        assert "pages_included" in stats
        assert "token_count" in stats
        assert stats["pages_retrieved"] > 0
        assert stats["pages_included"] > 0
        assert stats["token_count"] > 0


class TestEntityMatching:
    def test_entity_matching_identifies_names_and_aliases(
        self, wiki_env: tuple[Path, Path]
    ) -> None:
        stories, wiki = wiki_env

        (wiki / "index.md").write_text(
            _make_index(
                ("alice-smith", "character", "Alice Smith", "Alice, A. Smith"),
            )
        )
        _write_wiki_page(
            wiki,
            "characters",
            "alice-smith",
            _make_page_content(
                "alice-smith",
                "character",
                "Alice Smith",
                "Alice Smith is the protagonist detective.",
                aliases=["Alice", "A. Smith"],
                l1="Alice Smith — protagonist",
                l2="Alice Smith is the protagonist detective.",
                l3="Alice Smith is the protagonist. Full backstory.",
            ),
        )

        # Match by alias "Alice" in outline text
        result = _run_tool(
            *_snapshot_args(outline="Alice walked into the room"),
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        # Alice's page should be included via entity matching
        assert "Alice" in output["snapshot"] or "alice" in output["snapshot"].lower()
        assert output["stats"]["pages_included"] >= 1


class TestPovAndLocation:
    def test_pov_and_primary_location_always_included(
        self, wiki_env: tuple[Path, Path]
    ) -> None:
        stories, wiki = wiki_env

        (wiki / "index.md").write_text(
            _make_index(
                ("alice-smith", "character", "Alice Smith", "Alice"),
                ("old-library", "location", "Old Library", "Library"),
            )
        )
        _write_wiki_page(
            wiki,
            "characters",
            "alice-smith",
            _make_page_content(
                "alice-smith",
                "character",
                "Alice Smith",
                "Alice Smith is the protagonist.",
                l1="Alice Smith",
                l2="Alice Smith is the protagonist.",
                l3="Alice Smith is the protagonist. Full detail.",
            ),
        )
        _write_wiki_page(
            wiki,
            "locations",
            "old-library",
            _make_page_content(
                "old-library",
                "location",
                "Old Library",
                "The Old Library is a grand building.",
                l1="Old Library",
                l2="The Old Library is a grand building.",
                l3="The Old Library is a grand building. Full detail.",
            ),
        )

        # Outline does NOT mention Alice or Old Library — but they're forced via flags
        result = _run_tool(
            *_snapshot_args(
                outline="The wind howled through the streets",
                pov_character="alice-smith",
                primary_location="old-library",
            ),
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        snapshot = output["snapshot"]
        assert "Alice" in snapshot
        assert "Library" in snapshot or "library" in snapshot.lower()


class TestWikilinkTraversal:
    def test_wikilink_traversal_capped_at_5(self, wiki_env: tuple[Path, Path]) -> None:
        stories, wiki = wiki_env

        # Create a root page that links to 8 other pages
        index_entries = [
            ("root-char", "character", "Root Character", "Root"),
        ]
        for i in range(1, 9):
            index_entries.append(
                (f"linked-{i}", "character", f"Linked {i}", f"L{i}"),
            )
        (wiki / "index.md").write_text(_make_index(*index_entries))

        # Root page links to all 8
        links = " ".join(f"[[linked-{i}]]" for i in range(1, 9))
        _write_wiki_page(
            wiki,
            "characters",
            "root-char",
            _make_page_content(
                "root-char",
                "character",
                "Root Character",
                f"Root character knows everyone. {links}",
                l1="Root Character",
                l2="Root character knows everyone.",
                l3=f"Root character knows everyone. {links}",
            ),
        )

        # Create the 8 linked pages
        for i in range(1, 9):
            _write_wiki_page(
                wiki,
                "characters",
                f"linked-{i}",
                _make_page_content(
                    f"linked-{i}",
                    "character",
                    f"Linked {i}",
                    f"Character linked-{i} description.",
                    l1=f"Linked {i}",
                    l2=f"Character linked-{i} description.",
                    l3=f"Character linked-{i} full description.",
                ),
            )

        result = _run_tool(
            *_snapshot_args(outline="Root walked into the room"),
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        stats = output["stats"]
        # T4 traversal should contribute at most 5 additional pages
        assert stats["tiers"]["t4"] <= 5


class TestRelevanceScoring:
    def test_relevance_scoring_drops_below_threshold(
        self, wiki_env: tuple[Path, Path]
    ) -> None:
        stories, wiki = wiki_env

        # Create a page that will match and a page that won't
        (wiki / "index.md").write_text(
            _make_index(
                ("alice-smith", "character", "Alice Smith", "Alice"),
                ("irrelevant-npc", "character", "Irrelevant NPC", ""),
            )
        )
        _write_wiki_page(
            wiki,
            "characters",
            "alice-smith",
            _make_page_content(
                "alice-smith",
                "character",
                "Alice Smith",
                "Alice is the protagonist.",
                l1="Alice Smith",
                l2="Alice is the protagonist.",
                l3="Alice is the protagonist. Full detail.",
            ),
        )
        # This page has no entity match, no wikilinks, old date, low priority
        _write_wiki_page(
            wiki,
            "characters",
            "irrelevant-npc",
            (
                "---\n"
                "type: character\n"
                'name: "Irrelevant NPC"\n'
                "slug: irrelevant-npc\n"
                "confidence: speculative\n"
                "aliases: []\n"
                "first_appearance: 99\n"
                "version: 1\n"
                'last_updated: "2020-01-01T00:00:00Z"\n'
                "detail_levels:\n"
                '  L1: "Irrelevant NPC"\n'
                '  L2: "An irrelevant NPC."\n'
                '  L3: "An irrelevant NPC with no importance."\n'
                "---\n\n"
                "An irrelevant NPC with no importance.\n"
            ),
        )

        result = _run_tool(
            *_snapshot_args(outline="Alice explored the forest"),
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        snapshot = output["snapshot"].lower()
        # Alice should be included, irrelevant NPC should be excluded
        assert "alice" in snapshot
        # The irrelevant NPC has no entity match, no wikilink, no semantic match
        # Its score: 0.35*0 + 0.20*0 + 0.15*0 + 0.10*0 + 0.10*0.2 + 0.10*1.0 = 0.12 < 0.15
        assert "irrelevant npc" not in snapshot


class TestProtectedTier:
    def test_protected_tier_always_l3(self, wiki_env: tuple[Path, Path]) -> None:
        stories, wiki = wiki_env

        l3_content = (
            "Alice Smith is the protagonist. Full L3 backstory with all details."
        )
        l2_content = "Alice Smith is the protagonist detective."
        l1_content = "Alice Smith — protagonist"

        (wiki / "index.md").write_text(
            _make_index(
                ("alice-smith", "character", "Alice Smith", "Alice"),
                ("old-library", "location", "Old Library", "Library"),
            )
        )
        _write_wiki_page(
            wiki,
            "characters",
            "alice-smith",
            _make_page_content(
                "alice-smith",
                "character",
                "Alice Smith",
                l3_content,
                l1=l1_content,
                l2=l2_content,
                l3=l3_content,
            ),
        )

        loc_l3 = (
            "The Old Library is grand. Full L3 location with all architectural details."
        )
        _write_wiki_page(
            wiki,
            "locations",
            "old-library",
            _make_page_content(
                "old-library",
                "location",
                "Old Library",
                loc_l3,
                l1="Old Library — ancient building",
                l2="The Old Library is a grand building.",
                l3=loc_l3,
            ),
        )

        result = _run_tool(
            *_snapshot_args(
                outline="Something unrelated happens",
                pov_character="alice-smith",
                primary_location="old-library",
            ),
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        snapshot = output["snapshot"]
        # Protected pages should get L3 content
        assert l3_content in snapshot
        assert loc_l3 in snapshot


class TestTokenBudget:
    @pytest.fixture()
    def large_wiki(self, wiki_env: tuple[Path, Path]) -> tuple[Path, Path]:
        """Create wiki with 12 character pages to test budget enforcement."""
        stories, wiki = wiki_env
        entries = []
        for i in range(1, 13):
            slug = f"char-{i}"
            name = f"Character {i}"
            entries.append((slug, "character", name, f"C{i}"))
            body = f"Character {i} is important. " * 20  # ~80 words per page
            _write_wiki_page(
                wiki,
                "characters",
                slug,
                _make_page_content(
                    slug,
                    "character",
                    name,
                    body,
                    l1=f"Character {i} — summary",
                    l2=f"Character {i} is important. Brief description.",
                    l3=body,
                ),
            )
        (wiki / "index.md").write_text(_make_index(*entries))
        return stories, wiki

    def test_token_budget_enforcement(self, large_wiki: tuple[Path, Path]) -> None:
        stories, _wiki = large_wiki

        # Mention all characters to ensure they're retrieved
        outline = " ".join(f"Character {i}" for i in range(1, 13))
        result = _run_tool(
            *_snapshot_args(outline=outline, budget=500),
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        # Budget enforcement demotes page content; final snapshot includes
        # markdown headers which add overhead, so allow a margin.
        # Without budget enforcement 12 pages would be ~1200+ tokens.
        assert output["stats"]["token_count"] <= 700

    def test_graceful_degradation_demotes_not_drops(
        self, large_wiki: tuple[Path, Path]
    ) -> None:
        stories, _wiki = large_wiki

        outline = " ".join(f"Character {i}" for i in range(1, 13))
        result = _run_tool(
            *_snapshot_args(outline=outline, budget=500),
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        stats = output["stats"]
        # Pages are demoted (L3→L2→L1) but never dropped
        assert stats["pages_included"] == stats["pages_retrieved"]


class TestSectionStructure:
    def test_assembled_markdown_section_structure(
        self, wiki_env: tuple[Path, Path]
    ) -> None:
        stories, wiki = wiki_env

        (wiki / "index.md").write_text(
            _make_index(
                ("alice", "character", "Alice", ""),
                ("castle", "location", "Castle", ""),
                ("quest", "plot_thread", "The Quest", ""),
                ("magic-rule", "world_rule", "Magic Rule", ""),
            )
        )
        _write_wiki_page(
            wiki,
            "characters",
            "alice",
            _make_page_content(
                "alice",
                "character",
                "Alice",
                "Alice is brave.",
                l1="Alice",
                l2="Alice is brave.",
                l3="Alice is brave. Full.",
            ),
        )
        _write_wiki_page(
            wiki,
            "locations",
            "castle",
            _make_page_content(
                "castle",
                "location",
                "Castle",
                "The castle stands tall.",
                l1="Castle",
                l2="The castle stands tall.",
                l3="The castle stands tall. Full.",
            ),
        )
        _write_wiki_page(
            wiki,
            "plot-threads",
            "quest",
            _make_page_content(
                "quest",
                "plot_thread",
                "The Quest",
                "A dangerous quest.",
                l1="The Quest",
                l2="A dangerous quest.",
                l3="A dangerous quest. Full.",
            ),
        )
        _write_wiki_page(
            wiki,
            "world-rules",
            "magic-rule",
            _make_page_content(
                "magic-rule",
                "world_rule",
                "Magic Rule",
                "Magic follows rules.",
                l1="Magic Rule",
                l2="Magic follows rules.",
                l3="Magic follows rules. Full.",
            ),
        )

        result = _run_tool(
            *_snapshot_args(
                outline="Alice entered the Castle to discuss The Quest and the Magic Rule",
            ),
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        snapshot = output["snapshot"]
        assert "## Characters" in snapshot
        assert "## Location" in snapshot
        assert "## Active Plot Threads" in snapshot
        assert "## World Rules" in snapshot


class TestMissingPages:
    def test_missing_pages_skipped_with_warnings(
        self, wiki_env: tuple[Path, Path]
    ) -> None:
        stories, wiki = wiki_env

        (wiki / "index.md").write_text(
            _make_index(
                ("alice", "character", "Alice", ""),
            )
        )
        _write_wiki_page(
            wiki,
            "characters",
            "alice",
            _make_page_content(
                "alice",
                "character",
                "Alice",
                "Alice is brave.",
                l1="Alice",
                l2="Alice is brave.",
                l3="Alice is brave. Full.",
            ),
        )

        # Reference a non-existent slug as pov-character
        result = _run_tool(
            *_snapshot_args(
                outline="Alice walked around",
                pov_character="missing-person",
            ),
            stories_dir=stories,
        )
        # Tool should still succeed — missing slug gracefully skipped
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert "snapshot" in output


class TestDeltaCache:
    def test_delta_cache_reuse_unchanged(self, wiki_env: tuple[Path, Path]) -> None:
        stories, wiki = wiki_env

        (wiki / "index.md").write_text(
            _make_index(
                ("alice", "character", "Alice", ""),
            )
        )
        _write_wiki_page(
            wiki,
            "characters",
            "alice",
            _make_page_content(
                "alice",
                "character",
                "Alice",
                "Alice is brave.",
                l1="Alice",
                l2="Alice is brave.",
                l3="Alice is brave. Full.",
            ),
        )

        # Run scene 1 — populates cache
        result1 = _run_tool(
            *_snapshot_args(outline="Alice explored", chapter=1, scene=1),
            stories_dir=stories,
        )
        assert result1.returncode == 0, f"stderr: {result1.stderr}"
        out1 = json.loads(result1.stdout)
        # First run: all misses
        assert out1["stats"]["cache_misses"] > 0

        # Run scene 2 same chapter — should get cache hits
        result2 = _run_tool(
            *_snapshot_args(outline="Alice explored more", chapter=1, scene=2),
            stories_dir=stories,
        )
        assert result2.returncode == 0, f"stderr: {result2.stderr}"
        out2 = json.loads(result2.stdout)
        assert out2["stats"]["cache_hits"] > 0

    def test_chapter_boundary_invalidates_cache(
        self, wiki_env: tuple[Path, Path]
    ) -> None:
        stories, wiki = wiki_env

        (wiki / "index.md").write_text(
            _make_index(
                ("alice", "character", "Alice", ""),
            )
        )
        _write_wiki_page(
            wiki,
            "characters",
            "alice",
            _make_page_content(
                "alice",
                "character",
                "Alice",
                "Alice is brave.",
                l1="Alice",
                l2="Alice is brave.",
                l3="Alice is brave. Full.",
            ),
        )

        # Run chapter 1 scene 1
        result1 = _run_tool(
            *_snapshot_args(outline="Alice explored", chapter=1, scene=1),
            stories_dir=stories,
        )
        assert result1.returncode == 0, f"stderr: {result1.stderr}"

        # Run chapter 2 scene 1 — cache should be invalidated
        result2 = _run_tool(
            *_snapshot_args(outline="Alice explored again", chapter=2, scene=1),
            stories_dir=stories,
        )
        assert result2.returncode == 0, f"stderr: {result2.stderr}"
        out2 = json.loads(result2.stdout)
        # Different chapter → cache fully invalidated → all misses
        assert out2["stats"]["cache_hits"] == 0
        assert out2["stats"]["cache_misses"] > 0


class TestCacheStatus:
    def test_cache_status_operation(self, wiki_env: tuple[Path, Path]) -> None:
        stories, wiki = wiki_env

        (wiki / "index.md").write_text(
            _make_index(
                ("alice", "character", "Alice", ""),
            )
        )
        _write_wiki_page(
            wiki,
            "characters",
            "alice",
            _make_page_content(
                "alice",
                "character",
                "Alice",
                "Alice is brave.",
                l1="Alice",
                l2="Alice is brave.",
                l3="Alice is brave. Full.",
            ),
        )

        # First: run a snapshot to populate cache
        _run_tool(
            *_snapshot_args(outline="Alice explored", chapter=1, scene=1),
            stories_dir=stories,
        )

        # Then: check cache status
        result = _run_tool(
            "--operation",
            "cache-status",
            "--name",
            "test-story",
            "--chapter",
            "1",
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["cached"] is True
        assert output["chapter"] == 1
        assert output["entity_count"] > 0


class TestInputValidation:
    def test_invalid_slug_rejected(self, wiki_env: tuple[Path, Path]) -> None:
        stories, wiki = wiki_env

        (wiki / "index.md").write_text(_make_index(("alice", "character", "Alice", "")))
        _write_wiki_page(
            wiki,
            "characters",
            "alice",
            _make_page_content(
                "alice",
                "character",
                "Alice",
                "Alice is brave.",
                l1="Alice",
                l2="Alice is brave.",
                l3="Alice is brave. Full.",
            ),
        )

        result = _run_tool(
            *_snapshot_args(
                outline="test",
                pov_character="../../../etc/passwd",
            ),
            stories_dir=stories,
        )
        # Should fail with non-zero exit code
        assert result.returncode != 0
        assert (
            "invalid slug" in result.stderr.lower() or "error" in result.stderr.lower()
        )


class TestDefaultBudget:
    def test_snapshot_fits_within_default_budget(
        self, wiki_env: tuple[Path, Path]
    ) -> None:
        stories, wiki = wiki_env

        entries = []
        # 3 characters
        for i, (slug, name) in enumerate(
            [("alice", "Alice"), ("bob", "Bob"), ("carol", "Carol")], 1
        ):
            entries.append((slug, "character", name, ""))
            _write_wiki_page(
                wiki,
                "characters",
                slug,
                _make_page_content(
                    slug,
                    "character",
                    name,
                    f"{name} is a character in the story. " * 10,
                    l1=f"{name} — character",
                    l2=f"{name} is a character in the story.",
                    l3=f"{name} is a character in the story. " * 10,
                ),
            )

        # 1 location
        entries.append(("castle", "location", "Castle", ""))
        _write_wiki_page(
            wiki,
            "locations",
            "castle",
            _make_page_content(
                "castle",
                "location",
                "Castle",
                "The castle is a grand fortress. " * 10,
                l1="Castle — grand fortress",
                l2="The castle is a grand fortress.",
                l3="The castle is a grand fortress. " * 10,
            ),
        )

        # 2 plot threads
        for slug, name in [("quest", "The Quest"), ("betrayal", "The Betrayal")]:
            entries.append((slug, "plot_thread", name, ""))
            _write_wiki_page(
                wiki,
                "plot-threads",
                slug,
                _make_page_content(
                    slug,
                    "plot_thread",
                    name,
                    f"{name} is an active plot thread. " * 10,
                    l1=f"{name}",
                    l2=f"{name} is an active plot thread.",
                    l3=f"{name} is an active plot thread. " * 10,
                ),
            )

        (wiki / "index.md").write_text(_make_index(*entries))

        result = _run_tool(
            *_snapshot_args(
                outline="Alice and Bob entered the Castle to discuss The Quest and The Betrayal with Carol",
            ),
            stories_dir=stories,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["stats"]["token_count"] <= 15000
