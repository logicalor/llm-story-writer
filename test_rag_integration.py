#!/usr/bin/env python3
"""Legacy smoke test for prompt filename tracking on the outline strategy."""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from application.strategies.outline_chapter.strategy import OutlineChapterStrategy


async def test_rag_integration():
    """Test prompt filename tracking after RAG service removal."""
    print("🧪 Testing Prompt Filename Tracking on OutlineChapterStrategy")
    print("=" * 70)

    try:
        class MockSavepointRepo:
            def __init__(self):
                self.story_directories = []
                self._current_story_dir = None

            def set_story_directory(self, prompt_filename: str):
                """Mock method to track story directory updates."""
                self.story_directories.append(prompt_filename)
                self._current_story_dir = f"/tmp/{prompt_filename}"

        mock_savepoint_repo = MockSavepointRepo()

        print("\n1️⃣ Testing strategy creation...")
        strategy = OutlineChapterStrategy(
            model_provider=None,  # Mock for testing
            config={},
            prompt_loader=None,  # Mock for testing
            savepoint_repo=mock_savepoint_repo,
        )

        print("   ✅ Strategy created")
        print(f"   - Current prompt filename: {strategy.get_current_prompt_filename()}")

        print("\n2️⃣ Testing prompt filename differentiation...")

        prompt_filename_1 = "story_1.txt"
        print(f"   📁 Setting up savepoints for: {prompt_filename_1}")
        await strategy._setup_savepoints(prompt_filename_1)

        print(f"   ✅ Savepoints initialized for: {prompt_filename_1}")
        print(f"   - Current prompt filename: {strategy.get_current_prompt_filename()}")
        print(f"   - Savepoint manager prompt filename: {strategy.savepoint_manager.prompt_filename}")

        prompt_filename_2 = "story_2.txt"
        print(f"\n   📁 Setting up savepoints for: {prompt_filename_2}")

        await strategy._setup_savepoints(prompt_filename_2)

        print(f"   ✅ Savepoints initialized for: {prompt_filename_2}")
        print(f"   - Current prompt filename: {strategy.get_current_prompt_filename()}")
        print(f"   - Savepoint manager prompt filename: {strategy.savepoint_manager.prompt_filename}")

        print("\n3️⃣ Savepoint tracking verification:")
        print(f"   - Story directories tracked: {mock_savepoint_repo.story_directories}")

        if strategy.get_current_prompt_filename() != prompt_filename_2:
            print("   ❌ Current prompt filename did not update")
            return False

        if strategy.savepoint_manager is None:
            print("   ❌ Savepoint manager was not initialized")
            return False

        if strategy.savepoint_manager.prompt_filename != prompt_filename_2:
            print("   ❌ Savepoint manager prompt filename did not update")
            return False

        if mock_savepoint_repo.story_directories != [
            prompt_filename_1,
            prompt_filename_1,
            prompt_filename_2,
            prompt_filename_2,
        ]:
            print("   ❌ Expected prompt filename tracking updates were not recorded")
            return False

        print("\n🎉 Prompt filename tracking smoke test passed!")
        return True

    except Exception as e:
        print(f"\n❌ RAG integration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run the test
    success = asyncio.run(test_rag_integration())
    sys.exit(0 if success else 1)
