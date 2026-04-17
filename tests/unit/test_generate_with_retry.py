"""Unit tests for _generate_with_retry helper in integration fixture."""

from __future__ import annotations

from unittest.mock import call, patch

import pytest

from tests.integration.test_e2e_opencode import _generate_with_retry


def test_success_on_first_attempt() -> None:
    with patch(
        "tests.integration.test_e2e_opencode.generate_text",
        return_value="result",
    ) as mock_generate:
        result = _generate_with_retry("prompt")

    assert result == "result"
    mock_generate.assert_called_once_with("prompt")


def test_retries_on_transient_error_then_succeeds() -> None:
    with (
        patch(
            "tests.integration.test_e2e_opencode.generate_text",
            side_effect=[RuntimeError("fail once"), "result"],
        ) as mock_generate,
        patch("tests.integration.test_e2e_opencode.time.sleep") as mock_sleep,
    ):
        result = _generate_with_retry("prompt")

    assert result == "result"
    assert mock_generate.call_count == 2
    mock_generate.assert_has_calls([call("prompt"), call("prompt")])
    mock_sleep.assert_called_once_with(1)


def test_raises_after_all_attempts_fail() -> None:
    with (
        patch(
            "tests.integration.test_e2e_opencode.generate_text",
            side_effect=RuntimeError("fail"),
        ) as mock_generate,
        patch("tests.integration.test_e2e_opencode.time.sleep"),
    ):
        with pytest.raises(RuntimeError, match="fail"):
            _generate_with_retry("prompt")

    assert mock_generate.call_count == 3


def test_custom_max_attempts() -> None:
    with (
        patch(
            "tests.integration.test_e2e_opencode.generate_text",
            side_effect=RuntimeError("fail"),
        ) as mock_generate,
        patch("tests.integration.test_e2e_opencode.time.sleep"),
    ):
        with pytest.raises(RuntimeError, match="fail"):
            _generate_with_retry("prompt", max_attempts=2)

    assert mock_generate.call_count == 2


def test_sleep_backoff_schedule() -> None:
    with (
        patch(
            "tests.integration.test_e2e_opencode.generate_text",
            side_effect=RuntimeError("fail"),
        ),
        patch("tests.integration.test_e2e_opencode.time.sleep") as mock_sleep,
    ):
        with pytest.raises(RuntimeError, match="fail"):
            _generate_with_retry("prompt", max_attempts=3)

    assert mock_sleep.call_args_list == [call(1), call(4)]
