"""CLI tool for assembling pre-generation scene context snapshots.

Implements ADR 005: three-stage hybrid retrieval and context assembly pipeline.
Stage 1: Multi-tier retrieval (entity match, metadata, semantic, wikilink traversal)
Stage 2: Detail level selection and token budgeting
Stage 3: Structured context assembly with optional LLM synthesis
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src = str(Path(__file__).resolve().parents[1])
if _src not in sys.path:
    sys.path.insert(0, _src)

from src.tools._io import _atomic_write  # noqa: E402
from src.tools._llm import count_tokens, generate_text  # noqa: E402
from src.tools._wiki import (  # noqa: E402
    _validate_slug,
    find_pages,
    get_wiki_dir,
    match_entities_in_text,
    parse_frontmatter,
    read_index,
)
from src.tools.wiki_search import _get_collection  # noqa: E402

STORIES_DIR = Path(os.environ.get("STORIES_DIR", str(PROJECT_ROOT / "stories")))
CHROMADB_DIR = os.environ.get("CHROMADB_DIR", str(PROJECT_ROOT / ".chromadb"))

# --- Scoring constants ---
RRF_K = 60
SCORE_THRESHOLD = 0.15
DEFAULT_BUDGET = 15000

TYPE_PRIORITY: dict[str, float] = {
    "character": 1.0,
    "location": 1.0,
    "plot_thread": 0.8,
    "event": 0.6,
    "world_rule": 0.5,
}
DEFAULT_TYPE_PRIORITY = 0.3


def _error(msg: str) -> None:
    """Write error to stderr and exit with code 1."""
    sys.stderr.write(f"Error: {msg}\n")
    sys.exit(1)


def _validate_story_name(name: str) -> Path:
    """Validate story name does not escape the stories directory."""
    story_dir = (STORIES_DIR / name).resolve()
    if not story_dir.is_relative_to(STORIES_DIR.resolve()):
        _error(f"story name escapes stories directory: {name}")
    return story_dir


# ---------------------------------------------------------------------------
# Page reading helpers
# ---------------------------------------------------------------------------


def _extract_sentences(text: str, count: int) -> str:
    """Extract the first N sentences from text."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(sentences[:count])


def _read_page(page_path: Path) -> dict | None:
    """Read a wiki page and return {slug, type, metadata, body} or None."""
    if not page_path.exists():
        return None
    content = page_path.read_text()
    metadata, body = parse_frontmatter(content)
    slug = metadata.get("slug", page_path.stem)
    page_type = metadata.get("type", "unknown")
    return {
        "slug": slug,
        "type": page_type,
        "metadata": metadata,
        "body": body,
    }


def _get_page_content_at_level(page: dict, level: str) -> str:
    """Get page content at specified detail level (L1/L2/L3).

    Falls back to body extraction if pre-computed levels are missing.
    """
    detail_levels = page["metadata"].get("detail_levels", {})
    body = page.get("body", "")

    if level == "L1":
        return str(detail_levels.get("L1", body.split("\n")[0] if body else ""))
    elif level == "L2":
        return str(detail_levels.get("L2", _extract_sentences(body, 3)))
    else:  # L3 / full
        return body


def _find_page_by_slug(wiki_dir: Path, slug: str) -> Path | None:
    """Find a page by slug across all wiki subdirectories."""
    pages = find_pages(wiki_dir, slug=slug)
    return pages[0] if pages else None


# ---------------------------------------------------------------------------
# Stage 1: Hybrid Multi-Tier Retrieval
# ---------------------------------------------------------------------------


def _tier1_entity_match(
    outline: str,
    wiki_dir: Path,
    pov_character: str | None,
    primary_location: str | None,
) -> dict[str, dict]:
    """T1 — Deterministic entity matching.

    Returns {slug: page_result_dict} for all matched entities.
    """
    index_entries = read_index(wiki_dir)
    matched = match_entities_in_text(outline, index_entries)
    matched_slugs = {m["slug"] for m in matched}

    # Ensure POV character and primary location are included
    for forced_slug in (pov_character, primary_location):
        if forced_slug and forced_slug not in matched_slugs:
            # Find the index entry for this slug
            for entry in index_entries:
                if entry["slug"] == forced_slug:
                    matched.append(entry)
                    matched_slugs.add(forced_slug)
                    break

    results: dict[str, dict] = {}
    for entry in matched:
        slug = entry["slug"]
        page_path = _find_page_by_slug(wiki_dir, slug)
        if page_path is None:
            continue
        page = _read_page(page_path)
        if page is None:
            continue
        results[slug] = {
            **page,
            "tiers": {1},
            "entity_match_score": 1.0,
            "semantic_similarity": 0.0,
            "wikilink_proximity": 0.0,
        }
    return results


def _tier2_metadata_query(story_name: str) -> list[dict]:
    """T2 — Metadata-filtered query for active plot threads and world rules.

    Returns list of {slug, score, metadata} from ChromaDB.
    """
    collection = _get_collection(story_name)
    if collection is None or collection.count() == 0:
        return []

    results: list[dict] = []

    # Active plot threads
    try:
        plot_result = collection.get(
            where={
                "$and": [
                    {"type": {"$eq": "plot_thread"}},
                    {"status": {"$eq": "active"}},
                ]
            },
            limit=20,
        )
        if plot_result and plot_result.get("ids"):
            for i, doc_id in enumerate(plot_result["ids"]):
                metadatas = plot_result.get("metadatas") or []
                results.append(
                    {
                        "slug": doc_id,
                        "score": 1.0,
                        "metadata": metadatas[i] if i < len(metadatas) else {},
                    }
                )
    except Exception:
        pass  # ChromaDB may not support compound filters; skip gracefully

    # World rules
    try:
        rules_result = collection.get(
            where={"type": {"$eq": "world_rule"}},
            limit=20,
        )
        if rules_result and rules_result.get("ids"):
            for i, doc_id in enumerate(rules_result["ids"]):
                if any(r["slug"] == doc_id for r in results):
                    continue  # already have this slug
                metadatas = rules_result.get("metadatas") or []
                results.append(
                    {
                        "slug": doc_id,
                        "score": 1.0,
                        "metadata": metadatas[i] if i < len(metadatas) else {},
                    }
                )
    except Exception:
        pass

    return results


def _tier3_semantic_search(
    story_name: str,
    outline: str,
    n_results: int = 10,
) -> list[dict]:
    """T3 — Semantic vector search using scene outline.

    Returns list of {slug, score, metadata} with normalized similarity.
    """
    collection = _get_collection(story_name)
    if collection is None or collection.count() == 0:
        return []

    try:
        query_result = collection.query(
            query_texts=[outline],
            n_results=min(n_results, collection.count()),
        )
    except Exception:
        return []

    results: list[dict] = []
    if query_result and query_result.get("ids"):
        ids = query_result["ids"][0] if query_result["ids"] else []
        distances = (
            query_result["distances"][0] if query_result.get("distances") else []
        )
        metadatas = (
            query_result["metadatas"][0] if query_result.get("metadatas") else []
        )
        for i, doc_id in enumerate(ids):
            score = round(1.0 / (1.0 + distances[i]), 4) if i < len(distances) else 0.0
            results.append(
                {
                    "slug": doc_id,
                    "score": score,
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                }
            )
    return results


def _tier4_wikilink_traversal(
    current_pages: dict[str, dict],
    wiki_dir: Path,
    max_additional: int = 5,
) -> dict[str, dict]:
    """T4 — Follow [[wikilinks]] from existing pages, 1 additional hop.

    Returns {slug: page_result_dict} for newly discovered pages only.
    """
    # Collect all wikilinks from current pages (hop 1)
    hop1_slugs: set[str] = set()
    for page in current_pages.values():
        body = page.get("body", "")
        links = re.findall(r"\[\[([^\]]+)\]\]", body)
        for link in links:
            slug = link.strip()
            if slug and slug not in current_pages:
                hop1_slugs.add(slug)

    new_pages: dict[str, dict] = {}

    # Fetch hop-1 pages
    for slug in hop1_slugs:
        if len(new_pages) >= max_additional:
            break
        page_path = _find_page_by_slug(wiki_dir, slug)
        if page_path is None:
            continue
        loaded = _read_page(page_path)
        if loaded is None:
            continue
        new_pages[slug] = {
            **loaded,
            "tiers": {4},
            "entity_match_score": 0.0,
            "semantic_similarity": 0.0,
            "wikilink_proximity": 1.0,  # direct link from a T1-T3 page
        }

    # Hop 2: follow wikilinks from hop-1 pages
    hop2_slugs: set[str] = set()
    for hop1_page in new_pages.values():
        body = hop1_page.get("body", "")
        links = re.findall(r"\[\[([^\]]+)\]\]", body)
        for link in links:
            slug = link.strip()
            if slug and slug not in current_pages and slug not in new_pages:
                hop2_slugs.add(slug)

    for slug in hop2_slugs:
        if len(new_pages) >= max_additional:
            break
        page_path = _find_page_by_slug(wiki_dir, slug)
        if page_path is None:
            continue
        loaded = _read_page(page_path)
        if loaded is None:
            continue
        new_pages[slug] = {
            **loaded,
            "tiers": {4},
            "entity_match_score": 0.0,
            "semantic_similarity": 0.0,
            "wikilink_proximity": 0.5,  # 2-hop link
        }

    return new_pages


def _merge_and_score(
    t1_results: dict[str, dict],
    t2_results: list[dict],
    t3_results: list[dict],
    t4_results: dict[str, dict],
    wiki_dir: Path,
) -> dict[str, dict]:
    """Merge all tiers via RRF, compute relevance scores, and drop low scorers."""
    # Build ranked lists per tier for RRF
    tier_ranks: dict[int, list[str]] = {
        1: list(t1_results.keys()),
        2: [r["slug"] for r in t2_results],
        3: [r["slug"] for r in t3_results],
        4: list(t4_results.keys()),
    }

    # Compute RRF scores
    rrf_scores: dict[str, float] = {}
    for tier_id, ranked_slugs in tier_ranks.items():
        for rank, slug in enumerate(ranked_slugs):
            rrf_score = 1.0 / (RRF_K + rank + 1)
            rrf_scores[slug] = rrf_scores.get(slug, 0.0) + rrf_score

    # Build merged page dict — T1 pages already loaded; load others
    merged: dict[str, dict] = {}

    # Add T1 pages
    for slug, page in t1_results.items():
        merged[slug] = page

    # Add T2 pages (need to load from disk if not already present)
    for entry in t2_results:
        slug = entry["slug"]
        if slug in merged:
            merged[slug]["tiers"].add(2)
            continue
        page_path = _find_page_by_slug(wiki_dir, slug)
        if page_path is None:
            continue
        loaded = _read_page(page_path)
        if loaded is None:
            continue
        merged[slug] = {
            **loaded,
            "tiers": {2},
            "entity_match_score": 0.0,
            "semantic_similarity": 0.0,
            "wikilink_proximity": 0.0,
        }

    # Add T3 pages
    t3_scores: dict[str, float] = {}
    for entry in t3_results:
        slug = entry["slug"]
        t3_scores[slug] = entry["score"]
        if slug in merged:
            merged[slug]["tiers"].add(3)
            merged[slug]["semantic_similarity"] = entry["score"]
            continue
        page_path = _find_page_by_slug(wiki_dir, slug)
        if page_path is None:
            continue
        loaded = _read_page(page_path)
        if loaded is None:
            continue
        merged[slug] = {
            **loaded,
            "tiers": {3},
            "entity_match_score": 0.0,
            "semantic_similarity": entry["score"],
            "wikilink_proximity": 0.0,
        }

    # Update T3 similarity for pages that were in T1/T2 and also found in T3
    for slug, score in t3_scores.items():
        if slug in merged:
            merged[slug]["semantic_similarity"] = max(
                merged[slug].get("semantic_similarity", 0.0),
                score,
            )

    # Add T4 pages
    for slug, page in t4_results.items():
        if slug in merged:
            merged[slug]["tiers"].add(4)
            # Keep the better wikilink_proximity
            merged[slug]["wikilink_proximity"] = max(
                merged[slug].get("wikilink_proximity", 0.0),
                page["wikilink_proximity"],
            )
            continue
        merged[slug] = page

    # Compute final relevance scores
    now = datetime.now(timezone.utc)
    for slug, page in merged.items():
        entity_match = page.get("entity_match_score", 0.0)
        wikilink_prox = page.get("wikilink_proximity", 0.0)
        semantic_sim = page.get("semantic_similarity", 0.0)
        recency = _compute_recency(page.get("metadata", {}), now)
        type_prio = TYPE_PRIORITY.get(
            page.get("type", ""),
            DEFAULT_TYPE_PRIORITY,
        )

        page["relevance_score"] = (
            0.40 * entity_match
            + 0.20 * wikilink_prox
            + 0.20 * semantic_sim
            + 0.10 * recency
            + 0.10 * type_prio
        )

    # Drop pages below threshold
    return {
        slug: page
        for slug, page in merged.items()
        if page.get("relevance_score", 0.0) >= SCORE_THRESHOLD
    }


def _compute_recency(metadata: dict, now: datetime) -> float:
    """Compute recency score from last_updated metadata field."""
    last_updated = metadata.get("last_updated")
    if not last_updated:
        return 0.0
    try:
        if isinstance(last_updated, str):
            updated_dt = datetime.fromisoformat(last_updated)
        elif isinstance(last_updated, datetime):
            updated_dt = last_updated
        else:
            return 0.0

        # Ensure timezone-aware comparison
        if updated_dt.tzinfo is None:
            updated_dt = updated_dt.replace(tzinfo=timezone.utc)

        delta = now - updated_dt
        days = delta.days

        if days <= 0:
            return 1.0
        elif days <= 7:
            return 0.5
        else:
            return 0.2
    except (ValueError, TypeError):
        return 0.0


# ---------------------------------------------------------------------------
# Stage 2: Detail Level Selection & Token Budgeting
# ---------------------------------------------------------------------------


def _assign_detail_levels(
    pages: dict[str, dict],
    pov_character: str | None,
    primary_location: str | None,
    scene_type: str | None,
    chapter: int,
    budget: int,
) -> dict[str, dict]:
    """Assign L1/L2/L3 detail levels based on rank, scene type, and budget."""
    # Sort by relevance score descending
    sorted_slugs = sorted(
        pages.keys(),
        key=lambda s: pages[s].get("relevance_score", 0.0),
        reverse=True,
    )
    total = len(sorted_slugs)
    if total == 0:
        return pages

    # Assign initial detail levels by percentile rank
    for i, slug in enumerate(sorted_slugs):
        pct = i / total
        if pct < 0.30:
            pages[slug]["detail_level"] = "L3"
        elif pct < 0.70:
            pages[slug]["detail_level"] = "L2"
        else:
            pages[slug]["detail_level"] = "L1"

    # Protected tier: POV character and primary location always L3
    for protected_slug in (pov_character, primary_location):
        if protected_slug and protected_slug in pages:
            pages[protected_slug]["detail_level"] = "L3"

    # Scene-type adaptation
    if scene_type == "dialogue":
        for slug in sorted_slugs:
            if pages[slug].get("type") == "character":
                _boost_detail_level(pages[slug])
    elif scene_type == "action":
        for slug in sorted_slugs:
            if pages[slug].get("type") in ("location", "world_rule"):
                _boost_detail_level(pages[slug])

    # First appearances: pages with first_appearance == current chapter → L3
    for slug in sorted_slugs:
        fa = pages[slug].get("metadata", {}).get("first_appearance")
        if fa is not None:
            try:
                if int(fa) == chapter:
                    pages[slug]["detail_level"] = "L3"
            except (ValueError, TypeError):
                pass

    # Re-enforce protected tier after scene-type adaptation
    for protected_slug in (pov_character, primary_location):
        if protected_slug and protected_slug in pages:
            pages[protected_slug]["detail_level"] = "L3"

    # Token budgeting: compute totals and demote if over budget
    _enforce_token_budget(pages, sorted_slugs, pov_character, primary_location, budget)

    return pages


def _boost_detail_level(page: dict) -> None:
    """Boost detail level by one step (L1→L2 or L2→L3)."""
    current = page.get("detail_level", "L1")
    if current == "L1":
        page["detail_level"] = "L2"
    elif current == "L2":
        page["detail_level"] = "L3"


def _enforce_token_budget(
    pages: dict[str, dict],
    sorted_slugs: list[str],
    pov_character: str | None,
    primary_location: str | None,
    budget: int,
) -> None:
    """Iteratively demote lowest-scoring non-protected pages until within budget."""
    protected = {s for s in (pov_character, primary_location) if s}

    def _total_tokens() -> int:
        total = 0
        for slug in sorted_slugs:
            level = pages[slug].get("detail_level", "L1")
            content = _get_page_content_at_level(pages[slug], level)
            total += count_tokens(content)
        return total

    # Demote from bottom of the sorted list upward
    while _total_tokens() > budget:
        demoted = False
        for slug in reversed(sorted_slugs):
            if slug in protected:
                continue
            current = pages[slug].get("detail_level", "L1")
            if current == "L3":
                pages[slug]["detail_level"] = "L2"
                demoted = True
                break
            elif current == "L2":
                pages[slug]["detail_level"] = "L1"
                demoted = True
                break
        if not demoted:
            break  # All non-protected pages already at L1


# ---------------------------------------------------------------------------
# Stage 3: Structured Context Assembly
# ---------------------------------------------------------------------------


def _assemble_context(
    pages: dict[str, dict],
    pov_character: str | None,
    primary_location: str | None,
    chapter: int,
    scene: int,
    outline: str,
    scene_type: str | None,
) -> str:
    """Assemble pages into structured markdown context."""
    sections: list[str] = []
    sections.append(f"# Scene Context — Chapter {chapter}, Scene {scene}")

    # --- Characters ---
    char_pages = {s: p for s, p in pages.items() if p.get("type") == "character"}

    sections.append("\n## Characters")

    # POV Character
    if pov_character and pov_character in char_pages:
        page = char_pages.pop(pov_character)
        content = _get_page_content_at_level(page, page.get("detail_level", "L3"))
        sections.append(f"\n### POV Character\n{content}")

    # Remaining characters sorted by relevance score
    scene_chars: list[tuple[str, dict]] = []
    bg_chars: list[tuple[str, dict]] = []
    for slug, page in sorted(
        char_pages.items(),
        key=lambda kv: kv[1].get("relevance_score", 0.0),
        reverse=True,
    ):
        level = page.get("detail_level", "L1")
        if level in ("L3", "L2"):
            scene_chars.append((slug, page))
        else:
            bg_chars.append((slug, page))

    if scene_chars:
        sections.append("\n### Scene Characters")
        for slug, page in scene_chars:
            content = _get_page_content_at_level(page, page.get("detail_level", "L2"))
            name = page.get("metadata", {}).get("name", slug)
            sections.append(f"\n#### {name}\n{content}")

    if bg_chars:
        sections.append("\n### Background Characters")
        for slug, page in bg_chars:
            content = _get_page_content_at_level(page, "L1")
            name = page.get("metadata", {}).get("name", slug)
            sections.append(f"- **{name}**: {content}")

    # --- Location ---
    loc_pages = {s: p for s, p in pages.items() if p.get("type") == "location"}
    if loc_pages:
        sections.append("\n## Location")
        # Primary location first
        if primary_location and primary_location in loc_pages:
            page = loc_pages.pop(primary_location)
            content = _get_page_content_at_level(
                page,
                page.get("detail_level", "L3"),
            )
            sections.append(f"\n{content}")
        # Other locations
        for slug, page in sorted(
            loc_pages.items(),
            key=lambda kv: kv[1].get("relevance_score", 0.0),
            reverse=True,
        ):
            content = _get_page_content_at_level(
                page,
                page.get("detail_level", "L2"),
            )
            name = page.get("metadata", {}).get("name", slug)
            sections.append(f"\n### {name}\n{content}")

    # --- Active Plot Threads ---
    plot_pages = {s: p for s, p in pages.items() if p.get("type") == "plot_thread"}
    if plot_pages:
        sections.append("\n## Active Plot Threads")
        for slug, page in sorted(
            plot_pages.items(),
            key=lambda kv: kv[1].get("relevance_score", 0.0),
            reverse=True,
        ):
            content = _get_page_content_at_level(
                page,
                page.get("detail_level", "L2"),
            )
            name = page.get("metadata", {}).get("name", slug)
            sections.append(f"\n### {name}\n{content}")

    # --- World Rules ---
    rule_pages = {s: p for s, p in pages.items() if p.get("type") == "world_rule"}
    if rule_pages:
        sections.append("\n## World Rules")
        for slug, page in sorted(
            rule_pages.items(),
            key=lambda kv: kv[1].get("relevance_score", 0.0),
            reverse=True,
        ):
            content = _get_page_content_at_level(
                page,
                page.get("detail_level", "L2"),
            )
            name = page.get("metadata", {}).get("name", slug)
            sections.append(f"\n### {name}\n{content}")

    # --- Recent Events ---
    event_pages = {s: p for s, p in pages.items() if p.get("type") == "event"}
    if event_pages:
        sections.append("\n## Recent Events")
        # Take top 3 by relevance
        sorted_events = sorted(
            event_pages.items(),
            key=lambda kv: kv[1].get("relevance_score", 0.0),
            reverse=True,
        )[:3]
        for slug, page in sorted_events:
            content = _get_page_content_at_level(
                page,
                page.get("detail_level", "L2"),
            )
            name = page.get("metadata", {}).get("name", slug)
            sections.append(f"\n### {name}\n{content}")

    # --- Relationships ---
    rel_pages = {s: p for s, p in pages.items() if p.get("type") == "relationship"}
    if rel_pages:
        sections.append("\n## Relationships")
        for slug, page in sorted(
            rel_pages.items(),
            key=lambda kv: kv[1].get("relevance_score", 0.0),
            reverse=True,
        ):
            content = _get_page_content_at_level(
                page,
                page.get("detail_level", "L2"),
            )
            name = page.get("metadata", {}).get("name", slug)
            sections.append(f"\n### {name}\n{content}")

    return "\n".join(sections)


def _maybe_synthesize(
    snapshot: str,
    pages: dict[str, dict],
    outline: str,
) -> str:
    """Optionally run LLM synthesis if context exceeds complexity thresholds."""
    char_count = sum(1 for p in pages.values() if p.get("type") == "character")
    plot_count = sum(1 for p in pages.values() if p.get("type") == "plot_thread")

    if char_count <= 5 and plot_count <= 3:
        return snapshot

    try:
        return generate_text(
            prompt=(
                "Restructure and condense the following scene context. "
                "Do not add any information not in the source. "
                f"Focus on what is relevant to this scene: {outline}\n\n"
                f"{snapshot}"
            ),
            system_message=(
                "You are a context compression assistant. "
                "Preserve all facts, names, and relationships. "
                "Remove redundancy and reorder for clarity."
            ),
            temperature=0.1,
        )
    except RuntimeError:
        # LLM unavailable — return unsynthesized snapshot
        return snapshot


# ---------------------------------------------------------------------------
# Delta Caching
# ---------------------------------------------------------------------------


def _cache_dir(wiki_dir: Path) -> Path:
    """Return the .cache directory under wiki dir, creating if needed."""
    cache = wiki_dir / ".cache"
    cache.mkdir(parents=True, exist_ok=True)
    return cache


def _cache_path(wiki_dir: Path) -> Path:
    """Return the path to the snapshot cache file."""
    return _cache_dir(wiki_dir) / "snapshot_cache.json"


def _load_cache(wiki_dir: Path) -> dict | None:
    """Load cache from disk. Returns None if no cache or parse error."""
    path = _cache_path(wiki_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            return None
        return data
    except (json.JSONDecodeError, OSError):
        return None


def _save_cache(wiki_dir: Path, cache: dict) -> None:
    """Save cache to disk atomically."""
    _atomic_write(_cache_path(wiki_dir), json.dumps(cache, indent=2))


def _apply_cache(
    cache: dict | None,
    chapter: int,
    pages: dict[str, dict],
    wiki_dir: Path,
) -> tuple[dict[str, str], int, int]:
    """Apply delta caching. Returns (cached_content, hits, misses).

    cached_content maps slug → rendered content string for cache hits.
    Cache misses need fresh rendering.
    """
    if cache is None or cache.get("chapter") != chapter:
        return {}, 0, len(pages)

    cached_entities = cache.get("entities", {})
    cached_content = cache.get("content", {})
    hits = 0
    misses = 0
    reusable: dict[str, str] = {}

    for slug, page in pages.items():
        page_version = page.get("metadata", {}).get("version")
        cached_version = cached_entities.get(slug)

        if (
            slug in cached_content
            and cached_version is not None
            and page_version is not None
            and cached_version == page_version
        ):
            reusable[slug] = cached_content[slug]
            hits += 1
        else:
            misses += 1

    return reusable, hits, misses


def _update_cache(
    wiki_dir: Path,
    chapter: int,
    scene: int,
    pages: dict[str, dict],
    rendered: dict[str, str],
    stats: dict,
) -> None:
    """Build and save updated cache."""
    entities: dict[str, object] = {}
    for slug, page in pages.items():
        version = page.get("metadata", {}).get("version")
        entities[slug] = version

    cache = {
        "chapter": chapter,
        "scene": scene,
        "entities": entities,
        "content": rendered,
        "stats": stats,
    }
    _save_cache(wiki_dir, cache)


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------


def cmd_snapshot(args: argparse.Namespace) -> None:
    """Execute the full snapshot pipeline."""
    # Validate required args
    if args.scene is None:
        _error("--scene is required for snapshot operation")
    if not args.outline:
        _error("--outline is required for snapshot operation")

    story_dir = _validate_story_name(args.name)
    wiki_dir = get_wiki_dir(story_dir)

    if not wiki_dir.exists():
        print(
            json.dumps(
                {
                    "snapshot": f"# Scene Context — Chapter {args.chapter}, Scene {args.scene}\n\nNo wiki found.",
                    "stats": {
                        "pages_retrieved": 0,
                        "pages_included": 0,
                        "token_count": 0,
                        "cache_hits": 0,
                        "cache_misses": 0,
                        "tiers": {"t1": 0, "t2": 0, "t3": 0, "t4": 0},
                    },
                }
            )
        )
        return

    # Validate slug parameters
    pov_character = args.pov_character
    primary_location = args.primary_location
    if pov_character:
        _validate_slug(pov_character)
    if primary_location:
        _validate_slug(primary_location)

    extra_characters: list[str] = []
    if args.characters:
        for slug in args.characters.split(","):
            slug = slug.strip()
            if slug:
                _validate_slug(slug)
                extra_characters.append(slug)

    extra_locations: list[str] = []
    if args.locations:
        for slug in args.locations.split(","):
            slug = slug.strip()
            if slug:
                _validate_slug(slug)
                extra_locations.append(slug)

    budget = args.budget or DEFAULT_BUDGET
    scene_type = args.scene_type

    # --- Stage 1: Hybrid Multi-Tier Retrieval ---
    t1_results = _tier1_entity_match(
        args.outline,
        wiki_dir,
        pov_character,
        primary_location,
    )

    # Ensure extra characters/locations are in T1
    for slug in extra_characters:
        if slug not in t1_results:
            page_path = _find_page_by_slug(wiki_dir, slug)
            if page_path:
                loaded = _read_page(page_path)
                if loaded:
                    t1_results[slug] = {
                        **loaded,
                        "tiers": {1},
                        "entity_match_score": 1.0,
                        "semantic_similarity": 0.0,
                        "wikilink_proximity": 0.0,
                    }

    for slug in extra_locations:
        if slug not in t1_results:
            page_path = _find_page_by_slug(wiki_dir, slug)
            if page_path:
                loaded = _read_page(page_path)
                if loaded:
                    t1_results[slug] = {
                        **loaded,
                        "tiers": {1},
                        "entity_match_score": 1.0,
                        "semantic_similarity": 0.0,
                        "wikilink_proximity": 0.0,
                    }

    t2_results = _tier2_metadata_query(args.name)
    t3_results = _tier3_semantic_search(args.name, args.outline)

    # Build pre-T4 page set for wikilink traversal
    pre_t4: dict[str, dict] = dict(t1_results)
    for entry in t2_results:
        if entry["slug"] not in pre_t4:
            page_path = _find_page_by_slug(wiki_dir, entry["slug"])
            if page_path:
                loaded = _read_page(page_path)
                if loaded:
                    pre_t4[entry["slug"]] = loaded
    for entry in t3_results:
        if entry["slug"] not in pre_t4:
            page_path = _find_page_by_slug(wiki_dir, entry["slug"])
            if page_path:
                loaded = _read_page(page_path)
                if loaded:
                    pre_t4[entry["slug"]] = loaded

    t4_results = _tier4_wikilink_traversal(pre_t4, wiki_dir)

    # Merge, score, deduplicate
    pages = _merge_and_score(t1_results, t2_results, t3_results, t4_results, wiki_dir)

    # Count tier contributions
    tier_counts = {"t1": 0, "t2": 0, "t3": 0, "t4": 0}
    for page in pages.values():
        for t in page.get("tiers", set()):
            tier_counts[f"t{t}"] += 1

    pages_retrieved = len(pages)

    # --- Delta Caching ---
    cache = _load_cache(wiki_dir)
    cached_content, cache_hits, cache_misses = _apply_cache(
        cache,
        args.chapter,
        pages,
        wiki_dir,
    )

    # --- Stage 2: Detail Level Selection ---
    pages = _assign_detail_levels(
        pages,
        pov_character,
        primary_location,
        scene_type,
        args.chapter,
        budget,
    )

    # --- Stage 3: Render content and assemble ---
    rendered_content: dict[str, str] = {}
    for slug, page in pages.items():
        level = page.get("detail_level", "L1")
        if slug in cached_content:
            rendered_content[slug] = cached_content[slug]
        else:
            rendered_content[slug] = _get_page_content_at_level(page, level)

    # Assemble structured markdown
    snapshot = _assemble_context(
        pages,
        pov_character,
        primary_location,
        args.chapter,
        args.scene,
        args.outline,
        scene_type,
    )

    # Optional LLM synthesis
    snapshot = _maybe_synthesize(snapshot, pages, args.outline)

    token_count = count_tokens(snapshot)

    # Update cache
    stats = {
        "pages_retrieved": pages_retrieved,
        "pages_included": len(pages),
        "token_count": token_count,
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "tiers": tier_counts,
    }
    _update_cache(
        wiki_dir,
        args.chapter,
        args.scene,
        pages,
        rendered_content,
        stats,
    )

    print(json.dumps({"snapshot": snapshot, "stats": stats}, indent=2))


def cmd_cache_status(args: argparse.Namespace) -> None:
    """Return cache status for a story chapter."""
    story_dir = _validate_story_name(args.name)
    wiki_dir = get_wiki_dir(story_dir)
    cache = _load_cache(wiki_dir)

    if cache is None:
        print(
            json.dumps(
                {
                    "cached": False,
                    "chapter": None,
                    "scene": None,
                    "entity_count": 0,
                    "stats": None,
                }
            )
        )
        return

    print(
        json.dumps(
            {
                "cached": True,
                "chapter": cache.get("chapter"),
                "scene": cache.get("scene"),
                "entity_count": len(cache.get("entities", {})),
                "stats": cache.get("stats"),
            }
        )
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse arguments and dispatch to the appropriate command."""
    parser = argparse.ArgumentParser(description="Wiki snapshot tool")
    parser.add_argument(
        "--operation",
        required=True,
        choices=["snapshot", "cache-status"],
        help="Operation to perform",
    )
    parser.add_argument("--name", required=True, help="Story name")
    parser.add_argument("--chapter", required=True, type=int, help="Chapter number")
    parser.add_argument("--scene", type=int, help="Scene number")
    parser.add_argument("--outline", help="Scene outline text")
    parser.add_argument("--pov-character", help="POV character slug")
    parser.add_argument("--primary-location", help="Primary location slug")
    parser.add_argument(
        "--characters",
        help="Comma-separated additional character slugs",
    )
    parser.add_argument(
        "--locations",
        help="Comma-separated additional location slugs",
    )
    parser.add_argument(
        "--scene-type",
        choices=["dialogue", "action", "exposition", "mixed"],
        help="Scene type for detail level adaptation",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=DEFAULT_BUDGET,
        help=f"Token budget (default: {DEFAULT_BUDGET})",
    )

    args = parser.parse_args()

    if args.operation == "snapshot":
        cmd_snapshot(args)
    elif args.operation == "cache-status":
        cmd_cache_status(args)


if __name__ == "__main__":
    main()
