"""OpenAI-compatible embedding provider implementation."""

import logging
import os
import re
from typing import List, Optional
from urllib.parse import urlparse, urlunparse

import aiohttp

from domain.exceptions import ModelProviderError

logger = logging.getLogger(__name__)


def _normalize_base_url(base_url: str) -> str:
    """Normalize model API base URL to include scheme and /v1 path."""
    candidate = base_url.strip()
    if not re.match(r"^https?://", candidate):
        candidate = f"http://{candidate}"

    parsed = urlparse(candidate)
    path = parsed.path.rstrip("/")
    if path in ("", "/"):
        path = "/v1"

    return urlunparse(
        (
            parsed.scheme or "http",
            parsed.netloc,
            path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    ).rstrip("/")


class OpenAICompatibleEmbeddingProvider:
    """OpenAI-compatible embedding provider for generating text embeddings."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: str = "nomic-embed-text",
        host: Optional[str] = None,
    ):
        if base_url is None:
            base_url = os.environ.get("LLM_API_BASE", "http://127.0.0.1:1234/v1")
        if host:
            base_url = f"http://{host}/v1"

        self.base_url = _normalize_base_url(base_url)
        self.model = model

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        if not texts:
            return []

        embeddings = []
        for i, text in enumerate(texts):
            try:
                embeddings.append(await self._get_single_embedding(text))
            except Exception as exc:
                raise ModelProviderError(
                    f"Failed to generate embedding for text at index {i}: {exc}"
                ) from exc

        return embeddings

    async def get_single_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        return (await self.get_embeddings([text]))[0]

    async def _get_single_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text using OpenAI-compatible API."""
        payload = {"model": self.model, "input": text}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/embeddings", json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ModelProviderError(
                        f"OpenAI-compatible embedding API error: {response.status} - {error_text}"
                    )

                result = await response.json()
                data = result.get("data")
                if not isinstance(data, list) or not data:
                    raise ModelProviderError(
                        "No embedding data returned from OpenAI-compatible API"
                    )

                embedding = data[0].get("embedding")
                if not isinstance(embedding, list):
                    raise ModelProviderError(
                        "No embedding returned from OpenAI-compatible API"
                    )

                return embedding

    async def test_connection(self) -> bool:
        """Test if the model API server is accessible."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/models") as response:
                    return response.status == 200
        except Exception as exc:
            logger.error(f"Connection test failed: {exc}")
            return False

    async def get_model_info(self) -> Optional[dict]:
        """Get information about the embedding model."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/models/{self.model}"
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    return None
        except Exception as exc:
            logger.error(f"Failed to get model info: {exc}")
            return None
