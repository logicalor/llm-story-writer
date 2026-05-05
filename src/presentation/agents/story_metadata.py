"""Story Metadata agent - generates title, summary, and tags from the outline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from application.interfaces.model_provider import ModelProvider
from application.pipeline.handoffs import StoryMetadataResult
from domain.value_objects.generation_settings import GenerationSettings
from domain.value_objects.model_config import ModelConfig
from infrastructure.prompts.prompt_loader import PromptLoader
from presentation.pipeline_primitives import (
    TokenStreamBus,
    WikiContextBus,
    WikiContextEvent,
)
from tools.context_assembly import assemble_context


def _build_model_config(config: dict[str, Any], role: str, default: str) -> ModelConfig:
    models = config.get("models", {})
    model_name = models.get(role, default)
    return ModelConfig.from_string(model_name)


def _parse_tags(raw: str) -> list[str]:
    """Parse a JSON array of strings from LLM output, with fallback to []."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [tag for tag in parsed if isinstance(tag, str)]
    except (json.JSONDecodeError, ValueError):
        pass
    return []


def _parse_title(raw: str) -> str:
    """Extract a clean single-line title from an LLM response.

    Returns the first non-empty, non-heading line that is 100 chars or fewer.
    Falls back to the raw response truncated to 100 chars if nothing better is
    found — so the caller always gets something.
    """
    for line in raw.splitlines():
        stripped = line.strip()
        # Skip markdown headings, empty lines, or lines that look like
        # prose/explanation rather than a title.
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        # Heuristic: a bare title won't start with a bullet, number, or word
        # followed immediately by a colon (e.g. "Why?:").
        if stripped[0] in ("-", "*", ">") or (
            len(stripped) > 1 and stripped[1] in ("-", ".", ")")
        ):
            continue
        if len(stripped) <= 100:
            # Strip surrounding bold/italic markdown markers if present.
            stripped = stripped.strip("*_")
            return stripped
    return raw.strip()[:100]


class StoryMetadataAgent:
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

    async def run(
        self,
        story_name: str,
        outline_text: str,
        first_chapter: str,
        settings: GenerationSettings,
    ) -> StoryMetadataResult:
        await self.bus.emit(
            f"\n[Metadata] Generating story metadata for: {story_name}\n"
        )
        await self.wiki_bus.emit(
            WikiContextEvent(
                phase="story-metadata",
                event_type="entity_match",
                content=f"Generating story metadata for: {story_name}",
            )
        )

        _ctx = assemble_context(
            story_name,
            scope="metadata",
            focus=outline_text[:500] if outline_text else "",
            recap_window=("chapter", 20),
            token_budget=20000,
        )
        wiki_context: str = _ctx["wiki_snapshot"]
        recap_context: str = (
            "\n\n".join(_ctx["recap_snippets"]) if _ctx["recap_snippets"] else ""
        )

        model_config = _build_model_config(
            self.config, "story_metadata", "openai-compat://default"
        )

        title = ""
        await self.bus.emit("\n[Metadata] Generating title...\n")
        try:
            prompt = self._loader.load_prompt(
                "outline/create_title",
                {
                    "outline": outline_text,
                    "first_chapter": first_chapter,
                    "wiki_context": wiki_context,
                    "recap_context": recap_context,
                },
            )
            response = await self.provider.generate_text(
                [{"role": "user", "content": prompt}],
                model_config,
                seed=settings.seed,
            )
            if response:
                title = _parse_title(response)
                await self.bus.emit(f"[Metadata] Title: {title}\n")
        except Exception:
            pass

        summary = ""
        await self.bus.emit("\n[Metadata] Generating summary...\n")
        try:
            prompt = self._loader.load_prompt(
                "outline/create_summary",
                {
                    "outline": outline_text,
                    "chapter_content": first_chapter,
                    "wiki_context": wiki_context,
                    "recap_context": recap_context,
                },
            )
            response = await self.provider.generate_text(
                [{"role": "user", "content": prompt}],
                model_config,
                seed=settings.seed,
            )
            if response:
                summary = response.strip()
                await self.bus.emit(response)
        except Exception:
            pass

        tags: list[str] = []
        await self.bus.emit("\n[Metadata] Generating tags...\n")
        try:
            prompt = self._loader.load_prompt(
                "outline/create_tags",
                {
                    "outline": outline_text,
                    "first_chapter": first_chapter,
                    "wiki_context": wiki_context,
                    "recap_context": recap_context,
                },
            )
            response = await self.provider.generate_text(
                [{"role": "user", "content": prompt}],
                model_config,
                seed=settings.seed,
            )
            if response:
                await self.bus.emit(response)
                tags = _parse_tags(response)
        except Exception:
            pass

        return StoryMetadataResult(
            story_name=story_name,
            title=title,
            summary=summary,
            tags=tags,
        )
