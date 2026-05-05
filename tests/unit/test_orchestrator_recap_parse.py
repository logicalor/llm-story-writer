"""Verification tests for issue #350 recap event parsing."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from presentation.orchestrator import _coerce_event_list


def test_bare_json_array() -> None:
    assert _coerce_event_list('[{"name": "E1"}]') == [{"name": "E1"}]


def test_fenced_json() -> None:
    assert _coerce_event_list('```json\n[{"name": "E1"}]\n```') == [{"name": "E1"}]


def test_fenced_json_with_leading_prose() -> None:
    recap_events = 'Here are the events:\n```json\n[{"name": "E1"}]\n```'

    assert _coerce_event_list(recap_events) == [{"name": "E1"}]


def test_fenced_json_with_trailing_prose() -> None:
    recap_events = '```json\n[{"name": "E1"}]\n```\nEnd of output.'

    assert _coerce_event_list(recap_events) == [{"name": "E1"}]


def test_malformed_input_raises() -> None:
    with pytest.raises(ValueError, match="unparseable event list"):
        _coerce_event_list("not json at all")


def test_already_a_list() -> None:
    assert _coerce_event_list([{"name": "E1"}]) == [{"name": "E1"}]


def test_empty_string_returns_empty() -> None:
    assert _coerce_event_list("") == []
