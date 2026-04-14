"""Unit tests for ModelConfig value object."""

import pytest
from src.domain.value_objects.model_config import ModelConfig
from src.domain.exceptions import ValidationError


class TestModelConfig:
    """Test cases for ModelConfig value object."""
    
    def test_create_from_string_ollama(self):
        """Test creating ModelConfig from Ollama string."""
        model_string = "ollama://llama3:70b"
        config = ModelConfig.from_string(model_string)
        
        assert config.name == "llama3:70b"
        assert config.provider == "ollama"
        assert config.host is None
        assert config.parameters == {}
    
    def test_create_from_string_with_host(self):
        """Test creating ModelConfig with host."""
        model_string = "ollama://llama3:70b@192.168.1.100:11434"
        config = ModelConfig.from_string(model_string)
        
        assert config.name == "llama3:70b"
        assert config.provider == "ollama"
        assert config.host == "192.168.1.100:11434"
    
    def test_create_from_string_with_parameters(self):
        """Test creating ModelConfig with parameters."""
        model_string = "ollama://llama3:70b?temperature=0.7&top_p=0.9"
        config = ModelConfig.from_string(model_string)
        
        assert config.name == "llama3:70b"
        assert config.provider == "ollama"
        assert config.parameters["temperature"] == 0.7
        assert config.parameters["top_p"] == 0.9
    
    def test_create_from_string_google(self):
        """Test creating ModelConfig from Google string."""
        model_string = "google://gemini-1.5-pro"
        config = ModelConfig.from_string(model_string)
        
        assert config.name == "gemini-1.5-pro"
        assert config.provider == "google"
    
    def test_create_from_string_openrouter(self):
        """Test creating ModelConfig from OpenRouter string."""
        model_string = "openrouter://anthropic/claude-3-opus"
        config = ModelConfig.from_string(model_string)
        
        assert config.name == "anthropic/claude-3-opus"
        assert config.provider == "openrouter"
    
    def test_legacy_support(self):
        """Test legacy support for model names without provider."""
        model_string = "llama3:70b"
        config = ModelConfig.from_string(model_string)
        
        assert config.name == "llama3:70b"
        assert config.provider == "ollama"
    
    def test_invalid_provider(self):
        """Test validation of invalid provider."""
        with pytest.raises(ValidationError, match="Invalid provider"):
            ModelConfig.from_string("invalid://model")
    
    def test_empty_model_name(self):
        """Test validation of empty model name."""
        with pytest.raises(ValidationError, match="Model name cannot be empty"):
            ModelConfig(name="", provider="ollama")
    
    def test_empty_provider(self):
        """Test validation of empty provider."""
        with pytest.raises(ValidationError, match="Model provider cannot be empty"):
            ModelConfig(name="model", provider="")
    
    def test_to_string(self):
        """Test converting ModelConfig back to string."""
        config = ModelConfig(
            name="llama3:70b",
            provider="ollama",
            host="192.168.1.100:11434",
            parameters={"temperature": 0.7}
        )
        
        expected = "ollama://llama3:70b@192.168.1.100:11434?temperature=0.7"
        assert str(config) == expected
    
    def test_repr(self):
        """Test ModelConfig representation."""
        config = ModelConfig(
            name="llama3:70b",
            provider="ollama",
            host="192.168.1.100:11434"
        )
        
        expected = "ModelConfig(name='llama3:70b', provider='ollama', host='192.168.1.100:11434')"
        assert repr(config) == expected 