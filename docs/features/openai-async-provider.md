# OpenAI Async Provider

> Async OpenAI-compatible streaming model provider introduced for Issue #159 and PR #168.

## Overview

Issue #159 adds `OpenAIAsyncProvider` in `src/infrastructure/providers/openai_async_provider.py`. The class implements the existing `ModelProvider` interface with `openai.AsyncOpenAI`, so Python-native orchestration code can await completions directly and consume streamed token deltas without blocking the event loop.

This change does not replace the existing synchronous `OpenAICompatibleProvider`. Both providers now coexist on purpose. The sync provider remains available for older service paths, while the async provider is the migration target for new Python-native orchestrator and TUI work.

## User Guide

Install the active Python dependencies before using the provider:

```bash
pip install -e .
```

`pyproject.toml` now includes `openai>=1.0.0`. That package is required because `OpenAIAsyncProvider` constructs an `openai.AsyncOpenAI` client.

### Basic Text Generation

```python
import asyncio

from domain.value_objects.model_config import ModelConfig
from infrastructure.providers.openai_async_provider import OpenAIAsyncProvider


async def main() -> None:
    provider = OpenAIAsyncProvider(base_url="http://127.0.0.1:1234/v1")
    model_config = ModelConfig(
        name="local-model",
        provider="openai_async",
    )

    text = await provider.generate_text(
        messages=[
            {"role": "user", "content": "Write one short sentence about stars."}
        ],
        model_config=model_config,
    )

    print(text)


asyncio.run(main())
```

### Streaming Token Deltas

```python
import asyncio

from domain.value_objects.model_config import ModelConfig
from infrastructure.providers.openai_async_provider import OpenAIAsyncProvider


async def main() -> None:
    provider = OpenAIAsyncProvider()
    model_config = ModelConfig(
        name="local-model",
        provider="openai_async",
    )

    async for chunk in provider.stream_text(
        messages=[
            {"role": "user", "content": "Reply with one short sentence about stars."}
        ],
        model_config=model_config,
    ):
        print(chunk, end="", flush=True)


asyncio.run(main())
```

### Constructor Defaults

| Argument | Default | Notes |
|----------|---------|-------|
| `base_url` | `LLM_API_BASE` or `http://127.0.0.1:1234/v1` | Normalised to include scheme and `/v1` when missing |
| `api_key` | `LLM_API_KEY` or `"lm-studio"` | Empty values are replaced with `"lm-studio"` because the OpenAI SDK rejects empty strings |
| `timeout` | `60.0` | Passed into `AsyncOpenAI` |
| `max_retries` | `3` | Passed into `AsyncOpenAI` |
| `context_length` | `16384` | Upper bound for generated `max_tokens` |
| `randomize_seed` | `True` | Adds a random offset unless `static_seed` is set in model parameters |

## Developer Guide

### Key Files

- `src/infrastructure/providers/openai_async_provider.py` — async provider implementation
- `src/infrastructure/providers/openai_compatible_provider.py` — existing synchronous provider left unchanged
- `tests/unit/test_openai_async_provider.py` — mocked provider unit tests
- `tests/integration/test_openai_async_provider_live.py` — live streaming smoke test

### Behaviour

- Uses `openai.AsyncOpenAI` for non-blocking `await` and async streaming calls
- Caches clients per normalised host in `_clients`, so host overrides reuse the same async client instance
- Normalises host overrides and constructor `base_url` values to an OpenAI-compatible `/v1` base URL
- Removes provider-specific request keys such as `num_ctx`, `keep_alive`, `think`, and `stream` before calling the OpenAI SDK
- Strips `<think>...</think>` output before returning text to callers
- Supports JSON generation through `response_format={"type": "json_object"}` and falls back to regex extraction when the model wraps JSON in extra text
- Wraps `APIConnectionError`, `APITimeoutError`, and `APIStatusError` as `ModelProviderError`
- Treats model download as server-managed; `download_model()` prints guidance instead of calling a vendor-specific API

### Relationship To The Sync Provider

| Provider | File | Transport | Current role |
|----------|------|-----------|--------------|
| `OpenAICompatibleProvider` | `src/infrastructure/providers/openai_compatible_provider.py` | `requests`-based HTTP calls | Existing synchronous path for older runtime code |
| `OpenAIAsyncProvider` | `src/infrastructure/providers/openai_async_provider.py` | `openai.AsyncOpenAI` | Async path for Python-native orchestration and streaming UI work |

Both classes implement `ModelProvider`, and both consume the same `ModelConfig` object. In current code, `ModelConfig.provider` still stays `openai_compatible`; the async class identifies itself separately through `get_supported_providers()` returning `openai_async`.

The async provider is currently a standalone infrastructure class. No provider factory or orchestration wiring in `src/` selects it automatically yet, so callers instantiate it directly for now.

## Testing

Run the mocked unit coverage:

```bash
pytest tests/unit/test_openai_async_provider.py -q
```

Run the live streaming smoke test against a reachable OpenAI-compatible endpoint:

```bash
LLM_API_BASE=http://127.0.0.1:1234/v1 \
TEST_OPENAI_ASYNC_MODEL=local-model \
pytest tests/integration/test_openai_async_provider_live.py -v -m integration
```

The live test asserts that streaming yields more than one chunk and that the combined response is non-empty. It does not use the `llm_available` skip fixture from the end-to-end integration suite, so run it only when the endpoint is up and the selected model is loaded.

## Related

- [Python-Native Foundation](./python-native-foundation.md)
- [Integration Tests](../testing/integration-tests.md)
- [PRD: Python-Native Orchestration and TUI](../planning/python-native-migration/prd.md)
- [ADR 006: Replace Ollama SDK with Generic OpenAI-Compatible REST Provider](../planning/adr/006-openai-compatible-provider.md)
- Issue #159 — Python-native migration [2/9]: Async streaming model provider (OpenAI-compatible)
- PR #168 — Python-native migration [2/9]: Async streaming model provider (OpenAI-compatible)