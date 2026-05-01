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


def test_extract_consistency_result_null_sections_fallback() -> None:
    response = (
        '{"has_critical_findings": false, '
        '"wiki_lint_findings": null, '
        '"semantic_findings": null, '
        '"cross_chapter_findings": null}'
    )

    result = _extract_consistency_result(response)

    assert result == {"issues": [], "passed": True}


def test_extract_consistency_result_non_dict_payload() -> None:
    result = _extract_consistency_result("[]")

    assert result == {"issues": [], "passed": True}


def test_extract_consistency_result_non_dict_finding_items() -> None:
    response = (
        '{"has_critical_findings": false, '
        '"wiki_lint_findings": {"contradictions": [], "timeline_issues": [], "trait_drift": []}, '
        '"semantic_findings": ["unexpected string", {"finding": "valid finding", "severity": "info"}], '
        '"cross_chapter_findings": []}'
    )

    result = _extract_consistency_result(response)

    assert result == {
        "issues": [
            {
                "type": "semantic",
                "description": "valid finding",
                "severity": "info",
            }
        ],
        "passed": True,
    }


def test_extract_consistency_result_direct_format_no_issues() -> None:
    response = '{"issues": [], "has_critical_findings": false}'

    result = _extract_consistency_result(response)

    assert result == {"issues": [], "passed": True}


def test_extract_consistency_result_direct_format_with_critical() -> None:
    response = (
        '{"issues": [{"type": "continuity", "description": "gap", '
        '"severity": "critical", "location": "p3"}], '
        '"has_critical_findings": true}'
    )

    result = _extract_consistency_result(response)

    assert result["passed"] is False
    assert len(result["issues"]) == 1
    assert result["issues"][0] == {
        "type": "continuity",
        "description": "gap",
        "severity": "critical",
        "location": "p3",
    }


def test_extract_consistency_result_direct_format_with_warnings() -> None:
    response = (
        '{"issues": [{"type": "timeline", "description": "late", '
        '"severity": "warning"}], "has_critical_findings": false}'
    )

    result = _extract_consistency_result(response)

    assert result["passed"] is True
    assert len(result["issues"]) == 1
    assert result["issues"][0] == {
        "type": "timeline",
        "description": "late",
        "severity": "warning",
        "location": "",
    }


def test_extract_consistency_result_legacy_with_issues_key_not_misrouted() -> None:
    response = (
        '{"issues": [], '
        '"wiki_lint_findings": {"contradictions": ["x"], '
        '"timeline_issues": [], "trait_drift": []}}'
    )

    result = _extract_consistency_result(response)

    assert result["passed"] is True
    assert result["issues"] == [
        {
            "type": "contradiction",
            "description": "x",
            "severity": "critical",
        }
    ]


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
        "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
        return_value="system prompt",
    ):
        result = await agent.run("test-story", 7, "Chapter body")

    bus.close()
    emitted_tokens = await _collect_tokens(bus)

    assert emitted_tokens == tokens
    assert result == {"issues": [], "passed": True}
