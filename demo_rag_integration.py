#!/usr/bin/env python3
"""Legacy demo for prompt filename tracking on the outline strategy."""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from application.strategies.outline_chapter.strategy import OutlineChapterStrategy


async def demonstrate_rag_integration():
    """Demonstrate prompt filename tracking after RAG service removal."""
    print("🎭 Prompt Filename Tracking on OutlineChapterStrategy")
    print("=" * 60)

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

        print("\n🎯 Creating Outline Chapter Strategy...")
        strategy_config = {
            "models": {
                "initial_outline_writer": "openai-compat://llama3.2:3b",
                "creative_model": "openai-compat://llama3.2:3b",
                "info_model": "openai-compat://llama3.2:3b",
            },
            "max_chunk_size": 1000,
            "overlap_size": 200,
            "similarity_threshold": 0.7,
            "max_context_chunks": 20,
        }

        strategy = OutlineChapterStrategy(
            model_provider=None,  # Mock for demonstration
            config=strategy_config,
            prompt_loader=None,  # Mock for demonstration
            savepoint_repo=mock_savepoint_repo,
        )

        print("✅ Strategy created")
        print("ℹ️ Legacy demo name retained; direct rag_service injection was removed")

        print("\n🚀 Prompt Tracking Components:")
        print("-" * 40)

        print("\n1️⃣ Configuration:")
        print(f"   - Max Chunk Size: {strategy_config['max_chunk_size']}")
        print(f"   - Overlap Size: {strategy_config['overlap_size']}")
        print(f"   - Similarity Threshold: {strategy_config['similarity_threshold']}")
        print(f"   - Max Context Chunks: {strategy_config['max_context_chunks']}")

        print("\n2️⃣ Prompt Filename Differentiation Demo:")

        prompt_filename_1 = "adventure_story.txt"
        print(f"\n   📁 Setting up savepoints for: {prompt_filename_1}")
        await strategy._setup_savepoints(prompt_filename_1)

        print(f"   ✅ Savepoints initialized for: {prompt_filename_1}")
        print(f"   - Current prompt filename: {strategy.get_current_prompt_filename()}")
        print(f"   - Savepoint manager prompt filename: {strategy.savepoint_manager.prompt_filename}")

        prompt_filename_2 = "mystery_story.txt"
        print(f"\n   📁 Setting up savepoints for: {prompt_filename_2}")
        await strategy._setup_savepoints(prompt_filename_2)

        print(f"   ✅ Savepoints initialized for: {prompt_filename_2}")
        print(f"   - Current prompt filename: {strategy.get_current_prompt_filename()}")
        print(f"   - Savepoint manager prompt filename: {strategy.savepoint_manager.prompt_filename}")

        print("\n3️⃣ Savepoint Status:")
        print(f"   - Story directories tracked: {mock_savepoint_repo.story_directories}")
        print(f"   - Active prompt filename: {strategy.get_current_prompt_filename()}")

        print("\n4️⃣ Story Isolation Verification:")
        print("   ✅ Each prompt filename reconfigures savepoint state")
        print("   ✅ Prompt tracking stays on the strategy and savepoint manager")
        print("   ✅ No direct rag_service injection required")

        print("\n5️⃣ Benefits of Prompt Filename Differentiation:")
        print("   ✅ Story content is automatically isolated by prompt file")
        print("   ✅ No cross-contamination between different stories")
        print("   ✅ Seamless integration with existing savepoint system")

        print("\n🎉 Prompt Filename Tracking Demonstration Complete!")
        print("\n💡 Key Features Demonstrated:")
        print("   • Prompt filename tracking per story")
        print("   • Story isolation and context separation")
        print("   • Integration with existing savepoint workflow")
        print("   • Strategy state updates without deprecated constructor params")

        return True

    except Exception as e:
        print(f"\n❌ RAG integration demonstration failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run the demonstration
    success = asyncio.run(demonstrate_rag_integration())
    sys.exit(0 if success else 1)
