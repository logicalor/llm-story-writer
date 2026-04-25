"""Consistency Checker agent — checks chapter for narrative consistency."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, cast

from application.interfaces.model_provider import ModelProvider
from domain.value_objects.model_config import ModelConfig
from infrastructure.prompts.agent_prompt_loader import load_agent_prompt
from presentation.pipeline_primitives import (
    TokenStreamBus,
    WikiContextBus,
    WikiContextEvent,
)


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

    issues: list[dict[str, Any]] = []

    lint = data.get("wiki_lint_findings", {})
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

    for finding in data.get("semantic_findings", []):
        issues.append(
            {
                "type": "semantic",
                "description": finding.get("finding", ""),
                "severity": finding.get("severity", "info"),
            }
        )

    for finding in data.get("cross_chapter_findings", []):
        issues.append(
            {
                "type": "cross_chapter",
                "description": finding.get("contradiction", ""),
                "severity": "warning",
            }
        )

    passed = not data.get("has_critical_findings", False)
    return {"issues": issues, "passed": passed}


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
        self._system_prompt: str | None = None

    def _get_system_prompt(self) -> str:
        if self._system_prompt is None:
            self._system_prompt = load_agent_prompt("consistency-checker")
        return self._system_prompt

    async def run(
        self,
        story_name: str,
        chapter_number: int,
        chapter_content: str,
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

        model_config = _build_model_config(
            self.config,
            "checker_model",
            "openai-compat://default",
        )
        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {
                "role": "user",
                "content": (
                    f"Story: {story_name}\nChapter: {chapter_number}\n"
                    f"Chapter Content:\n{chapter_content[:4000]}"
                ),
            },
        ]

        full_text = ""
        stream = cast(
            AsyncIterator[str],
            self.provider.stream_text(messages, model_config),
        )
        async for token in stream:
            await self.bus.emit(token)
            full_text += token

        return _extract_consistency_result(full_text)
