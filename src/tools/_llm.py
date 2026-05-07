"""Shared lightweight LLM client for tool scripts."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

import requests


def _get_api_base() -> str:
    """Return the OpenAI-compatible API base URL."""
    return os.environ.get("LLM_API_BASE", "http://127.0.0.1:1234/v1")


def _get_model() -> str:
    """Return the default model identifier."""
    return os.environ.get("LLM_MODEL", "gemma-4-26b-a4b-it-heretic-guff")


def _append_debug_log(
    messages: list[dict[str, str]],
    model: str,
    response: str,
    *,
    temperature: float | None,
    max_tokens: int | None,
) -> None:
    """Append one JSONL record to the debug log file if LLM_DEBUG_LOG is set."""
    log_path = os.environ.get("LLM_DEBUG_LOG")
    if not log_path:
        return
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": messages,
        "response": response,
    }
    try:
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass  # Never let logging failures break generation


def generate_text(
    prompt: str,
    *,
    system_message: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    base_url: str | None = None,
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
        messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        base_url=base_url,
    )


def generate_text_messages(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    base_url: str | None = None,
) -> str:
    """Call OpenAI-compatible chat completions with a full message list.

    ``messages`` is a list of ``{"role": "...", "content": "..."}`` dicts.
    Returns the assistant response text.

    Raises ``RuntimeError`` on HTTP or API errors.
    """
    api_base = (
        base_url.rstrip("/") if base_url is not None else _get_api_base().rstrip("/")
    )
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

    content = _unwrap_output_tags(content)
    _append_debug_log(
        messages,
        str(payload["model"]),
        content,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return content


_OUTPUT_TAG_RE = re.compile(r"<output>\s*(.*?)\s*</output>", re.DOTALL | re.IGNORECASE)


def _unwrap_output_tags(text: str) -> str:
    """Strip ``<output>...</output>`` wrapper, returning the **last** block.

    Many prompt templates ask the model to wrap its response in ``<output>``
    tags. Reasoning / instruction-tuned models frequently emit multiple
    ``<output>`` blocks per turn: an early planning/scaffolding block (often
    containing a schema with ``[placeholder]`` markers) followed by the real
    final answer. The last block is the conventional "final answer" slot, so
    we extract that rather than the first match. Text without any tags is
    returned unchanged.
    """
    if not isinstance(text, str):
        return text
    matches = _OUTPUT_TAG_RE.findall(text)
    if not matches:
        # Handle unclosed tag: strip a leading <output> opener
        stripped = re.sub(r"^\s*<output>\s*", "", text, count=1, flags=re.IGNORECASE)
        stripped = re.sub(
            r"\s*</output>\s*$", "", stripped, count=1, flags=re.IGNORECASE
        )
        return stripped.strip() if stripped != text else text
    # Prefer the last non-empty block; fall back to the last block if all empty.
    for candidate in reversed(matches):
        stripped = candidate.strip()
        if stripped:
            return stripped
    return matches[-1].strip()


def count_tokens(text: str) -> int:
    """Estimate token count using word-based approximation."""
    return int(len(text.split()) * 1.33)


def extract_paragraph_tail(text: str, token_budget: int = 350) -> str:
    """Return the last N full paragraphs of *text* that fit within *token_budget*.

        Paragraphs are split on double-newline.  Walking backwards from the final
    paragraph, paragraphs are accumulated until the running token count would
        exceed *token_budget*.  A token is approximated as ``chars / 4``
    (consistent with the rest of the codebase).

    Rules:
    - If the entire text fits in the budget, the full text is returned.
    - If only one paragraph exists, that paragraph is returned regardless of length.
        - The returned string never has a leading ``…`` prefix (paragraph-boundary
      alignment makes it unnecessary).
    """
    if not text:
        return text
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return text

    accumulated: list[str] = []
    char_budget = token_budget * 4  # approximate: 1 token ≈ 4 chars

    for para in reversed(paragraphs):
        candidate = "\n\n".join([para] + accumulated)
        if len(candidate) > char_budget and accumulated:
            # Adding this paragraph would exceed the budget and we already
            # have at least one paragraph — stop here.
            break
        accumulated.insert(0, para)

    return "\n\n".join(accumulated)


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
