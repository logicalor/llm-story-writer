"""Dependency injection container."""

from dependency_injector import containers, providers
from pathlib import Path
from typing import Dict, Any

from application.services.story_generation_service import StoryGenerationService
from application.strategies.strategy_factory import StrategyFactory
from .providers.ollama_provider import OllamaProvider
from .providers.lm_studio_provider import LMStudioProvider
from .providers.langchain_provider import LangChainProvider
from .providers.llama_cpp_provider import LlamaCppProvider
from .storage.file_storage import FileStorage
from .storage.savepoint_repository import FilesystemSavepointRepository
from .logging.structured_logger import StructuredLogger, LogLevel
from .prompts.prompt_loader import PromptLoader


class Container(containers.DeclarativeContainer):
    """Application dependency injection container."""
    
    # Configuration
    config = providers.Configuration()
    
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
        host=config.ollama_host,
        context_length=config.context_length,
        randomize_seed=config.randomize_seed
    )
    
    lm_studio_provider = providers.Singleton(
        LMStudioProvider,
        host=config.lm_studio_host,
        context_length=config.context_length,
        randomize_seed=config.randomize_seed
    )
    
    langchain_provider = providers.Singleton(
        LangChainProvider,
        api_keys=config.api_keys,
        context_length=config.context_length,
        randomize_seed=config.randomize_seed
    )
    
    llama_cpp_provider = providers.Singleton(
        LlamaCppProvider,
        host=config.llama_cpp_host,
        context_length=config.context_length,
        randomize_seed=config.randomize_seed
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
        lambda factory, model_provider, config, savepoint_repo: 
        factory.create_strategy_with_prompts(config.get('generation', {}).get('strategy', 'outline-chapter'), model_provider, config, savepoint_repo),
        factory=strategy_factory,
        model_provider=ollama_provider,
        config=config,
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
    def create_from_config(cls, config_data: Dict[str, Any]) -> "Container":
        """Create container from configuration data."""
        container = cls()
        
        # Set configuration values
        container.config.from_dict(config_data)
        
        return container
    
    def wire_modules(self, *modules):
        """Wire modules to the container."""
        for module in modules:
            self.wire(modules=[module])
    
    def get_model_provider(self, provider_name: str):
        """Get model provider by name."""
        if provider_name == "ollama":
            return self.ollama_provider()
        elif provider_name == "lm_studio":
            return self.lm_studio_provider()
        elif provider_name == "langchain":
            return self.langchain_provider()
        elif provider_name == "llama_cpp":
            return self.llama_cpp_provider()
        else:
            raise ValueError(f"Unknown model provider: {provider_name}")
    
    def get_generation_settings(self):
        """Get generation settings from config."""
        return self.config.generation() 