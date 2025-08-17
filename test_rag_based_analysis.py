#!/usr/bin/env python3
"""Test script for RAG-based story analysis in the progressive story generation system."""

import asyncio
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from application.strategies.outline_chapter.story_state_manager import StoryStateManager
from domain.value_objects.generation_settings import GenerationSettings


async def test_rag_based_analysis():
    """Test the RAG-based analysis capabilities of the Story State Manager."""
    
    print("=== Testing RAG-Based Story Analysis ===\n")
    
    # Mock config
    config = {
        "models": {
            "initial_outline_writer": "llama3.1:8b",
            "chapter_outline_writer": "llama3.1:8b",
            "logical_model": "llama3.1:8b"
        },
        "debug": True
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
    
    # Test settings
    settings = GenerationSettings(
        wanted_chapters=3,
        debug=True,
        stream=False,
        seed=42,
        log_prompt_inputs=False
    )
    
    # Test 1: Story context initialization
    print("\n1. Testing story context initialization...")
    try:
        context = await story_state_manager.initialize_story_context("Test prompt", settings)
        print(f"✓ Story context initialized: {context.story_direction}")
        print(f"   Themes: {context.current_themes}")
        print(f"   Tone: {context.tone_style}")
    except Exception as e:
        print(f"⚠ Could not test context initialization: {e}")
    
    # Test 2: Chapter planning
    print("\n2. Testing chapter planning...")
    try:
        chapter_state = await story_state_manager.plan_next_chapter(settings)
        print(f"✓ Chapter planned: {chapter_state.title}")
        print(f"   Status: {chapter_state.status}")
        print(f"   Events: {len(chapter_state.key_events)}")
    except Exception as e:
        print(f"⚠ Could not test chapter planning: {e}")
    
    # Test 3: RAG-based evolution analysis
    print("\n3. Testing RAG-based evolution analysis...")
    try:
        # Simulate a completed chapter
        story_state_manager.chapters[1] = chapter_state
        
        # Test evolution analysis
        await story_state_manager.update_story_evolution(1, settings)
        print(f"✓ Evolution analysis completed")
        print(f"   Evolution log entries: {len(story_state_manager.story_evolution)}")
        
        if story_state_manager.story_evolution:
            print(f"   Latest evolution: {story_state_manager.story_evolution[-1]}")
        
    except Exception as e:
        print(f"⚠ Could not test evolution analysis: {e}")
    
    # Test 4: RAG-based character analysis
    print("\n4. Testing RAG-based character analysis...")
    try:
        character_data = await story_state_manager.analyze_character_development_rag("Sarah", settings)
        print(f"✓ Character analysis completed")
        print(f"   Current role: {character_data['current_role']}")
        print(f"   Personality traits: {len(character_data['personality_traits'])}")
        print(f"   Motivations: {len(character_data['motivations'])}")
        print(f"   Current goals: {len(character_data['current_goals'])}")
        
    except Exception as e:
        print(f"⚠ Could not test character analysis: {e}")
    
    # Test 5: RAG-based plot analysis
    print("\n5. Testing RAG-based plot analysis...")
    try:
        plot_data = await story_state_manager.analyze_plot_threads_rag(settings)
        print(f"✓ Plot analysis completed")
        print(f"   Active threads: {len(plot_data['active_threads'])}")
        print(f"   Resolved threads: {len(plot_data['resolved_threads'])}")
        print(f"   New threads: {len(plot_data['new_threads'])}")
        
    except Exception as e:
        print(f"⚠ Could not test plot analysis: {e}")
    
    # Test 6: Story summary
    print("\n6. Testing story summary...")
    try:
        summary = story_state_manager.get_story_summary()
        print(f"✓ Story summary generated")
        print(f"   Summary length: {len(summary)} characters")
        print(f"   Summary preview: {summary[:100]}...")
        
    except Exception as e:
        print(f"⚠ Could not test story summary: {e}")
    
    print("\n=== RAG-Based Analysis Test Completed ===")


def demonstrate_rag_benefits():
    """Demonstrate the benefits of RAG-based analysis."""
    
    print("\n=== RAG-Based Analysis Benefits ===\n")
    
    print("1. **Scalability**")
    print("   - Traditional approach: Must read entire chapter content")
    print("   - RAG approach: Query specific aspects without memory limitations")
    print("   - Benefit: Works with stories of any length\n")
    
    print("2. **Context Awareness**")
    print("   - Traditional approach: Limited to current chapter context")
    print("   - RAG approach: Can reference any part of the story")
    print("   - Benefit: Better continuity and consistency analysis\n")
    
    print("3. **Efficient Analysis**")
    print("   - Traditional approach: Process entire text for each analysis")
    print("   - RAG approach: Targeted queries for specific information")
    print("   - Benefit: Faster analysis and better resource utilization\n")
    
    print("4. **Focused Insights**")
    print("   - Traditional approach: General analysis of entire content")
    print("   - RAG approach: Specific questions about specific aspects")
    print("   - Benefit: More relevant and actionable insights\n")
    
    print("5. **Memory Efficiency**")
    print("   - Traditional approach: Load entire chapters into memory")
    print("   - RAG approach: Retrieve only relevant information")
    print("   - Benefit: Lower memory usage and better performance\n")


if __name__ == "__main__":
    print("Starting RAG-Based Story Analysis Tests...\n")
    
    # Run tests
    asyncio.run(test_rag_based_analysis())
    
    # Demonstrate benefits
    demonstrate_rag_benefits()
    
    print("\nAll tests and demonstrations completed!")
