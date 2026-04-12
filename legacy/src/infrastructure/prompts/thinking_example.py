"""Example demonstrating the new thinking capture functionality."""

import asyncio
from typing import Dict, Any
from domain.value_objects.model_config import ModelConfig
from domain.value_objects.generation_settings import GenerationSettings
from .prompt_handler import PromptHandler, PromptRequest
from .prompt_loader import PromptLoader
from application.interfaces.model_provider import ModelProvider
from domain.repositories.savepoint_repository import SavepointRepository


async def example_thinking_capture():
    """Example of how thinking is captured and saved to savepoints."""
    
    # Setup dependencies (these would typically come from your DI container)
    model_provider: ModelProvider = None  # Your model provider instance
    prompt_loader = PromptLoader("src/application/strategies/prompts/outline-chapter")
    savepoint_repo: SavepointRepository = None  # Your savepoint repository instance
    
    # Create the prompt handler
    handler = PromptHandler(
        model_provider=model_provider,
        prompt_loader=prompt_loader,
        savepoint_repo=savepoint_repo
    )
    
    # Set story directory for savepoints
    handler.set_story_directory("thinking_example_story")
    
    # Example 1: Text prompt with thinking capture
    model_config = ModelConfig.from_string("ollama://llama3:70b?think=true")
    
    request = PromptRequest(
        prompt_id="extract_story_start_date",
        variables={
            "prompt": "A story set in Victorian London in 1892..."
        },
        savepoint_id="extract_story_start_date_with_thinking",
        model_config=model_config
    )
    
    response = await handler.execute_prompt(request)
    print(f"Response content: {response.content}")
    print(f"Was cached: {response.was_cached}")
    print(f"Execution time: {response.execution_time}")
    
    # Example 2: Load the full savepoint with metadata
    if savepoint_repo:
        full_savepoint = await savepoint_repo.load_savepoint_with_metadata("extract_story_start_date_with_thinking")
        if full_savepoint:
            print("\n=== Full Savepoint Data ===")
            print(f"Frontmatter: {full_savepoint['_frontmatter']}")
            print(f"Body content: {full_savepoint['_body']}")
            
            # Access specific metadata
            frontmatter = full_savepoint['_frontmatter']
            print(f"\n=== Metadata ===")
            print(f"Prompt ID: {frontmatter.get('prompt_id')}")
            print(f"Model used: {frontmatter.get('model_config', {}).get('name')}")
            print(f"Execution time: {frontmatter.get('execution_time')}")
            print(f"Thinking captured: {frontmatter.get('thinking') is not None}")
            if frontmatter.get('thinking'):
                print(f"Thinking content: {frontmatter['thinking']}")
    
    # Example 3: JSON prompt with thinking capture
    json_request = PromptRequest(
        prompt_id="extract_base_context",
        variables={
            "prompt": "A sci-fi story about space exploration..."
        },
        savepoint_id="extract_base_context_json_with_thinking",
        model_config=model_config
    )
    
    json_response = await handler.execute_json_prompt(
        json_request, 
        required_attributes=["setting", "time_period", "main_conflict"]
    )
    print(f"\nJSON response: {json_response}")
    
    # Example 4: Load JSON savepoint with metadata
    if savepoint_repo:
        json_savepoint = await savepoint_repo.load_savepoint_with_metadata("extract_base_context_json_with_thinking")
        if json_savepoint:
            print("\n=== JSON Savepoint Data ===")
            frontmatter = json_savepoint['_frontmatter']
            print(f"Frontmatter: {frontmatter}")
            print(f"JSON body: {json_savepoint['_body']}")


def explain_savepoint_structure():
    """Explain the new savepoint structure."""
    print("""
=== New Savepoint Structure ===

The prompt handler now captures thinking content and saves it to savepoints with the following structure:

1. FRONTMATTER (YAML):
   - prompt_id: The ID of the prompt used
   - input_prompt: The actual prompt content sent to the model
   - thinking: The model's thinking process (if captured)
   - prepend_message: Any message prepended to the prompt
   - system_message: The system message used
   - model_config: Model configuration details
   - seed: Random seed used
   - execution_time: Time taken to execute
   - timestamp: When the savepoint was created

2. BODY:
   - The actual response content from the model
   - For text prompts: The cleaned response text
   - For JSON prompts: The JSON response object

=== Usage ===

- Normal usage returns only the response content (backward compatible)
- Use load_savepoint_with_metadata() to get full data including thinking
- Thinking is automatically captured when the model supports it
- All metadata is preserved for later examination

=== Example Savepoint File ===

---
prompt_id: extract_story_start_date
input_prompt: "Extract the story start date from the following prompt..."
thinking: "I need to analyze this prompt for temporal information..."
model_config:
  name: llama3:70b
  provider: ollama
  parameters:
    think: true
seed: 42
execution_time: 2.5
timestamp: "2024-01-15T10:30:00"
---

# Savepoint: extract_story_start_date_with_thinking

The story begins in 1892 during the Victorian era in London.
    """)


if __name__ == "__main__":
    # Note: These examples require actual model provider and savepoint repository instances
    # asyncio.run(example_thinking_capture())
    explain_savepoint_structure()
    print("\nExamples are provided for reference. Uncomment and provide actual dependencies to run.") 