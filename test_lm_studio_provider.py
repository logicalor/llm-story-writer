#!/usr/bin/env python3
"""Test script for LM Studio provider."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.infrastructure.providers.lm_studio_provider import LMStudioProvider
from src.domain.value_objects.model_config import ModelConfig


async def test_lm_studio_provider():
    """Test the LM Studio provider."""
    print("Testing LM Studio Provider...")
    
    # Create provider
    provider = LMStudioProvider(host="127.0.0.1:1234")
    
    # Create a test model config
    model_config = ModelConfig(
        name="test-model",
        provider="lm_studio",
        host="127.0.0.1:1234",
        parameters={
            "temperature": 0.7,
            "max_tokens": 100
        }
    )
    
    # Test model availability
    print(f"Testing model availability for {model_config.name}...")
    is_available = await provider.is_model_available(model_config)
    print(f"Model available: {is_available}")
    
    if not is_available:
        print("LM Studio is not running or not accessible at 127.0.0.1:1234")
        print("Please start LM Studio and ensure it's running on the default port")
        return
    
    # Test text generation
    print("\nTesting text generation...")
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


if __name__ == "__main__":
    asyncio.run(test_lm_studio_provider())
