"""Strategy factory for managing story writing strategies."""

from typing import Dict, Type, Optional
from domain.exceptions import ConfigurationError
from domain.repositories.savepoint_repository import SavepointRepository
from ..interfaces.story_strategy import StoryStrategy
from ..interfaces.model_provider import ModelProvider
from config.settings import AppConfig
from infrastructure.prompts.prompt_loader import PromptLoader
from .outline_chapter.strategy import OutlineChapterStrategy
from .stream_of_consciousness.strategy import StreamOfConsciousnessStrategy


class StrategyFactory:
    """Factory for creating and managing story writing strategies."""
    
    def __init__(self):
        self._strategies: Dict[str, Type[StoryStrategy]] = {}
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """Register the default strategies."""
        self.register_strategy("outline-chapter", OutlineChapterStrategy)
        self.register_strategy("stream-of-consciousness", StreamOfConsciousnessStrategy)
    
    def register_strategy(self, name: str, strategy_class: Type[StoryStrategy]):
        """Register a new strategy."""
        self._strategies[name] = strategy_class
    
    def get_available_strategies(self) -> Dict[str, str]:
        """Get list of available strategies with descriptions."""
        strategies = {}
        for name, strategy_class in self._strategies.items():
            # Create a temporary instance to get description
            # This is a bit hacky but works for getting metadata
            temp_strategy = strategy_class.__new__(strategy_class)
            if hasattr(temp_strategy, 'get_strategy_description'):
                strategies[name] = temp_strategy.get_strategy_description()
            else:
                strategies[name] = f"Strategy: {name}"
        return strategies
    
    def create_strategy(
        self,
        strategy_name: str,
        model_provider: ModelProvider,
        config: AppConfig,
        prompt_loader: PromptLoader,
        savepoint_repo: Optional[SavepointRepository] = None
    ) -> StoryStrategy:
        """Create a strategy instance."""
        if strategy_name not in self._strategies:
            available = ", ".join(self._strategies.keys())
            raise ConfigurationError(
                f"Unknown strategy '{strategy_name}'. Available strategies: {available}"
            )
        
        strategy_class = self._strategies[strategy_name]
        
        # Create strategy instance with required dependencies
        if strategy_name == "outline-chapter":
            return strategy_class(model_provider, config, prompt_loader, savepoint_repo)
        elif strategy_name == "stream-of-consciousness":
            return strategy_class(model_provider, config)
        else:
            # For future strategies, try to create with model_provider only
            return strategy_class(model_provider)
    
    def create_strategy_with_prompts(
        self,
        strategy_name: str,
        model_provider: ModelProvider,
        config: AppConfig,
        savepoint_repo: Optional[SavepointRepository] = None
    ) -> StoryStrategy:
        """Create a strategy instance with its own prompt loader."""
        if strategy_name not in self._strategies:
            available = ", ".join(self._strategies.keys())
            raise ConfigurationError(
                f"Unknown strategy '{strategy_name}'. Available strategies: {available}"
            )
        
        strategy_class = self._strategies[strategy_name]
        
        # Create a temporary instance to get the prompt directory
        temp_strategy = strategy_class.__new__(strategy_class)
        if hasattr(temp_strategy, 'get_prompt_directory'):
            prompt_dir = temp_strategy.get_prompt_directory()
            strategy_prompt_loader = PromptLoader(prompts_dir=prompt_dir)
        else:
            # Fallback to default prompt loader
            strategy_prompt_loader = PromptLoader(prompts_dir="src/prompts")
        
        # Create strategy instance with required dependencies
        if strategy_name == "outline-chapter":
            return strategy_class(model_provider, config, strategy_prompt_loader, savepoint_repo)
        elif strategy_name == "stream-of-consciousness":
            return strategy_class(model_provider, config)
        else:
            # For future strategies, try to create with model_provider only
            return strategy_class(model_provider)
    
    def validate_strategy_requirements(
        self,
        strategy_name: str,
        config: AppConfig
    ) -> bool:
        """Validate that a strategy's requirements are met."""
        if strategy_name not in self._strategies:
            return False
        
        # Create a temporary strategy to check requirements
        strategy_class = self._strategies[strategy_name]
        temp_strategy = strategy_class.__new__(strategy_class)
        
        if hasattr(temp_strategy, 'get_required_models'):
            required_models = temp_strategy.get_required_models()
            
            # Check if all required models are configured
            for model_name in required_models:
                try:
                    config.get_model(model_name)
                except Exception:
                    return False
        
        return True 