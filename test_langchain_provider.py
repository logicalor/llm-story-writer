#!/usr/bin/env python3
"""Test script for LangChain provider."""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.infrastructure.providers.langchain_provider import LangChainProvider
from src.domain.value_objects.model_config import ModelConfig


async def test_langchain_provider():
    """Test the LangChain provider with different model configurations."""
    print("Testing LangChain Provider...")
    
    # Create provider with API keys
    api_keys = {
        "openai": os.getenv("OPENAI_API_KEY"),
        "anthropic": os.getenv("ANTHROPIC_API_KEY"),
        "google": os.getenv("GOOGLE_API_KEY"),
        "huggingface": os.getenv("HUGGINGFACE_API_KEY")
    }
    
    provider = LangChainProvider(api_keys=api_keys)
    
    # Test different model configurations
    test_configs = [
        # OpenAI
        ModelConfig(
            name="gpt-3.5-turbo",
            provider="openai",
            parameters={"temperature": 0.7, "max_tokens": 100}
        ),
        # Anthropic
        ModelConfig(
            name="claude-3-haiku-20240307",
            provider="anthropic",
            parameters={"temperature": 0.7, "max_tokens": 100}
        ),
        # Google
        ModelConfig(
            name="gemini-1.5-pro",
            provider="google",
            parameters={"temperature": 0.7, "max_tokens": 100}
        ),
        # Ollama (local)
        ModelConfig(
            name="llama3:8b",
            provider="ollama",
            host="http://localhost:11434",
            parameters={"temperature": 0.7, "max_tokens": 100}
        ),
        # LM Studio (local)
        ModelConfig(
            name="llama-3-8b-instruct",
            provider="lm_studio",
            host="http://localhost:1234",
            parameters={"temperature": 0.7, "max_tokens": 100}
        ),
        # HuggingFace
        ModelConfig(
            name="microsoft/DialoGPT-medium",
            provider="huggingface",
            parameters={"temperature": 0.7, "max_tokens": 100}
        )
    ]
    
    for i, model_config in enumerate(test_configs, 1):
        print(f"\n--- Test {i}: {model_config.provider} - {model_config.name} ---")
        
        # Test model availability
        print(f"Testing model availability...")
        try:
            is_available = await provider.is_model_available(model_config)
            print(f"Model available: {is_available}")
            
            if not is_available:
                print(f"Model not available, skipping...")
                continue
                
        except Exception as e:
            print(f"Error checking availability: {e}")
            continue
        
        # Test text generation
        print(f"Testing text generation...")
        messages = [
            {"role": "user", "content": "Hello! Please respond with a short greeting."}
        ]
        
        try:
            response = await provider.generate_text(
                messages=messages,
                model_config=model_config,
                debug=True
            )
            print(f"Response: {response}")
        except Exception as e:
            print(f"Error generating text: {e}")
    
    # Test supported providers
    print(f"\nSupported providers: {await provider.get_supported_providers()}")


async def test_specific_provider():
    """Test a specific provider if API key is available."""
    provider_name = input("Enter provider to test (openai/anthropic/google/ollama/lm_studio/huggingface): ").strip().lower()
    model_name = input(f"Enter {provider_name} model name: ").strip()
    
    if not provider_name or not model_name:
        print("Invalid input")
        return
    
    # Create provider
    api_keys = {}
    if provider_name in ["openai", "anthropic", "google", "huggingface"]:
        env_var = f"{provider_name.upper()}_API_KEY"
        api_key = os.getenv(env_var)
        if not api_key:
            print(f"Please set {env_var} environment variable")
            return
        api_keys[provider_name] = api_key
    
    provider = LangChainProvider(api_keys=api_keys)
    
    # Create model config
    model_config = ModelConfig(
        name=model_name,
        provider=provider_name,
        parameters={"temperature": 0.7, "max_tokens": 100}
    )
    
    # Test
    print(f"\nTesting {provider_name} with model {model_name}...")
    
    try:
        is_available = await provider.is_model_available(model_config)
        print(f"Model available: {is_available}")
        
        if is_available:
            messages = [{"role": "user", "content": "Hello! Please respond with a short greeting."}]
            response = await provider.generate_text(messages, model_config, debug=True)
            print(f"Response: {response}")
        else:
            print("Model not available")
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    print("LangChain Provider Test")
    print("1. Test all available providers")
    print("2. Test specific provider")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        asyncio.run(test_langchain_provider())
    elif choice == "2":
        asyncio.run(test_specific_provider())
    else:
        print("Invalid choice")
