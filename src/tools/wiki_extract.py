"""CLI tool for extracting wiki entities and assembling batch payloads."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, NoReturn

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_path = str(PROJECT_ROOT / "src")
_root_path = str(PROJECT_ROOT)
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)
if _root_path not in sys.path:
    sys.path.insert(0, _root_path)

from infrastructure.prompts.prompt_loader import PromptLoader  # noqa: E402
from src.tools import _llm  # noqa: E402
from src.tools._io import _atomic_write, _validate_story_name  # noqa: E402
from src.tools._wiki import (  # noqa: E402
    get_wiki_dir,
    match_entities_in_text,
    parse_frontmatter,
    read_index,
    slugify,
)
from src.tools.wiki_update import run_batch  # noqa: E402


def _load_outline_savepoint(story_dir: Path) -> str:
    """Load the canonical outline text from savepoints.

    Prefers the `outline` step (the post-refinement canonical savepoint), then
    `refined_outline` (latest refinement), then `initial_outline`. Returns ""
    if none exist.
    """
    import asyncio as _asyncio  # noqa: PLC0415

    from infrastructure.storage.savepoint_repository import (  # noqa: PLC0415
        FilesystemSavepointRepository,
    )

    repo = FilesystemSavepointRepository(base_path=story_dir)
    repo.set_story_directory("savepoints")
    for step in ("outline", "refined_outline", "initial_outline"):
        try:
            if _asyncio.run(repo.has_savepoint(step)):
                data = _asyncio.run(repo.load_savepoint(step))
                if isinstance(data, str):
                    return data
                if data is not None:
                    return json.dumps(data, default=str)
        except Exception:
            continue
    return ""


_VALID_ENTITY_TYPES = {
    "character",
    "location",
    "plot_thread",
    "event",
    "theme",
    "world_rule",
    "relationship",
    "item",
    "faction",
}

_TYPE_NORMALIZATION = {
    "characters": "character",
    "locations": "location",
    "plot_threads": "plot_thread",
    "events": "event",
    "themes": "theme",
    "world_rules": "world_rule",
    "relationships": "relationship",
    "items": "item",
    "factions": "faction",
}

_CONFIDENCE_ORDER = {"speculative": 0, "planned": 1, "verified": 2}
_CACHE_FILE_NAME = ".wiki-extract-cache.json"

_PROMPT_LOADER: PromptLoader | None = None


def _error(message: str, *, details: dict[str, Any] | None = None) -> NoReturn:
    payload: dict[str, Any] = {"status": "error", "message": message}
    if details:
        payload.update(details)
    print(json.dumps(payload, indent=2))
    raise SystemExit(1)


def _get_prompt_loader() -> PromptLoader:
    global _PROMPT_LOADER
    if _PROMPT_LOADER is None:
        _PROMPT_LOADER = PromptLoader(prompts_dir=str(PROJECT_ROOT / "prompts"))
    return _PROMPT_LOADER


def _load_prompt(prompt_id: str, variables: dict[str, Any]) -> str:
    return _get_prompt_loader().load_prompt(prompt_id, variables)


def _chat_completion(prompt: str, *, model: str | None = None) -> str:
    return _llm.generate_text(prompt, model=model)


def _parse_json_response(raw_text: str, context: str) -> Any:
    cleaned = _llm._unwrap_output_tags(raw_text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{context} returned invalid JSON: {exc.msg}") from exc


def _read_json_file(path: Path, *, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} is not valid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{label} must contain a JSON object: {path}")
    return data


def _load_extract_cache(story_dir: Path) -> dict[str, Any]:
    cache_path = story_dir / _CACHE_FILE_NAME
    try:
        data = json.loads(cache_path.read_text())
    except OSError:
        return {}
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _save_extract_cache(story_dir: Path, cache: dict[str, Any]) -> None:
    _atomic_write(
        story_dir / _CACHE_FILE_NAME,
        json.dumps(cache, indent=2, ensure_ascii=True),
    )


def _delete_extract_cache(story_dir: Path) -> None:
    (story_dir / _CACHE_FILE_NAME).unlink(missing_ok=True)


def _coerce_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return json.dumps(value, indent=2, ensure_ascii=True)


def _extract_names(value: Any) -> list[str]:
    if isinstance(value, list):
        extracted_names: list[str] = []
        for item in value:
            if isinstance(item, str):
                extracted_names.append(item)
            elif isinstance(item, dict) and isinstance(item.get("name"), str):
                extracted_names.append(item["name"])
        return extracted_names
    if isinstance(value, dict):
        keyed_names: list[str] = []
        for key, item in value.items():
            if isinstance(key, str) and key:
                keyed_names.append(key)
            elif isinstance(item, dict) and isinstance(item.get("name"), str):
                keyed_names.append(item["name"])
        return keyed_names
    return []


def _normalize_type(raw_type: Any) -> str:
    if not isinstance(raw_type, str):
        raise ValueError("entity type must be a string")
    normalized = _TYPE_NORMALIZATION.get(raw_type.strip().lower(), raw_type.strip())
    if normalized not in _VALID_ENTITY_TYPES:
        raise ValueError(f"unsupported entity type: {raw_type}")
    return normalized


def _normalize_entity(
    entity: Any,
    *,
    default_confidence: str,
    first_appearance: int,
) -> dict[str, Any]:
    if not isinstance(entity, dict):
        raise ValueError("entity must be an object")

    name = entity.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("entity missing name")

    aliases = entity.get("aliases", [])
    if not isinstance(aliases, list):
        aliases = []
    alias_list = [
        alias for alias in aliases if isinstance(alias, str) and alias.strip()
    ]

    description = entity.get("description")
    if not isinstance(description, str):
        description = ""

    confidence = entity.get("confidence", default_confidence)
    if not isinstance(confidence, str) or confidence not in _CONFIDENCE_ORDER:
        confidence = default_confidence

    frontmatter = entity.get("frontmatter", {})
    if not isinstance(frontmatter, dict):
        frontmatter = {}

    return {
        "name": name.strip(),
        "type": _normalize_type(entity.get("type")),
        "aliases": alias_list,
        "description": description.strip(),
        "confidence": confidence,
        "frontmatter": frontmatter,
        "first_appearance": first_appearance,
    }


def _merge_entity(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    merged_aliases: list[str] = []
    for alias in [*base.get("aliases", []), *incoming.get("aliases", [])]:
        if isinstance(alias, str) and alias not in merged_aliases:
            merged_aliases.append(alias)
    merged["aliases"] = merged_aliases

    if len(incoming.get("description", "")) > len(base.get("description", "")):
        merged["description"] = incoming["description"]

    if (
        _CONFIDENCE_ORDER[incoming["confidence"]]
        > _CONFIDENCE_ORDER[base["confidence"]]
    ):
        merged["confidence"] = incoming["confidence"]

    merged["frontmatter"] = {
        **base.get("frontmatter", {}),
        **incoming.get("frontmatter", {}),
    }
    merged["first_appearance"] = min(
        int(base.get("first_appearance", 1)),
        int(incoming.get("first_appearance", 1)),
    )
    return merged


def _deduplicate_entities(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for entity in entities:
        key = slugify(entity["name"])
        if key in deduped:
            deduped[key] = _merge_entity(deduped[key], entity)
        else:
            deduped[key] = entity
            order.append(key)
    return [deduped[key] for key in order]


def _read_sheet_files(sheet_dir: Path) -> list[dict[str, Any]]:
    if not sheet_dir.exists():
        return []
    sheets: list[dict[str, Any]] = []
    for path in sorted(sheet_dir.glob("*.json")):
        data = _read_json_file(path, label="sheet")
        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            name = path.stem.replace("-", " ").title()
        sheet_text = data.get("sheet")
        if not isinstance(sheet_text, str) or not sheet_text.strip():
            summary = data.get("summary")
            sheet_text = summary if isinstance(summary, str) else _coerce_text(data)
        sheets.append({"name": name, "sheet_text": sheet_text, "path": path})
    return sheets


def _extract_outline_entities(
    outline: str,
    *,
    story_name: str,
    model: str | None,
    cache: dict[str, Any] | None = None,
    story_dir: Path | None = None,
) -> list[dict[str, Any]]:
    if cache is not None and "outline_entities" in cache:
        cached_result = cache["outline_entities"]
        if isinstance(cached_result, list):
            return cached_result

    prompt = _load_prompt(
        "wiki/extract_from_outline",
        {"outline": outline, "story_name": story_name},
    )
    result = _parse_json_response(
        _chat_completion(prompt, model=model), "outline extraction"
    )
    if not isinstance(result, list):
        raise ValueError("outline extraction must return a JSON array")
    normalized = [
        _normalize_entity(item, default_confidence="planned", first_appearance=1)
        for item in result
    ]
    if cache is not None and story_dir is not None:
        cache["outline_entities"] = normalized
        _save_extract_cache(story_dir, cache)
    return normalized


def _extract_sheet_entities(
    *,
    sheet_text: str,
    sheet_type: str,
    entity_name: str,
    model: str | None,
    sheet_path: Path | None = None,
    cache: dict[str, Any] | None = None,
    story_dir: Path | None = None,
) -> list[dict[str, Any]]:
    if story_dir is not None and sheet_path is not None:
        try:
            rel = str(sheet_path.relative_to(story_dir))
        except ValueError:
            rel = sheet_path.name
    elif sheet_path is not None:
        rel = sheet_path.name
    else:
        rel = entity_name

    if cache is not None:
        cached_sheets = cache.get("sheet_entities", {})
        if isinstance(cached_sheets, dict):
            cached_result = cached_sheets.get(rel)
            if isinstance(cached_result, list):
                return cached_result

    prompt = _load_prompt(
        "wiki/extract_from_sheet",
        {
            "sheet_text": sheet_text,
            "sheet_type": sheet_type,
            "entity_name": entity_name,
            "sheets_are_authoritative": "false",
        },
    )
    result = _parse_json_response(
        _chat_completion(prompt, model=model), f"{sheet_type} sheet extraction"
    )
    if not isinstance(result, dict):
        raise ValueError(f"{sheet_type} sheet extraction must return a JSON object")

    entities: list[dict[str, Any]] = []
    primary_entity = result.get("primary_entity")
    if primary_entity is not None:
        entities.append(
            _normalize_entity(
                primary_entity, default_confidence="planned", first_appearance=1
            )
        )

    related_entities = result.get("related_entities", [])
    if not isinstance(related_entities, list):
        raise ValueError(f"{sheet_type} sheet related_entities must be an array")
    for item in related_entities:
        entities.append(
            _normalize_entity(item, default_confidence="planned", first_appearance=1)
        )
    if cache is not None and story_dir is not None:
        cache.setdefault("sheet_entities", {})[rel] = entities
        _save_extract_cache(story_dir, cache)
    return entities


def _generate_detail_levels(
    entity: dict[str, Any],
    *,
    model: str | None,
    cache: dict[str, Any] | None = None,
    story_dir: Path | None = None,
) -> dict[str, str]:
    slug = entity.get("slug", "")
    if not isinstance(slug, str):
        slug = ""
    if cache is not None and slug:
        cached_detail_levels = cache.get("detail_levels", {})
        if isinstance(cached_detail_levels, dict):
            cached = cached_detail_levels.get(slug)
            if isinstance(cached, dict):
                return cached

    prompt = _load_prompt(
        "wiki/generate_detail_levels",
        {"entity": json.dumps(entity, indent=2, ensure_ascii=True)},
    )
    result = _parse_json_response(
        _chat_completion(prompt, model=model), "detail level generation"
    )
    if not isinstance(result, dict):
        raise ValueError("detail level generation must return a JSON object")

    detail_levels = {
        "L1": result.get("l1", ""),
        "L2": result.get("l2", ""),
        "L3": result.get("l3", ""),
    }
    if not all(isinstance(value, str) for value in detail_levels.values()):
        raise ValueError("detail level generation must return string values")
    if cache is not None and story_dir is not None and slug:
        cache.setdefault("detail_levels", {})[slug] = detail_levels
        _save_extract_cache(story_dir, cache)
    return detail_levels


def _build_create_entry(
    entity: dict[str, Any], detail_levels: dict[str, str]
) -> dict[str, Any]:
    return {
        "page_type": entity["type"],
        "page_name": entity["name"],
        "slug": slugify(entity["name"]),
        "body": entity["description"],
        "confidence": entity["confidence"],
        "first_appearance": entity["first_appearance"],
        "aliases": entity["aliases"],
        "detail_levels": detail_levels,
        "frontmatter": entity.get("frontmatter", {}),
    }


def _read_compact_page(story_dir: Path, slug: str) -> dict[str, Any] | None:
    wiki_dir = get_wiki_dir(story_dir)
    for page_path in wiki_dir.rglob(f"{slug}.md"):
        if not page_path.resolve().is_relative_to(wiki_dir.resolve()):
            continue
        metadata, body = parse_frontmatter(page_path.read_text())
        description = body.strip().splitlines()[0] if body.strip() else ""
        return {
            "name": metadata.get("name", slug),
            "slug": metadata.get("slug", slug),
            "type": metadata.get("type", "unknown"),
            "first_appearance": metadata.get("first_appearance"),
            "description": description,
        }
    return None


def _resolve_chapter_path(story_dir: Path, path_arg: str) -> Path:
    candidate = Path(path_arg)
    if not candidate.is_absolute():
        candidate = (story_dir / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if not candidate.is_relative_to(story_dir.resolve()):
        raise ValueError("chapter text path must be inside the story directory")
    if not candidate.exists() or not candidate.is_file():
        raise FileNotFoundError(f"chapter text file not found: {candidate}")
    return candidate


def _merge_update_entries(
    state_changes: Any,
    new_aliases: Any,
) -> list[dict[str, Any]]:
    if not isinstance(state_changes, list):
        raise ValueError("state_changes must be an array")
    if not isinstance(new_aliases, list):
        raise ValueError("new_aliases must be an array")

    updates_by_slug: dict[str, dict[str, Any]] = {}

    for item in state_changes:
        if not isinstance(item, dict):
            raise ValueError("state_changes entries must be objects")
        slug = item.get("slug")
        if not isinstance(slug, str) or not slug:
            raise ValueError("state_changes entry missing slug")
        update = updates_by_slug.setdefault(slug, {"slug": slug})

        frontmatter = item.get("frontmatter")
        updated_fields = item.get("updated_fields")
        if isinstance(frontmatter, dict):
            update["frontmatter"] = {
                **update.get("frontmatter", {}),
                **frontmatter,
            }
        elif isinstance(updated_fields, dict):
            update["frontmatter"] = {
                **update.get("frontmatter", {}),
                **updated_fields,
            }

        merge_body = item.get("merge_body")
        if not isinstance(merge_body, str):
            description = item.get("description")
            merge_body = description if isinstance(description, str) else None
        if isinstance(merge_body, str) and merge_body.strip():
            if (
                isinstance(update.get("merge_body"), str)
                and update["merge_body"].strip()
            ):
                update["merge_body"] = (
                    update["merge_body"].rstrip("\n") + "\n\n" + merge_body.strip()
                )
            else:
                update["merge_body"] = merge_body.strip()

        body = item.get("body")
        if isinstance(body, str) and body.strip():
            update["body"] = body.strip()

        aliases = item.get("aliases")
        if isinstance(aliases, list):
            existing = update.get("aliases", [])
            merged_aliases: list[str] = []
            for alias in [*existing, *aliases]:
                if isinstance(alias, str) and alias not in merged_aliases:
                    merged_aliases.append(alias)
            update["aliases"] = merged_aliases

    for item in new_aliases:
        if not isinstance(item, dict):
            raise ValueError("new_aliases entries must be objects")
        slug = item.get("slug")
        aliases = item.get("aliases", [])
        if not isinstance(slug, str) or not slug:
            raise ValueError("new_aliases entry missing slug")
        if not isinstance(aliases, list):
            raise ValueError("new_aliases aliases must be an array")
        update = updates_by_slug.setdefault(slug, {"slug": slug})
        existing = update.get("aliases", [])
        merged_aliases = []
        for alias in [*existing, *aliases]:
            if isinstance(alias, str) and alias not in merged_aliases:
                merged_aliases.append(alias)
        update["aliases"] = merged_aliases

    return list(updates_by_slug.values())


def _build_payload_from_entities(
    entities: list[dict[str, Any]],
    *,
    model: str | None,
    cache: dict[str, Any] | None = None,
    story_dir: Path | None = None,
) -> dict[str, Any]:
    creates = []
    for entity in entities:
        entity_with_slug = {**entity, "slug": slugify(entity["name"])}
        detail_levels = _generate_detail_levels(
            entity_with_slug,
            model=model,
            cache=cache,
            story_dir=story_dir,
        )
        creates.append(_build_create_entry(entity, detail_levels))
    return {"creates": creates, "updates": [], "timeline_events": []}


def cmd_initial_populate(args: argparse.Namespace) -> None:
    story_dir = _validate_story_name(args.name)
    cache = _load_extract_cache(story_dir)
    state = _read_json_file(story_dir / "state.json", label="state.json")

    outline_text = _load_outline_savepoint(story_dir)
    if not outline_text.strip():
        state_for_outline = _read_json_file(
            story_dir / "state.json", label="state.json"
        )
        outline_text = state_for_outline.get("outline", "") or ""
    if not outline_text.strip():
        raise ValueError(
            "outline savepoint missing — run Phase 2 (outline-planner) before wiki population"
        )

    # Tolerate both list and object-map state shapes.
    _extract_names(state.get("characters"))
    _extract_names(state.get("settings"))

    entities = _extract_outline_entities(
        outline_text,
        story_name=story_dir.name,
        model=args.model,
        cache=cache,
        story_dir=story_dir,
    )

    for sheet in _read_sheet_files(story_dir / "characters"):
        entities.extend(
            _extract_sheet_entities(
                sheet_text=sheet["sheet_text"],
                sheet_type="character",
                entity_name=sheet["name"],
                model=args.model,
                sheet_path=sheet["path"],
                cache=cache,
                story_dir=story_dir,
            )
        )

    for sheet in _read_sheet_files(story_dir / "settings"):
        entities.extend(
            _extract_sheet_entities(
                sheet_text=sheet["sheet_text"],
                sheet_type="setting",
                entity_name=sheet["name"],
                model=args.model,
                sheet_path=sheet["path"],
                cache=cache,
                story_dir=story_dir,
            )
        )

    payload = _build_payload_from_entities(
        _deduplicate_entities(entities),
        model=args.model,
        cache=cache,
        story_dir=story_dir,
    )

    if not args.apply:
        print(
            json.dumps(
                {
                    "status": "ok",
                    "applied": False,
                    **payload,
                },
                indent=2,
            )
        )
        return

    summary = run_batch(args.name, payload)
    _delete_extract_cache(story_dir)

    # Write the Phase 6 milestone savepoint so the orchestrator's resume path
    # (savepoint-mgr next-phase) recognises Phase 6 as complete. Previously
    # the orchestrator had to create this savepoint manually after delegating
    # to wiki-maintainer, which was easy to skip on retry/resume.
    try:
        from infrastructure.storage.savepoint_repository import (  # noqa: PLC0415
            FilesystemSavepointRepository,
        )
        import asyncio as _asyncio  # noqa: PLC0415

        repo = FilesystemSavepointRepository(base_path=story_dir)
        _asyncio.run(
            repo.save_savepoint(
                "wiki_populated",
                {
                    "status": "complete",
                    "created": summary["created"],
                    "updated": summary["updated"],
                    "entity_counts": summary["entity_counts"],
                },
            )
        )
    except Exception as exc:  # pragma: no cover — defensive
        print(
            f"Warning: wiki_populated savepoint write failed: {exc}",
            file=sys.stderr,
        )

    print(
        json.dumps(
            {
                "status": "ok",
                "created": summary["created"],
                "updated": summary["updated"],
                "timeline_events": summary["timeline_events"],
                "entity_counts": summary["entity_counts"],
                "applied": True,
            },
            indent=2,
        )
    )


def cmd_update_from_chapter(args: argparse.Namespace) -> None:
    story_dir = _validate_story_name(args.name)
    cache = _load_extract_cache(story_dir)
    chapter_path = _resolve_chapter_path(story_dir, args.chapter_text_path)
    chapter_text = chapter_path.read_text()

    wiki_dir = get_wiki_dir(story_dir)
    index_entries = read_index(wiki_dir) if wiki_dir.exists() else []
    matches = match_entities_in_text(chapter_text, index_entries)

    existing_entities = []
    for match in matches:
        slug = match.get("slug")
        if not isinstance(slug, str):
            continue
        compact_page = _read_compact_page(story_dir, slug)
        if compact_page is not None:
            existing_entities.append(compact_page)

    chapter_cache_key = f"chapter_entities/{args.chapter_number}"
    cached_extracted = cache.get(chapter_cache_key)
    if cached_extracted is not None:
        extracted = cached_extracted
    else:
        prompt = _load_prompt(
            "wiki/extract_from_chapter",
            {
                "chapter_text": chapter_text,
                "chapter_number": args.chapter_number,
                "existing_entities": json.dumps(
                    existing_entities, indent=2, ensure_ascii=True
                ),
            },
        )
        extracted = _parse_json_response(
            _chat_completion(prompt, model=args.model), "chapter extraction"
        )
        if not isinstance(extracted, dict):
            raise ValueError("chapter extraction must return a JSON object")
        cache[chapter_cache_key] = extracted
        _save_extract_cache(story_dir, cache)
    if not isinstance(extracted, dict):
        # Guard against corrupted cache: a manually-edited cache file could store a
        # non-dict value at the chapter_entities key, which would bypass the inner
        # check in the else branch.
        raise ValueError("chapter extraction must return a JSON object")

    raw_new_entities = extracted.get("new_entities", [])
    if not isinstance(raw_new_entities, list):
        raise ValueError("new_entities must be an array")
    new_entities = _deduplicate_entities(
        [
            _normalize_entity(
                item,
                default_confidence="verified",
                first_appearance=args.chapter_number,
            )
            for item in raw_new_entities
        ]
    )

    creates = []
    for entity in new_entities:
        entity_with_slug = {**entity, "slug": slugify(entity["name"])}
        detail_levels = _generate_detail_levels(
            entity_with_slug,
            model=args.model,
            cache=cache,
            story_dir=story_dir,
        )
        creates.append(_build_create_entry(entity, detail_levels))

    updates = _merge_update_entries(
        extracted.get("state_changes", []),
        extracted.get("new_aliases", []),
    )
    timeline_events = extracted.get("timeline_events", [])
    if not isinstance(timeline_events, list):
        raise ValueError("timeline_events must be an array")

    payload = {
        "creates": creates,
        "updates": updates,
        "timeline_events": timeline_events,
    }

    if not args.apply:
        print(
            json.dumps(
                {
                    "status": "ok",
                    "applied": False,
                    **payload,
                },
                indent=2,
            )
        )
        return

    summary = run_batch(args.name, payload)
    _delete_extract_cache(story_dir)
    print(
        json.dumps(
            {
                "status": "ok",
                "created": summary["created"],
                "updated": summary["updated"],
                "timeline_events": summary["timeline_events"],
                "entity_counts": summary["entity_counts"],
                "applied": True,
            },
            indent=2,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Wiki extraction tool")
    subparsers = parser.add_subparsers(dest="operation", required=True)

    initial = subparsers.add_parser(
        "initial-populate",
        help="Extract initial wiki entities from outline and sheets",
    )
    initial.add_argument("--name", required=True, help="Story name")
    initial.add_argument("--model", help="Override model name")
    initial.set_defaults(apply=True)
    initial.add_argument(
        "--apply",
        dest="apply",
        action="store_true",
        help="Apply batch to wiki (default)",
    )
    initial.add_argument(
        "--dry-run",
        dest="apply",
        action="store_false",
        help="Return batch payload without applying it",
    )

    update = subparsers.add_parser(
        "update-from-chapter",
        help="Extract wiki updates from a completed chapter",
    )
    update.add_argument("--name", required=True, help="Story name")
    update.add_argument(
        "--chapter-number", required=True, type=int, help="Chapter number"
    )
    update.add_argument(
        "--chapter-text-path",
        required=True,
        help="Path to chapter text file inside the story directory",
    )
    update.add_argument("--model", help="Override model name")
    update.set_defaults(apply=True)
    update.add_argument(
        "--apply",
        dest="apply",
        action="store_true",
        help="Apply batch to wiki (default)",
    )
    update.add_argument(
        "--dry-run",
        dest="apply",
        action="store_false",
        help="Return batch payload without applying it",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.operation == "initial-populate":
            cmd_initial_populate(args)
        elif args.operation == "update-from-chapter":
            cmd_update_from_chapter(args)
    except FileNotFoundError as exc:
        _error(str(exc))
    except ValueError as exc:
        _error(str(exc))
    except RuntimeError as exc:
        _error(str(exc))


if __name__ == "__main__":
    main()
