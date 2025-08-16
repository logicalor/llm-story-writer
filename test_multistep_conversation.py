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
    """Test multi-step conversation across all providers."""
    print("\n" + "="*60)
    print("Testing Multi-step Conversation (All Providers)")
    print("="*60)
    
    # Test Ollama
    print("\n--- Testing Ollama Provider ---")
    try:
        ollama_provider = OllamaProvider(host="127.0.0.1:11434")
        ollama_config = ModelConfig(
            name="llama3:8b",
            provider="ollama",
            parameters={"temperature": 0.7, "max_tokens": 200}
        )
        
        response = await ollama_provider.generate_multistep_conversation(
            user_messages=["Hello!", "What's 2+2?", "Now multiply that by 3"],
            model_config=ollama_config,
            system_message="You are a helpful math tutor.",
            debug=True,
            stream=True  # Enable streaming
        )
        print(f"Ollama Response: {response[:100]}...")
    except Exception as e:
        print(f"Ollama Error: {e}")
    
    # Test LM Studio
    print("\n--- Testing LM Studio Provider ---")
    try:
        lm_studio_provider = LMStudioProvider(host="127.0.0.1:1234")
        lm_studio_config = ModelConfig(
            name="llama-3-8b-instruct",
            provider="lm_studio",
            parameters={"temperature": 0.7, "max_tokens": 200}
        )
        
        response = await lm_studio_provider.generate_multistep_conversation(
            user_messages=["Hello!", "What's 2+2?", "Now multiply that by 3"],
            model_config=lm_studio_config,
            system_message="You are a helpful math tutor.",
            debug=True,
            stream=True  # Enable streaming
        )
        print(f"LM Studio Response: {response[:100]}...")
    except Exception as e:
        print(f"LM Studio Error: {e}")
    
    # Test LangChain
    print("\n--- Testing LangChain Provider ---")
    try:
        # Try to get API keys from environment
        api_keys = {}
        if os.getenv("OPENAI_API_KEY"):
            api_keys["openai"] = os.getenv("OPENAI_API_KEY")
        if os.getenv("ANTHROPIC_API_KEY"):
            api_keys["anthropic"] = os.getenv("ANTHROPIC_API_KEY")
        
        if not api_keys:
            print("No API keys found. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variables.")
            return
        
        langchain_provider = LangChainProvider(api_keys=api_keys)
        
        # Use the first available provider
        provider_name = list(api_keys.keys())[0]
        model_name = "gpt-3.5-turbo" if provider_name == "openai" else "claude-3-haiku-20240307"
        
        langchain_config = ModelConfig(
            name=model_name,
            provider="langchain",
            parameters={"temperature": 0.7, "max_tokens": 200}
        )
        
        response = await langchain_provider.generate_multistep_conversation(
            user_messages=["Hello!", "What's 2+2?", "Now multiply that by 3"],
            model_config=langchain_config,
            system_message="You are a helpful math tutor.",
            debug=True,
            stream=True  # Enable streaming
        )
        print(f"LangChain Response: {response[:100]}...")
    except Exception as e:
        print(f"LangChain Error: {e}")


async def test_specific_provider_conversation():
    """Test multi-step conversation with a specific provider."""
    print("\n" + "="*60)
    print("Testing Specific Provider Multi-step Conversation")
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
        parameters={"temperature": 0.7, "max_tokens": 200}
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
    
    print(f"\nTesting {provider_choice} with {len(user_messages)} messages (STREAMING MODE)...")
    print("You should see each response stream in real-time!")
    
    try:
        # Test multi-step conversation with streaming enabled
        response = await provider.generate_multistep_conversation(
            user_messages=user_messages,
            model_config=model_config,
            system_message=system_message,
            debug=True,
            stream=True  # Enable streaming
        )
        
        print(f"\nFinal Response (Complete):")
        print(f"{'='*40}")
        print(response)
        print(f"{'='*40}")
        
    except Exception as e:
        print(f"Error: {e}")


async def test_conversation_memory():
    """Test that conversation memory is maintained across steps."""
    print("\n" + "="*60)
    print("Testing Conversation Memory")
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
        parameters={"temperature": 0.7, "max_tokens": 200}
    )
    
    # Test conversation memory with a story development scenario
    user_messages = [
        "I want to write a story about a robot learning to paint.",
        "The robot's name is ArtBot-3000.",
        "ArtBot-3000 lives in a world where humans have forgotten how to create art.",
        "What should happen when ArtBot-3000 creates its first painting?",
        "How does the story end? Remember ArtBot-3000's name and the world setting."
    ]
    
    system_message = "You are a creative writing coach helping develop a story about a robot artist. Remember all the details mentioned in the conversation."
    
    print(f"\nTesting {provider_choice} conversation memory with story development...")
    print("This will test if the AI remembers ArtBot-3000's name and the world setting across all steps.")
    print("STREAMING MODE ENABLED - Watch each response build in real-time!")
    
    try:
        # Test multi-step conversation with streaming enabled
        response = await provider.generate_multistep_conversation(
            user_messages=user_messages,
            model_config=model_config,
            system_message=system_message,
            debug=True,
            stream=True  # Enable streaming
        )
        
        print(f"\nFinal Response (Complete):")
        print(f"{'='*40}")
        print(response)
        print(f"{'='*40}")
        
        # Check if memory was maintained
        if "ArtBot-3000" in response and "forgotten how to create art" in response:
            print("\n✅ SUCCESS: Conversation memory maintained! The AI remembered key details.")
        else:
            print("\n❌ FAILURE: Conversation memory may not be working properly.")
            print("Expected to see 'ArtBot-3000' and 'forgotten how to create art' in the final response.")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    print("Multi-step Conversation Test")
    print("1. Test all providers")
    print("2. Test specific provider")
    print("3. Test conversation memory")
    print("4. Test streaming conversation")
    
    choice = input("Enter choice (1, 2, 3, or 4): ").strip()
    
    if choice == "1":
        asyncio.run(test_multistep_conversation())
    elif choice == "2":
        asyncio.run(test_specific_provider_conversation())
    elif choice == "3":
        asyncio.run(test_conversation_memory())
    elif choice == "4":
        asyncio.run(test_streaming_conversation())
    else:
        print("Invalid choice")


async def test_streaming_conversation():
    """Test streaming multi-step conversation functionality."""
    print("\n" + "="*60)
    print("Testing Streaming Multi-step Conversation")
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
        parameters={"temperature": 0.7, "max_tokens": 200}
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
    
    print(f"\nTesting {provider_choice} with {len(user_messages)} messages (STREAMING MODE)...")
    print("You should see each response stream in real-time!")
    
    try:
        # Test streaming multi-step conversation
        response = await provider.generate_multistep_conversation(
            user_messages=user_messages,
            model_config=model_config,
            system_message=system_message,
            debug=True,
            stream=True  # Enable streaming
        )
        
        print(f"\nFinal Response (Complete):")
        print(f"{'='*40}")
        print(response)
        print(f"{'='*40}")
        
    except Exception as e:
        print(f"Error: {e}")
