"""Backward compatibility alias for the OpenAI-compatible embedding provider."""

from .openai_compatible_embedding_provider import (
    OpenAICompatibleEmbeddingProvider as OllamaEmbeddingProvider,
)

__all__ = ["OllamaEmbeddingProvider"]
