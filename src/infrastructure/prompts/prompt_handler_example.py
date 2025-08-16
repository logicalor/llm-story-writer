"""Example usage of the PromptHandler."""

import asyncio
from typing import Dict, Any
from domain.value_objects.model_config import ModelConfig
from domain.value_objects.generation_settings import GenerationSettings
from .prompt_handler import PromptHandler, PromptRequest
from .prompt_loader import PromptLoader
from application.interfaces.model_provider import ModelProvider
from domain.repositories.savepoint_repository import SavepointRepository


async def example_usage():
    """Example of how to use the PromptHandler."""
    
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
    handler.set_story_directory("my_story")
    
    # Example 1: Basic prompt execution
    model_config = ModelConfig.from_string("ollama://llama3:70b")
    
    request = PromptRequest(
        prompt_id="extract_story_start_date",
        variables={
            "prompt": "A story set in Victorian London in 1892..."
        },
        savepoint_id="extract_story_start_date",
        model_config=model_config
    )
    
    response = await handler.execute_prompt(request)
    print(f"Content: {response.content}")
    print(f"Was cached: {response.was_cached}")
    print(f"Execution time: {response.execution_time}")
    
    # Example 2: Force regeneration
    request.force_regenerate = True
    response = await handler.execute_prompt(request)
    print(f"Regenerated content: {response.content}")
    
    # Example 3: With prepend message and system message
    request = PromptRequest(
        prompt_id="generate_story_elements",
        variables={
            "prompt": "A fantasy story about a young wizard..."
        },
        savepoint_id="generate_story_elements",
        prepend_message="Please focus on creating unique and memorable characters.",
        system_message="You are an expert fantasy writer specializing in character development.",
        model_config=model_config
    )
    
    response = await handler.execute_prompt(request)
    print(f"Story elements: {response.content}")
    
    # Example 4: JSON prompt
    json_request = PromptRequest(
        prompt_id="extract_base_context",
        variables={
            "prompt": "A sci-fi story about space exploration..."
        },
        savepoint_id="extract_base_context_json",
        model_config=model_config
    )
    
    json_response = await handler.execute_json_prompt(
        json_request, 
        required_attributes=["setting", "time_period", "main_conflict"]
    )
    print(f"JSON response: {json_response}")
    
    # Example 5: Check savepoint status
    exists = await handler.check_savepoint_exists("extract_story_start_date")
    print(f"Savepoint exists: {exists}")
    
    # Example 6: List all savepoints
    savepoints = await handler.list_savepoints()
    print(f"Available savepoints: {list(savepoints.keys())}")


async def example_with_generation_settings():
    """Example using GenerationSettings from the existing codebase."""
    
    # Setup
    model_provider: ModelProvider = None
    prompt_loader = PromptLoader("src/application/strategies/prompts/outline-chapter")
    savepoint_repo: SavepointRepository = None
    
    handler = PromptHandler(
        model_provider=model_provider,
        prompt_loader=prompt_loader,
        savepoint_repo=savepoint_repo
    )
    
    # Create generation settings
    settings = GenerationSettings(
        model="ollama://llama3:70b",
        temperature=0.7,
        seed=42
    )
    
    # Convert to ModelConfig
    model_config = ModelConfig.from_string(settings.model)
    
    # Create request
    request = PromptRequest(
        prompt_id="generate_initial_outline",
        variables={
            "prompt": "A mystery novel about a detective solving a murder...",
            "story_elements": "Characters: Detective Sarah, Victim John, Suspects...",
            "base_context": "Setting: Small town in Maine, 1980s..."
        },
        savepoint_id="generate_initial_outline",
        model_config=model_config,
        seed=settings.seed,
        system_message="You are an expert mystery writer..."
    )
    
    response = await handler.execute_prompt(request)
    print(f"Outline: {response.content}")


if __name__ == "__main__":
    # Note: These examples require actual model provider and savepoint repository instances
    # asyncio.run(example_usage())
    # asyncio.run(example_with_generation_settings())
    print("Examples are provided for reference. Uncomment and provide actual dependencies to run.") 