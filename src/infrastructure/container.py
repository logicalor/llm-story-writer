"""Dependency injection container."""

from dependency_injector import containers, providers
from pathlib import Path
from typing import Dict

from config.settings import AppConfig
from application.services.story_generation_service import StoryGenerationService
from application.strategies.strategy_factory import StrategyFactory
from .providers.ollama_provider import OllamaProvider
from .storage.file_storage import FileStorage
from .storage.savepoint_repository import FilesystemSavepointRepository
from .logging.structured_logger import StructuredLogger, LogLevel
from .prompts.prompt_loader import PromptLoader


class Container(containers.DeclarativeContainer):
    """Application dependency injection container."""
    
    # Configuration
    config = providers.Configuration()
    
    # Store the actual AppConfig object
    app_config = providers.Configuration()
    
    # Infrastructure
    logger = providers.Singleton(
        StructuredLogger,
        log_file=providers.Callable(lambda logs_dir: Path(logs_dir) / "app.log", config.logs_dir),
        level=LogLevel.INFO,
        enable_console=True
    )
    
    prompt_loader = providers.Singleton(
        PromptLoader,
        prompts_dir="src/prompts"
    )
    
    ollama_provider = providers.Singleton(
        OllamaProvider,
        host=config.ollama_host
    )
    
    file_storage = providers.Singleton(
        FileStorage,
        base_path=providers.Callable(lambda output_dir: Path(output_dir), config.output_dir)
    )
    
    savepoint_repository = providers.Singleton(
        FilesystemSavepointRepository,
        base_path=providers.Callable(lambda savepoint_dir: Path(savepoint_dir), config.savepoint_dir)
    )
    
    # Strategy factory
    strategy_factory = providers.Singleton(StrategyFactory)
    
    # Strategy (created dynamically based on config)
    strategy = providers.Factory(
        lambda factory, model_provider, app_config, savepoint_repo: 
        factory.create_strategy_with_prompts(app_config.generation.strategy, model_provider, app_config, savepoint_repo),
        factory=strategy_factory,
        model_provider=ollama_provider,
        app_config=app_config,
        savepoint_repo=savepoint_repository
    )
    
    # Application services
    story_generation_service = providers.Factory(
        StoryGenerationService,
        strategy=strategy,
        model_provider=ollama_provider,
        storage=file_storage,
        savepoint_repo=savepoint_repository
    )
    
    @classmethod
    def create_from_config(cls, app_config: AppConfig) -> "Container":
        """Create container from application config."""
        container = cls()
        
        # Set configuration values
        container.config.from_dict(app_config.to_dict())
        container.app_config.override(providers.Object(app_config))
        
        # Override providers with config-specific settings
        container.ollama_provider.override(
            providers.Singleton(
                OllamaProvider,
                host=app_config.ollama_host
            )
        )
        
        container.file_storage.override(
            providers.Singleton(
                FileStorage,
                base_path=app_config.output_dir
            )
        )
        
        container.savepoint_repository.override(
            providers.Singleton(
                FilesystemSavepointRepository,
                base_path=app_config.savepoint_dir
            )
        )
        
        return container
    
    def wire_modules(self, *modules):
        """Wire modules to the container."""
        for module in modules:
            self.wire(modules=[module])
    
    def get_model_provider(self, provider_name: str):
        """Get model provider by name."""
        if provider_name == "ollama":
            return self.ollama_provider()
        else:
            raise ValueError(f"Unknown model provider: {provider_name}")
    
    def get_generation_settings(self):
        """Get generation settings from config."""
        return self.app_config().generation 