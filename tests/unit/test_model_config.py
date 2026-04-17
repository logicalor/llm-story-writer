"""Unit tests for ModelConfig value object."""

import pytest
from src.domain.value_objects.model_config import ModelConfig
from src.domain.exceptions import ValidationError


class TestModelConfig:
    """Test cases for ModelConfig value object."""

    def test_create_from_string_openai_compatible(self):
        """Test creating ModelConfig from OpenAI-compatible string."""
        model_string = "openai-compat://llama3:70b"
        config = ModelConfig.from_string(model_string)

        assert config.name == "llama3:70b"
        assert config.provider == "openai_compatible"
        assert config.host is None
        assert config.parameters == {}

    def test_create_from_string_with_host(self):
        """Test creating ModelConfig with host."""
        model_string = "openai-compat://llama3:70b@192.168.1.100:11434"
        config = ModelConfig.from_string(model_string)

        assert config.name == "llama3:70b"
        assert config.provider == "openai_compatible"
        assert config.host == "192.168.1.100:11434"

    def test_create_from_string_with_parameters(self):
        """Test creating ModelConfig with parameters."""
        model_string = "openai-compat://llama3:70b?temperature=0.7&top_p=0.9"
        config = ModelConfig.from_string(model_string)

        assert config.name == "llama3:70b"
        assert config.provider == "openai_compatible"
        assert config.parameters["temperature"] == 0.7
        assert config.parameters["top_p"] == 0.9

    def test_create_from_string_ollama_backward_compat(self):
        """Test creating ModelConfig from Ollama string for backward compatibility."""
        model_string = "ollama://llama3:70b"
        config = ModelConfig.from_string(model_string)

        assert config.name == "llama3:70b"
        assert config.provider == "openai_compatible"
        assert config.original_scheme == "ollama"

    def test_create_from_string_lm_studio(self):
        """Test creating ModelConfig from LM Studio string with underscore scheme."""
        model_string = "lm_studio://llama3:8b"
        config = ModelConfig.from_string(model_string)

        assert config.name == "llama3:8b"
        assert config.provider == "lm_studio"
        assert config.host is None
        assert config.parameters == {}

    def test_create_from_string_llama_cpp_with_host(self):
        """Test creating ModelConfig from llama.cpp string with underscore scheme."""
        model_string = "llama_cpp://mistral-7b@127.0.0.1:8080"
        config = ModelConfig.from_string(model_string)

        assert config.name == "mistral-7b"
        assert config.provider == "llama_cpp"
        assert config.host == "127.0.0.1:8080"

    def test_create_from_string_google(self):
        """Test that google:// provider is rejected as unsupported."""
        with pytest.raises(ValidationError, match="Invalid provider"):
            ModelConfig.from_string("google://gemini-1.5-pro")

    def test_create_from_string_openrouter(self):
        """Test that openrouter:// provider is rejected as unsupported."""
        with pytest.raises(ValidationError, match="Invalid provider"):
            ModelConfig.from_string("openrouter://anthropic/claude-3-opus")

    @pytest.mark.parametrize("scheme", ["google", "openrouter", "openai", "anthropic"])
    def test_removed_cloud_provider_schemes_raise_validation_error(self, scheme):
        """Test that all four removed cloud provider schemes are rejected."""
        with pytest.raises(ValidationError, match="Invalid provider"):
            ModelConfig.from_string(f"{scheme}://some-model")

    def test_legacy_support(self):
        """Test legacy support for model names without provider."""
        model_string = "llama3:70b"
        config = ModelConfig.from_string(model_string)

        assert config.name == "llama3:70b"
        assert config.provider == "openai_compatible"

    def test_invalid_provider(self):
        """Test validation of invalid provider."""
        with pytest.raises(ValidationError, match="Invalid provider"):
            ModelConfig.from_string("invalid://model")

    def test_empty_model_name(self):
        """Test validation of empty model name."""
        with pytest.raises(ValidationError, match="Model name cannot be empty"):
            ModelConfig(name="", provider="openai_compatible")

    def test_empty_provider(self):
        """Test validation of empty provider."""
        with pytest.raises(ValidationError, match="Model provider cannot be empty"):
            ModelConfig(name="model", provider="")

    def test_to_string(self):
        """Test converting ModelConfig back to string."""
        config = ModelConfig(
            name="llama3:70b",
            provider="openai_compatible",
            host="192.168.1.100:11434",
            parameters={"temperature": 0.7},
        )

        expected = "openai-compat://llama3:70b@192.168.1.100:11434?temperature=0.7"
        assert str(config) == expected

    def test_to_string_preserves_ollama_scheme_when_input_used_it(self):
        """Test converting backward-compatible Ollama input back to Ollama URI."""
        config = ModelConfig.from_string("ollama://llama3:70b@192.168.1.100:11434")

        expected = "ollama://llama3:70b@192.168.1.100:11434"
        assert str(config) == expected

    def test_repr(self):
        """Test ModelConfig representation."""
        config = ModelConfig(
            name="llama3:70b",
            provider="openai_compatible",
            host="192.168.1.100:11434",
        )

        expected = "ModelConfig(name='llama3:70b', provider='openai_compatible', host='192.168.1.100:11434')"
        assert repr(config) == expected
