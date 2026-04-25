"""Configuration loader for reading from config.yml."""

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict
from urllib.parse import urlparse, urlunparse

import yaml

from domain.exceptions import ConfigurationError

if TYPE_CHECKING:
    from domain.value_objects.generation_settings import GenerationSettings


def _normalize_model_api_base(value: str) -> str:
    """Normalize model API base to full URL with /v1 path."""
    candidate = value.strip()
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


class ConfigLoader:
    """Loads configuration from config.yml."""

    def __init__(self, config_file: str = "config.yml"):
        self.config_file = Path(config_file)

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from config.yml."""
        if not self.config_file.exists():
            raise ConfigurationError(
                f"Configuration file not found: {self.config_file}"
            )

        try:
            content = self.config_file.read_text(encoding="utf-8")
            config_data = yaml.safe_load(content)

            # Merge translation settings into generation settings
            if "translation" in config_data:
                translation = config_data["translation"]
                config_data["generation"].update(
                    {
                        "translate_language": translation.get("translate_language"),
                        "translate_prompt_language": translation.get(
                            "translate_prompt_language"
                        ),
                    }
                )
                del config_data["translation"]

            # Merge infrastructure settings with defaults
            if "infrastructure" in config_data:
                infrastructure = config_data["infrastructure"]
                model_api_base = infrastructure.get("model_api_base")

                config_data.update(
                    {
                        "output_dir": infrastructure.get("output_dir", "Stories"),
                        "savepoint_dir": infrastructure.get(
                            "savepoint_dir", "SavePoints"
                        ),
                        "logs_dir": infrastructure.get("logs_dir", "Logs"),
                        "model_api_base": _normalize_model_api_base(
                            model_api_base
                            or os.environ.get(
                                "LLM_API_BASE", "http://127.0.0.1:1234/v1"
                            )
                        ),
                        "context_length": infrastructure.get("context_length", 4096),
                        "randomize_seed": infrastructure.get("randomize_seed", True),
                        # RAG Configuration
                        "embedding_model": infrastructure.get(
                            "embedding_model", "openai-compat://nomic-embed-text"
                        ),
                        "vector_dimensions": infrastructure.get(
                            "vector_dimensions", 1536
                        ),
                        "similarity_threshold": infrastructure.get(
                            "similarity_threshold", 0.7
                        ),
                        "max_context_chunks": infrastructure.get(
                            "max_context_chunks", 20
                        ),
                        "max_chunk_size": infrastructure.get("max_chunk_size", 1000),
                        "overlap_size": infrastructure.get("overlap_size", 200),
                    }
                )
                del config_data["infrastructure"]

            config_data.pop("api_keys", None)

            return config_data

        except Exception as e:
            raise ConfigurationError(
                f"Failed to load configuration from {self.config_file}: {e}"
            ) from e

    def get_generation_settings(self) -> "GenerationSettings":
        """Get generation settings from config."""
        from domain.value_objects.generation_settings import GenerationSettings

        config = self.load_config()
        generation_data = config.get("generation", {})
        return GenerationSettings.from_dict(generation_data)
