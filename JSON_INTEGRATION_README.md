# LiteLLMJson Integration for AIStoryWriter

This document describes the new LiteLLMJson integration that consolidates manual JSON extraction into a centralized, schema-driven approach.

## Overview

The `execute_prompt_with_savepoint` function now supports automatic JSON parsing and validation using [LiteLLMJson](https://pypi.org/project/LiteLLMJson/). This eliminates the need for manual regex-based JSON extraction and provides consistent, reliable JSON parsing across all prompts.

## New Parameters

### `execute_prompt_with_savepoint` Function

```python
async def execute_prompt_with_savepoint(
    handler: PromptHandler,
    prompt_id: str,
    variables: Optional[Dict[str, Any]] = None,
    savepoint_id: Optional[str] = None,
    prepend_message: Optional[str] = None,
    model_config: Optional[ModelConfig] = None,
    force_regenerate: bool = False,
    system_message: Optional[str] = None,
    expect_json: bool = False,           # NEW: Enable JSON parsing
    json_schema: Optional[Dict[str, Any]] = None,  # NEW: JSON schema for validation
    **kwargs
) -> PromptResponse:
```

### `PromptRequest` Class

```python
@dataclass
class PromptRequest:
    # ... existing fields ...
    expect_json: bool = False           # NEW: Whether to expect JSON response
    json_schema: Optional[Dict[str, Any]] = None  # NEW: JSON schema for parsing
```

### `PromptResponse` Class

```python
@dataclass
class PromptResponse:
    # ... existing fields ...
    json_parsed: bool = False           # NEW: Whether JSON parsing succeeded
    json_errors: Optional[str] = None   # NEW: JSON parsing error details
```

## Usage Examples

### 1. Scene Definitions with JSON Schema

```python
# Define the JSON schema
SCENE_DEFINITIONS_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "description": {"type": "string"},
            "characters": {"type": "array", "items": {"type": "string"}},
            "setting": {"type": "string"},
            "conflict": {"type": "string"},
            "tone": {"type": "string"},
            "key_events": {"type": "array", "items": {"type": "string"}},
            "dialogue": {"type": "string"},
            "resolution": {"type": "string"},
            "lead_in": {"type": "string"}
        },
        "required": ["title", "description", "characters", "setting", "conflict", "tone", "key_events", "dialogue", "resolution", "lead_in"]
    }
}

# Execute prompt with JSON parsing
response = await execute_prompt_with_savepoint(
    handler=self.prompt_handler,
    prompt_id="chapters/parse_scene_definitions",
    variables={"chapter_outline": chapter_outline},
    savepoint_id=f"chapter_{chapter_num}/scene_definitions",
    model_config=model_config,
    seed=settings.seed,
    debug=settings.debug,
    stream=settings.stream,
    log_prompt_inputs=settings.log_prompt_inputs,
    system_message=self.system_message,
    expect_json=True,                    # Enable JSON parsing
    json_schema=SCENE_DEFINITIONS_SCHEMA # Provide schema
)

# Handle the response
if response.json_parsed:
    scene_definitions = json.loads(response.content)
    print(f"Successfully parsed {len(scene_definitions)} scene definitions")
else:
    print(f"JSON parsing failed: {response.json_errors}")
    # Fallback to manual parsing if needed
```

### 2. Character Sheets with JSON Schema

```python
CHARACTER_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "role": {"type": "string"},
            "description": {"type": "string"},
            "personality": {"type": "string"},
            "goals": {"type": "array", "items": {"type": "string"}},
            "conflicts": {"type": "array", "items": {"type": "string"}},
            "development_arc": {"type": "string"}
        },
        "required": ["name", "role", "description", "personality", "goals", "conflicts", "development_arc"]
    }
}

response = await execute_prompt_with_savepoint(
    handler=self.prompt_handler,
    prompt_id="chapters/create_character_sheet",
    variables={"character_name": "John Doe"},
    savepoint_id=f"chapter_{chapter_num}/character_sheet",
    model_config=model_config,
    expect_json=True,
    json_schema=CHARACTER_SCHEMA
)
```

### 3. Convenience Function

For JSON-specific prompts, you can use the convenience function:

```python
from src.infrastructure.prompts.prompt_wrapper import execute_json_prompt_with_savepoint_lite

response = await execute_json_prompt_with_savepoint_lite(
    handler=self.prompt_handler,
    prompt_id="chapters/parse_scene_definitions",
    json_schema=SCENE_DEFINITIONS_SCHEMA,
    variables={"chapter_outline": chapter_outline},
    savepoint_id=f"chapter_{chapter_num}/scene_definitions",
    model_config=model_config
)
```

## Migration Guide

### Before (Manual JSON Extraction)

```python
# Old way with manual parsing
response = await execute_prompt_with_savepoint(
    handler=self.prompt_handler,
    prompt_id="chapters/parse_scene_definitions",
    variables={"chapter_outline": chapter_outline},
    savepoint_id=f"chapter_{chapter_num}/scene_definitions",
    model_config=model_config
)

# Manual JSON extraction
try:
    json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response.content, re.DOTALL)
    if json_match:
        json_content = json_match.group(1)
        scene_definitions = json.loads(json_content)
    else:
        json_match = re.search(r'(\[.*?\])', response.content, re.DOTALL)
        if json_match:
            json_content = json_match.group(1)
            scene_definitions = json.loads(json_content)
        else:
            scene_definitions = json.loads(response.content)
    
    if isinstance(scene_definitions, list):
        expected_scene_count = len(scene_definitions)
    else:
        raise ValueError("Expected JSON array of scenes")
        
except (json.JSONDecodeError, ValueError) as e:
    print(f"JSON parsing failed: {e}")
    scene_definitions = []
```

### After (Automatic JSON Parsing)

```python
# New way with automatic parsing
response = await execute_prompt_with_savepoint(
    handler=self.prompt_handler,
    prompt_id="chapters/parse_scene_definitions",
    variables={"chapter_outline": chapter_outline},
    savepoint_id=f"chapter_{chapter_num}/scene_definitions",
    model_config=model_config,
    expect_json=True,
    json_schema=SCENE_DEFINITIONS_SCHEMA
)

# Automatic JSON handling
if response.json_parsed:
    scene_definitions = json.loads(response.content)
    expected_scene_count = len(scene_definitions)
else:
    print(f"JSON parsing failed: {response.json_errors}")
    scene_definitions = []
```

## Benefits

1. **Centralized Logic**: All JSON parsing is handled in one place
2. **Schema Validation**: Automatic validation against defined schemas
3. **Error Handling**: Clear error messages and fallback behavior
4. **Consistency**: Same behavior across all prompts
5. **Debugging**: Better visibility into parsing success/failure
6. **Maintainability**: No more scattered regex patterns
7. **Reliability**: LiteLLMJson handles edge cases and malformed responses

## Error Handling

The system gracefully handles JSON parsing failures:

- If `expect_json=True` but no schema is provided, JSON parsing is skipped
- If JSON parsing fails, the original response content is preserved
- Error details are available in `response.json_errors`
- The `response.json_parsed` flag indicates success/failure

## Dependencies

Make sure to install LiteLLMJson:

```bash
pip install LiteLLMJson>=0.0.1
```

Or add to your requirements.txt:

```
LiteLLMJson>=0.0.1
```

## Backward Compatibility

This integration is fully backward compatible:

- Existing code continues to work unchanged
- New JSON parameters are optional
- No breaking changes to existing APIs
- Gradual migration is possible

## Testing

Run the test script to see the integration in action:

```bash
python test_litellm_json_integration.py
```

## Future Enhancements

Potential future improvements:

1. **Schema Caching**: Cache compiled schemas for performance
2. **Validation Levels**: Different strictness levels for parsing
3. **Custom Parsers**: Support for custom parsing logic
4. **Batch Processing**: Handle multiple JSON responses efficiently
5. **Schema Evolution**: Support for schema versioning and migration
