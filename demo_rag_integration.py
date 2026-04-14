#!/usr/bin/env python3
"""Demonstration script for RAG integration with prompt filename differentiation."""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from application.strategies.outline_chapter.strategy import OutlineChapterStrategy


async def demonstrate_rag_integration():
    """Demonstrate RAG integration with prompt filename differentiation."""
    print("🎭 RAG Integration with Prompt Filename Differentiation")
    print("=" * 60)
    
    try:
        # Create a mock RAG service for demonstration
        class MockRAGService:
            def __init__(self):
                self.name = "MockRAGService"
                self.description = "A mock RAG service for demonstration purposes"
                self._stories = {}
                self._next_id = 1
            
            def __str__(self):
                return self.name
            
            async def create_story(self, story_name: str, prompt_file_path: str) -> int:
                """Mock story creation that demonstrates prompt filename differentiation."""
                story_id = self._next_id
                self._next_id += 1
                self._stories[story_id] = {
                    "story_name": story_name,
                    "prompt_file_path": prompt_file_path
                }
                print(f"      📝 Created RAG story {story_id} for '{prompt_file_path}'")
                return story_id
        
        mock_rag_service = MockRAGService()
        
        # Demonstrate strategy creation with RAG
        print("\n🎯 Creating Outline Chapter Strategy with RAG...")
        strategy_config = {
            "models": {
                "initial_outline_writer": "ollama://llama3.2:3b",
                "creative_model": "ollama://llama3.2:3b",
                "info_model": "ollama://llama3.2:3b"
            },
            "max_chunk_size": 1000,
            "overlap_size": 200,
            "similarity_threshold": 0.7,
            "max_context_chunks": 20
        }
        
        strategy = OutlineChapterStrategy(
            model_provider=None,  # Mock for demonstration
            config=strategy_config,
            prompt_loader=None,   # Mock for demonstration
            savepoint_repo=None,  # Mock for demonstration
            rag_service=mock_rag_service
        )
        
        print("✅ Strategy created with RAG integration")
        
        # Demonstrate RAG integration components
        print("\n🚀 RAG Integration Components:")
        print("-" * 40)
        
        # 1. RAG Service
        print("\n1️⃣ RAG Service:")
        print(f"   - Service: {strategy.rag_service}")
        print(f"   - Type: {type(strategy.rag_service).__name__}")
        
        # 2. Outline Generator RAG Integration
        print("\n2️⃣ Outline Generator RAG Integration:")
        print(f"   - RAG Service: {strategy.outline_generator.rag_service}")
        print(f"   - RAG Integration: {strategy.outline_generator.rag_integration}")
        print(f"   - Integration Type: {type(strategy.outline_generator.rag_integration).__name__}")
        
        # 3. Configuration
        print("\n3️⃣ Configuration:")
        print(f"   - Max Chunk Size: {strategy_config['max_chunk_size']}")
        print(f"   - Overlap Size: {strategy_config['overlap_size']}")
        print(f"   - Similarity Threshold: {strategy_config['similarity_threshold']}")
        print(f"   - Max Context Chunks: {strategy_config['max_context_chunks']}")
        
        # 4. Demonstrate prompt filename differentiation
        print("\n4️⃣ Prompt Filename Differentiation Demo:")
        
        # Mock savepoint repo for demonstration
        class MockSavepointRepo:
            def __init__(self):
                pass
            
            def set_story_directory(self, prompt_filename: str):
                """Mock method to set story directory."""
                pass
        
        strategy.savepoint_repo = MockSavepointRepo()
        
        # Test with first prompt filename
        prompt_filename_1 = "adventure_story.txt"
        print(f"\n   📁 Setting up savepoints for: {prompt_filename_1}")
        strategy._setup_savepoints(prompt_filename_1)
        
        # Wait for async initialization
        await asyncio.sleep(0.1)
        
        print(f"   ✅ RAG story initialized for: {prompt_filename_1}")
        print(f"   - RAG story ID: {strategy.get_rag_story_id()}")
        print(f"   - Current prompt filename: {strategy.get_current_prompt_filename()}")
        
        # Test with second prompt filename
        prompt_filename_2 = "mystery_story.txt"
        print(f"\n   📁 Setting up savepoints for: {prompt_filename_2}")
        strategy._setup_savepoints(prompt_filename_2)
        
        # Wait for async initialization
        await asyncio.sleep(0.1)
        
        print(f"   ✅ RAG story initialized for: {prompt_filename_2}")
        print(f"   - RAG story ID: {strategy.get_rag_story_id()}")
        print(f"   - Current prompt filename: {strategy.get_current_prompt_filename()}")
        
        # 5. Show RAG status
        print("\n5️⃣ RAG Status:")
        rag_status = strategy.get_rag_status()
        for key, value in rag_status.items():
            print(f"   - {key}: {value}")
        
        # 6. Demonstrate story isolation
        print("\n6️⃣ Story Isolation Verification:")
        print(f"   - Total RAG stories created: {len(mock_rag_service._stories)}")
        for story_id, story_info in mock_rag_service._stories.items():
            print(f"     Story {story_id}: {story_info['story_name']} -> {story_info['prompt_file_path']}")
        
        # 7. Show the benefits
        print("\n7️⃣ Benefits of Prompt Filename Differentiation:")
        print("   ✅ Each prompt filename gets its own RAG story context")
        print("   ✅ Story content is automatically isolated by prompt file")
        print("   ✅ No cross-contamination between different stories")
        print("   ✅ RAG operations are automatically scoped to the current story")
        print("   ✅ Seamless integration with existing savepoint system")
        
        print("\n🎉 RAG Integration with Prompt Filename Differentiation Complete!")
        print("\n💡 Key Features Demonstrated:")
        print("   • Automatic RAG story creation per prompt filename")
        print("   • Story isolation and context separation")
        print("   • Integration with existing savepoint workflow")
        print("   • Foundation for RAG-enhanced story generation")
        
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
