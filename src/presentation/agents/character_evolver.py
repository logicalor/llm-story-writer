"""Character Evolver agent - updates character sheets after each chapter."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from application.interfaces.model_provider import ModelProvider
from application.pipeline.handoffs import ChapterDraft
from domain.value_objects.generation_settings import GenerationSettings
from domain.value_objects.model_config import ModelConfig
from infrastructure.prompts.prompt_loader import PromptLoader
from presentation.pipeline_primitives import TokenStreamBus, WikiContextBus
from tools._io import STORIES_DIR, _atomic_write, _validate_story_name
from tools._persist import persist_markdown, read_markdown_ref


def _build_model_config(config: dict[str, Any], role: str, default: str) -> ModelConfig:
    models = config.get("models", {})
    model_name = models.get(role, default)
    return ModelConfig.from_string(model_name)


def _should_apply_update(analysis: str) -> bool:
    if len(analysis.strip()) <= 20:
        return False

    try:
        parsed = json.loads(analysis)
    except json.JSONDecodeError:
        return True

    if not isinstance(parsed, dict):
        return True
    return bool(parsed.get("needs_update"))


class CharacterEvolverAgent:
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

    async def _run_prompt(
        self,
        prompt_name: str,
        variables: dict[str, Any],
        model_config: ModelConfig,
        settings: GenerationSettings,
    ) -> str:
        prompt = self._loader.load_prompt(prompt_name, variables)
        return await self.provider.generate_text(
            [{"role": "user", "content": prompt}],
            model_config,
            seed=settings.seed,
        )

    async def run(
        self,
        story_name: str,
        chapter_draft: ChapterDraft,
        chapter_number: int,
        settings: GenerationSettings,
    ) -> dict[str, str]:
        _validate_story_name(story_name)
        story_root = STORIES_DIR / story_name
        characters_dir = STORIES_DIR / story_name / "characters"
        if not characters_dir.exists():
            return {}

        model_config = _build_model_config(
            self.config,
            "chapter_writer",
            "openai-compat://default",
        )
        results: dict[str, str] = {}

        scenes_path = (
            STORIES_DIR
            / story_name
            / "chapters"
            / f"chapter_{chapter_number}_scenes.json"
        )
        chapter_synopsis = (
            scenes_path.read_text(encoding="utf-8")
            if scenes_path.exists()
            else chapter_draft.content
        )

        for character_path in sorted(characters_dir.glob("*.json")):
            if character_path.stem.startswith("_"):
                continue
            character_name = character_path.stem
            try:
                raw_data = character_path.read_text(encoding="utf-8")
                sheet_data = json.loads(raw_data)
                if not isinstance(sheet_data, dict):
                    raise ValueError("Character sheet JSON must be an object")
                character_name = str(sheet_data.get("name") or character_path.stem)
                resolved_data = {
                    **sheet_data,
                    "sheet": (
                        read_markdown_ref(story_root, _ref)
                        if isinstance(_ref := sheet_data.get("sheet"), dict)
                        else (_ref or "")
                    ),
                    "chunks": {
                        k: (
                            read_markdown_ref(story_root, v)
                            if isinstance(v, dict)
                            else (v or "")
                        )
                        for k, v in sheet_data.get("chunks", {}).items()
                    },
                    "summary": (
                        read_markdown_ref(story_root, _ref)
                        if isinstance(_ref := sheet_data.get("summary"), dict)
                        else (_ref or "")
                    ),
                    "abridged": (
                        read_markdown_ref(story_root, _ref)
                        if isinstance(_ref := sheet_data.get("abridged"), dict)
                        else (_ref or "")
                    ),
                }

                extracted_events = await self._run_prompt(
                    "characters/extract_from_chapter",
                    {"chapter_synopsis": chapter_synopsis},
                    model_config,
                    settings,
                )
                if len(extracted_events.strip()) <= 20:
                    results[character_name] = "unchanged"
                    continue

                changes_analysis = await self._run_prompt(
                    "characters/analyze_changes",
                    {
                        "character_name": character_name,
                        "current_character_sheet": json.dumps(
                            resolved_data, ensure_ascii=False
                        ),
                        "chapter_outline": chapter_synopsis,
                    },
                    model_config,
                    settings,
                )
                if not _should_apply_update(changes_analysis):
                    results[character_name] = "unchanged"
                    continue

                existing_text = (
                    resolved_data.get("sheet")
                    or resolved_data.get("abridged")
                    or resolved_data.get("summary")
                    or ""
                )
                updated_sheet = await self._run_prompt(
                    "characters/update",
                    {
                        "character_name": character_name,
                        "current_character_sheet": existing_text,
                        "changes_to_apply": changes_analysis,
                    },
                    model_config,
                    settings,
                )
                if not updated_sheet.strip():
                    results[character_name] = "unchanged"
                    continue

                slug = character_path.stem
                updated_data = {
                    "name": character_name,
                    "sheet": persist_markdown(
                        story_root, f"characters/{slug}/sheet.md", updated_sheet
                    ),
                    "abridged": sheet_data.get("abridged", ""),
                    "summary": sheet_data.get("summary", ""),
                    "chunks": sheet_data.get("chunks", {}),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                _atomic_write(
                    character_path,
                    json.dumps(updated_data, indent=2, ensure_ascii=False),
                )
                results[character_name] = "updated"
            except Exception as exc:
                results[character_name] = "unchanged"
                await self.bus.emit(
                    "\n[Character Evolution] "
                    f"chapter {chapter_number} {character_name} skipped "
                    f"({type(exc).__name__}: {exc})\n"
                )

        return results
