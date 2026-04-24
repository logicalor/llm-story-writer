"""CLI tool for running consistency checks across the story wiki."""

from __future__ import annotations

import sys
from pathlib import Path
import argparse
import json
import re
from datetime import datetime, timezone

# Add the project root to sys.path so 'src' can be imported
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.tools._io import STORIES_DIR, _atomic_write, _validate_story_name  # noqa: E402
from src.tools._wiki import (  # noqa: E402
    WIKI_SUBDIRS,
    _TYPE_TO_DIR,
    _validate_slug,
    find_pages,
    get_wiki_dir,
    match_entities_in_text,
    parse_frontmatter,
    read_index,
)

# Wikilink pattern: [[slug]] or [[slug|display text]]
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")

# Timeline entry pattern: - **Chapter N** — TIME — DESCRIPTION
_TIMELINE_RE = re.compile(r"- \*\*Chapter (\d+)\*\* — (.+?) — (.+)")

# Required frontmatter fields for entity pages
_REQUIRED_FIELDS = ("type", "name", "slug", "confidence", "first_appearance")


# ---------------------------------------------------------------------------
# Finding dataclass
# ---------------------------------------------------------------------------


def _finding(
    severity: str,
    category: str,
    subtype: str,
    pages: list[str],
    message: str,
    suggested_fix: str,
) -> dict:
    """Build a finding dict."""
    return {
        "severity": severity,
        "category": category,
        "subtype": subtype,
        "pages": pages,
        "message": message,
        "suggested_fix": suggested_fix,
    }


def _summarise(findings: list[dict]) -> dict:
    """Count findings by severity."""
    errors = sum(1 for f in findings if f["severity"] == "error")
    warnings = sum(1 for f in findings if f["severity"] == "warning")
    info = sum(1 for f in findings if f["severity"] == "info")
    return {
        "errors": errors,
        "warnings": warnings,
        "info": info,
        "total": len(findings),
    }


def _output(operation: str, findings: list[dict]) -> None:
    """Print JSON report to stdout."""
    print(
        json.dumps(
            {
                "status": "ok",
                "operation": operation,
                "findings": findings,
                "summary": _summarise(findings),
            },
            indent=2,
        )
    )


# ---------------------------------------------------------------------------
# Contradictions.md append
# ---------------------------------------------------------------------------


def _append_contradictions(wiki_dir: Path, label: str, findings: list[dict]) -> None:
    """Append new findings to wiki/contradictions.md."""
    if not findings:
        return

    contradict_path = wiki_dir / "contradictions.md"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines: list[str] = [f"\n## {ts} — {label}\n"]
    for f in findings:
        page_list = ", ".join(f["pages"]) if f["pages"] else "n/a"
        lines.append(
            f"- **{f['severity']}** {f['category']}/{f['subtype']}: "
            f"{f['message']} — Pages: {page_list}"
        )
    lines.append("")

    block = "\n".join(lines)

    if contradict_path.exists():
        content = contradict_path.read_text()
    else:
        content = "# Contradictions\n"

    content = content.rstrip("\n") + "\n" + block
    _atomic_write(contradict_path, content)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_wikilinks(text: str) -> list[str]:
    """Extract wikilink slugs from markdown text."""
    return _WIKILINK_RE.findall(text)


def _all_wiki_slugs(wiki_dir: Path) -> set[str]:
    """Return set of all slugs that have a .md page on disk."""
    slugs: set[str] = set()
    for subdir in WIKI_SUBDIRS:
        subdir_path = wiki_dir / subdir
        if not subdir_path.exists():
            continue
        for p in subdir_path.glob("*.md"):
            if p.resolve().is_relative_to(wiki_dir.resolve()):
                slugs.add(p.stem)
    return slugs


def _parse_timeline(wiki_dir: Path) -> list[dict]:
    """Parse main-timeline.md and return list of {chapter, time, description}."""
    tl_path = wiki_dir / "timeline" / "main-timeline.md"
    if not tl_path.exists():
        return []

    entries: list[dict] = []
    for line in tl_path.read_text().splitlines():
        m = _TIMELINE_RE.match(line.strip())
        if m:
            entries.append(
                {
                    "chapter": int(m.group(1)),
                    "time": m.group(2),
                    "description": m.group(3),
                }
            )
    return entries


def _all_filesystem_pages(wiki_dir: Path) -> dict[str, Path]:
    """Return {slug: path} for all .md pages in wiki subdirs."""
    pages: dict[str, Path] = {}
    for subdir in WIKI_SUBDIRS:
        subdir_path = wiki_dir / subdir
        if not subdir_path.exists():
            continue
        for p in sorted(subdir_path.glob("*.md")):
            if p.resolve().is_relative_to(wiki_dir.resolve()):
                pages[p.stem] = p
    return pages


# ---------------------------------------------------------------------------
# Command: check-chapter
# ---------------------------------------------------------------------------


def cmd_check_chapter(args: argparse.Namespace) -> None:
    """Run post-chapter contradiction detection."""
    # Validate required args first
    if not args.chapter_text:
        print("Error: --chapter-text is required for check-chapter", file=sys.stderr)
        sys.exit(2)
    if args.chapter_number is None:
        print("Error: --chapter-number is required for check-chapter", file=sys.stderr)
        sys.exit(2)

    story_dir = _validate_story_name(args.name)

    # Validate chapter-text path before any file I/O
    chapter_path = Path(args.chapter_text).resolve()
    stories_resolved = STORIES_DIR.resolve()
    if not chapter_path.is_relative_to(stories_resolved):
        print(
            "Error: chapter-text path must be within the stories directory",
            file=sys.stderr,
        )
        sys.exit(1)
    if not chapter_path.exists():
        print(
            f"Error: chapter-text file not found: {args.chapter_text}",
            file=sys.stderr,
        )
        sys.exit(1)

    wiki_dir = get_wiki_dir(story_dir)

    if not wiki_dir.exists():
        _output("check-chapter", [])
        return

    chapter_text = chapter_path.read_text()
    chapter_num: int = args.chapter_number

    index_entries = read_index(wiki_dir)
    all_slugs = _all_wiki_slugs(wiki_dir)
    findings: list[dict] = []

    # --- Entity mentions cross-reference ---
    matched = match_entities_in_text(chapter_text, index_entries)
    for entry in matched:
        slug = entry["slug"]
        # Check if entity has a wiki page
        pages = find_pages(wiki_dir, slug=slug)
        if not pages:
            findings.append(
                _finding(
                    "warning",
                    "factual_consistency",
                    "missing_entity",
                    [slug],
                    f"Entity '{entry['name']}' mentioned in chapter {chapter_num} "
                    f"but has no wiki page",
                    f"Create a wiki page for '{entry['name']}' with slug '{slug}'",
                )
            )
            continue

        # Check character status contradictions
        page_content = pages[0].read_text()
        metadata, _body = parse_frontmatter(page_content)
        if metadata.get("type") == "character" and metadata.get("status") == "dead":
            findings.append(
                _finding(
                    "error",
                    "characterization",
                    "status_contradiction",
                    [slug],
                    f"Character '{entry['name']}' has status 'dead' in wiki "
                    f"but is mentioned in chapter {chapter_num}",
                    f"Verify if '{entry['name']}' should be alive or if the "
                    f"mention is a flashback/memory",
                )
            )

    # --- Broken wikilinks in chapter text ---
    wikilinks = _extract_wikilinks(chapter_text)
    for link_slug in wikilinks:
        if link_slug not in all_slugs:
            findings.append(
                _finding(
                    "warning",
                    "factual_consistency",
                    "broken_wikilink",
                    [link_slug],
                    f"Wikilink [[{link_slug}]] in chapter {chapter_num} "
                    f"points to non-existent page",
                    f"Create page for '{link_slug}' or fix the wikilink",
                )
            )

    # --- Timeline ordering check ---
    timeline = _parse_timeline(wiki_dir)
    if timeline:
        for entry in timeline:
            if entry["chapter"] > chapter_num:
                findings.append(
                    _finding(
                        "warning",
                        "timeline_plot_logic",
                        "chapter_ordering_violation",
                        [],
                        f"Timeline contains entry for chapter {entry['chapter']} "
                        f"which is ahead of current chapter {chapter_num}: "
                        f"'{entry['description']}'",
                        "Verify timeline entry is correct or remove future entries",
                    )
                )

    # Append to contradictions.md
    _append_contradictions(wiki_dir, f"Chapter {chapter_num} check", findings)

    _output("check-chapter", findings)


# ---------------------------------------------------------------------------
# Command: check-full
# ---------------------------------------------------------------------------


def cmd_check_full(args: argparse.Namespace) -> None:
    """Run comprehensive wiki lint."""
    story_dir = _validate_story_name(args.name)
    wiki_dir = get_wiki_dir(story_dir)

    if not wiki_dir.exists():
        _output("check-full", [])
        return

    if args.current_chapter is None:
        print("Error: --current-chapter is required for check-full", file=sys.stderr)
        sys.exit(2)

    current_chapter: int = args.current_chapter
    findings: list[dict] = []

    index_entries = read_index(wiki_dir)
    index_slugs = {e["slug"] for e in index_entries}
    fs_pages = _all_filesystem_pages(wiki_dir)
    fs_slugs = set(fs_pages.keys())

    # --- Orphan detection ---
    # Pages on disk but not in index
    for slug in sorted(fs_slugs - index_slugs):
        findings.append(
            _finding(
                "warning",
                "factual_consistency",
                "orphan_reference",
                [slug],
                f"Page '{slug}' exists on disk but is not listed in index.md",
                f"Add '{slug}' to index.md or remove the orphan page",
            )
        )

    # Entries in index with no file
    for slug in sorted(index_slugs - fs_slugs):
        findings.append(
            _finding(
                "warning",
                "factual_consistency",
                "orphan_reference",
                [slug],
                f"Index entry '{slug}' has no corresponding .md file on disk",
                f"Create the page for '{slug}' or remove from index.md",
            )
        )

    # --- Stale claims ---
    for slug, page_path in sorted(fs_pages.items()):
        content = page_path.read_text()
        metadata, _body = parse_frontmatter(content)

        first_app = metadata.get("first_appearance")
        last_updated = metadata.get("last_updated")

        # Use last_updated if it's a chapter number (int); otherwise fall back to first_appearance
        page_chapter = None
        reference_field = "first_appearance"
        if isinstance(first_app, int):
            page_chapter = first_app

        if isinstance(last_updated, int):
            page_chapter = last_updated
            reference_field = "last_updated"
        elif isinstance(last_updated, str):
            # last_updated is a timestamp string; check first_appearance instead
            pass

        if page_chapter is not None and current_chapter - page_chapter > 5:
            findings.append(
                _finding(
                    "info",
                    "narrative_style",
                    "stale_claim",
                    [slug],
                    f"Page '{slug}' ({reference_field}: {page_chapter}) "
                    f"has not been updated in {current_chapter - page_chapter}+ chapters "
                    f"(current: {current_chapter})",
                    f"Review and update '{slug}' for current chapter relevance",
                )
            )

        # --- Confidence downgrade candidates ---
        if (
            metadata.get("confidence") == "verified"
            and page_chapter is not None
            and current_chapter - page_chapter >= 10
        ):
            findings.append(
                _finding(
                    "info",
                    "narrative_style",
                    "confidence_downgrade",
                    [slug],
                    f"Page '{slug}' has confidence 'verified' but hasn't been "
                    f"updated in {current_chapter - page_chapter}+ chapters — "
                    f"may need review",
                    f"Re-verify '{slug}' or downgrade confidence to 'speculative'",
                )
            )

    # --- Missing cross-references (broken wikilinks) ---
    all_slugs = _all_wiki_slugs(wiki_dir)
    for slug, page_path in sorted(fs_pages.items()):
        content = page_path.read_text()
        _metadata, body = parse_frontmatter(content)
        wikilinks = _extract_wikilinks(body)
        for link_slug in wikilinks:
            if link_slug not in all_slugs:
                findings.append(
                    _finding(
                        "warning",
                        "factual_consistency",
                        "broken_wikilink",
                        [slug, link_slug],
                        f"Page '{slug}' contains wikilink [[{link_slug}]] "
                        f"pointing to non-existent page",
                        f"Create page for '{link_slug}' or fix the wikilink in '{slug}'",
                    )
                )

    # --- Timeline ordering ---
    timeline = _parse_timeline(wiki_dir)
    if timeline:
        prev_chapter = -1
        for entry in timeline:
            ch = entry["chapter"]
            if ch < prev_chapter:
                findings.append(
                    _finding(
                        "error",
                        "timeline_plot_logic",
                        "temporal_ordering",
                        [],
                        f"Timeline chapter numbers are not monotonically non-decreasing: "
                        f"chapter {ch} appears after chapter {prev_chapter}",
                        "Re-order timeline entries so chapter numbers are non-decreasing",
                    )
                )
            prev_chapter = ch

    # --- Index integrity ---
    for entry in index_entries:
        slug = entry["slug"]
        page_type = entry["type"]
        if slug in fs_pages:
            page_path = fs_pages[slug]
            content = page_path.read_text()
            metadata, _body = parse_frontmatter(content)
            # Check type matches
            fm_type = metadata.get("type", "")
            if fm_type and fm_type != page_type:
                findings.append(
                    _finding(
                        "warning",
                        "factual_consistency",
                        "naming_inconsistency",
                        [slug],
                        f"Index lists '{slug}' as type '{page_type}' but page "
                        f"frontmatter says '{fm_type}'",
                        f"Update index or page frontmatter for '{slug}' to match",
                    )
                )
            # Check correct directory
            expected_dir = _TYPE_TO_DIR.get(fm_type, "")
            if expected_dir:
                actual_dir = page_path.parent.name
                if actual_dir != expected_dir:
                    findings.append(
                        _finding(
                            "warning",
                            "factual_consistency",
                            "naming_inconsistency",
                            [slug],
                            f"Page '{slug}' is in directory '{actual_dir}' but "
                            f"type '{fm_type}' should be in '{expected_dir}'",
                            f"Move '{slug}.md' to {expected_dir}/",
                        )
                    )

    # Append to contradictions.md
    _append_contradictions(wiki_dir, "Full lint", findings)

    _output("check-full", findings)


# ---------------------------------------------------------------------------
# Command: check-entity
# ---------------------------------------------------------------------------


def cmd_check_entity(args: argparse.Namespace) -> None:
    """Validate a single entity page."""
    story_dir = _validate_story_name(args.name)
    wiki_dir = get_wiki_dir(story_dir)

    if not args.slug:
        print("Error: --slug is required for check-entity", file=sys.stderr)
        sys.exit(2)

    slug = args.slug
    _validate_slug(slug)

    findings: list[dict] = []

    if not wiki_dir.exists():
        findings.append(
            _finding(
                "error",
                "factual_consistency",
                "missing_entity",
                [slug],
                f"Wiki directory does not exist for story '{args.name}'",
                "Initialise the wiki with wiki-init",
            )
        )
        _output("check-entity", findings)
        return

    # --- Find entity page ---
    pages = find_pages(wiki_dir, slug=slug)
    if not pages:
        findings.append(
            _finding(
                "error",
                "factual_consistency",
                "missing_entity",
                [slug],
                f"No wiki page found for slug '{slug}'",
                f"Create a wiki page for '{slug}'",
            )
        )
        _output("check-entity", findings)
        return

    page_path = pages[0]
    content = page_path.read_text()
    metadata, body = parse_frontmatter(content)

    # --- Required fields ---
    for field in _REQUIRED_FIELDS:
        if field not in metadata:
            findings.append(
                _finding(
                    "error",
                    "factual_consistency",
                    "missing_entity",
                    [slug],
                    f"Page '{slug}' is missing required frontmatter field '{field}'",
                    f"Add '{field}' to the frontmatter of '{slug}'",
                )
            )

    # --- Detail levels ---
    detail_levels = metadata.get("detail_levels", {})
    if not isinstance(detail_levels, dict):
        detail_levels = {}
    for level in ("L1", "L2", "L3"):
        if level not in detail_levels or not detail_levels[level]:
            findings.append(
                _finding(
                    "warning",
                    "narrative_style",
                    "stale_claim",
                    [slug],
                    f"Page '{slug}' is missing detail level '{level}'",
                    f"Add '{level}' content to detail_levels for '{slug}'",
                )
            )

    # --- Wikilinks in body ---
    all_slugs = _all_wiki_slugs(wiki_dir)
    wikilinks = _extract_wikilinks(body)
    for link_slug in wikilinks:
        if link_slug not in all_slugs:
            findings.append(
                _finding(
                    "warning",
                    "factual_consistency",
                    "broken_wikilink",
                    [slug, link_slug],
                    f"Page '{slug}' contains wikilink [[{link_slug}]] "
                    f"pointing to non-existent page",
                    f"Create page for '{link_slug}' or fix the wikilink",
                )
            )

    # --- Verify entity in index ---
    index_entries = read_index(wiki_dir)
    index_slugs = {e["slug"] for e in index_entries}
    if slug not in index_slugs:
        findings.append(
            _finding(
                "warning",
                "factual_consistency",
                "orphan_reference",
                [slug],
                f"Page '{slug}' exists but is not listed in index.md",
                f"Add '{slug}' to index.md",
            )
        )

    # --- Verify correct type directory ---
    fm_type = metadata.get("type", "")
    expected_dir = _TYPE_TO_DIR.get(fm_type, "")  # type: ignore[arg-type]
    if expected_dir:
        actual_dir = page_path.parent.name
        if actual_dir != expected_dir:
            findings.append(
                _finding(
                    "warning",
                    "factual_consistency",
                    "naming_inconsistency",
                    [slug],
                    f"Page '{slug}' is in directory '{actual_dir}' but "
                    f"type '{fm_type}' should be in '{expected_dir}'",
                    f"Move '{slug}.md' to {expected_dir}/",
                )
            )

    # Append to contradictions.md
    _append_contradictions(wiki_dir, "Entity check", findings)

    _output("check-entity", findings)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse arguments and dispatch to the appropriate command."""
    parser = argparse.ArgumentParser(description="Wiki lint tool")
    parser.add_argument(
        "--operation",
        required=True,
        choices=["check-chapter", "check-full", "check-entity"],
        help="Lint operation to perform",
    )
    parser.add_argument("--name", required=True, help="Story name")
    parser.add_argument(
        "--chapter-number", type=int, help="Chapter number (for check-chapter)"
    )
    parser.add_argument(
        "--chapter-text",
        help="File path to chapter content (for check-chapter)",
    )
    parser.add_argument(
        "--current-chapter", type=int, help="Current chapter number (for check-full)"
    )
    parser.add_argument("--slug", help="Entity slug (for check-entity)")

    args = parser.parse_args()

    if args.operation == "check-chapter":
        cmd_check_chapter(args)
    elif args.operation == "check-full":
        cmd_check_full(args)
    elif args.operation == "check-entity":
        cmd_check_entity(args)


if __name__ == "__main__":
    main()
