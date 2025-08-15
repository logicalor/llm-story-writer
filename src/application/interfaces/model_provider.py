"""Model provider interface."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from domain.value_objects.model_config import ModelConfig


class ModelProvider(ABC):
    """Abstract interface for model providers."""
    
    @abstractmethod
    async def generate_text(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        seed: Optional[int] = None,
        format_type: Optional[str] = None,
        min_word_count: int = 1,
        debug: bool = False,
        stream: bool = False
    ) -> str:
        """Generate text from messages."""
        pass
    
    @abstractmethod
    async def generate_multistep_conversation(
        self,
        user_messages: List[str],
        model_config: ModelConfig,
        system_message: Optional[str] = None,
        seed: Optional[int] = None,
        debug: bool = False
    ) -> str:
        """Generate text through a multi-step conversation with memory."""
        pass
    
    @abstractmethod
    async def generate_json(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        required_attributes: List[str],
        seed: Optional[int] = None,
        debug: bool = False
    ) -> Dict[str, Any]:
        """Generate JSON response from messages."""
        pass
    
    @abstractmethod
    async def stream_text(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        seed: Optional[int] = None,
        format_type: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream text generation from messages."""
        pass
    
    @abstractmethod
    async def is_model_available(self, model_config: ModelConfig) -> bool:
        """Check if a model is available."""
        pass
    
    @abstractmethod
    async def download_model(self, model_config: ModelConfig) -> None:
        """Download a model."""
        pass
    
    @abstractmethod
    async def get_supported_providers(self) -> List[str]:
        """Get list of supported providers."""
        pass 