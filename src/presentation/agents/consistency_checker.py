"""Consistency Checker agent — checks chapter for narrative consistency."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, cast

from pathlib import Path

from application.interfaces.model_provider import ModelProvider
from application.pipeline.handoffs import OutlineResult
from domain.value_objects.model_config import ModelConfig
from infrastructure.prompts.prompt_loader import PromptLoader
from tools._io import STORIES_DIR
from tools._persist import read_markdown_ref
from tools.context_assembly import assemble_context, render_recap_as_markdown
from presentation.pipeline_primitives import (
    TokenStreamBus,
    WikiContextBus,
    WikiContextEvent,
)
from application.interfaces.model_provider import StreamToken


def _build_model_config(config: dict[str, Any], role: str, default: str) -> ModelConfig:
    models = config.get("models", {})
    model_name = models.get(role, default)
    return ModelConfig.from_string(model_name)


def _extract_consistency_result(text: str) -> dict[str, Any]:
    """Parse LLM response text into a structured consistency result."""
    stripped = text.strip()
    if "```json" in stripped:
        parts = stripped.split("```json", 1)
        if len(parts) > 1:
            stripped = parts[1].split("```", 1)[0].strip()
    elif "```" in stripped:
        parts = stripped.split("```", 1)
        if len(parts) > 1:
            inner = parts[1].split("```", 1)[0].strip()
            if inner.startswith("{"):
                stripped = inner

    try:
        data = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return {"issues": [], "passed": True}

    if not isinstance(data, dict):
        return {"issues": [], "passed": True}

    issues: list[dict[str, Any]] = []

    # Supports both new direct-generation format (has "issues" list and "has_critical_findings")
    # and legacy format (has "wiki_lint_findings", "semantic_findings", etc.).
    # New direct-generation format
    if isinstance(data.get("issues"), list) and "has_critical_findings" in data:
        for item in data["issues"]:
            if not isinstance(item, dict):
                continue
            issues.append(
                {
                    "type": item.get("type", "continuity"),
                    "description": item.get("description", ""),
                    "severity": item.get("severity", "info"),
                    "location": item.get("location", ""),
                    "scene_number": item.get("scene_number"),
                }
            )
        passed = not data.get("has_critical_findings", False)
        return {"issues": issues, "passed": passed}

    # Legacy format fallback
    lint = data.get("wiki_lint_findings") or {}
    for contradiction in lint.get("contradictions", []):
        issues.append(
            {
                "type": "contradiction",
                "description": contradiction,
                "severity": "critical",
            }
        )
    for timeline_issue in lint.get("timeline_issues", []):
        issues.append(
            {
                "type": "timeline",
                "description": timeline_issue,
                "severity": "warning",
            }
        )
    for trait in lint.get("trait_drift", []):
        issues.append(
            {
                "type": "trait_drift",
                "description": trait,
                "severity": "warning",
            }
        )

    for finding in data.get("semantic_findings") or []:
        if not isinstance(finding, dict):
            continue
        issues.append(
            {
                "type": "semantic",
                "description": finding.get("finding", ""),
                "severity": finding.get("severity", "info"),
            }
        )

    for finding in data.get("cross_chapter_findings") or []:
        if not isinstance(finding, dict):
            continue
        issues.append(
            {
                "type": "cross_chapter",
                "description": finding.get("contradiction", ""),
                "severity": "warning",
            }
        )

    passed = not data.get("has_critical_findings", False)
    return {"issues": issues, "passed": passed}


def _resolve_refs(obj: Any, story_root: Path) -> Any:
    """Recursively resolve {"$ref": "path"} dicts to their file contents."""
    if isinstance(obj, dict):
        if "$ref" in obj:
            return read_markdown_ref(story_root, obj)
        return {k: _resolve_refs(v, story_root) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_refs(item, story_root) for item in obj]
    return obj


def _extract_outline_text(
    outline_result: OutlineResult | None,
    chapter_number: int,
    story_root: Path | None = None,
) -> str:
    if outline_result is None:
        return ""

    chapter_index = chapter_number - 1

    try:
        chapter_details = outline_result.chapter_details[chapter_index]
    except IndexError:
        chapter_details = None

    if chapter_details:
        if story_root is not None:
            chapter_details = _resolve_refs(chapter_details, story_root)
        return json.dumps(chapter_details, ensure_ascii=False, indent=2)

    try:
        chapter_outline = outline_result.chapter_outlines[chapter_index]
    except IndexError:
        chapter_outline = None

    if chapter_outline:
        if story_root is not None:
            chapter_outline = _resolve_refs(chapter_outline, story_root)
        return json.dumps(chapter_outline, ensure_ascii=False, indent=2)

    return ""


class ConsistencyCheckerAgent:
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

    @staticmethod
    def _load_scene_definitions(story_name: str, chapter_number: int) -> str:
        """Load the scene definitions JSON for a chapter, or return empty string."""
        scenes_json_path: Path = (
            STORIES_DIR
            / story_name
            / "chapters"
            / f"chapter_{chapter_number}_scenes.json"
        )
        if not scenes_json_path.exists():
            return ""
        try:
            return scenes_json_path.read_text(encoding="utf-8")
        except OSError:
            return ""

    @staticmethod
    def _build_delineated_content(
        story_name: str, chapter_number: int, fallback: str
    ) -> str:
        """Assemble scene files with --- Scene N --- delimiters for the checker.

        Falls back to the pre-assembled chapter text if scene files are absent.
        """
        scenes_dir: Path = (
            STORIES_DIR / story_name / "chapters" / f"chapter_{chapter_number}"
        )
        scene_files = (
            sorted(scenes_dir.glob("scene_*.md")) if scenes_dir.exists() else []
        )
        if not scene_files:
            return fallback
        parts: list[str] = []
        for scene_file in scene_files:
            # Extract scene number from filename (scene_1.md → 1)
            try:
                scene_num = int(scene_file.stem.split("_", 1)[1])
            except (IndexError, ValueError):
                scene_num = len(parts) + 1
            prose = scene_file.read_text(encoding="utf-8").strip()
            parts.append(f"--- Scene {scene_num} ---\n\n{prose}")
        return "\n\n".join(parts)

    async def run(
        self,
        story_name: str,
        chapter_number: int,
        chapter_content: str,
        outline_result: OutlineResult | None = None,
    ) -> dict[str, Any]:
        """Check chapter for consistency issues.

        Returns a dict with keys: 'issues' (list), 'passed' (bool).
        """
        await self.wiki_bus.emit(
            WikiContextEvent(
                phase="consistency",
                event_type="detail_level",
                content=f"Checking chapter {chapter_number} consistency",
            )
        )

        loader = self._loader
        story_root = STORIES_DIR / story_name
        outline = _extract_outline_text(outline_result, chapter_number, story_root)
        delineated = self._build_delineated_content(
            story_name, chapter_number, chapter_content
        )
        ctx = assemble_context(
            story_name,
            scope="consistency",
            focus=outline or chapter_content[:500],
            chapter=chapter_number,
            recap_window=("chapter", 3),
        )
        wiki_context: str = ctx["wiki_snapshot"]
        recap_context: str = render_recap_as_markdown(ctx["recap_snippets"])
        wiki_relationships: str = ""
        scene_definitions = self._load_scene_definitions(story_name, chapter_number)
        system_prompt = loader.load_prompt(
            "chapter_review/consistency_check_direct",
            variables={
                "chapter_content": delineated,
                "story_name": story_name,
                "chapter_number": str(chapter_number),
                "outline": outline,
                "wiki_context": wiki_context,
                "recap_context": recap_context,
                "wiki_relationships": wiki_relationships,
                "scene_definitions": scene_definitions,
            },
        )

        model_config = _build_model_config(
            self.config,
            "checker_model",
            "openai-compat://default",
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Return the JSON consistency report."},
        ]

        full_text = ""
        stream = cast(
            AsyncIterator[StreamToken],
            self.provider.stream_text(messages, model_config),
        )
        async for st in stream:
            if st.kind == "content":
                await self.bus.emit(st.text)
                full_text += st.text

        return _extract_consistency_result(full_text)
