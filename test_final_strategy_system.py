#!/usr/bin/env python3
"""Final test script for the complete strategy system with prompt organization."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.application.strategies.strategy_factory import StrategyFactory
from src.infrastructure.prompts.prompt_loader import PromptLoader


def test_strategy_system():
    """Test the complete strategy system with prompt organization."""
    try:
        print("🧪 Testing Complete Strategy System with Prompt Organization")
        print("=" * 60)
        
        # Test strategy factory
        factory = StrategyFactory()
        print("✓ StrategyFactory created successfully")
        
        # Test available strategies
        strategies = factory.get_available_strategies()
        print("✓ Available strategies:")
        for name, description in strategies.items():
            print(f"  - {name}: {description}")
        
        # Test prompt directories
        print("\n✓ Testing prompt directories:")
        
        # Test outline-chapter strategy
        outline_chapter_strategy = factory.create_strategy_with_prompts(
            "outline-chapter", None, None
        )
        outline_prompt_dir = outline_chapter_strategy.get_prompt_directory()
        print(f"  - outline-chapter: {outline_prompt_dir}")
        
        # Test stream-of-consciousness strategy
        stream_strategy = factory.create_strategy_with_prompts(
            "stream-of-consciousness", None, None
        )
        stream_prompt_dir = stream_strategy.get_prompt_directory()
        print(f"  - stream-of-consciousness: {stream_prompt_dir}")
        
        # Test prompt loaders
        print("\n✓ Testing prompt loaders:")
        
        outline_loader = PromptLoader(prompts_dir=outline_prompt_dir)
        print(f"  - outline-chapter prompt loader created")
        
        stream_loader = PromptLoader(prompts_dir=stream_prompt_dir)
        print(f"  - stream-of-consciousness prompt loader created")
        
        # Test strategy metadata
        print("\n✓ Testing strategy metadata:")
        print(f"  - outline-chapter:")
        print(f"    Name: {outline_chapter_strategy.get_strategy_name()}")
        print(f"    Version: {outline_chapter_strategy.get_strategy_version()}")
        print(f"    Description: {outline_chapter_strategy.get_strategy_description()}")
        print(f"    Required models: {outline_chapter_strategy.get_required_models()}")
        print(f"    Prompt directory: {outline_chapter_strategy.get_prompt_directory()}")
        
        print(f"  - stream-of-consciousness:")
        print(f"    Name: {stream_strategy.get_strategy_name()}")
        print(f"    Version: {stream_strategy.get_strategy_version()}")
        print(f"    Description: {stream_strategy.get_strategy_description()}")
        print(f"    Required models: {stream_strategy.get_required_models()}")
        print(f"    Prompt directory: {stream_strategy.get_prompt_directory()}")
        
        print("\n🎉 All tests passed! The strategy system with prompt organization is working correctly.")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_strategy_system()
    sys.exit(0 if success else 1) 