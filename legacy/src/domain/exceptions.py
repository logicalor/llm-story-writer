"""Domain exceptions for the AI Story Writer application."""


class StoryGenerationError(Exception):
    """Base exception for story generation errors."""
    pass


class ModelProviderError(StoryGenerationError):
    """Raised when model provider fails."""
    pass


class ConfigurationError(StoryGenerationError):
    """Raised when configuration is invalid."""
    pass


class ValidationError(StoryGenerationError):
    """Raised when data validation fails."""
    pass


class StorageError(StoryGenerationError):
    """Raised when storage operations fail."""
    pass


class PromptError(StoryGenerationError):
    """Raised when prompt processing fails."""
    pass


class GenerationTimeoutError(StoryGenerationError):
    """Raised when generation times out."""
    pass 