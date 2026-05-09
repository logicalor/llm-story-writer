"""Final Editor agent - post-assembly prose pass for voice and pacing."""

from __future__ import annotations

from pathlib import Path
from typing import Any, AsyncIterator, cast

from application.interfaces.model_provider import ModelProvider
from application.pipeline.handoffs import ChapterDraft, FinalEditResult
from domain.value_objects.generation_settings import GenerationSettings
from domain.value_objects.model_config import ModelConfig
from infrastructure.prompts.prompt_loader import PromptLoader
from presentation.pipeline_primitives import (
    TokenStreamBus,
    WikiContextBus,
    WikiContextEvent,
)
from application.interfaces.model_provider import StreamToken
from tools.context_assembly import assemble_context, render_recap_as_markdown
from tools._io import _validate_story_name
from tools._wiki import get_wiki_dir, match_entities_in_text, read_index


def _build_model_config(config: dict[str, Any], role: str, default: str) -> ModelConfig:
    models = config.get("models", {})
    model_name = models.get(role, default)
    return ModelConfig.from_string(model_name)


class FinalEditorAgent:
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
        self._loader = PromptLoader(prompts_dir="prompts")

    def build_prior_summaries(self, approved_chapters: list[ChapterDraft]) -> list[str]:
        """Pre-compute prior-chapter summaries for the full chapter list."""
        prior_summaries: list[str] = []
        running_summaries: list[str] = []
        for index, draft in enumerate(approved_chapters):
            chapter_number = (
                draft.chapter_number if hasattr(draft, "chapter_number") else index + 1
            )
            prior_summaries.append("\n".join(running_summaries))
            running_summaries.append(
                f"Chapter {chapter_number}: {draft.title} — "
                f"{draft.content[:200].replace(chr(10), ' ')}..."
            )
        return prior_summaries

    async def edit_single_chapter(
        self,
        draft: ChapterDraft,
        prior_summary: str,
        chapter_number: int,
        settings: GenerationSettings,
    ) -> ChapterDraft:
        """Edit a single chapter using optional scrub and voice passes."""
        model_config = _build_model_config(
            self.config, "chapter_writer", "openai-compat://default"
        )

        await self.wiki_bus.emit(
            WikiContextEvent(
                phase="final-edit",
                event_type="entity_match",
                content=f"Final editing chapter {chapter_number} of {draft.story_name}",
            )
        )

        _ctx = assemble_context(
            draft.story_name,
            scope="final_edit",
            focus=draft.synopsis or draft.content[:500],
            chapter=chapter_number,
            recap_window=("chapter", 3),
        )
        wiki_context: str = _ctx["wiki_snapshot"]
        recap_context: str = render_recap_as_markdown(_ctx["recap_snippets"])

        if settings.enable_scrubbing:
            character_aliases = ""
            try:
                _story_dir: Path = _validate_story_name(draft.story_name)
                _wiki_dir = get_wiki_dir(_story_dir)
                if _wiki_dir.exists():
                    _index_entries = read_index(_wiki_dir)
                    _char_entries = [
                        entry
                        for entry in _index_entries
                        if entry.get("type") == "character"
                    ]
                    _matches = match_entities_in_text(draft.content, _char_entries)
                    _matched_slugs = {match.get("slug") for match in _matches}
                    _alias_lines: list[str] = []
                    for _entry in _char_entries:
                        if _entry.get("slug") not in _matched_slugs:
                            continue
                        _name = _entry.get("name", "")
                        _aliases = [
                            alias
                            for alias in _entry.get("aliases", [])
                            if isinstance(alias, str) and alias.strip()
                        ]
                        if _aliases:
                            _alias_lines.append(
                                f"{_name} (aliases: {', '.join(_aliases)})"
                            )
                        elif _name:
                            _alias_lines.append(_name)
                    character_aliases = "\n".join(_alias_lines)
                else:
                    await self.wiki_bus.emit(
                        WikiContextEvent(
                            phase="final-edit",
                            event_type="warning",
                            content="character alias lookup skipped: wiki unavailable",
                        )
                    )
            except Exception as _alias_exc:
                await self.wiki_bus.emit(
                    WikiContextEvent(
                        phase="final-edit",
                        event_type="error",
                        content=f"character alias lookup failed: {_alias_exc}",
                    )
                )
                character_aliases = ""

            prose_prompt = self._loader.load_prompt(
                "final_edit/prose_scrub",
                variables={
                    "chapter_text": draft.content,
                    "chapter_number": str(chapter_number),
                    "character_aliases": character_aliases,
                },
            )
            messages = [
                {"role": "system", "content": prose_prompt},
                {"role": "user", "content": "Return the findings JSON."},
            ]
            prose_findings = ""
            stream = cast(
                AsyncIterator[StreamToken],
                self.provider.stream_text(messages, model_config, seed=settings.seed),
            )
            async for st in stream:
                if st.kind == "content":
                    prose_findings += st.text
            prose_findings = prose_findings.strip()

            voice_prompt = self._loader.load_prompt(
                "final_edit/voice_consistency_pass",
                variables={
                    "chapter_text": draft.content,
                    "prior_chapters_summary": prior_summary,
                },
            )
            messages = [
                {"role": "system", "content": voice_prompt},
                {"role": "user", "content": "Return the findings JSON."},
            ]
            voice_findings = ""
            stream = cast(
                AsyncIterator[StreamToken],
                self.provider.stream_text(messages, model_config, seed=settings.seed),
            )
            async for st in stream:
                if st.kind == "content":
                    voice_findings += st.text
            voice_findings = voice_findings.strip()
        else:
            prose_findings = ""
            voice_findings = ""

        system_prompt = self._loader.load_prompt(
            "final_edit/edit_chapter_direct",
            variables={
                "chapter_text": draft.content,
                "chapter_number": str(chapter_number),
                "chapter_title": draft.title,
                "prior_chapters_summary": prior_summary,
                "prose_findings": prose_findings,
                "voice_findings": voice_findings,
                "wiki_context": wiki_context,
                "recap_context": recap_context,
            },
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Return the polished chapter."},
        ]

        full_text = ""
        stream = cast(
            AsyncIterator[StreamToken],
            self.provider.stream_text(messages, model_config, seed=settings.seed),
        )
        async for st in stream:
            if st.kind == "content":
                await self.bus.emit(st.text)
                full_text += st.text

        edited_content = full_text.strip() if full_text.strip() else draft.content
        return ChapterDraft(
            story_name=draft.story_name,
            chapter_number=draft.chapter_number,
            title=draft.title,
            content=edited_content,
            word_count=len(edited_content.split()),
            synopsis=draft.synopsis,
            scene_definitions=list(draft.scene_definitions),
            recap=dict(draft.recap),
            consistency_findings=list(draft.consistency_findings),
            critic_findings=list(draft.critic_findings),
            savepoint_id=draft.savepoint_id,
        )

    async def run(
        self,
        story_name: str,
        approved_chapters: list[ChapterDraft],
        settings: GenerationSettings,
    ) -> FinalEditResult:
        """Perform a prose editing pass over each approved chapter.

        Each chapter is passed individually to the LLM with the final-editor
        system prompt. The returned text replaces the chapter content. If the
        LLM returns an empty response, the original content is preserved.
        """
        edited_chapters: list[ChapterDraft] = []
        prior_summaries = self.build_prior_summaries(approved_chapters)

        for index, draft in enumerate(approved_chapters):
            chapter_number = (
                draft.chapter_number if hasattr(draft, "chapter_number") else index + 1
            )
            edited_chapters.append(
                await self.edit_single_chapter(
                    draft,
                    prior_summaries[index],
                    chapter_number,
                    settings,
                )
            )

        return FinalEditResult(
            story_name=story_name,
            chapters_processed=len(edited_chapters),
            total_issues_found=0,
            total_revisions_made=len(edited_chapters),
            edited_chapters=edited_chapters,
        )
