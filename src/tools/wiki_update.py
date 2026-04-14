"""CLI tool for creating, updating, and managing wiki pages."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src = str(Path(__file__).resolve().parents[1])
if _src not in sys.path:
    sys.path.insert(0, _src)

from src.tools._io import _atomic_write, _validate_story_name  # noqa: E402
from src.tools._wiki import (  # noqa: E402
    _TYPE_TO_DIR,
    _validate_slug,
    find_pages,
    get_wiki_dir,
    parse_frontmatter,
    read_index,
    render_frontmatter,
    write_index,
)

CHROMADB_DIR = os.environ.get("CHROMADB_DIR", str(PROJECT_ROOT / ".chromadb"))

# Valid page types
_VALID_PAGE_TYPES = set(_TYPE_TO_DIR.keys()) - {"contradiction"}


# ---------------------------------------------------------------------------
# ChromaDB helpers
# ---------------------------------------------------------------------------


def _upsert_to_chromadb(story_name: str, slug: str, body: str, metadata: dict) -> None:
    """Upsert a page into the ChromaDB wiki collection. Graceful on failure."""
    try:
        import chromadb  # type: ignore[import-not-found]

        client = chromadb.PersistentClient(path=CHROMADB_DIR)
        collection_name = f"wiki-{story_name}"
        collection = client.get_or_create_collection(name=collection_name)

        # Build metadata — only string/int/float/bool values for ChromaDB
        chroma_meta: dict[str, str | int | float | bool] = {}
        for key in ("type", "name", "slug", "confidence", "first_appearance"):
            if key in metadata:
                chroma_meta[key] = metadata[key]
        # Type-specific fields
        for key in ("role", "status", "region", "chapter", "impact"):
            if key in metadata:
                chroma_meta[key] = metadata[key]

        collection.upsert(
            ids=[slug],
            documents=[body],
            metadatas=[chroma_meta],
        )
    except Exception as exc:
        print(
            f"Warning: ChromaDB upsert failed (non-fatal): {exc}",
            file=sys.stderr,
        )


# ---------------------------------------------------------------------------
# Log helper
# ---------------------------------------------------------------------------


def _append_log(wiki_dir: Path, message: str) -> None:
    """Append an entry to log.md."""
    log_path = wiki_dir / "log.md"
    ts = datetime.now(timezone.utc).isoformat()
    entry = f"- {ts} — {message}\n"

    if log_path.exists():
        content = log_path.read_text()
    else:
        content = "# Wiki Change Log\n"

    content = content.rstrip("\n") + "\n" + entry
    _atomic_write(log_path, content)


# ---------------------------------------------------------------------------
# Command: create
# ---------------------------------------------------------------------------


def cmd_create(args: argparse.Namespace) -> None:
    """Create a new wiki page."""
    story_dir = _validate_story_name(args.name)
    wiki_dir = get_wiki_dir(story_dir)

    if not wiki_dir.exists():
        print("Error: wiki not initialised — run wiki-init first", file=sys.stderr)
        sys.exit(1)

    # Validate page type
    page_type = args.page_type
    if page_type not in _VALID_PAGE_TYPES:
        print(
            f"Error: invalid page type '{page_type}'. "
            f"Valid types: {sorted(_VALID_PAGE_TYPES)}",
            file=sys.stderr,
        )
        sys.exit(2)

    slug = args.slug
    _validate_slug(slug)

    # Check slug doesn't already exist
    existing = find_pages(wiki_dir, slug=slug)
    if existing:
        print(f"Error: page with slug '{slug}' already exists", file=sys.stderr)
        sys.exit(1)

    # Parse optional JSON args
    aliases: list[str] = []
    if args.aliases:
        try:
            parsed = json.loads(args.aliases)
            if not isinstance(parsed, list) or not all(
                isinstance(a, str) for a in parsed
            ):
                print(
                    "Error: --aliases must be a JSON array of strings",
                    file=sys.stderr,
                )
                sys.exit(2)
            aliases = parsed
        except json.JSONDecodeError:
            print("Error: --aliases is not valid JSON", file=sys.stderr)
            sys.exit(2)

    detail_levels: dict[str, str] = {}
    if args.detail_levels:
        try:
            parsed_dl = json.loads(args.detail_levels)
            if not isinstance(parsed_dl, dict):
                print(
                    "Error: --detail-levels must be a JSON object",
                    file=sys.stderr,
                )
                sys.exit(2)
            detail_levels = parsed_dl
        except json.JSONDecodeError:
            print("Error: --detail-levels is not valid JSON", file=sys.stderr)
            sys.exit(2)

    # Build frontmatter
    ts = datetime.now(timezone.utc).isoformat()
    metadata: dict = {
        "type": page_type,
        "name": args.page_name,
        "slug": slug,
        "confidence": args.confidence or "verified",
        "first_appearance": args.first_appearance or 1,
        "aliases": aliases,
        "last_updated": ts,
        "version": 1,
        "detail_levels": detail_levels,
    }

    # Type-specific fields
    if page_type == "character":
        if args.role:
            metadata["role"] = args.role
        if args.status:
            metadata["status"] = args.status
    elif page_type == "location":
        if args.region:
            metadata["region"] = args.region
    elif page_type == "event":
        if args.chapter:
            metadata["chapter"] = args.chapter
        if args.impact:
            metadata["impact"] = args.impact
    elif page_type == "plot_thread":
        if args.status:
            metadata["status"] = args.status

    body = args.body or ""
    content = render_frontmatter(metadata, body)

    # Write page file
    type_dir = _TYPE_TO_DIR[page_type]
    page_path = wiki_dir / type_dir / f"{slug}.md"
    _atomic_write(page_path, content)

    # Update index.md
    index_entries = read_index(wiki_dir)
    index_entries.append(
        {
            "name": args.page_name,
            "slug": slug,
            "type": page_type,
            "aliases": aliases,
        }
    )
    write_index(wiki_dir, index_entries)

    # Log
    _append_log(wiki_dir, f"[create] {slug}: Created {page_type} page")

    # ChromaDB upsert
    _upsert_to_chromadb(args.name, slug, body, metadata)

    print(json.dumps({"status": "ok", "slug": slug, "path": str(page_path)}))


# ---------------------------------------------------------------------------
# Command: update
# ---------------------------------------------------------------------------


def cmd_update(args: argparse.Namespace) -> None:
    """Update an existing wiki page."""
    story_dir = _validate_story_name(args.name)
    wiki_dir = get_wiki_dir(story_dir)

    if not wiki_dir.exists():
        print("Error: wiki not initialised", file=sys.stderr)
        sys.exit(1)

    slug = args.slug
    _validate_slug(slug)

    pages = find_pages(wiki_dir, slug=slug)
    if not pages:
        print(f"Error: page '{slug}' not found", file=sys.stderr)
        sys.exit(1)

    page_path = pages[0]
    content = page_path.read_text()
    metadata, body = parse_frontmatter(content)

    # Merge frontmatter from --frontmatter arg
    if args.frontmatter:
        try:
            fm_update = json.loads(args.frontmatter)
            if not isinstance(fm_update, dict):
                print(
                    "Error: --frontmatter must be a JSON object",
                    file=sys.stderr,
                )
                sys.exit(2)
            metadata.update(fm_update)
        except json.JSONDecodeError:
            print("Error: --frontmatter is not valid JSON", file=sys.stderr)
            sys.exit(2)

    # Update detail_levels
    if args.detail_levels:
        try:
            dl_update = json.loads(args.detail_levels)
            if not isinstance(dl_update, dict):
                print(
                    "Error: --detail-levels must be a JSON object",
                    file=sys.stderr,
                )
                sys.exit(2)
            existing_dl = metadata.get("detail_levels", {})
            if not isinstance(existing_dl, dict):
                existing_dl = {}
            existing_dl.update(dl_update)
            metadata["detail_levels"] = existing_dl
        except json.JSONDecodeError:
            print("Error: --detail-levels is not valid JSON", file=sys.stderr)
            sys.exit(2)

    # Body handling
    if args.body is not None:
        body = args.body
    elif args.merge_body is not None:
        body = body.rstrip("\n") + "\n\n" + args.merge_body

    # Auto-increment version and timestamp
    version = metadata.get("version", 0)
    if not isinstance(version, int):
        version = 0
    metadata["version"] = version + 1
    metadata["last_updated"] = datetime.now(timezone.utc).isoformat()

    new_content = render_frontmatter(metadata, body)
    _atomic_write(page_path, new_content)

    # Update index if name or aliases changed
    if args.frontmatter:
        fm_update = json.loads(args.frontmatter)
        if "name" in fm_update or "aliases" in fm_update:
            index_entries = read_index(wiki_dir)
            for entry in index_entries:
                if entry["slug"] == slug:
                    if "name" in fm_update:
                        entry["name"] = fm_update["name"]
                    if "aliases" in fm_update:
                        entry["aliases"] = fm_update["aliases"]
                    break
            write_index(wiki_dir, index_entries)

    # Log
    _append_log(wiki_dir, f"[update] {slug}: Updated to version {metadata['version']}")

    # ChromaDB upsert
    _upsert_to_chromadb(args.name, slug, body, metadata)

    print(json.dumps({"status": "ok", "slug": slug, "version": metadata["version"]}))


# ---------------------------------------------------------------------------
# Command: append-timeline
# ---------------------------------------------------------------------------


def cmd_append_timeline(args: argparse.Namespace) -> None:
    """Append events to the main timeline."""
    story_dir = _validate_story_name(args.name)
    wiki_dir = get_wiki_dir(story_dir)

    if not wiki_dir.exists():
        print("Error: wiki not initialised", file=sys.stderr)
        sys.exit(1)

    if not args.events:
        print("Error: --events is required for append-timeline", file=sys.stderr)
        sys.exit(2)

    try:
        events = json.loads(args.events)
        if not isinstance(events, list):
            print("Error: --events must be a JSON array", file=sys.stderr)
            sys.exit(2)
        for ev in events:
            if not isinstance(ev, dict):
                print("Error: each event must be a JSON object", file=sys.stderr)
                sys.exit(2)
            for field in ("time", "description", "chapter"):
                if field not in ev:
                    print(
                        f"Error: event missing required field '{field}'",
                        file=sys.stderr,
                    )
                    sys.exit(2)
    except json.JSONDecodeError:
        print("Error: --events is not valid JSON", file=sys.stderr)
        sys.exit(2)

    timeline_path = wiki_dir / "timeline" / "main-timeline.md"

    # Read existing entries
    existing_entries: list[dict] = []
    if timeline_path.exists():
        content = timeline_path.read_text()
        for line in content.splitlines():
            line = line.strip()
            if not line.startswith("- **Chapter"):
                continue
            # Parse: - **Chapter N** — TIME — DESCRIPTION
            import re

            m = re.match(r"- \*\*Chapter (\d+)\*\* — (.+?) — (.+)", line)
            if m:
                existing_entries.append(
                    {
                        "chapter": int(m.group(1)),
                        "time": m.group(2),
                        "description": m.group(3),
                    }
                )

    # Add new events
    for ev in events:
        existing_entries.append(
            {
                "chapter": ev["chapter"],
                "time": str(ev["time"]),
                "description": str(ev["description"]),
            }
        )

    # Sort by time
    existing_entries.sort(key=lambda e: e["time"])

    # Render
    lines = ["# Main Timeline", ""]
    for entry in existing_entries:
        lines.append(
            f"- **Chapter {entry['chapter']}** — {entry['time']} — {entry['description']}"
        )
    lines.append("")

    _atomic_write(timeline_path, "\n".join(lines))

    # Log
    _append_log(wiki_dir, f"[append-timeline] Added {len(events)} events")

    print(json.dumps({"status": "ok", "events_added": len(events)}))


# ---------------------------------------------------------------------------
# Command: batch
# ---------------------------------------------------------------------------


def cmd_batch(args: argparse.Namespace) -> None:
    """Execute multiple wiki operations atomically."""
    story_dir = _validate_story_name(args.name)
    wiki_dir = get_wiki_dir(story_dir)

    if not wiki_dir.exists():
        print("Error: wiki not initialised", file=sys.stderr)
        sys.exit(1)

    if not args.payload:
        print("Error: --payload is required for batch", file=sys.stderr)
        sys.exit(2)

    try:
        payload = json.loads(args.payload)
        if not isinstance(payload, dict):
            print("Error: --payload must be a JSON object", file=sys.stderr)
            sys.exit(2)
    except json.JSONDecodeError:
        print("Error: --payload is not valid JSON", file=sys.stderr)
        sys.exit(2)

    creates = payload.get("creates", [])
    updates = payload.get("updates", [])
    timeline_events = payload.get("timeline_events", [])

    if not isinstance(creates, list) or not isinstance(updates, list):
        print("Error: creates and updates must be arrays", file=sys.stderr)
        sys.exit(2)
    if not isinstance(timeline_events, list):
        print("Error: timeline_events must be an array", file=sys.stderr)
        sys.exit(2)

    created_files: list[Path] = []
    modified_backups: list[tuple[Path, str]] = []
    created_count = 0
    updated_count = 0

    try:
        # --- Creates ---
        for item in creates:
            if not isinstance(item, dict):
                raise ValueError("each create entry must be an object")
            slug = item.get("slug", "")
            page_type = item.get("page_type", "")
            page_name = item.get("page_name", "")

            if not slug or not page_type or not page_name:
                raise ValueError("create entry missing slug, page_type, or page_name")

            _validate_slug(slug)
            if page_type not in _VALID_PAGE_TYPES:
                raise ValueError(f"invalid page type: {page_type}")

            existing = find_pages(wiki_dir, slug=slug)
            if existing:
                raise ValueError(f"page '{slug}' already exists")

            aliases: list[str] = item.get("aliases", [])
            if not isinstance(aliases, list) or not all(
                isinstance(a, str) for a in aliases
            ):
                aliases = []

            detail_levels = item.get("detail_levels", {})
            if not isinstance(detail_levels, dict):
                detail_levels = {}

            ts = datetime.now(timezone.utc).isoformat()
            metadata: dict = {
                "type": page_type,
                "name": page_name,
                "slug": slug,
                "confidence": item.get("confidence", "verified"),
                "first_appearance": item.get("first_appearance", 1),
                "aliases": aliases,
                "last_updated": ts,
                "version": 1,
                "detail_levels": detail_levels,
            }

            # Type-specific fields
            for field in ("role", "status", "region", "chapter", "impact"):
                if field in item:
                    metadata[field] = item[field]

            body = item.get("body", "")
            content = render_frontmatter(metadata, body)

            type_dir = _TYPE_TO_DIR[page_type]
            page_path = wiki_dir / type_dir / f"{slug}.md"
            _atomic_write(page_path, content)
            created_files.append(page_path)
            created_count += 1

            # ChromaDB upsert
            _upsert_to_chromadb(args.name, slug, body, metadata)

        # Update index with all new creates
        if creates:
            index_entries = read_index(wiki_dir)
            for item in creates:
                slug = item["slug"]
                index_entries.append(
                    {
                        "name": item["page_name"],
                        "slug": slug,
                        "type": item["page_type"],
                        "aliases": item.get("aliases", []),
                    }
                )
            write_index(wiki_dir, index_entries)

        # --- Updates ---
        for item in updates:
            if not isinstance(item, dict):
                raise ValueError("each update entry must be an object")
            slug = item.get("slug", "")
            if not slug:
                raise ValueError("update entry missing slug")

            _validate_slug(slug)
            pages = find_pages(wiki_dir, slug=slug)
            if not pages:
                raise ValueError(f"page '{slug}' not found for update")

            page_path = pages[0]
            old_content = page_path.read_text()
            modified_backups.append((page_path, old_content))

            metadata, body = parse_frontmatter(old_content)

            # Merge frontmatter
            fm_update = item.get("frontmatter", {})
            if isinstance(fm_update, dict):
                metadata.update(fm_update)

            # Detail levels
            dl_update = item.get("detail_levels")
            if isinstance(dl_update, dict):
                existing_dl = metadata.get("detail_levels", {})
                if not isinstance(existing_dl, dict):
                    existing_dl = {}
                existing_dl.update(dl_update)
                metadata["detail_levels"] = existing_dl

            # Body
            if "body" in item and item["body"] is not None:
                body = item["body"]
            elif "merge_body" in item and item["merge_body"] is not None:
                body = body.rstrip("\n") + "\n\n" + item["merge_body"]

            version = metadata.get("version", 0)
            if not isinstance(version, int):
                version = 0
            metadata["version"] = version + 1
            metadata["last_updated"] = datetime.now(timezone.utc).isoformat()

            new_content = render_frontmatter(metadata, body)
            _atomic_write(page_path, new_content)
            updated_count += 1

            _upsert_to_chromadb(args.name, slug, body, metadata)

        # --- Timeline events ---
        timeline_added = 0
        if timeline_events:
            for ev in timeline_events:
                if not isinstance(ev, dict):
                    raise ValueError("each timeline event must be an object")
                for field in ("time", "description", "chapter"):
                    if field not in ev:
                        raise ValueError(
                            f"timeline event missing required field '{field}'"
                        )

            timeline_path = wiki_dir / "timeline" / "main-timeline.md"

            # Back up existing timeline
            if timeline_path.exists():
                modified_backups.append((timeline_path, timeline_path.read_text()))

            # Read existing entries
            import re

            existing_entries: list[dict] = []
            if timeline_path.exists():
                tl_content = timeline_path.read_text()
                for line in tl_content.splitlines():
                    line_s = line.strip()
                    if not line_s.startswith("- **Chapter"):
                        continue
                    m = re.match(r"- \*\*Chapter (\d+)\*\* — (.+?) — (.+)", line_s)
                    if m:
                        existing_entries.append(
                            {
                                "chapter": int(m.group(1)),
                                "time": m.group(2),
                                "description": m.group(3),
                            }
                        )

            for ev in timeline_events:
                existing_entries.append(
                    {
                        "chapter": ev["chapter"],
                        "time": str(ev["time"]),
                        "description": str(ev["description"]),
                    }
                )

            existing_entries.sort(key=lambda e: e["time"])

            tl_lines = ["# Main Timeline", ""]
            for entry in existing_entries:
                tl_lines.append(
                    f"- **Chapter {entry['chapter']}** — {entry['time']} — {entry['description']}"
                )
            tl_lines.append("")
            _atomic_write(timeline_path, "\n".join(tl_lines))
            timeline_added = len(timeline_events)

        # Log
        _append_log(
            wiki_dir,
            f"[batch] Created {created_count}, updated {updated_count}, "
            f"timeline +{timeline_added}",
        )

        print(
            json.dumps(
                {
                    "status": "ok",
                    "created": created_count,
                    "updated": updated_count,
                    "timeline_events": timeline_added,
                }
            )
        )

    except Exception as exc:
        # Rollback: restore modified files
        rollback = "full"
        for backup_path, backup_content in modified_backups:
            try:
                _atomic_write(backup_path, backup_content)
            except Exception:
                rollback = "partial"

        # Rollback: delete newly created files
        for created_path in created_files:
            try:
                created_path.unlink(missing_ok=True)
            except Exception:
                rollback = "partial"

        print(
            json.dumps(
                {
                    "status": "error",
                    "message": str(exc),
                    "rollback": rollback,
                }
            )
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Command: log
# ---------------------------------------------------------------------------


def cmd_log(args: argparse.Namespace) -> None:
    """Append an entry to log.md."""
    story_dir = _validate_story_name(args.name)
    wiki_dir = get_wiki_dir(story_dir)

    if not wiki_dir.exists():
        print("Error: wiki not initialised", file=sys.stderr)
        sys.exit(1)

    if not args.message:
        print("Error: --message is required for log", file=sys.stderr)
        sys.exit(2)

    _append_log(wiki_dir, args.message)
    print(json.dumps({"status": "ok"}))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse arguments and dispatch to the appropriate command."""
    parser = argparse.ArgumentParser(description="Wiki update tool")
    parser.add_argument(
        "--operation",
        required=True,
        choices=["create", "update", "append-timeline", "batch", "log"],
        help="Operation to perform",
    )
    parser.add_argument("--name", required=True, help="Story name")
    parser.add_argument("--slug", help="Page slug")
    parser.add_argument("--page-type", help="Page type")
    parser.add_argument("--page-name", help="Display name")
    parser.add_argument("--body", help="Page body markdown")
    parser.add_argument("--merge-body", help="Content to append to existing body")
    parser.add_argument(
        "--confidence",
        choices=["verified", "planned", "speculative"],
        help="Confidence level",
    )
    parser.add_argument(
        "--first-appearance", type=int, help="Chapter of first appearance"
    )
    parser.add_argument("--aliases", help="JSON array of aliases")
    parser.add_argument("--detail-levels", help="JSON object with L1, L2, L3 keys")
    parser.add_argument("--frontmatter", help="JSON object of fields to merge")
    parser.add_argument("--role", help="Character role")
    parser.add_argument("--status", help="Character/plot_thread status")
    parser.add_argument("--region", help="Location region")
    parser.add_argument("--chapter", type=int, help="Event chapter")
    parser.add_argument("--impact", help="Event impact")
    parser.add_argument("--events", help="JSON array of timeline events")
    parser.add_argument("--payload", help="JSON payload for batch operations")
    parser.add_argument("--message", help="Log message")

    args = parser.parse_args()

    # Validate required args per operation
    if args.operation == "create":
        if not args.slug:
            print("Error: --slug is required for create", file=sys.stderr)
            sys.exit(2)
        if not args.page_type:
            print("Error: --page-type is required for create", file=sys.stderr)
            sys.exit(2)
        if not args.page_name:
            print("Error: --page-name is required for create", file=sys.stderr)
            sys.exit(2)
        cmd_create(args)
    elif args.operation == "update":
        if not args.slug:
            print("Error: --slug is required for update", file=sys.stderr)
            sys.exit(2)
        cmd_update(args)
    elif args.operation == "append-timeline":
        cmd_append_timeline(args)
    elif args.operation == "batch":
        cmd_batch(args)
    elif args.operation == "log":
        cmd_log(args)


if __name__ == "__main__":
    main()
