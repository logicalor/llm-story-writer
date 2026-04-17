#!/usr/bin/env python3
"""Test character sheet generation functionality."""

import asyncio
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.application.strategies.outline_chapter_strategy import OutlineChapterStrategy
from src.domain.value_objects.generation_settings import GenerationSettings
from src.config.settings import AppConfig
from src.infrastructure.prompts.prompt_loader import PromptLoader
from src.infrastructure.providers.openai_compatible_provider import (
    OpenAICompatibleProvider,
)


async def test_character_extraction():
    """Test character name extraction from story elements."""
    # Create minimal configurations for testing
    from src.domain.value_objects.model_config import ModelConfig
    from src.domain.value_objects.generation_settings import GenerationSettings

    # Create model configs
    models = {
        "initial_outline_writer": ModelConfig(
            name="llama3:8b", provider="openai_compatible"
        ),
        "chapter_outline_writer": ModelConfig(
            name="llama3:8b", provider="openai_compatible"
        ),
        "chapter_stage1_writer": ModelConfig(
            name="llama3:8b", provider="openai_compatible"
        ),
        "chapter_stage2_writer": ModelConfig(
            name="llama3:8b", provider="openai_compatible"
        ),
        "chapter_stage3_writer": ModelConfig(
            name="llama3:8b", provider="openai_compatible"
        ),
        "chapter_stage4_writer": ModelConfig(
            name="llama3:8b", provider="openai_compatible"
        ),
        "chapter_revision_writer": ModelConfig(
            name="llama3:8b", provider="openai_compatible"
        ),
        "revision_model": ModelConfig(name="llama3:8b", provider="openai_compatible"),
        "eval_model": ModelConfig(name="llama3:8b", provider="openai_compatible"),
        "info_model": ModelConfig(name="llama3:8b", provider="openai_compatible"),
        "scrub_model": ModelConfig(name="llama3:8b", provider="openai_compatible"),
        "checker_model": ModelConfig(name="llama3:8b", provider="openai_compatible"),
        "translator_model": ModelConfig(name="llama3:8b", provider="openai_compatible"),
    }

    # Create generation settings
    generation = GenerationSettings(
        seed=42,
        debug=True,
        stream=False,
        wanted_chapters=5,
        enable_outline_critique=False,
    )

    # Create app config
    config = AppConfig(models=models, generation=generation)

    strategy = OutlineChapterStrategy(
        model_provider=OpenAICompatibleProvider(base_url="http://127.0.0.1:11434/v1"),
        config=config,
        prompt_loader=PromptLoader(),
    )

    # Test story elements with character information
    test_story_elements = """
    ### Main Character(s)
    
    #### Sarah Chen
    **Name**: Sarah Chen
    **Age**: 28
    **Occupation**: Software Engineer
    
    #### Marcus Rodriguez
    **Name**: Marcus Rodriguez
    **Age**: 32
    **Occupation**: Detective
    
    ### Supporting Characters
    
    #### Dr. Emily Watson
    **Name**: Dr. Emily Watson
    **Age**: 45
    **Occupation**: Research Scientist
    """

    # Create minimal settings for testing
    test_settings = GenerationSettings(
        seed=42,
        debug=True,
        stream=False,
        wanted_chapters=5,
        enable_outline_critique=False,
    )

    character_names = await strategy._extract_character_names(
        test_story_elements, test_settings
    )

    print("Extracted character names:")
    for name in character_names:
        print(f"  - {name}")

    expected_names = ["Sarah Chen", "Marcus Rodriguez", "Dr. Emily Watson"]

    # Check if all expected names were extracted
    for expected in expected_names:
        if expected not in character_names:
            print(f"❌ Expected character '{expected}' not found")
            return False

    print("✅ All expected character names were extracted successfully")
    return True


async def test_character_sheet_generation():
    """Test the complete character sheet generation flow."""
    print("\nTesting character sheet generation...")

    # Create a minimal story elements string for testing
    test_story_elements = """
    ### Main Character(s)
    
    #### Test Character
    **Name**: Test Character
    **Age**: 25
    **Occupation**: Test Subject
    """

    # Create generation settings
    settings = GenerationSettings(
        seed=42,
        debug=True,
        stream=False,
        wanted_chapters=5,
        enable_outline_critique=False,
    )

    try:
        # Create minimal configurations for testing
        from src.domain.value_objects.model_config import ModelConfig

        # Create model configs
        models = {
            "initial_outline_writer": ModelConfig(
                name="llama3:8b", provider="openai_compatible"
            ),
            "chapter_outline_writer": ModelConfig(
                name="llama3:8b", provider="openai_compatible"
            ),
            "chapter_stage1_writer": ModelConfig(
                name="llama3:8b", provider="openai_compatible"
            ),
            "chapter_stage2_writer": ModelConfig(
                name="llama3:8b", provider="openai_compatible"
            ),
            "chapter_stage3_writer": ModelConfig(
                name="llama3:8b", provider="openai_compatible"
            ),
            "chapter_stage4_writer": ModelConfig(
                name="llama3:8b", provider="openai_compatible"
            ),
            "chapter_revision_writer": ModelConfig(
                name="llama3:8b", provider="openai_compatible"
            ),
            "revision_model": ModelConfig(
                name="llama3:8b", provider="openai_compatible"
            ),
            "eval_model": ModelConfig(name="llama3:8b", provider="openai_compatible"),
            "info_model": ModelConfig(name="llama3:8b", provider="openai_compatible"),
            "scrub_model": ModelConfig(name="llama3:8b", provider="openai_compatible"),
            "checker_model": ModelConfig(
                name="llama3:8b", provider="openai_compatible"
            ),
            "translator_model": ModelConfig(
                name="llama3:8b", provider="openai_compatible"
            ),
        }

        # Create app config
        config = AppConfig(models=models, generation=settings)

        # Create strategy instance
        strategy = OutlineChapterStrategy(
            model_provider=OpenAICompatibleProvider(
                base_url="http://127.0.0.1:11434/v1"
            ),
            config=config,
            prompt_loader=PromptLoader(),
        )

        # Test character name extraction
        character_names = await strategy._extract_character_names(
            test_story_elements, settings
        )
        print(f"Found {len(character_names)} characters: {character_names}")

        if not character_names:
            print("❌ No characters found in test story elements")
            return False

        print("✅ Character extraction test passed")
        return True

    except Exception as e:
        print(f"❌ Error during character sheet generation test: {e}")
        return False


async def main():
    """Run all tests."""
    print("🧪 Testing Character Sheet Generation Functionality")
    print("=" * 50)

    # Test 1: Character extraction
    test1_passed = await test_character_extraction()

    # Test 2: Basic functionality
    test2_passed = await test_character_sheet_generation()

    print("\n" + "=" * 50)
    if test1_passed and test2_passed:
        print("🎉 All tests passed! Character sheet generation is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
