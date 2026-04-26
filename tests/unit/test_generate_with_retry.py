"""Unit tests for _generate_with_retry helper in integration fixture."""

from __future__ import annotations

from unittest.mock import call, patch

import pytest


def _generate_with_retry(prompt: str, max_attempts: int = 3) -> str:
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")

    from src.tools._llm import generate_text
    import time

    last_err: Exception = RuntimeError("unreachable")
    for attempt in range(max_attempts):
        try:
            return generate_text(prompt)
        except Exception as err:
            last_err = err
            if attempt < max_attempts - 1:
                time.sleep(4**attempt)
    raise last_err


def test_success_on_first_attempt() -> None:
    with patch(
        "src.tools._llm.generate_text",
        return_value="result",
    ) as mock_generate:
        result = _generate_with_retry("prompt")

    assert result == "result"
    mock_generate.assert_called_once_with("prompt")


def test_retries_on_transient_error_then_succeeds() -> None:
    with (
        patch(
            "src.tools._llm.generate_text",
            side_effect=[RuntimeError("fail once"), "result"],
        ) as mock_generate,
        patch("time.sleep") as mock_sleep,
    ):
        result = _generate_with_retry("prompt")

    assert result == "result"
    assert mock_generate.call_count == 2
    mock_generate.assert_has_calls([call("prompt"), call("prompt")])
    mock_sleep.assert_called_once_with(1)


def test_raises_after_all_attempts_fail() -> None:
    with (
        patch(
            "src.tools._llm.generate_text",
            side_effect=RuntimeError("fail"),
        ) as mock_generate,
        patch("time.sleep"),
    ):
        with pytest.raises(RuntimeError, match="fail"):
            _generate_with_retry("prompt")

    assert mock_generate.call_count == 3


def test_custom_max_attempts() -> None:
    with (
        patch(
            "src.tools._llm.generate_text",
            side_effect=RuntimeError("fail"),
        ) as mock_generate,
        patch("time.sleep"),
    ):
        with pytest.raises(RuntimeError, match="fail"):
            _generate_with_retry("prompt", max_attempts=2)

    assert mock_generate.call_count == 2


def test_sleep_backoff_schedule() -> None:
    with (
        patch(
            "src.tools._llm.generate_text",
            side_effect=RuntimeError("fail"),
        ),
        patch("time.sleep") as mock_sleep,
    ):
        with pytest.raises(RuntimeError, match="fail"):
            _generate_with_retry("prompt", max_attempts=3)

    assert mock_sleep.call_args_list == [call(1), call(4)]


def test_invalid_max_attempts_raises_value_error() -> None:
    with pytest.raises(ValueError, match="max_attempts must be >= 1"):
        _generate_with_retry("prompt", max_attempts=0)

    with pytest.raises(ValueError, match="max_attempts must be >= 1"):
        _generate_with_retry("prompt", max_attempts=-1)
