#!/usr/bin/env python3
"""
Test script to verify chapter synopsis generation functionality.
"""

import asyncio
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.application.strategies.outline_chapter_strategy import OutlineChapterStrategy
from src.domain.value_objects.generation_settings import GenerationSettings
from src.domain.entities.story import Outline
from src.infrastructure.providers.ollama_provider import OllamaProvider
from src.config.config_loader import ConfigLoader
from src.infrastructure.prompts.prompt_loader import PromptLoader
from src.infrastructure.storage.savepoint_repository import FilesystemSavepointRepository as SavepointRepository

async def test_chapter_synopsis_generation():
    """Test the chapter synopsis generation functionality."""
    
    # Load configuration
    config_loader = ConfigLoader()
    config = config_loader.load_config()
    
    # Initialize components
    model_provider = OllamaProvider(config.ollama_host)
    prompt_loader = PromptLoader("src/application/strategies/prompts/outline-chapter")
    savepoint_repo = SavepointRepository()
    
    # Create strategy
    strategy = OutlineChapterStrategy(
        model_provider=model_provider,
        config=config,
        prompt_loader=prompt_loader,
        savepoint_repo=savepoint_repo
    )
    
    # Test settings
    settings = GenerationSettings(
        seed=42,
        debug=True,
        stream=False
    )
    
    # Test prompt
    test_prompt = """
    Write a short story about a young detective who discovers a mysterious artifact in an old library.
    The story should be about 3-4 chapters long and include elements of mystery and adventure.
    """
    
    try:
        print("Generating outline...")
        outline = await strategy.generate_outline(test_prompt, settings, "test_synopsis")
        
        print("Generating chapter synopses...")
        chapters = await strategy.generate_chapters(outline, settings)
        
        print(f"Generated {len(chapters)} chapters")
        print("Chapter synopsis generation completed successfully!")
        
        # List the savepoints to verify they were created
        print("\nChecking savepoints...")
        for i in range(1, 5):  # Check for chapters 1-4
            try:
                synopsis = await savepoint_repo.load_step(f"test_synopsis/chapter_{i}/base_synopsis")
                print(f"Chapter {i} synopsis found: {len(synopsis)} characters")
            except Exception as e:
                print(f"Chapter {i} synopsis not found: {e}")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_chapter_synopsis_generation()) 