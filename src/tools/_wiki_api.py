"""Typed programmatic API for wiki updates."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from infrastructure.prompts.prompt_loader import PromptLoader
from tools import _llm
from tools._io import _atomic_write, _validate_story_name
from tools._wiki import (
    get_wiki_dir,
    match_entities_in_text,
    parse_frontmatter,
    read_index,
    render_frontmatter,
    slugify,
    write_index,
)
from tools.recap_index import query_recap
from tools.wiki_update import run_batch

PROJECT_ROOT = Path(__file__).resolve().parents[2]

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

_TYPE_TO_PROMPT = {
    "character": "characters",
    "location": "locations",
    "event": "events",
    "faction": "factions",
    "item": "items",
    "plot_thread": "plot_threads",
    "theme": "themes",
    "world_rule": "world_rules",
    "relationship": "relationships",
}

_CONFIDENCE_ORDER = {"speculative": 0, "planned": 1, "verified": 2}
_CACHE_FILE_NAME = ".wiki-extract-cache.json"

_PROMPT_LOADER: PromptLoader | None = None


def _get_prompt_loader() -> PromptLoader:
    global _PROMPT_LOADER
    if _PROMPT_LOADER is None:
        _PROMPT_LOADER = PromptLoader(prompts_dir=str(PROJECT_ROOT / "prompts"))
    return _PROMPT_LOADER


def _load_prompt(prompt_id: str, variables: dict[str, Any]) -> str:
    return _get_prompt_loader().load_prompt(prompt_id, variables)


def _chat_completion(
    prompt: str, *, model: str | None = None, base_url: str | None = None
) -> str:
    return _llm.generate_text(prompt, model=model, base_url=base_url)


def _parse_json_response(raw_text: str, context: str) -> Any:
    cleaned = _llm._unwrap_output_tags(raw_text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{context} returned invalid JSON: {exc.msg}") from exc


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


def _generate_detail_levels(
    entity: dict[str, Any],
    *,
    model: str | None,
    cache: dict[str, Any] | None = None,
    story_dir: Path | None = None,
    base_url: str | None = None,
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
        _chat_completion(prompt, model=model, base_url=base_url),
        "detail level generation",
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


def _read_full_page_body(
    story_dir: Path, slug: str
) -> tuple[dict[str, Any], str] | None:
    wiki_dir = get_wiki_dir(story_dir)
    if not wiki_dir.exists():
        return None

    resolved_wiki_dir = wiki_dir.resolve()
    for page_path in wiki_dir.rglob(f"{slug}.md"):
        if not page_path.resolve().is_relative_to(resolved_wiki_dir):
            continue
        raw_text = page_path.read_text()
        metadata, _body = parse_frontmatter(raw_text)
        return metadata, raw_text
    return None


def _extract_type_candidates(
    story_name: str,
    page_type: str,
    chapter_text: str,
    index_entries: list[dict[str, Any]],
    *,
    model: str | None = None,
    base_url: str | None = None,
    prior_recap_context: str = "",
) -> list[dict[str, Any]]:
    _ = story_name
    prompt_suffix = _TYPE_TO_PROMPT.get(page_type)
    if prompt_suffix is None:
        raise ValueError(f"unsupported page type: {page_type}")

    filtered_entries = [
        entry for entry in index_entries if entry.get("type") == page_type
    ]
    prompt_vars: dict[str, Any] = {
        "chapter_text": chapter_text,
        "existing_pages_index": json.dumps(
            filtered_entries,
            indent=2,
            ensure_ascii=True,
        ),
    }
    if page_type == "event":
        prompt_vars["prior_recap_context"] = prior_recap_context
    prompt = _load_prompt(
        f"wiki/extract_{prompt_suffix}_from_chapter",
        prompt_vars,
    )
    result = _parse_json_response(
        _chat_completion(prompt, model=model, base_url=base_url),
        f"{page_type} extraction",
    )
    if not isinstance(result, list):
        raise ValueError(f"{page_type} extraction must return a JSON array")
    return [item for item in result if isinstance(item, dict)]


def _replace_markdown_section(body: str, heading: str, new_content: str) -> str:
    lines = body.splitlines()
    heading_text = heading.strip()
    start_index: int | None = None

    for index, line in enumerate(lines):
        if line.strip() == heading_text:
            start_index = index
            break

    replacement_lines = [heading_text]
    stripped_content = new_content.strip()
    if stripped_content:
        replacement_lines.extend(["", *stripped_content.splitlines()])

    if start_index is None:
        if body.strip():
            return body.rstrip("\n") + "\n\n" + "\n".join(replacement_lines) + "\n"
        return "\n".join(replacement_lines) + "\n"

    end_index = len(lines)
    for index in range(start_index + 1, len(lines)):
        if lines[index].startswith("#"):
            end_index = index
            break

    updated_lines = lines[:start_index] + replacement_lines + lines[end_index:]
    updated_body = "\n".join(updated_lines).rstrip("\n")
    return updated_body + "\n"


def _apply_merge_patch(story_dir: Path, slug: str, patch: dict[str, Any]) -> bool:
    if patch.get("no_change") is True:
        return False

    wiki_dir = get_wiki_dir(story_dir)
    resolved_wiki_dir = wiki_dir.resolve()
    page_path: Path | None = None
    for candidate_path in wiki_dir.rglob(f"{slug}.md"):
        if candidate_path.resolve().is_relative_to(resolved_wiki_dir):
            page_path = candidate_path
            break

    if page_path is None:
        raise ValueError(f"page '{slug}' not found for merge")

    original_text = page_path.read_text()
    metadata, body = parse_frontmatter(original_text)

    frontmatter_delta = patch.get("frontmatter_delta")
    if isinstance(frontmatter_delta, dict):
        metadata.update(frontmatter_delta)

    aliases_add = patch.get("aliases_add")
    if isinstance(aliases_add, list):
        existing_aliases = metadata.get("aliases", [])
        if not isinstance(existing_aliases, list):
            existing_aliases = []
        merged_aliases: list[str] = []
        for alias in [*existing_aliases, *aliases_add]:
            if isinstance(alias, str) and alias.strip() and alias not in merged_aliases:
                merged_aliases.append(alias)
        metadata["aliases"] = merged_aliases

    body_append = patch.get("body_append")
    if isinstance(body_append, str) and body_append.strip():
        if body.strip():
            body = body.rstrip("\n") + "\n\n" + body_append.strip() + "\n"
        else:
            body = body_append.strip() + "\n"

    body_sections_replace = patch.get("body_sections_replace")
    if isinstance(body_sections_replace, list):
        for section_patch in body_sections_replace:
            if not isinstance(section_patch, dict):
                continue
            heading = section_patch.get("heading")
            new_content = section_patch.get("new_content")
            if (
                isinstance(heading, str)
                and heading.strip()
                and isinstance(new_content, str)
            ):
                body = _replace_markdown_section(body, heading, new_content)

    candidate_text = render_frontmatter(metadata, body.rstrip("\n"))
    if candidate_text == original_text:
        return False

    version = metadata.get("version", 0)
    if not isinstance(version, int):
        version = 0
    metadata["version"] = version + 1
    metadata["last_updated"] = datetime.now(timezone.utc).isoformat()

    new_text = render_frontmatter(metadata, body.rstrip("\n"))

    _atomic_write(page_path, new_text)

    index_entries = read_index(wiki_dir)
    index_changed = False
    for entry in index_entries:
        if entry.get("slug") != slug:
            continue
        name = metadata.get("name")
        aliases = metadata.get("aliases")
        if isinstance(name, str) and entry.get("name") != name:
            entry["name"] = name
            index_changed = True
        if isinstance(aliases, list):
            normalized_aliases = [
                alias for alias in aliases if isinstance(alias, str) and alias.strip()
            ]
            if entry.get("aliases") != normalized_aliases:
                entry["aliases"] = normalized_aliases
                index_changed = True
        break
    if index_changed:
        write_index(wiki_dir, index_entries)

    return True


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


def _prepare_chapter_update(
    story_name: str,
    chapter_number: int,
    chapter_text: str,
    *,
    model: str | None = None,
    base_url: str | None = None,
) -> tuple[Path, dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    story_dir = _validate_story_name(story_name)
    cache = _load_extract_cache(story_dir)

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

    chapter_cache_key = f"chapter_entities/{chapter_number}"
    cached_extracted = cache.get(chapter_cache_key)
    if cached_extracted is not None:
        extracted = cached_extracted
    else:
        prompt = _load_prompt(
            "wiki/extract_from_chapter",
            {
                "chapter_text": chapter_text,
                "chapter_number": chapter_number,
                "existing_entities": json.dumps(
                    existing_entities, indent=2, ensure_ascii=True
                ),
            },
        )
        extracted = _parse_json_response(
            _chat_completion(prompt, model=model, base_url=base_url),
            "chapter extraction",
        )
        if not isinstance(extracted, dict):
            raise ValueError("chapter extraction must return a JSON object")
        cache[chapter_cache_key] = extracted
        _save_extract_cache(story_dir, cache)

    raw_new_entities = extracted.get("new_entities", [])
    if not isinstance(raw_new_entities, list):
        raise ValueError("new_entities must be an array")
    new_entities = _deduplicate_entities(
        [
            _normalize_entity(
                item,
                default_confidence="verified",
                first_appearance=chapter_number,
            )
            for item in raw_new_entities
        ]
    )

    creates = []
    for entity in new_entities:
        entity_with_slug = {**entity, "slug": slugify(entity["name"])}
        detail_levels = _generate_detail_levels(
            entity_with_slug,
            model=model,
            cache=cache,
            story_dir=story_dir,
            base_url=base_url,
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
    return story_dir, payload, creates, updates


def update_wiki_from_chapter(
    story_name: str,
    chapter_number: int,
    chapter_text: str,
    *,
    model: str | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    """Run wiki update for a chapter from chapter text string.

    Deprecated: use update_wiki_full_pass instead.

    This is the programmatic API used by WikiMaintainerAgent.
    Unlike cmd_update_from_chapter, this accepts chapter text directly
    instead of requiring a file path.

    Returns a dict with keys:
      created: int
      updated: int
      timeline_events: int
      entity_counts: dict
      new_slugs: list[str]   - slugs of newly created pages
      updated_slugs: list[str]  - slugs of updated pages
    """
    story_dir, payload, creates, updates = _prepare_chapter_update(
        story_name,
        chapter_number,
        chapter_text,
        model=model,
        base_url=base_url,
    )

    summary = run_batch(story_name, payload)
    _delete_extract_cache(story_dir)

    return {
        **summary,
        "new_slugs": [create["slug"] for create in creates],
        "updated_slugs": [update["slug"] for update in updates],
    }


def update_wiki_full_pass(
    story_name: str,
    chapter: int,
    chapter_text: str,
    *,
    model: str | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    story_dir = _validate_story_name(story_name)
    wiki_dir = get_wiki_dir(story_dir)
    index_entries = read_index(wiki_dir) if wiki_dir.exists() else []

    _prior_recap_context = ""
    try:
        _recap_results = query_recap(
            story_name,
            query_text=chapter_text[:500],
            n_results=3,
        )
        if _recap_results:
            _snippets = [
                recap_result["document"]
                for recap_result in _recap_results
                if recap_result.get("document")
            ]
            _prior_recap_context = "\n\n---\n\n".join(_snippets)
    except Exception as _recap_exc:
        logging.warning(
            "[Wiki] WARNING event recap context unavailable: %s",
            _recap_exc,
        )
        _prior_recap_context = ""

    pass_a_types = list(_TYPE_TO_PROMPT.keys())
    type_candidates: dict[str, list[dict[str, Any]]] = {
        page_type: [] for page_type in pass_a_types
    }

    if pass_a_types:
        with ThreadPoolExecutor(max_workers=min(9, len(pass_a_types))) as executor:
            future_to_type = {
                executor.submit(
                    _extract_type_candidates,
                    story_name,
                    page_type,
                    chapter_text,
                    index_entries,
                    model=model,
                    base_url=base_url,
                    **(
                        {"prior_recap_context": _prior_recap_context}
                        if page_type == "event"
                        else {}
                    ),
                ): page_type
                for page_type in pass_a_types
            }
            for future in as_completed(future_to_type):
                page_type = future_to_type[future]
                try:
                    type_candidates[page_type] = future.result()
                except Exception as exc:
                    logging.warning(
                        "[Wiki] WARNING type=%s extraction failed: %s",
                        page_type,
                        exc,
                    )
                    type_candidates[page_type] = []

    for page_type in pass_a_types:
        type_index = [
            entry for entry in index_entries if entry.get("type") == page_type
        ]
        alias_matches = match_entities_in_text(chapter_text, type_index)
        if not type_candidates[page_type] and alias_matches:
            matched_names = [
                match.get("name", match.get("slug", "?")) for match in alias_matches
            ]
            logging.warning(
                "[Wiki] WARNING type=%s 0 candidates but aliases matched: %s",
                page_type,
                ", ".join(matched_names),
            )

    per_type_stats = {
        page_type: {"created": 0, "updated": 0} for page_type in pass_a_types
    }
    cache = _load_extract_cache(story_dir)

    try:
        for page_type, candidates in type_candidates.items():
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue

                candidate_name = candidate.get("name")
                if not isinstance(candidate_name, str) or not candidate_name.strip():
                    logging.warning(
                        "[Wiki] WARNING type=%s candidate missing name; skipped",
                        page_type,
                    )
                    continue

                slug = slugify(candidate_name)
                full_page = _read_full_page_body(story_dir, slug)

                if full_page is None:
                    entity = _normalize_entity(
                        candidate,
                        default_confidence="inferred",
                        first_appearance=chapter,
                    )
                    entity_with_slug = {**entity, "slug": slug}
                    detail_levels = _generate_detail_levels(
                        entity_with_slug,
                        model=model,
                        cache=cache,
                        story_dir=story_dir,
                        base_url=base_url,
                    )
                    create_entry = _build_create_entry(entity, detail_levels)
                    run_batch(
                        story_name,
                        {
                            "creates": [create_entry],
                            "updates": [],
                            "timeline_events": [],
                        },
                    )
                    per_type_stats[page_type]["created"] += 1
                    index_entries.append(
                        {
                            "name": entity["name"],
                            "slug": slug,
                            "type": entity["type"],
                            "aliases": entity["aliases"],
                        }
                    )
                    continue

                _existing_metadata, raw_page_text = full_page
                merge_prompt = _load_prompt(
                    "wiki/merge_page",
                    {
                        "existing_page_body": raw_page_text,
                        "new_candidate": json.dumps(
                            candidate,
                            indent=2,
                            ensure_ascii=True,
                        ),
                    },
                )
                raw_response = _chat_completion(
                    merge_prompt,
                    model=model,
                    base_url=base_url,
                )
                patch = _parse_json_response(raw_response, "merge page")
                if not isinstance(patch, dict):
                    raise ValueError("merge page must return a JSON object")
                if patch.get("no_change"):
                    continue
                changed = _apply_merge_patch(story_dir, slug, patch)
                if changed:
                    per_type_stats[page_type]["updated"] += 1
                    refreshed_index = read_index(wiki_dir) if wiki_dir.exists() else []
                    index_entries = refreshed_index
    finally:
        _delete_extract_cache(story_dir)

    total_created = sum(stats["created"] for stats in per_type_stats.values())
    total_updated = sum(stats["updated"] for stats in per_type_stats.values())
    return {
        "per_type": per_type_stats,
        "total_created": total_created,
        "total_updated": total_updated,
    }
