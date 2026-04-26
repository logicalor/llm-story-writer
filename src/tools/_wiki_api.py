"""Typed programmatic API for wiki updates."""

from __future__ import annotations

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
    slugify,
)
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
