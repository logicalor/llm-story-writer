"""Verification tests for _llm.py shared LLM client module.

Tests JSON extraction helpers and default config — no LLM server needed.
"""

import pytest

from src.tools._llm import _extract_json_block, _get_api_base, _get_model


def test_extract_json_from_plain() -> None:
    """_extract_json_block with plain JSON string."""
    raw = '{"key": "value", "num": 42}'
    result = _extract_json_block(raw)
    assert result == '{"key": "value", "num": 42}'


def test_extract_json_from_markdown_fenced() -> None:
    """JSON wrapped in ```json ... ``` fences."""
    raw = '```json\n{"status": "ok"}\n```'
    result = _extract_json_block(raw)
    import json

    parsed = json.loads(result)
    assert parsed == {"status": "ok"}


def test_extract_json_from_text_with_json() -> None:
    """JSON embedded in surrounding text."""
    raw = 'Here is the result:\n{"answer": 42}\nHope that helps!'
    result = _extract_json_block(raw)
    import json

    parsed = json.loads(result)
    assert parsed == {"answer": 42}


def test_extract_json_invalid_raises() -> None:
    """Invalid JSON (no object/array) returns text as-is; json.loads raises."""
    import json

    raw = "this is not json at all"
    result = _extract_json_block(raw)
    with pytest.raises(json.JSONDecodeError):
        json.loads(result)


def test_generate_text_missing_api_base(monkeypatch: pytest.MonkeyPatch) -> None:
    """Appropriate error when LLM_API_BASE points to unreachable server."""
    from src.tools._llm import generate_text

    monkeypatch.setenv("LLM_API_BASE", "http://127.0.0.1:1")
    with pytest.raises(RuntimeError, match="LLM API request failed"):
        generate_text("test prompt")


def test_generate_text_messages_missing_api_base(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """generate_text_messages raises RuntimeError when API unreachable."""
    from src.tools._llm import generate_text_messages

    monkeypatch.setenv("LLM_API_BASE", "http://127.0.0.1:1")
    with pytest.raises(RuntimeError, match="LLM API request failed"):
        generate_text_messages([{"role": "user", "content": "test"}])


def test_generate_text_delegates_to_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """generate_text() builds correct messages list and delegates."""
    from src.tools._llm import generate_text

    captured: list[list[dict[str, str]]] = []

    def fake_generate_text_messages(
        messages: list[dict[str, str]], **kwargs: object
    ) -> str:
        captured.append(messages)
        return "ok"

    monkeypatch.setattr(
        "src.tools._llm.generate_text_messages", fake_generate_text_messages
    )

    # Without system_message
    generate_text("test")
    assert captured[-1] == [{"role": "user", "content": "test"}]

    # With system_message
    generate_text("test", system_message="sys")
    assert captured[-1] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "test"},
    ]


def test_default_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify default LLM_API_BASE and LLM_MODEL values."""
    monkeypatch.delenv("LLM_API_BASE", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    assert _get_api_base() == "http://127.0.0.1:1234/v1"
    assert _get_model() == "gemma-4-26b-a4b-it-heretic-guff"


def test_debug_log_written(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    """LLM_DEBUG_LOG causes a JSONL record to be appended after each call."""
    import json as _json

    from src.tools._llm import generate_text_messages

    log_file = tmp_path / "llm_debug.jsonl"
    monkeypatch.setenv("LLM_DEBUG_LOG", str(log_file))

    messages = [{"role": "user", "content": "hello"}]
    response_text = "world"

    # Fake the HTTP call so we never need a real server
    import unittest.mock as mock

    fake_resp = mock.MagicMock()
    fake_resp.json.return_value = {
        "choices": [{"message": {"content": response_text}}]
    }
    fake_resp.raise_for_status.return_value = None

    with mock.patch("src.tools._llm.requests.post", return_value=fake_resp):
        result = generate_text_messages(messages, model="test-model")

    assert result == response_text
    assert log_file.exists()
    record = _json.loads(log_file.read_text())
    assert record["model"] == "test-model"
    assert record["messages"] == messages
    assert record["response"] == response_text
    assert "timestamp" in record


def test_debug_log_not_written_when_unset(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    """No log file is created when LLM_DEBUG_LOG is not set."""
    import unittest.mock as mock

    from src.tools._llm import generate_text_messages

    monkeypatch.delenv("LLM_DEBUG_LOG", raising=False)
    log_file = tmp_path / "should_not_exist.jsonl"

    fake_resp = mock.MagicMock()
    fake_resp.json.return_value = {
        "choices": [{"message": {"content": "hi"}}]
    }
    fake_resp.raise_for_status.return_value = None

    with mock.patch("src.tools._llm.requests.post", return_value=fake_resp):
        generate_text_messages([{"role": "user", "content": "ping"}])

    assert not log_file.exists()
