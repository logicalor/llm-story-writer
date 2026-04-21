"""Verification tests for OpenAI-compatible embedding provider."""

import asyncio
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from domain.exceptions import ModelProviderError

_provider_spec = importlib.util.spec_from_file_location(
    "openai_compatible_embedding_provider_module",
    PROJECT_ROOT
    / "src"
    / "infrastructure"
    / "providers"
    / "openai_compatible_embedding_provider.py",
)
assert _provider_spec is not None and _provider_spec.loader is not None
_provider_module = importlib.util.module_from_spec(_provider_spec)
_provider_spec.loader.exec_module(_provider_module)
OpenAICompatibleEmbeddingProvider = _provider_module.OpenAICompatibleEmbeddingProvider


class _FakeResponse:
    def __init__(self, status: int = 200, json_data: dict | None = None) -> None:
        self.status = status
        self._json_data = json_data or {"data": [{"embedding": [0.1, 0.2, 0.3]}]}

    async def __aenter__(self) -> "_FakeResponse":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def json(self) -> dict:
        return self._json_data

    async def text(self) -> str:
        return "error"


class _FakeSession:
    def __init__(self, response: _FakeResponse, captured: dict[str, object]) -> None:
        self._response = response
        self._captured = captured

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def post(self, url: str, json: dict[str, object]) -> _FakeResponse:
        self._captured["url"] = url
        self._captured["json"] = json
        return self._response

    def get(self, url: str) -> _FakeResponse:
        self._captured["url"] = url
        return self._response


class _RaisingSession:
    async def __aenter__(self) -> "_RaisingSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def post(self, url: str, json: dict[str, object]) -> _FakeResponse:
        raise Exception("api failure")


class TestOpenAICompatibleEmbeddingProvider:
    def test_get_single_embedding_uses_v1_embeddings_endpoint(self) -> None:
        provider = OpenAICompatibleEmbeddingProvider()
        captured: dict[str, object] = {}

        with patch(
            "aiohttp.ClientSession",
            return_value=_FakeSession(_FakeResponse(), captured),
        ):
            asyncio.run(provider.get_single_embedding("hello"))

        assert "/v1/embeddings" in str(captured["url"])

    def test_get_single_embedding_uses_input_key_not_prompt(self) -> None:
        provider = OpenAICompatibleEmbeddingProvider()
        captured: dict[str, object] = {}

        with patch(
            "aiohttp.ClientSession",
            return_value=_FakeSession(_FakeResponse(), captured),
        ):
            asyncio.run(provider.get_single_embedding("hello"))

        payload = captured["json"]
        assert isinstance(payload, dict)
        assert payload["input"] == "hello"
        assert "prompt" not in payload

    def test_get_single_embedding_parses_data_array_response(self) -> None:
        provider = OpenAICompatibleEmbeddingProvider()
        response = _FakeResponse(json_data={"data": [{"embedding": [0.1, 0.2, 0.3]}]})

        with patch(
            "aiohttp.ClientSession",
            return_value=_FakeSession(response, {}),
        ):
            embedding = asyncio.run(provider.get_single_embedding("hello"))

        assert embedding == [0.1, 0.2, 0.3]

    def test_test_connection_calls_v1_models(self) -> None:
        provider = OpenAICompatibleEmbeddingProvider()
        captured: dict[str, object] = {}

        with patch(
            "aiohttp.ClientSession",
            return_value=_FakeSession(_FakeResponse(), captured),
        ):
            connected = asyncio.run(provider.test_connection())

        assert connected is True
        assert str(captured["url"]).endswith("/v1/models")

    def test_base_url_constructed_correctly(self) -> None:
        provider = OpenAICompatibleEmbeddingProvider(
            base_url="http://127.0.0.1:1234/v1"
        )

        assert provider.base_url == "http://127.0.0.1:1234/v1"

    def test_get_embeddings_raises_on_api_failure(self) -> None:
        provider = OpenAICompatibleEmbeddingProvider()

        with patch("aiohttp.ClientSession", return_value=_RaisingSession()):
            try:
                asyncio.run(provider.get_embeddings(["test text"]))
            except ModelProviderError as exc:
                assert "api failure" in str(exc)
            else:
                raise AssertionError("ModelProviderError not raised")

    def test_get_single_embedding_raises_on_non_200(self) -> None:
        provider = OpenAICompatibleEmbeddingProvider()
        response = _FakeResponse(status=500)

        with patch(
            "aiohttp.ClientSession",
            return_value=_FakeSession(response, {}),
        ):
            try:
                asyncio.run(provider._get_single_embedding("test text"))
            except ModelProviderError as exc:
                assert "500" in str(exc)
            else:
                raise AssertionError("ModelProviderError not raised")
