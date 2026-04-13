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
    assert _get_api_base() == "http://localhost:11434/v1"
    assert _get_model() == "huihui_ai/magistral-abliterated:24b"
