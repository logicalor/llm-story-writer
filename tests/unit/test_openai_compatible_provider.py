"""Verification tests for OpenAI-compatible chat provider."""

import asyncio
import importlib.util
import sys
from pathlib import Path
from unittest.mock import Mock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from domain.exceptions import ModelProviderError
from domain.value_objects.model_config import ModelConfig

_provider_spec = importlib.util.spec_from_file_location(
    "openai_compatible_provider_module",
    PROJECT_ROOT
    / "src"
    / "infrastructure"
    / "providers"
    / "openai_compatible_provider.py",
)
assert _provider_spec is not None and _provider_spec.loader is not None
_provider_module = importlib.util.module_from_spec(_provider_spec)
_provider_spec.loader.exec_module(_provider_module)
OpenAICompatibleProvider = _provider_module.OpenAICompatibleProvider


def _build_provider() -> OpenAICompatibleProvider:
    provider = OpenAICompatibleProvider.__new__(OpenAICompatibleProvider)
    provider.base_url = "http://127.0.0.1:11434/v1"
    provider.context_length = 16384
    provider.randomize_seed = True
    provider.clients = {}
    return provider


class TestOpenAICompatibleProvider:
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

    def test_prepare_options_removes_ollama_specific_keys(self) -> None:
        provider = _build_provider()
        model_config = ModelConfig(
            name="llama3",
            provider="openai_compatible",
            parameters={"keep_alive": 0, "think": True},
        )

        options = provider._prepare_options(model_config)

        assert "keep_alive" not in options
        assert "think" not in options

    def test_prepare_options_sets_json_response_format(self) -> None:
        provider = _build_provider()
        model_config = ModelConfig(name="llama3", provider="openai_compatible")

        options = provider._prepare_options(model_config, format_type="json")

        assert options["response_format"] == {"type": "json_object"}

    def test_get_supported_providers_returns_expected(self) -> None:
        with patch.object(
            OpenAICompatibleProvider, "_ensure_requests_installed", return_value=None
        ):
            provider = OpenAICompatibleProvider()

        supported = asyncio.run(provider.get_supported_providers())

        assert "openai_compatible" in supported
        assert "ollama" in supported

    def test_make_request_posts_to_correct_endpoint(self) -> None:
        provider = _build_provider()
        model_config = ModelConfig(
            name="llama3",
            provider="openai_compatible",
            host="api.example.test:1234",
        )
        response = Mock()
        response.json.return_value = {"choices": []}

        with patch("requests.post", return_value=response) as mock_post:
            asyncio.run(provider._make_request({"model": "llama3"}, model_config))

        called_url = mock_post.call_args.args[0]
        assert called_url.endswith("/chat/completions")
        assert called_url == "http://api.example.test:1234/v1/chat/completions"

    def test_generate_text_extracts_content_from_choices(self) -> None:
        provider = _build_provider()
        model_config = ModelConfig(name="llama3", provider="openai_compatible")

        with patch.object(
            provider,
            "_make_request",
            return_value={"choices": [{"message": {"content": "hello world"}}]},
        ):
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

        with patch.object(
            provider,
            "_make_request",
            side_effect=Exception("network error"),
        ):
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
