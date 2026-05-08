"""Context assembly helper — single entry point for wiki + recap retrieval."""

from __future__ import annotations

import sys
from typing import Any, Literal

from domain.exceptions import StoryGenerationError
from tools._llm import count_tokens, generate_text
from tools.recap_index import query_recap
from tools.wiki_snapshot import get_snapshot

# ---------------------------------------------------------------------------
# Per-scope wiki budget caps (tokens)
# ---------------------------------------------------------------------------
_SCOPE_WIKI_BUDGET: dict[str, int] = {
    "outline": 6000,
    "chapter": 12000,
    "scene": 8000,
    "consistency": 10000,
    "recap": 2000,
    "metadata": 4000,
    "final_edit": 10000,
}

# Scopes where an empty wiki snapshot is expected (no warning emitted)
_INITIAL_SCOPES: frozenset[str] = frozenset({"outline"})

# Scopes where ChromaDB unavailability is fatal
_FATAL_CHROMA_SCOPES: frozenset[str] = frozenset({"chapter", "consistency"})


def assemble_context(
    story_name: str,
    *,
    scope: Literal[
        "outline",
        "chapter",
        "scene",
        "consistency",
        "recap",
        "metadata",
        "final_edit",
    ],
    focus: str,
    chapter: int | None = None,
    scene: int | None = None,
    pov_character: str | None = None,
    primary_location: str | None = None,
    characters: tuple[str, ...] = (),
    locations: tuple[str, ...] = (),
    keywords: tuple[str, ...] = (),
    recap_window: tuple[str, int] = ("character", 3),
    token_budget: int = 15000,
) -> dict:  # {"wiki_snapshot": str, "recap_snippets": list[str]}
    """Assemble wiki + recap context for an agent.

    Internally calls `wiki_snapshot.get_snapshot` and
    `recap_index.query_recap` with parameters determined by `scope`.
    The token budget is split: wiki_snapshot <= 70%, recap_snippets <= 30%.
    """
    wiki_budget = min(_SCOPE_WIKI_BUDGET[scope], int(token_budget * 0.7))
    recap_budget = int(token_budget * 0.3)

    # --- Wiki snapshot ---
    wiki_text: str = _retrieve_wiki(
        story_name=story_name,
        scope=scope,
        focus=focus,
        chapter=chapter,
        scene=scene,
        pov_character=pov_character,
        primary_location=primary_location,
        characters=characters,
        locations=locations,
        wiki_budget=wiki_budget,
    )

    # --- Recap snippets ---
    recap_snippets: list[str] = _retrieve_recap(
        story_name=story_name,
        scope=scope,
        focus=focus,
        chapter=chapter,
        characters=characters,
        locations=locations,
        recap_window=recap_window,
        recap_budget=recap_budget,
    )

    return {"wiki_snapshot": wiki_text, "recap_snippets": recap_snippets}


def render_recap_as_markdown(snippets: list[str]) -> str:
    """Convert a list of recap event JSON strings to a concise markdown narrative.

    Returns an empty string if snippets is empty.
    Calls the local LLM synchronously.
    """
    if not snippets:
        return ""
    import pathlib

    from infrastructure.prompts.prompt_loader import PromptLoader

    _loader = PromptLoader(
        prompts_dir=str(pathlib.Path(__file__).resolve().parents[2] / "prompts")
    )
    combined = "\n\n---\n\n".join(snippets)
    try:
        prompt = _loader.load_prompt(
            "recap/render_markdown", variables={"events_json": combined}
        )
        return generate_text(prompt)
    except Exception as exc:
        print(
            f"[ContextAssembly] Warning: recap markdown render failed: {exc}",
            file=sys.stderr,
        )
        return "\n\n".join(snippets)


def _retrieve_wiki(
    *,
    story_name: str,
    scope: str,
    focus: str,
    chapter: int | None,
    scene: int | None,
    pov_character: str | None,
    primary_location: str | None,
    characters: tuple[str, ...],
    locations: tuple[str, ...],
    wiki_budget: int,
) -> str:
    """Call get_snapshot and handle empty/error conditions."""
    result = get_snapshot(
        story_name=story_name,
        chapter=chapter or 0,
        scene=scene or 0,
        outline=focus,
        pov_character=pov_character,
        characters=list(characters) if characters else None,
        primary_location=primary_location,
        locations=list(locations) if locations else None,
        budget=wiki_budget,
    )

    if result is None:
        if scope in _FATAL_CHROMA_SCOPES:
            raise StoryGenerationError(
                f"Wiki snapshot unavailable for story={story_name!r}, scope={scope!r}"
            )
        if scope not in _INITIAL_SCOPES:
            print(
                f"[ContextAssembly] Warning: wiki snapshot empty for"
                f" story={story_name!r}, scope={scope!r}",
                file=sys.stderr,
            )
        return ""

    return result


def _retrieve_recap(
    *,
    story_name: str,
    scope: str,
    focus: str,
    chapter: int | None,
    characters: tuple[str, ...],
    locations: tuple[str, ...],
    recap_window: tuple[str, int],
    recap_budget: int,
) -> list[str]:
    """Retrieve recap entries according to recap_window strategy."""
    strategy, n = recap_window
    if strategy == "none" or n == 0:
        return []

    raw: list[dict[str, Any]] = []
    try:
        raw = _fetch_recap_raw(
            story_name=story_name,
            strategy=strategy,
            n=n,
            focus=focus,
            chapter=chapter,
            characters=characters,
            locations=locations,
        )
    except Exception as exc:
        if scope in _FATAL_CHROMA_SCOPES:
            raise StoryGenerationError(
                f"Recap retrieval failed for story={story_name!r},"
                f" scope={scope!r}: {exc}"
            ) from exc
        print(
            f"[ContextAssembly] Warning: recap retrieval error for"
            f" scope={scope!r}: {exc}",
            file=sys.stderr,
        )
        return []

    return _apply_recap_budget(raw, recap_budget)


def _fetch_recap_raw(
    *,
    story_name: str,
    strategy: str,
    n: int,
    focus: str,
    chapter: int | None,
    characters: tuple[str, ...],
    locations: tuple[str, ...],
) -> list[dict[str, Any]]:
    """Fetch raw recap dicts for the given strategy."""
    if strategy == "character":
        seen: set[str] = set()
        rows: list[dict[str, Any]] = []
        for slug in characters:
            for row in query_recap(story_name, character=slug):
                if row["id"] not in seen:
                    seen.add(row["id"])
                    rows.append(row)
        rows.sort(
            key=lambda r: (r.get("metadata") or {}).get("chapter", 0),
            reverse=True,
        )
        return rows[:n]

    if strategy == "chapter":
        if chapter is not None and chapter > 1:
            lo = max(1, chapter - n)
            hi = chapter - 1
            rows = query_recap(story_name, chapter_range=(lo, hi))
        else:
            rows = query_recap(story_name)
        rows.sort(
            key=lambda r: (r.get("metadata") or {}).get("chapter", 0),
            reverse=True,
        )
        return rows[:n]

    if strategy == "location":
        seen2: set[str] = set()
        rows2: list[dict[str, Any]] = []
        for slug in locations:
            for row in query_recap(story_name, location=slug):
                if row["id"] not in seen2:
                    seen2.add(row["id"])
                    rows2.append(row)
        rows2.sort(
            key=lambda r: (r.get("metadata") or {}).get("chapter", 0),
            reverse=True,
        )
        return rows2[:n]

    if strategy == "semantic":
        return query_recap(story_name, query_text=focus, n_results=n)

    print(
        f"[ContextAssembly] Warning: unknown recap_window strategy {strategy!r},"
        " skipping",
        file=sys.stderr,
    )
    return []


def _apply_recap_budget(
    rows: list[dict[str, Any]],
    recap_budget: int,
) -> list[str]:
    """Extract document text from rows, capping at recap_budget tokens."""
    snippets: list[str] = []
    used_tokens = 0
    for row in rows:
        doc = row.get("document") or ""
        if not doc:
            continue
        doc_tokens = count_tokens(doc)
        if used_tokens + doc_tokens > recap_budget:
            break
        snippets.append(doc)
        used_tokens += doc_tokens
    return snippets
