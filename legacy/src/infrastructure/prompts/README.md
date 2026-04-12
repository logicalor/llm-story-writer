# Prompt Handler System

This directory contains a comprehensive prompt handling system that manages savepoints and prompt execution with a clean, easy-to-use interface.

## Overview

The prompt handler system provides:

1. **Automatic savepoint management** - Check for existing savepoints and return cached results
2. **Flexible prompt execution** - Support for text and JSON responses
3. **Easy integration** - Simple wrapper functions for common use cases
4. **Rich metadata** - Execution time, caching status, and model information

## Components

### Core Classes

- **`PromptHandler`** - Main handler class that manages prompt execution and savepoints
- **`PromptRequest`** - Data class for specifying prompt execution parameters
- **`PromptResponse`** - Data class containing the response and metadata

### Wrapper Functions

- **`execute_prompt_with_savepoint`** - Simple wrapper for text prompts with savepoint management
- **`execute_prompt`** - Simple wrapper for text prompts without savepoint management
- **`execute_json_prompt_with_savepoint`** - Simple wrapper for JSON prompts with savepoint management
- **`execute_json_prompt`** - Simple wrapper for JSON prompts without savepoint management
- **`quick_prompt`** - Convenience function that creates a handler and executes a prompt

## Basic Usage

### 1. Create a PromptHandler

```python
from infrastructure.prompts.prompt_handler import PromptHandler
from infrastructure.prompts.prompt_loader import PromptLoader
from domain.value_objects.model_config import ModelConfig

# Setup dependencies
model_provider = your_model_provider
prompt_loader = PromptLoader("path/to/prompts")
savepoint_repo = your_savepoint_repository

# Create handler
handler = PromptHandler(
    model_provider=model_provider,
    prompt_loader=prompt_loader,
    savepoint_repo=savepoint_repo
)
```

### 2. Execute a Simple Prompt

```python
from infrastructure.prompts.prompt_wrapper import execute_prompt_with_savepoint

# Create model config
model_config = ModelConfig.from_string("ollama://llama3:70b")

# Execute prompt with savepoint management
response = await execute_prompt_with_savepoint(
    handler=handler,
    prompt_id="extract_story_start_date",
    variables={"prompt": "A story set in 1892..."},
    savepoint_id="extract_story_start_date",
    model_config=model_config
)

print(f"Content: {response.content}")
print(f"Was cached: {response.was_cached}")
print(f"Execution time: {response.execution_time}")
```

### 2b. Execute a Prompt Without Savepoint Management

```python
from infrastructure.prompts.prompt_wrapper import execute_prompt

# Execute prompt without savepoint management (savepoint_id is optional)
response = await execute_prompt(
    handler=handler,
    prompt_id="extract_story_start_date",
    variables={"prompt": "A story set in 1892..."},
    model_config=model_config
)

print(f"Content: {response.content}")
print(f"Execution time: {response.execution_time}")
```

### 3. Execute a JSON Prompt

```python
from infrastructure.prompts.prompt_wrapper import execute_json_prompt_with_savepoint

json_response = await execute_json_prompt_with_savepoint(
    handler=handler,
    prompt_id="extract_base_context",
    required_attributes=["setting", "time_period", "main_conflict"],
    variables={"prompt": "A sci-fi story..."},
    savepoint_id="extract_base_context_json",
    model_config=model_config
)

print(f"Setting: {json_response['setting']}")
```

### 3b. Execute a JSON Prompt Without Savepoint Management

```python
from infrastructure.prompts.prompt_wrapper import execute_json_prompt

json_response = await execute_json_prompt(
    handler=handler,
    prompt_id="extract_base_context",
    required_attributes=["setting", "time_period", "main_conflict"],
    variables={"prompt": "A sci-fi story..."},
    model_config=model_config
)

print(f"Setting: {json_response['setting']}")
```

### 4. Force Regeneration

```python
response = await execute_prompt_with_savepoint(
    handler=handler,
    prompt_id="generate_story_elements",
    variables={"prompt": "A fantasy story..."},
    savepoint_id="generate_story_elements",
    model_config=model_config,
    force_regenerate=True  # Ignore existing savepoint
)
```

### 5. Add Custom Messages

```python
response = await execute_prompt_with_savepoint(
    handler=handler,
    prompt_id="generate_chapter_content",
    variables={"chapter_num": 1, "outline": "..."},
    savepoint_id="chapter_1_content",
    prepend_message="Please focus on creating vivid descriptions.",
    system_message="You are an expert creative writer specializing in fantasy novels.",
    model_config=model_config
)
```

## Advanced Usage

### Direct PromptHandler Usage

```python
from infrastructure.prompts.prompt_handler import PromptRequest

request = PromptRequest(
    prompt_id="generate_initial_outline",
    variables={
        "prompt": "A mystery novel...",
        "story_elements": "Characters: Detective Sarah...",
        "base_context": "Setting: Small town..."
    },
    savepoint_id="generate_initial_outline",
    model_config=model_config,
    seed=42,
    system_message="You are an expert mystery writer...",
    force_regenerate=False
)

response = await handler.execute_prompt(request)
```

### Savepoint Management

```python
# Check if savepoint exists
exists = await handler.check_savepoint_exists("my_savepoint")

# Load savepoint directly
content = await handler.load_savepoint("my_savepoint")

# Delete savepoint
deleted = await handler.delete_savepoint("my_savepoint")

# List all savepoints
savepoints = await handler.list_savepoints()

# Clear all savepoints
await handler.clear_all_savepoints()
```

### Set Story Directory

```python
# Set directory for savepoints (useful for organizing by story)
handler.set_story_directory("my_fantasy_novel")
```

## Integration with Existing Strategy

You can easily integrate this with your existing `OutlineChapterStrategy`:

```python
class EnhancedOutlineChapterStrategy:
    def __init__(self, model_provider, prompt_loader, savepoint_repo):
        self.prompt_handler = PromptHandler(
            model_provider=model_provider,
            prompt_loader=prompt_loader,
            savepoint_repo=savepoint_repo
        )
    
    async def extract_story_start_date(self, prompt: str, settings: GenerationSettings) -> str:
        model_config = ModelConfig.from_string(settings.model)
        
        response = await execute_prompt_with_savepoint(
            handler=self.prompt_handler,
            prompt_id="extract_story_start_date",
            variables={"prompt": prompt},
            savepoint_id="extract_story_start_date",
            model_config=model_config,
            seed=settings.seed
        )
        
        return response.content
```

## Parameters

### PromptRequest Parameters

- **`prompt_id`** (str) - ID of the prompt to execute
- **`variables`** (Dict[str, Any], optional) - Variables to substitute in the prompt
- **`savepoint_id`** (str, optional) - ID for the savepoint. If `None` or not provided, no savepoint management is performed
- **`prepend_message`** (str, optional) - Message to prepend to the prompt
- **`model_config`** (ModelConfig, optional) - Model configuration to use
- **`force_regenerate`** (bool) - Force regeneration even if savepoint exists
- **`system_message`** (str, optional) - System message for the model
- **`seed`** (int, optional) - Random seed for reproducible results
- **`format_type`** (str, optional) - Format type for the response
- **`min_word_count`** (int) - Minimum word count for the response
- **`debug`** (bool) - Enable debug mode
- **`stream`** (bool) - Enable streaming response

### PromptResponse Fields

- **`content`** (str) - The generated content
- **`savepoint_id`** (str, optional) - The savepoint ID used
- **`was_cached`** (bool) - Whether the result was loaded from cache
- **`model_used`** (str, optional) - The model that was used
- **`execution_time`** (float, optional) - Time taken to execute the prompt

## Error Handling

The prompt handler includes comprehensive error handling:

- **Prompt loading errors** - Wrapped in `StoryGenerationError`
- **Model execution errors** - Wrapped in `StoryGenerationError`
- **Savepoint errors** - Logged as warnings but don't fail the request

## Optional Savepoint Management

The `savepoint_id` parameter is optional in all wrapper functions. When `savepoint_id` is `None` or not provided:

- **No savepoint checking** - The prompt will always be executed fresh
- **No savepoint saving** - Results won't be cached for future use
- **Faster execution** - No savepoint repository operations
- **Simpler API** - Use `execute_prompt()` instead of `execute_prompt_with_savepoint()`

This is useful for:
- **One-off prompts** that don't need caching
- **Testing and debugging** without savepoint overhead
- **Real-time applications** where caching isn't desired
- **Simple integrations** where savepoint management isn't needed

## Best Practices

1. **Use descriptive savepoint IDs** - Make them unique and meaningful
2. **Set story directories** - Organize savepoints by story
3. **Handle force_regenerate carefully** - Only use when you need fresh results
4. **Use system messages** - Provide context for better results
5. **Monitor execution times** - Use the metadata to optimize performance
6. **Choose the right wrapper** - Use `execute_prompt()` for simple cases, `execute_prompt_with_savepoint()` when caching is needed

## Examples

See the following files for complete examples:

- `prompt_handler_example.py` - Basic usage examples
- `usage_example.py` - Integration with existing strategy
- `prompt_wrapper.py` - Simple wrapper functions 