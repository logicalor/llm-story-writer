"""Wiki page generation from outline data."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from application.pipeline.handoffs import OutlineResult
from domain.value_objects.model_config import ModelConfig
from infrastructure.prompts.prompt_loader import PromptLoader
from tools import _llm
from tools._io import _validate_story_name
from tools._persist import read_markdown_ref
from tools._wiki import get_wiki_dir, slugify
from tools.wiki_update import run_batch

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PROMPT_LOADER = PromptLoader(prompts_dir=str(PROJECT_ROOT / "prompts"))


def _resolve_markdown(value: str | dict[str, str], story_root: Path) -> str:
    if isinstance(value, dict):
        return read_markdown_ref(story_root, value)
    return value or ""


def _build_outline_excerpt(outline_result: OutlineResult, story_root: Path) -> str:
    parts: list[str] = []

    story_elements = _resolve_markdown(
        outline_result.story_elements, story_root
    ).strip()
    if story_elements:
        parts.append(story_elements)

    summary = _resolve_markdown(outline_result.summary, story_root).strip()
    if summary and summary not in parts:
        parts.append(summary)

    if outline_result.chapter_outlines:
        resolved_outlines: list[dict[str, Any]] = []
        for chapter in outline_result.chapter_outlines:
            if not isinstance(chapter, dict):
                continue
            chapter_copy = dict(chapter)
            raw_summary = chapter_copy.get("summary")
            if isinstance(raw_summary, dict):
                chapter_copy["summary"] = read_markdown_ref(story_root, raw_summary)
            elif raw_summary is None:
                chapter_copy["summary"] = ""
            resolved_outlines.append(chapter_copy)
        if resolved_outlines:
            parts.append(json.dumps(resolved_outlines, ensure_ascii=False))

    return "\n\n".join(part for part in parts if part)


def _invoke_provider(
    provider: Any,
    messages: list[dict[str, str]],
    model_config: ModelConfig,
    *,
    seed: int | None,
) -> str:
    return asyncio.run(provider.generate_text(messages, model_config, seed=seed))


def _parse_json_payload(raw_text: str, *, expect: type[dict] | type[list]) -> Any:
    candidate = _llm._extract_json_block(raw_text.strip())
    parsed = json.loads(candidate)
    if expect is dict and not isinstance(parsed, dict):
        raise ValueError(f"Expected dict, got {type(parsed).__name__}")
    if expect is list and not isinstance(parsed, list):
        raise ValueError(f"Expected list, got {type(parsed).__name__}")
    return parsed


def _generation_seed(config: dict[str, Any]) -> int | None:
    if config.get("randomize_seed"):
        return None
    generation = config.get("generation", {})
    seed = generation.get("seed")
    return seed if isinstance(seed, int) else None


def _model_config(config: dict[str, Any]) -> ModelConfig:
    models = config.get("models", {})
    model_name = models.get("chapter_writer", "openai-compat://default")
    return ModelConfig.from_string(model_name)


def _extract_entities(
    story_name: str,
    outline_excerpt: str,
    provider: Any,
    model_config: ModelConfig,
    *,
    seed: int | None,
) -> list[dict[str, Any]]:
    prompt = _PROMPT_LOADER.load_prompt(
        "wiki/extract_from_outline",
        {"story_name": story_name, "outline": outline_excerpt},
    )
    for attempt in range(2):
        raw_text = _invoke_provider(
            provider,
            [{"role": "user", "content": prompt}],
            model_config,
            seed=seed,
        )
        try:
            parsed = _parse_json_payload(raw_text, expect=list)
        except (json.JSONDecodeError, ValueError) as exc:
            if attempt == 1:
                logger.warning("Entity extraction failed: %s", exc)
                return []
            continue

        entities: list[dict[str, Any]] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            entity_type = item.get("type")
            if not isinstance(name, str) or not name.strip():
                continue
            if not isinstance(entity_type, str) or not entity_type.strip():
                continue
            aliases = item.get("aliases")
            if not isinstance(aliases, list):
                aliases = []
            entities.append(
                {
                    "name": name.strip(),
                    "type": entity_type.strip(),
                    "aliases": [alias for alias in aliases if isinstance(alias, str)],
                }
            )
        return entities

    return []


def _page_body(section_map: list[tuple[str, str]]) -> str:
    return "\n\n".join(
        f"## {heading}\n{content.strip()}"
        for heading, content in section_map
        if isinstance(content, str) and content.strip()
    )


def _generate_page(
    prompt_name: str,
    variables: dict[str, Any],
    provider: Any,
    model_config: ModelConfig,
    *,
    seed: int | None,
) -> dict[str, Any] | None:
    prompt = _PROMPT_LOADER.load_prompt(prompt_name, variables)
    for attempt in range(2):
        raw_text = _invoke_provider(
            provider,
            [{"role": "user", "content": prompt}],
            model_config,
            seed=seed,
        )
        try:
            parsed = _parse_json_payload(raw_text, expect=dict)
        except (json.JSONDecodeError, ValueError) as exc:
            if attempt == 1:
                logger.warning("Wiki page generation failed for %s: %s", variables, exc)
                return None
            continue
        return parsed
    return None


def _dedupe_entities(
    entities: list[dict[str, Any]], target_type: str
) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entity in entities:
        entity_type = entity.get("type")
        name = entity.get("name")
        if entity_type != target_type or not isinstance(name, str):
            continue
        key = slugify(name)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entity)
    return deduped


def generate_character_pages(
    story_name: str,
    outline_result: OutlineResult,
    provider: Any,
    config: dict[str, Any],
    stories_dir: Path,
) -> dict[str, int]:
    """Generate wiki pages for all outline characters.

    Returns {"generated": int, "skipped": int}.
    """
    _validate_story_name(story_name)
    story_root = stories_dir / story_name
    wiki_dir = get_wiki_dir(story_root)
    outline_excerpt = _build_outline_excerpt(outline_result, story_root)
    model_config = _model_config(config)
    seed = _generation_seed(config)
    entities = _dedupe_entities(
        _extract_entities(
            story_name, outline_excerpt, provider, model_config, seed=seed
        ),
        "character",
    )

    generated = 0
    skipped = 0
    for entity in entities:
        character_name = entity["name"]
        page_data = _generate_page(
            "wiki/generate_character_page",
            {
                "story_name": story_name,
                "outline_excerpt": outline_excerpt,
                "character_name": character_name,
            },
            provider,
            model_config,
            seed=seed,
        )
        if page_data is None:
            continue

        page_name = page_data.get("page_name") or character_name
        if not isinstance(page_name, str) or not page_name.strip():
            page_name = character_name
        slug = page_data.get("slug")
        if not isinstance(slug, str) or not slug.strip():
            slug = slugify(page_name).replace("-", "_")
        page_slug = slug.replace("_", "-")
        page_path = wiki_dir / "characters" / f"{page_slug}.md"
        if page_path.exists():
            skipped += 1
            continue

        aliases = page_data.get("aliases")
        if not isinstance(aliases, list):
            aliases = []

        body = _page_body(
            [
                ("Background", str(page_data.get("L3_background") or "")),
                ("Personality", str(page_data.get("L3_personality") or "")),
                ("Motivations", str(page_data.get("L3_motivations") or "")),
                ("Relationships", str(page_data.get("L3_relationships") or "")),
                ("Skills", str(page_data.get("L3_skills") or "")),
                ("Growth Arc", str(page_data.get("L3_growth_arc") or "")),
                ("Current State", str(page_data.get("L3_current_state") or "")),
            ]
        )
        summary = run_batch(
            story_name,
            {
                "creates": [
                    {
                        "slug": page_slug,
                        "page_type": "character",
                        "page_name": page_name,
                        "confidence": "verified",
                        "first_appearance": 1,
                        "aliases": [
                            alias for alias in aliases if isinstance(alias, str)
                        ],
                        "detail_levels": {
                            "L1": str(page_data.get("L1") or "").strip(),
                            "L2": str(page_data.get("L2") or "").strip(),
                            "L3": body,
                        },
                        "body": body,
                    }
                ]
            },
        )
        generated += int(summary.get("created", 0))

    return {"generated": generated, "skipped": skipped}


def generate_location_pages(
    story_name: str,
    outline_result: OutlineResult,
    provider: Any,
    config: dict[str, Any],
    stories_dir: Path,
) -> dict[str, int]:
    """Generate wiki pages for all outline locations.

    Returns {"generated": int, "skipped": int}.
    """
    _validate_story_name(story_name)
    story_root = stories_dir / story_name
    wiki_dir = get_wiki_dir(story_root)
    outline_excerpt = _build_outline_excerpt(outline_result, story_root)
    model_config = _model_config(config)
    seed = _generation_seed(config)
    entities = _dedupe_entities(
        _extract_entities(
            story_name, outline_excerpt, provider, model_config, seed=seed
        ),
        "location",
    )

    generated = 0
    skipped = 0
    for entity in entities:
        location_name = entity["name"]
        page_data = _generate_page(
            "wiki/generate_location_page",
            {
                "story_name": story_name,
                "outline_excerpt": outline_excerpt,
                "location_name": location_name,
            },
            provider,
            model_config,
            seed=seed,
        )
        if page_data is None:
            continue

        page_name = page_data.get("page_name") or location_name
        if not isinstance(page_name, str) or not page_name.strip():
            page_name = location_name
        slug = page_data.get("slug")
        if not isinstance(slug, str) or not slug.strip():
            slug = slugify(page_name).replace("-", "_")
        page_slug = slug.replace("_", "-")
        page_path = wiki_dir / "locations" / f"{page_slug}.md"
        if page_path.exists():
            skipped += 1
            continue

        aliases = page_data.get("aliases")
        if not isinstance(aliases, list):
            aliases = []

        body = _page_body(
            [
                ("Geography", str(page_data.get("L3_geography") or "")),
                ("History", str(page_data.get("L3_history") or "")),
                ("Atmosphere", str(page_data.get("L3_atmosphere") or "")),
                ("Inhabitants", str(page_data.get("L3_inhabitants") or "")),
                ("Significance", str(page_data.get("L3_significance") or "")),
                ("Current State", str(page_data.get("L3_current_state") or "")),
            ]
        )
        summary = run_batch(
            story_name,
            {
                "creates": [
                    {
                        "slug": page_slug,
                        "page_type": "location",
                        "page_name": page_name,
                        "confidence": "verified",
                        "first_appearance": 1,
                        "aliases": [
                            alias for alias in aliases if isinstance(alias, str)
                        ],
                        "detail_levels": {
                            "L1": str(page_data.get("L1") or "").strip(),
                            "L2": str(page_data.get("L2") or "").strip(),
                            "L3": body,
                        },
                        "body": body,
                    }
                ]
            },
        )
        generated += int(summary.get("created", 0))

    return {"generated": generated, "skipped": skipped}
