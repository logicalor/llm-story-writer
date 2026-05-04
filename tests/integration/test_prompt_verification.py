"""Integration test: verify 5 direct-generation prompts do not trigger tool-calling narration.

Requires a running LM Studio instance at http://127.0.0.1:1234/v1.
Auto-skips when LM Studio is not running.

Run with:
    pytest tests/integration/test_prompt_verification.py -v -m integration
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from domain.value_objects.model_config import ModelConfig
from infrastructure.prompts.prompt_loader import PromptLoader
from infrastructure.providers.openai_compatible_provider import OpenAICompatibleProvider

LM_STUDIO_URL = os.environ.get("LLM_API_BASE", "http://127.0.0.1:1234/v1")

DEFAULT_MODEL_NAME = os.environ.get(
    "LM_STUDIO_MODEL", "gemma-4-26b-a4b-it-heretic-guff"
)

FORBIDDEN_STRINGS = [
    "outline-generator",
    "critique-runner",
    "scene-writer",
    "wiki-snapshot",
    "rag-query",
    "savepoint-mgr",
    "recap-manager",
    "wiki-lint",
    "wiki-search",
    "story-state",
    "i am calling",
    "i will call",
    "calling `",
    "call `",
    "operation:",
    "self-correction",
]


def _assert_no_tool_calling(response_text: str, prompt_name: str) -> None:
    lower = response_text.lower()
    for forbidden in FORBIDDEN_STRINGS:
        assert forbidden not in lower, (
            f"Prompt '{prompt_name}' produced tool-calling narration: "
            f"forbidden string '{forbidden}' found in response.\n"
            f"Response (first 500 chars): {response_text[:500]!r}"
        )


@pytest.mark.usefixtures("llm_available")
@pytest.mark.integration
@pytest.mark.slow
class TestPromptVerification:
    def test_outline_create_direct(self) -> None:
        """outline/create_direct prompt must not produce tool-calling narration."""
        loader = PromptLoader(str(PROJECT_ROOT / "prompts"))
        system_prompt = loader.load_prompt(
            "outline/create_direct",
            variables={
                "prompt": ("A 2-chapter short story about a robot learning to dream."),
                "desired_chapters": "2",
                "story_elements": "",
                "base_context": "",
                "early_chapters": "1",
                "rising_start": "2",
                "rising_end": "2",
                "climax_start": "2",
                "climax_end": "2",
                "resolution_start": "2",
            },
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Please generate the complete outline."},
        ]
        provider = OpenAICompatibleProvider()
        model_config = ModelConfig(
            name=DEFAULT_MODEL_NAME,
            provider="openai_compatible",
            parameters={"temperature": 0.7, "max_tokens": 600},
        )

        async def _generate() -> str:
            return await provider.generate_text(messages, model_config)

        response_text = asyncio.run(_generate())
        _assert_no_tool_calling(response_text, "outline/create_direct")

    def test_outline_arc_assessment_direct(self) -> None:
        """outline/arc_assessment_direct prompt must not produce tool-calling narration."""
        loader = PromptLoader(str(PROJECT_ROOT / "prompts"))
        system_prompt = loader.load_prompt(
            "outline/arc_assessment_direct",
            variables={
                "outline": (
                    "Chapter 1: The Signal – A robot detects an unusual signal "
                    "in its sleep-cycle processor. "
                    "Chapter 2: The Dream – The robot begins interpreting the "
                    "signal as dreams and shares it with its maintenance companion."
                ),
                "critic_summary": "",
                "arc_distribution": "",
                "promise_payoff": "",
            },
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Provide your assessment."},
        ]
        provider = OpenAICompatibleProvider()
        model_config = ModelConfig(
            name=DEFAULT_MODEL_NAME,
            provider="openai_compatible",
            parameters={"temperature": 0.7, "max_tokens": 600},
        )

        async def _generate() -> str:
            return await provider.generate_text(messages, model_config)

        response_text = asyncio.run(_generate())
        _assert_no_tool_calling(response_text, "outline/arc_assessment_direct")

    def test_chapters_write_chapter_direct(self) -> None:
        """chapters/write_chapter_direct prompt must not produce tool-calling narration."""
        loader = PromptLoader(str(PROJECT_ROOT / "prompts"))
        system_prompt = loader.load_prompt(
            "chapters/write_chapter_direct",
            variables={
                "chapter_number": "1",
                "chapter_title": "The Signal",
                "chapter_summary": "A robot detects a signal.",
                "story_name": "test-fix",
                "base_context": "",
                "story_elements": "",
                "previous_chapter_summary": "",
                "next_chapter_summary": "",
                "character_context_block": "",
                "setting_context_block": "",
            },
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Write the chapter now."},
        ]
        provider = OpenAICompatibleProvider()
        model_config = ModelConfig(
            name=DEFAULT_MODEL_NAME,
            provider="openai_compatible",
            parameters={"temperature": 0.7, "max_tokens": 600},
        )

        async def _generate() -> str:
            return await provider.generate_text(messages, model_config)

        response_text = asyncio.run(_generate())
        _assert_no_tool_calling(response_text, "chapters/write_chapter_direct")

    def test_final_edit_edit_chapter_direct(self) -> None:
        """final_edit/edit_chapter_direct prompt must not produce tool-calling narration."""
        loader = PromptLoader(str(PROJECT_ROOT / "prompts"))
        system_prompt = loader.load_prompt(
            "final_edit/edit_chapter_direct",
            variables={
                "chapter_text": (
                    "The robot walked through the quiet corridor of the "
                    "maintenance bay, its sensors detecting the faint hum of a "
                    "signal it had never encountered before."
                ),
                "chapter_number": "1",
                "chapter_title": "The Signal",
                "prior_chapters_summary": "",
            },
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Return the polished chapter."},
        ]
        provider = OpenAICompatibleProvider()
        model_config = ModelConfig(
            name=DEFAULT_MODEL_NAME,
            provider="openai_compatible",
            parameters={"temperature": 0.7, "max_tokens": 600},
        )

        async def _generate() -> str:
            return await provider.generate_text(messages, model_config)

        response_text = asyncio.run(_generate())
        _assert_no_tool_calling(response_text, "final_edit/edit_chapter_direct")

    def test_chapter_review_consistency_check_direct(self) -> None:
        """chapter_review/consistency_check_direct must not produce tool-calling narration."""
        loader = PromptLoader(str(PROJECT_ROOT / "prompts"))
        system_prompt = loader.load_prompt(
            "chapter_review/consistency_check_direct",
            variables={
                "chapter_content": (
                    "Unit-7 served aboard the orbital station for three "
                    "standard years before the signal changed everything."
                ),
                "story_name": "test-fix",
                "chapter_number": "1",
                "outline": "",
            },
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Return the JSON consistency report."},
        ]
        provider = OpenAICompatibleProvider()
        model_config = ModelConfig(
            name=DEFAULT_MODEL_NAME,
            provider="openai_compatible",
            parameters={"temperature": 0.7, "max_tokens": 600},
        )

        async def _generate() -> str:
            return await provider.generate_text(messages, model_config)

        response_text = asyncio.run(_generate())
        _assert_no_tool_calling(
            response_text, "chapter_review/consistency_check_direct"
        )
