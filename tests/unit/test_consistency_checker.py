import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from presentation.agents.consistency_checker import (
    ConsistencyCheckerAgent,
    _extract_consistency_result,
)
from presentation.pipeline_primitives import TokenStreamBus, WikiContextBus


async def _collect_tokens(bus: TokenStreamBus) -> list[str]:
    tokens: list[str] = []
    async for token in bus:
        tokens.append(token)
    return tokens


async def _stream_tokens(tokens: list[str]):
    for token in tokens:
        yield token


class _ProviderStub:
    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens

    def stream_text(self, messages, model_config):
        return _stream_tokens(self.tokens)


def test_extract_consistency_result_no_issues() -> None:
    response = (
        '{"has_critical_findings": false, '
        '"wiki_lint_findings": {"contradictions": [], "timeline_issues": [], "trait_drift": []}, '
        '"semantic_findings": [], '
        '"cross_chapter_findings": []}'
    )

    result = _extract_consistency_result(response)

    assert result == {"issues": [], "passed": True}


def test_extract_consistency_result_with_critical_findings() -> None:
    response = (
        '{"has_critical_findings": true, '
        '"wiki_lint_findings": {"contradictions": ["Chapter 2 says rain; Chapter 3 says clear sky"], '
        '"timeline_issues": [], "trait_drift": []}, '
        '"semantic_findings": [], '
        '"cross_chapter_findings": []}'
    )

    result = _extract_consistency_result(response)

    assert result == {
        "issues": [
            {
                "type": "contradiction",
                "description": "Chapter 2 says rain; Chapter 3 says clear sky",
                "severity": "critical",
            }
        ],
        "passed": False,
    }


def test_extract_consistency_result_malformed_json_fallback() -> None:
    result = _extract_consistency_result("This is not valid JSON!!!")

    assert result == {"issues": [], "passed": True}


def test_extract_consistency_result_json_in_fence() -> None:
    response = (
        "```json\n"
        '{"has_critical_findings": false, '
        '"wiki_lint_findings": {"contradictions": [], "timeline_issues": [], "trait_drift": []}, '
        '"semantic_findings": [{"finding": "Minor name inconsistency", "severity": "warning"}], '
        '"cross_chapter_findings": []}'
        "\n```"
    )

    result = _extract_consistency_result(response)

    assert result == {
        "issues": [
            {
                "type": "semantic",
                "description": "Minor name inconsistency",
                "severity": "warning",
            }
        ],
        "passed": True,
    }


@pytest.mark.asyncio
async def test_run_emits_tokens_and_returns_parsed_result() -> None:
    response = (
        '{"has_critical_findings": false, '
        '"wiki_lint_findings": {"contradictions": [], "timeline_issues": [], "trait_drift": []}, '
        '"semantic_findings": [], '
        '"cross_chapter_findings": []}'
    )
    tokens = [response[:30], response[30:75], response[75:120], response[120:]]
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    agent = ConsistencyCheckerAgent(
        provider=_ProviderStub(tokens),
        config={},
        bus=bus,
        wiki_bus=wiki_bus,
    )

    with patch(
        "presentation.agents.consistency_checker.load_agent_prompt",
        return_value="system prompt",
    ):
        result = await agent.run("test-story", 7, "Chapter body")

    bus.close()
    emitted_tokens = await _collect_tokens(bus)

    assert emitted_tokens == tokens
    assert result == {"issues": [], "passed": True}