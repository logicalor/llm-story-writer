#!/usr/bin/env python3
"""Test script for RAG integration with prompt filename differentiation."""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from application.strategies.outline_chapter.strategy import OutlineChapterStrategy


async def test_rag_integration():
    """Test RAG integration with prompt filename differentiation."""
    print("🧪 Testing RAG Integration with Prompt Filename Differentiation")
    print("=" * 70)
    
    try:
        # Test 1: Strategy without RAG service
        print("\n1️⃣ Testing Strategy without RAG service...")
        strategy_no_rag = OutlineChapterStrategy(
            model_provider=None,  # Mock for testing
            config={},
            prompt_loader=None,   # Mock for testing
            savepoint_repo=None,  # Mock for testing
            rag_service=None      # No RAG service
        )
        
        print("   ✅ Strategy created without RAG service")
        print(f"   - RAG service: {strategy_no_rag.rag_service}")
        print(f"   - Outline generator RAG service: {strategy_no_rag.outline_generator.rag_service}")
        
        # Test 2: Strategy with RAG service
        print("\n2️⃣ Testing Strategy with RAG service...")
        
        # Create a mock RAG service
        class MockRAGService:
            def __init__(self):
                self.name = "MockRAGService"
                self._stories = {}
                self._next_id = 1
            
            def __str__(self):
                return self.name
            
            async def create_story(self, story_name: str, prompt_file_path: str) -> int:
                """Mock story creation that tracks prompt filename differentiation."""
                story_id = self._next_id
                self._next_id += 1
                self._stories[story_id] = {
                    "story_name": story_name,
                    "prompt_file_path": prompt_file_path
                }
                print(f"      📝 Mock RAG: Created story {story_id} for '{prompt_file_path}'")
                return story_id
        
        mock_rag_service = MockRAGService()
        
        strategy_with_rag = OutlineChapterStrategy(
            model_provider=None,  # Mock for testing
            config={
                "max_chunk_size": 1000,
                "overlap_size": 200
            },
            prompt_loader=None,   # Mock for testing
            savepoint_repo=None,  # Mock for testing
            rag_service=mock_rag_service  # With RAG service
        )
        
        print("   ✅ Strategy created with RAG service")
        print(f"   - RAG service: {strategy_with_rag.rag_service}")
        print(f"   - Outline generator RAG service: {strategy_with_rag.outline_generator.rag_service}")
        print(f"   - Outline generator RAG integration: {strategy_with_rag.outline_generator.rag_integration}")
        
        # Test 3: Test prompt filename differentiation
        print("\n3️⃣ Testing Prompt Filename Differentiation...")
        
        # Test with first prompt filename
        prompt_filename_1 = "story_1.txt"
        print(f"   📁 Setting up savepoints for: {prompt_filename_1}")
        
        # Mock savepoint repo for testing
        class MockSavepointRepo:
            def __init__(self):
                pass
            
            def set_story_directory(self, prompt_filename: str):
                """Mock method to set story directory."""
                pass
        
        strategy_with_rag.savepoint_repo = MockSavepointRepo()
        
        # Call _setup_savepoints to trigger RAG story initialization
        strategy_with_rag._setup_savepoints(prompt_filename_1)
        
        # Wait a bit for async initialization
        await asyncio.sleep(0.1)
        
        print(f"   ✅ RAG story initialized for: {prompt_filename_1}")
        print(f"   - RAG story ID: {strategy_with_rag.get_rag_story_id()}")
        print(f"   - Current prompt filename: {strategy_with_rag.get_current_prompt_filename()}")
        
        # Test with second prompt filename
        prompt_filename_2 = "story_2.txt"
        print(f"\n   📁 Setting up savepoints for: {prompt_filename_2}")
        
        strategy_with_rag._setup_savepoints(prompt_filename_2)
        
        # Wait a bit for async initialization
        await asyncio.sleep(0.1)
        
        print(f"   ✅ RAG story initialized for: {prompt_filename_2}")
        print(f"   - RAG story ID: {strategy_with_rag.get_rag_story_id()}")
        print(f"   - Current prompt filename: {strategy_with_rag.get_current_prompt_filename()}")
        
        # Test 4: Verify RAG status
        print("\n4️⃣ RAG Status Verification:")
        rag_status = strategy_with_rag.get_rag_status()
        for key, value in rag_status.items():
            print(f"   - {key}: {value}")
        
        # Test 5: Verify story isolation
        print("\n5️⃣ Story Isolation Verification:")
        print(f"   - Mock RAG stories created: {len(mock_rag_service._stories)}")
        for story_id, story_info in mock_rag_service._stories.items():
            print(f"     Story {story_id}: {story_info['story_name']} -> {story_info['prompt_file_path']}")
        
        # Verify that different prompt filenames created different stories
        if len(mock_rag_service._stories) == 2:
            print("   ✅ Different prompt filenames created separate RAG stories")
        else:
            print("   ❌ Expected 2 separate RAG stories")
            return False
        
        print("\n🎉 RAG integration with prompt filename differentiation test passed!")
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
