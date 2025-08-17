#!/usr/bin/env python3
"""Test script for progressive story generation system."""

import asyncio
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from application.strategies.outline_chapter.strategy import OutlineChapterStrategy
from application.strategies.outline_chapter.story_state_manager import StoryStateManager
from domain.value_objects.generation_settings import GenerationSettings
from infrastructure.providers.ollama_provider import OllamaProvider
from infrastructure.prompts.prompt_loader import PromptLoader
from infrastructure.savepoints import SavepointManager
from domain.repositories.savepoint_repository import SavepointRepository


async def test_progressive_story_generation():
    """Test the progressive story generation system."""
    
    print("=== Testing Progressive Story Generation System ===\n")
    
    # Initialize components
    print("1. Initializing components...")
    
    # Mock config (you would load this from your actual config)
    config = {
        "models": {
            "initial_outline_writer": "llama3.1:8b",
            "chapter_outline_writer": "llama3.1:8b", 
            "logical_model": "llama3.1:8b",
            "scene_writer": "llama3.1:8b",
            "info_model": "llama3.1:8b"
        },
        "max_chunk_size": 1000,
        "overlap_size": 200
    }
    
    # Initialize provider (using Ollama as an example)
    try:
        provider = OllamaProvider(config)
        print("✓ Ollama provider initialized")
    except Exception as e:
        print(f"⚠ Could not initialize Ollama provider: {e}")
        print("   Using mock provider for demonstration")
        # Create a mock provider for demonstration
        class MockProvider:
            async def generate_text(self, *args, **kwargs):
                return "Mock response for demonstration purposes"
        provider = MockProvider()
    
    # Initialize prompt loader
    prompt_loader = PromptLoader("src/application/strategies/outline_chapter/prompts")
    print("✓ Prompt loader initialized")
    
    # Initialize savepoint repository
    savepoint_repo = SavepointRepository("test_stories")
    print("✓ Savepoint repository initialized")
    
    # Initialize strategy
    strategy = OutlineChapterStrategy(
        model_provider=provider,
        config=config,
        prompt_loader=prompt_loader,
        savepoint_repo=savepoint_repo
    )
    print("✓ Strategy initialized")
    
    # Test story prompt
    test_prompt = """
    Write a mystery story about a young detective named Sarah who discovers she can see ghosts. 
    She must solve a murder while navigating the supernatural world and learning about her family's 
    hidden supernatural legacy. The story should explore themes of justice, redemption, and personal growth.
    """
    
    # Test settings
    settings = GenerationSettings(
        wanted_chapters=3,
        debug=True,
        stream=False,
        seed=42,
        log_prompt_inputs=False
    )
    
    print(f"\n2. Testing progressive story generation...")
    print(f"   Prompt: {test_prompt.strip()}")
    print(f"   Target chapters: {settings.wanted_chapters}")
    
    try:
        # Test the progressive story generation
        chapters = await strategy.generate_progressive_story(test_prompt, settings)
        
        print(f"\n✓ Progressive story generation completed!")
        print(f"   Generated {len(chapters)} chapters")
        
        # Display chapter summaries
        for i, chapter in enumerate(chapters, 1):
            print(f"\n   Chapter {i}: {chapter.title}")
            print(f"   Content length: {len(chapter.content)} characters")
            print(f"   Preview: {chapter.content[:100]}...")
        
        # Test story state manager directly
        print(f"\n3. Testing Story State Manager directly...")
        
        # Get story summary
        summary = strategy.story_state_manager.get_story_summary()
        print(f"   Story Summary:\n{summary}")
        
        # Test planning next chapter
        print(f"\n4. Testing next chapter planning...")
        next_chapter = await strategy.story_state_manager.plan_next_chapter(settings)
        print(f"   Next chapter planned: {next_chapter.title}")
        print(f"   Status: {next_chapter.status}")
        print(f"   Key events: {len(next_chapter.key_events)}")
        
        print(f"\n=== Progressive Story Generation Test Completed Successfully! ===")
        
    except Exception as e:
        print(f"\n❌ Error during progressive story generation: {e}")
        import traceback
        traceback.print_exc()


async def test_story_state_manager():
    """Test the Story State Manager in isolation."""
    
    print("\n=== Testing Story State Manager in Isolation ===\n")
    
    # Mock config
    config = {
        "models": {
            "initial_outline_writer": "llama3.1:8b",
            "chapter_outline_writer": "llama3.1:8b",
            "logical_model": "llama3.1:8b"
        }
    }
    
    # Mock components
    class MockProvider:
        async def generate_text(self, *args, **kwargs):
            return "Mock response for demonstration purposes"
    
    class MockPromptHandler:
        async def execute_prompt(self, *args, **kwargs):
            class MockResponse:
                content = """
                Direction: A young detective discovers supernatural abilities and solves mysteries
                Themes: justice, redemption, supernatural vs reality, personal growth
                Tone: mysterious, slightly dark but hopeful
                Audience: Young adult to adult readers
                Pacing: medium
                """
            return MockResponse()
    
    class MockSavepointManager:
        def __init__(self):
            self.savepoint_repo = type('MockRepo', (), {'_current_story_dir': '/tmp/test_story'})()
    
    # Initialize Story State Manager
    story_state_manager = StoryStateManager(
        model_provider=MockProvider(),
        config=config,
        prompt_handler=MockPromptHandler(),
        system_message="You are a creative writer.",
        savepoint_manager=MockSavepointManager()
    )
    
    print("✓ Story State Manager initialized")
    
    # Test story context initialization
    print("\n1. Testing story context initialization...")
    try:
        context = await story_state_manager.initialize_story_context("Test prompt", None)
        print(f"✓ Story context initialized: {context.story_direction}")
        print(f"   Themes: {context.current_themes}")
        print(f"   Tone: {context.tone_style}")
    except Exception as e:
        print(f"⚠ Could not test context initialization: {e}")
    
    # Test chapter planning
    print("\n2. Testing chapter planning...")
    try:
        chapter_state = await story_state_manager.plan_next_chapter(None)
        print(f"✓ Chapter planned: {chapter_state.title}")
        print(f"   Status: {chapter_state.status}")
        print(f"   Events: {len(chapter_state.key_events)}")
    except Exception as e:
        print(f"⚠ Could not test chapter planning: {e}")
    
    print("\n=== Story State Manager Test Completed ===")


if __name__ == "__main__":
    print("Starting Progressive Story Generation System Tests...\n")
    
    # Run tests
    asyncio.run(test_story_state_manager())
    asyncio.run(test_progressive_story_generation())
    
    print("\nAll tests completed!")
