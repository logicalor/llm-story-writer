"""Integration tests for OpenAIAsyncProvider — require live LM Studio."""

import asyncio
import importlib.util
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from domain.value_objects.model_config import ModelConfig

_provider_spec = importlib.util.spec_from_file_location(
    "openai_async_provider_module_live",
    PROJECT_ROOT / "src" / "infrastructure" / "providers" / "openai_async_provider.py",
)
assert _provider_spec is not None and _provider_spec.loader is not None
_provider_module = importlib.util.module_from_spec(_provider_spec)
_provider_spec.loader.exec_module(_provider_module)
OpenAIAsyncProvider = _provider_module.OpenAIAsyncProvider


@pytest.mark.integration
class TestOpenAIAsyncProviderLive:
    def test_streams_live_yields_multiple_chunks(self, llm_available: str) -> None:
        provider = OpenAIAsyncProvider(
            base_url=llm_available,
            api_key=os.environ.get("LLM_API_KEY"),
        )
        model_config = ModelConfig(
            name=os.environ.get("TEST_OPENAI_ASYNC_MODEL")
            or os.environ.get("LLM_MODEL")
            or "local-model",
            provider="openai_compatible",
        )

        async def collect() -> list[str]:
            return [
                chunk
                async for chunk in provider.stream_text(
                    messages=[
                        {
                            "role": "user",
                            "content": "Reply with one short sentence about stars.",
                        }
                    ],
                    model_config=model_config,
                )
            ]

        chunks = asyncio.run(collect())

        assert len(chunks) > 1
        assert "".join(chunks).strip()
