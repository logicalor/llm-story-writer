#!/usr/bin/env python3
"""Test script for multi-step conversation functionality."""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.infrastructure.providers.ollama_provider import OllamaProvider
from src.infrastructure.providers.lm_studio_provider import LMStudioProvider
from src.infrastructure.providers.langchain_provider import LangChainProvider
from src.domain.value_objects.model_config import ModelConfig


async def test_multistep_conversation():
    """Test multi-step conversation with different providers."""
    print("Testing Multi-step Conversation Functionality...")
    
    # Example conversation flow
    system_message = "You are a helpful AI assistant helping to develop a story outline. Be creative and engaging."
    
    user_messages = [
        "Hello! I want to write a science fiction story about time travel.",
        "The main character is a scientist who discovers a way to send messages to the past.",
        "What are some interesting complications that could arise from this discovery?",
        "How should the story end? Should the scientist succeed or fail?",
        "Give me a brief summary of the complete story arc."
    ]
    
    print(f"System Message: {system_message}")
    print(f"User Messages: {len(user_messages)}")
    for i, msg in enumerate(user_messages, 1):
        print(f"  {i}. {msg}")
    print()
    
    # Test with different providers
    providers = [
        ("Ollama", OllamaProvider(host="127.0.0.1:11434")),
        ("LM Studio", LMStudioProvider(host="127.0.0.1:1234")),
        ("LangChain", LangChainProvider(api_keys={}))
    ]
    
    for provider_name, provider in providers:
        print(f"\n{'='*60}")
        print(f"Testing {provider_name} Provider")
        print(f"{'='*60}")
        
        # Create a simple model config for testing
        model_config = ModelConfig(
            name="test-model",
            provider=provider_name.lower().replace(" ", "_"),
            parameters={"temperature": 0.7, "max_tokens": 200}
        )
        
        try:
            # Test basic availability
            print(f"Checking {provider_name} availability...")
            is_available = await provider.is_model_available(model_config)
            
            if not is_available:
                print(f"{provider_name} is not available, skipping...")
                continue
            
            print(f"{provider_name} is available, testing multi-step conversation...")
            
            # Test multi-step conversation
            response = await provider.generate_multistep_conversation(
                user_messages=user_messages,
                model_config=model_config,
                system_message=system_message,
                debug=True
            )
            
            print(f"\n{provider_name} Final Response:")
            print(f"{'='*40}")
            print(response)
            print(f"{'='*40}")
            
        except Exception as e:
            print(f"Error testing {provider_name}: {e}")
            continue


async def test_specific_provider_conversation():
    """Test multi-step conversation with a specific provider."""
    print("\n" + "="*60)
    print("Test Specific Provider Conversation")
    print("="*60)
    
    provider_choice = input("Choose provider (ollama/lm_studio/langchain): ").strip().lower()
    
    if provider_choice not in ["ollama", "lm_studio", "langchain"]:
        print("Invalid provider choice")
        return
    
    # Create provider
    if provider_choice == "ollama":
        provider = OllamaProvider(host="127.0.0.1:11434")
        model_name = input("Enter Ollama model name (e.g., llama3:8b): ").strip()
    elif provider_choice == "lm_studio":
        provider = LMStudioProvider(host="127.0.0.1:1234")
        model_name = input("Enter LM Studio model name (e.g., llama-3-8b-instruct): ").strip()
    elif provider_choice == "langchain":
        # Get API keys for cloud providers
        api_keys = {}
        if input("Use OpenAI? (y/n): ").strip().lower() == 'y':
            api_keys["openai"] = os.getenv("OPENAI_API_KEY") or input("Enter OpenAI API key: ").strip()
        if input("Use Anthropic? (y/n): ").strip().lower() == 'y':
            api_keys["anthropic"] = os.getenv("ANTHROPIC_API_KEY") or input("Enter Anthropic API key: ").strip()
        
        provider = LangChainProvider(api_keys=api_keys)
        model_name = input("Enter model name (e.g., gpt-3.5-turbo): ").strip()
    
    if not model_name:
        print("Invalid model name")
        return
    
    # Create model config
    model_config = ModelConfig(
        name=model_name,
        provider=provider_choice,
        parameters={"temperature": 0.7, "max_tokens": 300}
    )
    
    # Get conversation details
    system_message = input("Enter system message (or press Enter for none): ").strip() or None
    
    print("Enter user messages (one per line, empty line to finish):")
    user_messages = []
    while True:
        message = input(f"Message {len(user_messages) + 1}: ").strip()
        if not message:
            break
        user_messages.append(message)
    
    if not user_messages:
        print("No messages entered")
        return
    
    print(f"\nTesting {provider_choice} with {len(user_messages)} messages...")
    
    try:
        # Test multi-step conversation
        response = await provider.generate_multistep_conversation(
            user_messages=user_messages,
            model_config=model_config,
            system_message=system_message,
            debug=True
        )
        
        print(f"\nFinal Response:")
        print(f"{'='*40}")
        print(response)
        print(f"{'='*40}")
        
    except Exception as e:
        print(f"Error: {e}")


async def test_conversation_memory():
    """Test that conversation memory is properly maintained."""
    print("\n" + "="*60)
    print("Testing Conversation Memory")
    print("="*60)
    
    # Use Ollama for this test (most likely to be available)
    provider = OllamaProvider(host="127.0.0.1:11434")
    
    model_config = ModelConfig(
        name="llama3:8b",
        provider="ollama",
        parameters={"temperature": 0.7, "max_tokens": 150}
    )
    
    # Test conversation that requires memory
    system_message = "You are a helpful assistant. Remember what the user tells you and refer back to it."
    
    user_messages = [
        "My name is Alice and I love reading science fiction books.",
        "What's my name and what do I love?",
        "I also have a cat named Whiskers.",
        "What's my cat's name?",
        "Tell me everything you know about me so far."
    ]
    
    try:
        print("Testing conversation memory with sequential questions...")
        response = await provider.generate_multistep_conversation(
            user_messages=user_messages,
            model_config=model_config,
            system_message=system_message,
            debug=True
        )
        
        print(f"\nMemory Test Response:")
        print(f"{'='*40}")
        print(response)
        print(f"{'='*40}")
        
        # Check if the response shows memory
        if "Alice" in response and "Whiskers" in response and "science fiction" in response:
            print("✅ Memory test PASSED - Assistant remembered the conversation details")
        else:
            print("❌ Memory test FAILED - Assistant didn't remember key details")
            
    except Exception as e:
        print(f"Error testing conversation memory: {e}")


if __name__ == "__main__":
    print("Multi-step Conversation Test")
    print("1. Test all providers")
    print("2. Test specific provider")
    print("3. Test conversation memory")
    
    choice = input("Enter choice (1, 2, or 3): ").strip()
    
    if choice == "1":
        asyncio.run(test_multistep_conversation())
    elif choice == "2":
        asyncio.run(test_specific_provider_conversation())
    elif choice == "3":
        asyncio.run(test_conversation_memory())
    else:
        print("Invalid choice")
