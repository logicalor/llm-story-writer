"""Application configuration settings."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
from domain.value_objects.model_config import ModelConfig
from domain.value_objects.generation_settings import GenerationSettings
from domain.exceptions import ConfigurationError


@dataclass
class AppConfig:
    """Main application configuration."""
    
    # Model configurations
    models: Dict[str, ModelConfig]
    
    # Generation settings
    generation: GenerationSettings
    
    # Paths
    output_dir: Path = Path("Stories")
    savepoint_dir: Path = Path("SavePoints")
    logs_dir: Path = Path("Logs")
    
    # Ollama settings
    ollama_host: str = "127.0.0.1:11434"
    ollama_context_length: int = 16384
    
    # API settings
    google_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    
    # Feature flags
    use_improved_recap_sanitizer: bool = True
    use_multi_stage_recap_sanitizer: bool = True
    
    def __post_init__(self):
        """Validate configuration."""
        # Ensure required models are present
        required_models = [
            "initial_outline_writer",
            "chapter_outline_writer", 
            "chapter_stage1_writer",
            "chapter_stage2_writer",
            "chapter_stage3_writer",
            "chapter_stage4_writer",
            "chapter_revision_writer",
            "revision_model",
            "eval_model",
            "info_model",
            "scrub_model",
            "checker_model",
            "translator_model"
        ]
        
        for model_name in required_models:
            if model_name not in self.models:
                raise ConfigurationError(f"Required model '{model_name}' not found in configuration")
        
        # Create directories if they don't exist
        self.output_dir.mkdir(exist_ok=True)
        self.savepoint_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
    
    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        """Create AppConfig from dictionary."""
        # Convert model strings to ModelConfig objects
        models = {}
        for name, model_string in data.get("models", {}).items():
            models[name] = ModelConfig.from_string(model_string)
        
        # Create generation settings
        generation = GenerationSettings.from_dict(data.get("generation", {}))
        
        # Convert paths
        output_dir = Path(data.get("output_dir", "Stories"))
        savepoint_dir = Path(data.get("savepoint_dir", "SavePoints"))
        logs_dir = Path(data.get("logs_dir", "Logs"))
        
        return cls(
            models=models,
            generation=generation,
            output_dir=output_dir,
            savepoint_dir=savepoint_dir,
            logs_dir=logs_dir,
            ollama_host=data.get("ollama_host", "127.0.0.1:11434"),
            ollama_context_length=data.get("ollama_context_length", 16384),
            google_api_key=data.get("google_api_key"),
            openrouter_api_key=data.get("openrouter_api_key"),
            use_improved_recap_sanitizer=data.get("use_improved_recap_sanitizer", True),
            use_multi_stage_recap_sanitizer=data.get("use_multi_stage_recap_sanitizer", True),
        )
    
    def to_dict(self) -> dict:
        """Convert AppConfig to dictionary."""
        return {
            "models": {name: str(model) for name, model in self.models.items()},
            "generation": self.generation.to_dict(),
            "output_dir": str(self.output_dir),
            "savepoint_dir": str(self.savepoint_dir),
            "logs_dir": str(self.logs_dir),
            "ollama_host": self.ollama_host,
            "ollama_context_length": self.ollama_context_length,
            "google_api_key": self.google_api_key,
            "openrouter_api_key": self.openrouter_api_key,
            "use_improved_recap_sanitizer": self.use_improved_recap_sanitizer,
            "use_multi_stage_recap_sanitizer": self.use_multi_stage_recap_sanitizer,
        }
    
    def get_model(self, name: str) -> ModelConfig:
        """Get a model configuration by name."""
        if name not in self.models:
            raise ConfigurationError(f"Model '{name}' not found in configuration")
        return self.models[name]
    
    def update_model(self, name: str, model: ModelConfig) -> None:
        """Update a model configuration."""
        self.models[name] = model
    
    def update_generation_settings(self, **kwargs) -> None:
        """Update generation settings."""
        self.generation = self.generation.with_updates(**kwargs) 