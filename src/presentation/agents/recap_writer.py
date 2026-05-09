"""Recap writer agent - generates chapter recap artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from application.interfaces.model_provider import ModelProvider
from domain.value_objects.generation_settings import GenerationSettings
from domain.value_objects.model_config import ModelConfig
from infrastructure.prompts.prompt_loader import PromptLoader
from presentation.pipeline_primitives import (
    TokenStreamBus,
    WikiContextBus,
    WikiContextEvent,
)
from tools._io import STORIES_DIR
from tools._wiki import get_wiki_dir, match_entities_in_text, read_index
from tools.context_assembly import assemble_context, render_recap_as_markdown


def _build_model_config(config: dict[str, Any], role: str, default: str) -> ModelConfig:
    models = config.get("models", {})
    model_name = models.get(role, default)
    return ModelConfig.from_string(model_name)


def _parse_events_from_json(text: str) -> list[dict]:
    """Extract a list of event dicts from an LLM JSON response."""
    if not text:
        return []
    stripped = text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", stripped)
    candidate = fence_match.group(1).strip() if fence_match else stripped
    try:
        obj = json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        return []
    if isinstance(obj, list):
        return [e for e in obj if isinstance(e, dict)]
    if isinstance(obj, dict):
        events = obj.get("events")
        if isinstance(events, list):
            return [e for e in events if isinstance(e, dict)]
    return []


class RecapWriterAgent:
    def __init__(
        self,
        provider: ModelProvider,
        config: dict[str, Any],
        bus: TokenStreamBus,
        wiki_bus: WikiContextBus,
    ) -> None:
        self.provider = provider
        self.config = config
        self.bus = bus
        self.wiki_bus = wiki_bus
        project_root = Path(__file__).resolve().parents[3]
        self._loader = PromptLoader(prompts_dir=str(project_root / "prompts"))

    async def _run_stage(
        self,
        prompt_name: str,
        variables: dict[str, Any],
        model_config: ModelConfig,
        settings: GenerationSettings,
    ) -> str:
        try:
            prompt = self._loader.load_prompt(prompt_name, variables)
            response = await self.provider.generate_text(
                [{"role": "user", "content": prompt}],
                model_config,
                seed=settings.seed,
            )
        except Exception:
            return ""

        if isinstance(response, str):
            output = response
        else:
            output = json.dumps(response, ensure_ascii=False)

        if output:
            await self.bus.emit(output)
        return output

    async def _emit_stage(self, chapter_number: int, stage_name: str) -> None:
        await self.bus.emit(f"\n[Recap] Chapter {chapter_number} — {stage_name}\n")

    async def run(
        self,
        story_name: str,
        chapter_number: int,
        chapter_content: str,
        previous_recap: str,
        story_start_date: str,
        settings: GenerationSettings,
    ) -> dict[str, Any]:
        await self.wiki_bus.emit(
            WikiContextEvent(
                phase="recap",
                event_type="entity_match",
                content=(f"Generating recap for {story_name} chapter {chapter_number}"),
            )
        )

        _char_slugs: tuple[str, ...] = ()
        _wiki_context: str = ""
        _related_recap_history: str = ""
        try:
            _wiki_dir = get_wiki_dir(STORIES_DIR / story_name)
            _index_entries = read_index(_wiki_dir)
            _char_entries = [e for e in _index_entries if e.get("type") == "character"]
            _matched = match_entities_in_text(chapter_content, _char_entries)
            _char_slugs = tuple(e["slug"] for e in _matched)
        except Exception:
            pass

        try:
            _ctx = assemble_context(
                story_name,
                scope="recap",
                focus=chapter_content[:2000],
                chapter=chapter_number,
                characters=_char_slugs,
                recap_window=("character", 5),
            )
            _wiki_context = _ctx["wiki_snapshot"]
            _related_recap_history = render_recap_as_markdown(_ctx["recap_snippets"])
        except Exception:
            pass

        model_config = _build_model_config(
            self.config,
            "recap_writer",
            "openai-compat://default",
        )

        await self._emit_stage(chapter_number, "extract chapter events")
        events = await self._run_stage(
            "extract_chapter_events",
            {
                "chapter_content": chapter_content,
                "previous_chapter_recap": previous_recap,
                "wiki_context": _wiki_context,
                "related_recap_history": _related_recap_history,
            },
            model_config,
            settings,
        )
        if not events:
            return {"events": []}

        if not settings.use_multi_stage_recap_sanitizer:
            await self._emit_stage(chapter_number, "format json")
            formatted = await self._run_stage(
                "recap/format_json",
                {"enriched_events": events},
                model_config,
                settings,
            )
            return {
                "events": _parse_events_from_json(formatted),
                "compact": formatted,
                "sanitised": formatted,
            }

        await self._emit_stage(chapter_number, "assign event timing")
        timed_events = await self._run_stage(
            "recap/assign_event_timing",
            {
                "events": events,
                "story_start_date": story_start_date,
                "previous_chapter_recap": previous_recap,
            },
            model_config,
            settings,
        )

        await self._emit_stage(chapter_number, "enrich event details")
        enriched_events = await self._run_stage(
            "recap/enrich_event_details",
            {"timed_events": timed_events},
            model_config,
            settings,
        )

        await self._emit_stage(chapter_number, "format json")
        formatted = await self._run_stage(
            "recap/format_json",
            {"enriched_events": enriched_events},
            model_config,
            settings,
        )

        await self._emit_stage(chapter_number, "compact events")
        compact = await self._run_stage(
            "recap/compact_events",
            {"events_json": formatted},
            model_config,
            settings,
        )
        compact = compact or formatted

        if settings.use_improved_recap_sanitizer:
            await self._emit_stage(chapter_number, "sanitize recap")
            sanitised = await self._run_stage(
                "recap/sanitize",
                {
                    "previous_chapter_recap": previous_recap,
                    "recap": compact,
                    "story_start_date": story_start_date,
                    "related_recap_history": _related_recap_history,
                },
                model_config,
                settings,
            )
            sanitised = sanitised or compact
        else:
            sanitised = compact

        return {
            "events": _parse_events_from_json(formatted),
            "compact": compact,
            "sanitised": sanitised,
        }
