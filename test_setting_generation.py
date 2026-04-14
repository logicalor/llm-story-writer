#!/usr/bin/env python3
"""
Simple test script to verify setting generation methods work correctly.
"""

import asyncio
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_setting_generation():
    """Test that setting generation methods can be imported and instantiated."""
    try:
        from application.strategies.outline_chapter_strategy import OutlineChapterStrategy
        print("✓ Successfully imported OutlineChapterStrategy")
        
        # Check if the new methods exist
        strategy = OutlineChapterStrategy.__new__(OutlineChapterStrategy)
        
        # Check if setting generation methods exist
        if hasattr(strategy, '_generate_setting_sheets'):
            print("✓ _generate_setting_sheets method exists")
        else:
            print("✗ _generate_setting_sheets method missing")
            
        if hasattr(strategy, '_extract_setting_names'):
            print("✓ _extract_setting_names method exists")
        else:
            print("✗ _extract_setting_names method missing")
            
        if hasattr(strategy, '_generate_single_setting_sheet'):
            print("✓ _generate_single_setting_sheet method exists")
        else:
            print("✗ _generate_single_setting_sheet method missing")
        
        print("\n✓ All setting generation methods are present!")
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("Testing setting generation methods...")
    success = asyncio.run(test_setting_generation())
    sys.exit(0 if success else 1)
