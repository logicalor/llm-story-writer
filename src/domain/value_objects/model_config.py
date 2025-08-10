"""Model configuration value objects."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs
from ..exceptions import ValidationError


@dataclass(frozen=True)
class ModelConfig:
    """Configuration for a language model."""
    
    name: str
    provider: str
    host: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate the model configuration."""
        if not self.name:
            raise ValidationError("Model name cannot be empty")
        
        if not self.provider:
            raise ValidationError("Model provider cannot be empty")
        
        # Validate provider
        valid_providers = {"ollama", "google", "openrouter", "openai", "anthropic"}
        if self.provider.lower() not in valid_providers:
            raise ValidationError(f"Invalid provider: {self.provider}. Must be one of {valid_providers}")
    
    @classmethod
    def from_string(cls, model_string: str) -> "ModelConfig":
        """Create ModelConfig from a string representation.
        
        Format: provider://model@host?param1=value1&param2=value2
        Examples:
            - "ollama://llama3:70b"
            - "google://gemini-1.5-pro"
            - "ollama://llama3:70b@192.168.1.100:11434?temperature=0.7"
        """
        if "://" not in model_string:
            # Legacy support for model names without provider
            return cls(name=model_string, provider="ollama")
        
        try:
            parsed = urlparse(model_string)
            provider = parsed.scheme.lower()
            
            # Handle different provider formats
            if provider == "openrouter":
                model = f"{parsed.netloc}{parsed.path}"
                host = None
            elif provider == "ollama":
                # For Ollama, the model name includes the path
                if "@" in parsed.netloc:
                    model_part, host = parsed.netloc.split("@", 1)
                    model = f"{model_part}{parsed.path}"
                else:
                    model = f"{parsed.netloc}{parsed.path}"
                    host = None
            elif "@" in parsed.netloc:
                model, host = parsed.netloc.split("@", 1)
            else:
                model = parsed.netloc
                host = None
            
            # Parse query parameters
            query_params = parse_qs(parsed.query)
            parameters = {}
            for key, values in query_params.items():
                if len(values) == 1:
                    # Try to convert to appropriate type
                    value = values[0]
                    try:
                        # Try float first
                        parameters[key] = float(value)
                    except ValueError:
                        # Keep as string
                        parameters[key] = value
                else:
                    parameters[key] = values
            
            return cls(
                name=model,
                provider=provider,
                host=host,
                parameters=parameters
            )
        except Exception as e:
            raise ValidationError(f"Invalid model string format: {model_string}. Error: {e}")
    
    def to_string(self) -> str:
        """Convert ModelConfig back to string representation."""
        result = f"{self.provider}://{self.name}"
        
        if self.host:
            result += f"@{self.host}"
        
        if self.parameters:
            param_strings = []
            for key, value in self.parameters.items():
                param_strings.append(f"{key}={value}")
            result += "?" + "&".join(param_strings)
        
        return result
    
    def __str__(self) -> str:
        return self.to_string()
    
    def __repr__(self) -> str:
        return f"ModelConfig(name='{self.name}', provider='{self.provider}', host='{self.host}')" 