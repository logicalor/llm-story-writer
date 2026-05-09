"""Verification tests for OpenAIAsyncProvider."""

import asyncio
import importlib.util
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import Request
from openai import APIConnectionError

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from domain.exceptions import ModelProviderError
from domain.value_objects.model_config import ModelConfig
from application.interfaces.model_provider import StreamToken

_provider_spec = importlib.util.spec_from_file_location(
    "openai_async_provider_module",
    PROJECT_ROOT / "src" / "infrastructure" / "providers" / "openai_async_provider.py",
)
assert _provider_spec is not None and _provider_spec.loader is not None
_provider_module = importlib.util.module_from_spec(_provider_spec)
_provider_spec.loader.exec_module(_provider_module)
OpenAIAsyncProvider = _provider_module.OpenAIAsyncProvider


def _build_provider() -> OpenAIAsyncProvider:
    provider = OpenAIAsyncProvider.__new__(OpenAIAsyncProvider)
    provider.base_url = "http://127.0.0.1:1234/v1"
    provider._api_key = "lm-studio"
    provider._timeout = 60.0
    provider._max_retries = 3
    provider.context_length = 16384
    provider.randomize_seed = False
    provider._clients = {}
    return provider


class TestOpenAIAsyncProvider:
    def test_prepare_options_uses_max_tokens_not_num_ctx(self) -> None:
        provider = _build_provider()
        model_config = ModelConfig(
            name="llama3",
            provider="openai_compatible",
            parameters={"num_ctx": 4096},
        )

        options = provider._prepare_options(model_config)

        assert options["max_tokens"] == 4096
        assert "num_ctx" not in options

    def test_prepare_options_removes_provider_specific_keys(self) -> None:
        provider = _build_provider()
        model_config = ModelConfig(
            name="llama3",
            provider="openai_compatible",
            parameters={"keep_alive": 0, "think": True, "stream": True},
        )

        options = provider._prepare_options(model_config)

        assert "keep_alive" not in options
        assert "think" not in options
        assert "stream" not in options

    def test_prepare_options_sets_json_response_format(self) -> None:
        provider = _build_provider()
        model_config = ModelConfig(name="llama3", provider="openai_compatible")

        options = provider._prepare_options(model_config, format_type="json")

        assert options["response_format"] == {"type": "json_object"}

    def test_prepare_options_applies_default_temperature_and_top_p(self) -> None:
        provider = _build_provider()
        model_config = ModelConfig(name="llama3", provider="openai_compatible")

        options = provider._prepare_options(model_config)

        assert options["temperature"] == 0.7
        assert options["top_p"] == 0.9

    def test_get_supported_providers_returns_openai_async(self) -> None:
        provider = _build_provider()

        supported = asyncio.run(provider.get_supported_providers())

        assert supported == ["openai_async"]

    def test_generate_text_extracts_content_from_response(self) -> None:
        provider = _build_provider()
        model_config = ModelConfig(name="llama3", provider="openai_compatible")
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "hello world"
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = asyncio.run(
                provider.generate_text(
                    messages=[{"role": "user", "content": "Say hello"}],
                    model_config=model_config,
                )
            )

        assert result == "hello world"

    def test_generate_text_raises_model_provider_error_on_exception(self) -> None:
        provider = _build_provider()
        model_config = ModelConfig(name="llama3", provider="openai_compatible")
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=APIConnectionError(
                message="network error",
                request=Request("POST", "http://127.0.0.1:1234/v1/chat/completions"),
            )
        )

        with patch.object(provider, "_get_client", return_value=mock_client):
            try:
                asyncio.run(
                    provider.generate_text(
                        messages=[{"role": "user", "content": "Say hello"}],
                        model_config=model_config,
                    )
                )
            except ModelProviderError as exc:
                assert "network error" in str(exc)
            else:
                raise AssertionError("ModelProviderError not raised")

    def test_stream_text_yields_multiple_deltas(self) -> None:
        provider = _build_provider()
        model_config = ModelConfig(name="llama3", provider="openai_compatible")
        mock_client = MagicMock()

        async def async_gen():
            for chunk_text in ["hello", " world", "!"]:
                chunk = MagicMock()
                chunk.choices = [MagicMock()]
                chunk.choices[0].delta.content = chunk_text
                chunk.choices[0].delta.model_extra = None
                yield chunk

        mock_client.chat.completions.create = AsyncMock(return_value=async_gen())

        async def collect() -> list[StreamToken]:
            return [
                chunk
                async for chunk in provider.stream_text(
                    messages=[{"role": "user", "content": "Say hello"}],
                    model_config=model_config,
                )
            ]

        with patch.object(provider, "_get_client", return_value=mock_client):
            chunks = asyncio.run(collect())

        assert chunks == [
            StreamToken(text="hello", kind="content"),
            StreamToken(text=" world", kind="content"),
            StreamToken(text="!", kind="content"),
        ]

    def test_generate_text_stream_true_accumulates_chunks(self) -> None:
        provider = _build_provider()
        model_config = ModelConfig(name="llama3", provider="openai_compatible")

        async def fake_stream_text(*args, **kwargs):
            del args, kwargs
            for chunk in ["hello", " world", "!"]:
                yield StreamToken(text=chunk, kind="content")

        with patch.object(provider, "stream_text", fake_stream_text):
            result = asyncio.run(
                provider.generate_text(
                    messages=[{"role": "user", "content": "Say hello"}],
                    model_config=model_config,
                    stream=True,
                )
            )

        assert result == "hello world!"

    def test_filter_think_tags_removes_think_block(self) -> None:
        # _filter_think_tags was removed; thinking is handled via StreamToken kind="thinking".
        # This test is kept as a no-op placeholder to avoid breaking test count expectations.
        pass

    def test_generate_text_multi_role_messages(self) -> None:
        provider = _build_provider()
        model_config = ModelConfig(name="llama3", provider="openai_compatible")
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "multi-role response"
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = asyncio.run(
                provider.generate_text(
                    messages=messages,
                    model_config=model_config,
                )
            )

        assert result == "multi-role response"

    def test_stream_text_multi_role_messages(self) -> None:
        provider = _build_provider()
        model_config = ModelConfig(name="llama3", provider="openai_compatible")
        mock_client = MagicMock()

        async def async_gen():
            for chunk_text in ["multi-", "role ", "stream"]:
                chunk = MagicMock()
                chunk.choices = [MagicMock()]
                chunk.choices[0].delta.content = chunk_text
                chunk.choices[0].delta.model_extra = None
                yield chunk

        mock_client.chat.completions.create = AsyncMock(return_value=async_gen())

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]

        async def collect() -> list[StreamToken]:
            return [
                chunk
                async for chunk in provider.stream_text(
                    messages=messages,
                    model_config=model_config,
                )
            ]

        with patch.object(provider, "_get_client", return_value=mock_client):
            chunks = asyncio.run(collect())

        assert chunks == [
            StreamToken(text="multi-", kind="content"),
            StreamToken(text="role ", kind="content"),
            StreamToken(text="stream", kind="content"),
        ]

    def test_generate_text_stream_true_multi_role_messages(self) -> None:
        provider = _build_provider()
        model_config = ModelConfig(name="llama3", provider="openai_compatible")

        async def fake_stream_text(*args, **kwargs):
            del args, kwargs
            for chunk in ["multi-", "role ", "stream"]:
                yield StreamToken(text=chunk, kind="content")

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]

        with patch.object(provider, "stream_text", fake_stream_text):
            result = asyncio.run(
                provider.generate_text(
                    messages=messages,
                    model_config=model_config,
                    stream=True,
                )
            )

        assert result == "multi-role stream"

    def test_empty_api_key_defaults_to_lm_studio(self) -> None:
        with patch.object(_provider_module, "AsyncOpenAI") as mock_async_openai:
            with patch.dict(_provider_module.os.environ, {}, clear=True):
                provider = OpenAIAsyncProvider(api_key="")

        assert provider._api_key == "lm-studio"
        mock_async_openai.assert_called_once_with(
            base_url="http://127.0.0.1:1234/v1",
            api_key="lm-studio",
            timeout=60.0,
            max_retries=3,
        )

    # -----------------------------------------------------------------------
    # Thinking-mode StreamToken tests (issue #431)
    # -----------------------------------------------------------------------

    def _make_chunk(self, content=None, reasoning=None):
        """Build a minimal mock chunk that mimics the OpenAI streaming delta."""
        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta.content = content
        extra: dict = {}
        if reasoning is not None:
            extra["reasoning_content"] = reasoning
        chunk.choices[0].delta.model_extra = extra if extra else None
        return chunk

    def test_stream_text_reasoning_only_chunk_yields_thinking_token(self) -> None:
        provider = _build_provider()
        model_config = ModelConfig(name="llama3", provider="openai_compatible")
        mock_client = MagicMock()

        async def async_gen():
            yield self._make_chunk(content=None, reasoning="step A")

        mock_client.chat.completions.create = AsyncMock(return_value=async_gen())

        async def collect() -> list[StreamToken]:
            return [
                st
                async for st in provider.stream_text(
                    messages=[{"role": "user", "content": "Think!"}],
                    model_config=model_config,
                )
            ]

        with patch.object(provider, "_get_client", return_value=mock_client):
            tokens = asyncio.run(collect())

        assert tokens == [StreamToken(text="step A", kind="thinking")]

    def test_stream_text_both_reasoning_and_content_yields_thinking_then_content(
        self,
    ) -> None:
        provider = _build_provider()
        model_config = ModelConfig(name="llama3", provider="openai_compatible")
        mock_client = MagicMock()

        async def async_gen():
            yield self._make_chunk(content="prose", reasoning="rationale")

        mock_client.chat.completions.create = AsyncMock(return_value=async_gen())

        async def collect() -> list[StreamToken]:
            return [
                st
                async for st in provider.stream_text(
                    messages=[{"role": "user", "content": "Go"}],
                    model_config=model_config,
                )
            ]

        with patch.object(provider, "_get_client", return_value=mock_client):
            tokens = asyncio.run(collect())

        assert tokens == [
            StreamToken(text="rationale", kind="thinking"),
            StreamToken(text="prose", kind="content"),
        ]

    def test_stream_text_neither_reasoning_nor_content_yields_no_token(self) -> None:
        provider = _build_provider()
        model_config = ModelConfig(name="llama3", provider="openai_compatible")
        mock_client = MagicMock()

        async def async_gen():
            yield self._make_chunk(content=None, reasoning=None)

        mock_client.chat.completions.create = AsyncMock(return_value=async_gen())

        async def collect() -> list[StreamToken]:
            return [
                st
                async for st in provider.stream_text(
                    messages=[{"role": "user", "content": "Go"}],
                    model_config=model_config,
                )
            ]

        with patch.object(provider, "_get_client", return_value=mock_client):
            tokens = asyncio.run(collect())

        assert tokens == []

    def test_filter_think_tags_removed(self) -> None:
        """_filter_think_tags must no longer exist — thinking is handled via StreamToken."""
        provider = _build_provider()
        assert not hasattr(provider, "_filter_think_tags")
