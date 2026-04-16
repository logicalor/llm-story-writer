"""RAG configuration loader."""

from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import urlparse, urlunparse

from config.config_loader import ConfigLoader


def _normalize_model_api_base(value: str) -> str:
    """Normalize model API base to full URL with /v1 path."""
    parsed = urlparse(value if "://" in value else f"http://{value}")
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


def _parse_embedding_model_uri(embedding_model: str) -> Tuple[Optional[str], str]:
    """Parse embedding model URI into optional host and model name."""
    for scheme in ("openai-compat://", "ollama://"):
        if embedding_model.startswith(scheme):
            remainder = embedding_model[len(scheme) :]
            if "/" in remainder:
                candidate_host, model_name = remainder.split("/", 1)
                if ":" in candidate_host:
                    return candidate_host, model_name
            return None, remainder

    return None, embedding_model


@dataclass
class RAGConfig:
    """Configuration for the RAG system."""

    # PostgreSQL configuration
    postgres_host: str
    postgres_database: str
    postgres_user: str
    postgres_password: str

    # Embedding configuration
    embedding_model: str
    vector_dimensions: int
    similarity_threshold: float
    max_context_chunks: int
    configured_model_api_base: Optional[str] = None

    # Content chunking configuration
    max_chunk_size: int = 1000
    overlap_size: int = 200

    @property
    def connection_string(self) -> str:
        """Get the PostgreSQL connection string."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}/{self.postgres_database}"

    @property
    def model_api_base(self) -> str:
        """Extract model API base from config or embedding model string."""
        if self.configured_model_api_base:
            return _normalize_model_api_base(self.configured_model_api_base)

        host, _ = _parse_embedding_model_uri(self.embedding_model)
        return _normalize_model_api_base(host or "127.0.0.1:11434")

    @property
    def embedding_model_name(self) -> str:
        """Extract the actual model name from the embedding model string."""
        _, model_name = _parse_embedding_model_uri(self.embedding_model)
        return model_name or "nomic-embed-text"


class RAGConfigLoader:
    """Loader for RAG configuration from config.md."""

    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader

    def load_rag_config(self) -> RAGConfig:
        """Load RAG configuration from the main config."""
        config = self.config_loader.load_config()

        return RAGConfig(
            postgres_host=config.get("postgres_host", "localhost:5432"),
            postgres_database=config.get("postgres_database", "story_writer"),
            postgres_user=config.get("postgres_user", "story_user"),
            postgres_password=config.get("postgres_password", "story_pass"),
            embedding_model=config.get(
                "embedding_model", "openai-compat://nomic-embed-text"
            ),
            vector_dimensions=config.get("vector_dimensions", 1536),
            similarity_threshold=config.get("similarity_threshold", 0.7),
            max_context_chunks=config.get("max_context_chunks", 20),
            configured_model_api_base=config.get(
                "model_api_base", config.get("ollama_host")
            ),
            max_chunk_size=config.get("max_chunk_size", 1000),
            overlap_size=config.get("overlap_size", 200),
        )

    def validate_config(self, rag_config: RAGConfig) -> list:
        """Validate RAG configuration and return any errors."""
        errors = []

        # Check PostgreSQL configuration
        if not rag_config.postgres_host:
            errors.append("postgres_host is required")

        if not rag_config.postgres_database:
            errors.append("postgres_database is required")

        if not rag_config.postgres_user:
            errors.append("postgres_user is required")

        if not rag_config.postgres_password:
            errors.append("postgres_password is required")

        # Check embedding configuration
        if not rag_config.embedding_model:
            errors.append("embedding_model is required")

        if rag_config.vector_dimensions <= 0:
            errors.append("vector_dimensions must be positive")

        if not (0.0 <= rag_config.similarity_threshold <= 1.0):
            errors.append("similarity_threshold must be between 0.0 and 1.0")

        if rag_config.max_context_chunks <= 0:
            errors.append("max_context_chunks must be positive")

        # Check chunking configuration
        if rag_config.max_chunk_size <= 0:
            errors.append("max_chunk_size must be positive")

        if rag_config.overlap_size < 0:
            errors.append("overlap_size must be non-negative")

        if rag_config.overlap_size >= rag_config.max_chunk_size:
            errors.append("overlap_size must be less than max_chunk_size")

        return errors
