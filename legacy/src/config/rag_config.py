"""RAG configuration loader."""

from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from config.config_loader import ConfigLoader


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
    
    # Content chunking configuration
    max_chunk_size: int = 1000
    overlap_size: int = 200
    
    @property
    def connection_string(self) -> str:
        """Get the PostgreSQL connection string."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}/{self.postgres_database}"
    
    @property
    def ollama_host(self) -> str:
        """Extract Ollama host from embedding model string."""
        if self.embedding_model.startswith("ollama://"):
            # Format: ollama://host:port/model_name or ollama://model_name
            parts = self.embedding_model.split("/")
            if len(parts) >= 3:
                # Check if the third part contains a colon (host:port)
                if ":" in parts[2]:
                    return parts[2]  # host:port part
                else:
                    return "127.0.0.1:11434"  # Default host
        return "127.0.0.1:11434"  # Default
    
    @property
    def embedding_model_name(self) -> str:
        """Extract the actual model name from the embedding model string."""
        if self.embedding_model.startswith("ollama://"):
            # Format: ollama://host:port/model_name or ollama://model_name
            parts = self.embedding_model.split("/")
            if len(parts) >= 3:
                # Check if the third part contains a colon (host:port)
                if ":" in parts[2]:
                    # Format: ollama://host:port/model_name
                    if len(parts) >= 4:
                        return parts[3]  # model_name part
                else:
                    # Format: ollama://model_name
                    return parts[2]  # model_name part
        return "nomic-embed-text"  # Default


class RAGConfigLoader:
    """Loader for RAG configuration from config.md."""
    
    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader
    
    def load_rag_config(self) -> RAGConfig:
        """Load RAG configuration from the main config."""
        config = self.config_loader.load_config()
        
        infrastructure = config.get("infrastructure", {})
        
        return RAGConfig(
            postgres_host=infrastructure.get("postgres_host", "localhost:5432"),
            postgres_database=infrastructure.get("postgres_database", "story_writer"),
            postgres_user=infrastructure.get("postgres_user", "story_user"),
            postgres_password=infrastructure.get("postgres_password", "story_pass"),
            embedding_model=infrastructure.get("embedding_model", "ollama://nomic-embed-text"),
            vector_dimensions=infrastructure.get("vector_dimensions", 1536),
            similarity_threshold=infrastructure.get("similarity_threshold", 0.7),
            max_context_chunks=infrastructure.get("max_context_chunks", 20),
            max_chunk_size=infrastructure.get("max_chunk_size", 1000),
            overlap_size=infrastructure.get("overlap_size", 200)
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
