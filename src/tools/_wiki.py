"""Shared wiki utilities for wiki tools."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

# --- Constants ---
WIKI_SUBDIRS = [
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
]


# --- YAML Frontmatter ---
def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content.

    Returns (metadata_dict, body_text). Returns ({}, content) if no frontmatter.
    """
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    # parts[0] is empty (before first ---), parts[1] is YAML, parts[2] is body
    try:
        metadata = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return {}, content

    if not isinstance(metadata, dict):
        return {}, content

    body = parts[2].lstrip("\n")
    return metadata, body


def render_frontmatter(metadata: dict, body: str) -> str:
    """Render metadata dict + body back to markdown with YAML frontmatter."""
    fm = yaml.dump(metadata, default_flow_style=False, sort_keys=False).rstrip("\n")
    return f"---\n{fm}\n---\n\n{body}"


# --- Slug Generation ---
def slugify(name: str) -> str:
    """Convert a name to a kebab-case slug.

    Falls back to a hash-based slug when the input contains no ASCII
    word characters (e.g. names entirely in non-Latin scripts or
    punctuation), so downstream code never receives an empty slug.
    """
    if not isinstance(name, str):
        name = str(name)
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    if not slug:
        import hashlib

        digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:10]
        slug = f"entity-{digest}"
    return slug


# --- Index Operations ---
def read_index(wiki_dir: Path) -> list[dict]:
    """Read index.md and return list of entity entries.

    Each entry: {name, slug, type, aliases, path}
    """
    index_path = wiki_dir / "index.md"
    if not index_path.exists():
        return []

    content = index_path.read_text()
    entries: list[dict] = []

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Format: - slug | type | name | aliases | path
        if not line.startswith("- "):
            continue

        parts = line[2:].split("|")
        if len(parts) < 3:
            continue

        slug = parts[0].strip()
        page_type = parts[1].strip()
        name = parts[2].strip()
        aliases: list[str] = []
        if len(parts) >= 4:
            raw_aliases = parts[3].strip()
            if raw_aliases:
                aliases = [a.strip() for a in raw_aliases.split(",") if a.strip()]

        path = ""
        if len(parts) >= 5:
            path = parts[4].strip()
        if not path:
            subdir = _TYPE_TO_DIR.get(page_type, "")
            path = f"{subdir}/{slug}.md" if subdir else f"{slug}.md"

        entries.append(
            {
                "name": name,
                "slug": slug,
                "type": page_type,
                "aliases": aliases,
                "path": path,
            }
        )

    return entries


def write_index(wiki_dir: Path, entries: list[dict]) -> None:
    """Write entity entries to index.md in structured format."""
    from tools._io import _atomic_write

    lines = ["# Wiki Index", "", "<!-- slug | type | name | aliases | path -->", ""]
    for entry in sorted(entries, key=lambda e: e.get("slug", "")):
        aliases_str = ", ".join(entry.get("aliases", []))
        slug = entry["slug"]
        page_type = entry["type"]
        subdir = _TYPE_TO_DIR.get(page_type, "")
        path = entry.get("path") or (f"{subdir}/{slug}.md" if subdir else f"{slug}.md")
        lines.append(
            f"- {slug} | {page_type} | {entry['name']} | {aliases_str} | {path}"
        )
    lines.append("")

    _atomic_write(wiki_dir / "index.md", "\n".join(lines))


def match_entities_in_text(text: str, index_entries: list[dict]) -> list[dict]:
    """Match entity names and aliases in text against index entries.

    Returns list of matched entries with their slugs.
    """
    text_lower = text.lower()
    matched: list[dict] = []
    seen_slugs: set[str] = set()

    for entry in index_entries:
        if entry["slug"] in seen_slugs:
            continue

        names_to_check = [entry["name"]] + entry.get("aliases", [])
        for name in names_to_check:
            if name.lower() in text_lower:
                matched.append(entry)
                seen_slugs.add(entry["slug"])
                break

    return matched


# --- Wiki Path Helpers ---
def get_wiki_dir(story_dir: Path) -> Path:
    """Get the wiki directory for a story."""
    return story_dir / "wiki"


_TYPE_TO_DIR = {
    "character": "characters",
    "location": "locations",
    "event": "events",
    "faction": "factions",
    "item": "items",
    "plot_thread": "plot-threads",
    "world_rule": "world-rules",
    "theme": "themes",
    "relationship": "relationships",
    "timeline_entry": "timeline",
    "chapter_synopsis": "chapters",
    "contradiction": "characters",  # stored alongside, or root
}


def _validate_slug(slug: str) -> None:
    """Reject empty slugs or slugs containing path traversal sequences/backslashes.

    Raises ValueError on invalid input so callers (e.g. run_batch) can catch
    it and roll back gracefully. Previously this called sys.exit(1), which
    killed long-running pipeline processes on any malformed entity name.
    """
    if not isinstance(slug, str) or not slug:
        raise ValueError(f"invalid slug (empty): {slug!r}")
    if ".." in slug or "/" in slug or "\\" in slug:
        raise ValueError(f"invalid slug (contains '..', '/' or '\\\\'): {slug!r}")


def _validate_glob_pattern(pattern: str) -> None:
    """Reject glob patterns containing path traversal sequences or slashes.

    Raises ValueError on invalid input rather than calling sys.exit.
    """
    if not isinstance(pattern, str) or not pattern:
        raise ValueError(f"invalid glob pattern (empty): {pattern!r}")
    if ".." in pattern or "/" in pattern or "\\" in pattern:
        raise ValueError(
            f"invalid glob pattern (contains '..', '/' or '\\\\'): {pattern!r}"
        )


def _filter_within_wiki(wiki_dir: Path, paths: list[Path]) -> list[Path]:
    """Filter paths to only those within the wiki directory."""
    resolved_wiki = wiki_dir.resolve()
    return [p for p in paths if p.resolve().is_relative_to(resolved_wiki)]


def find_pages(
    wiki_dir: Path,
    slug: str | None = None,
    page_type: str | None = None,
    glob_pattern: str | None = None,
) -> list[Path]:
    """Find wiki pages by slug, type, or glob pattern."""
    results: list[Path] = []

    if slug:
        _validate_slug(slug)
        # Search all subdirectories for {slug}.md
        for subdir in WIKI_SUBDIRS:
            candidate = wiki_dir / subdir / f"{slug}.md"
            if candidate.exists():
                results.append(candidate)
        # Also check wiki root
        root_candidate = wiki_dir / f"{slug}.md"
        if root_candidate.exists():
            results.append(root_candidate)

    elif page_type:
        if page_type not in _TYPE_TO_DIR:
            return []
        subdir_name = _TYPE_TO_DIR[page_type]
        subdir_path = wiki_dir / subdir_name
        if subdir_path.exists():
            results.extend(sorted(subdir_path.glob("*.md")))

    elif glob_pattern:
        _validate_glob_pattern(glob_pattern)
        results.extend(sorted(wiki_dir.glob(glob_pattern)))

    else:
        # Return all pages across all subdirs
        for subdir in WIKI_SUBDIRS:
            subdir_path = wiki_dir / subdir
            if subdir_path.exists():
                results.extend(sorted(subdir_path.glob("*.md")))

    # Belt-and-suspenders: ensure all results are within wiki_dir
    return _filter_within_wiki(wiki_dir, results)
