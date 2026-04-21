"""Shared lightweight LLM client for tool scripts."""

from __future__ import annotations

import os
import re

import requests


def _get_api_base() -> str:
    """Return the OpenAI-compatible API base URL."""
    return os.environ.get("LLM_API_BASE", "http://127.0.0.1:1234/v1")


def _get_model() -> str:
    """Return the default model identifier."""
    return os.environ.get("LLM_MODEL", "huihui_ai/magistral-abliterated:24b")


def generate_text(
    prompt: str,
    *,
    system_message: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    """Call OpenAI-compatible chat completions API and return assistant content.

    Builds a messages list and delegates to :func:`generate_text_messages`.

    Raises ``RuntimeError`` on HTTP or API errors.
    """
    messages: list[dict[str, str]] = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    return generate_text_messages(
        messages, model=model, temperature=temperature, max_tokens=max_tokens
    )


def generate_text_messages(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    """Call OpenAI-compatible chat completions with a full message list.

    ``messages`` is a list of ``{"role": "...", "content": "..."}`` dicts.
    Returns the assistant response text.

    Raises ``RuntimeError`` on HTTP or API errors.
    """
    api_base = _get_api_base().rstrip("/")
    url = f"{api_base}/chat/completions"

    payload: dict[str, object] = {
        "model": model or _get_model(),
        "messages": messages,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    try:
        resp = requests.post(url, json=payload, timeout=600)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"LLM API request failed: {exc}") from exc

    try:
        data = resp.json()
    except ValueError as exc:
        raise RuntimeError(f"LLM API returned non-JSON response: {exc}") from exc

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected LLM API response structure: {exc}") from exc

    return _unwrap_output_tags(content)


_OUTPUT_TAG_RE = re.compile(
    r"<output>\s*(.*?)\s*</output>", re.DOTALL | re.IGNORECASE
)


def _unwrap_output_tags(text: str) -> str:
    """Strip surrounding ``<output>...</output>`` tags if present.

    Many prompt templates ask the model to wrap its response in ``<output>``
    tags. This helper extracts the inner content so savepoints store the
    actual payload rather than the tag wrapper. Text without the tags is
    returned unchanged.
    """
    if not isinstance(text, str):
        return text
    match = _OUTPUT_TAG_RE.search(text)
    if match is None:
        # Handle unclosed tag: strip a leading <output> opener
        stripped = re.sub(r"^\s*<output>\s*", "", text, count=1, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*</output>\s*$", "", stripped, count=1, flags=re.IGNORECASE)
        return stripped.strip() if stripped != text else text
    return match.group(1).strip()


def count_tokens(text: str) -> int:
    """Estimate token count using word-based approximation."""
    return int(len(text.split()) * 1.33)


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences from text and extract JSON content."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _extract_json_block(text: str) -> str:
    """Extract the first JSON object or array from text."""
    text = _strip_markdown_fences(text)

    # Find first { or [
    obj_idx = text.find("{")
    arr_idx = text.find("[")

    if obj_idx == -1 and arr_idx == -1:
        return text

    if obj_idx == -1:
        start = arr_idx
        open_char, close_char = "[", "]"
    elif arr_idx == -1:
        start = obj_idx
        open_char, close_char = "{", "}"
    elif arr_idx < obj_idx:
        start = arr_idx
        open_char, close_char = "[", "]"
    else:
        start = obj_idx
        open_char, close_char = "{", "}"

    # Find matching closing bracket
    depth = 0
    in_string = False
    escape_next = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == open_char:
            depth += 1
        elif ch == close_char:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    # Fallback — return from start to end
    return text[start:]
