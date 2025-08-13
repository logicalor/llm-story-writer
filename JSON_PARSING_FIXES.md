# JSON Parsing Fixes for Character and Setting Extraction

## Problem Identified

The character and setting extraction methods were not properly parsing JSON responses from LLMs. The system was getting raw markdown with backticks instead of extracting the actual JSON content, leading to errors like:

```
[PROMPT TIMING] characters/create_abridged | Model: huihui_ai/magistral-abliterated:24b | Duration: 106.48s (savepoint: characters/```json/sheet-abridged)
[CHARACTER ABRIDGED] Generated abridged summary for ```json
[CHARACTER SHEETS] Generating sheet for: ```
```

## Root Cause

The extraction methods were using simple line-by-line parsing instead of JSON parsing, even though the prompts explicitly requested JSON output format:

- `characters/extract_names.md` - Expects JSON array output
- `characters/extract_from_chapter.md` - Expects JSON array output  
- `settings/extract_names.md` - Expects JSON array output
- `settings/extract_from_chapter.md` - Expects JSON array output

## Solution Implemented

Updated all extraction methods to properly parse JSON responses with fallback to line parsing:

### 1. JSON Parsing Priority
- **Primary**: Look for JSON content wrapped in markdown backticks (```json [...] ```)
- **Secondary**: Look for JSON arrays without backticks
- **Fallback**: Line-by-line parsing for compatibility

### 2. Methods Fixed

#### Character Manager
- `extract_character_names()` - Extract from story elements
- `extract_chapter_characters()` - Extract from chapter synopsis
- `extract_chapter_characters_from_outline()` - Extract from chapter outline

#### Setting Manager  
- `extract_setting_names()` - Extract from story elements
- `extract_chapter_settings()` - Extract from chapter synopsis

### 3. Parsing Logic

```python
# First try to parse as JSON (the expected format)
try:
    # Look for JSON content wrapped in markdown backticks
    json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', names_text, re.DOTALL)
    if json_match:
        json_content = json_match.group(1)
        parsed_names = json.loads(json_content)
        if isinstance(parsed_names, list):
            character_names = [str(name).strip() for name in parsed_names if name and str(name).strip()]
    else:
        # Try to find JSON array without backticks
        json_match = re.search(r'(\[.*?\])', names_text, re.DOTALL)
        if json_match:
            json_content = json_match.group(1)
            parsed_names = json.loads(json_content)
            # ... process names
            
except (json.JSONDecodeError, AttributeError) as e:
    # Fallback to line-by-line parsing
    # ... existing line parsing logic
```

## Benefits

1. **Correct JSON Parsing**: Now properly extracts character/setting names from JSON responses
2. **Robust Fallback**: Maintains compatibility with non-JSON responses
3. **Better Debugging**: Clear logging of parsing success/failure
4. **Consistent Behavior**: All extraction methods now work the same way
5. **LLM Compatibility**: Works with various LLM response formats

## Expected Output Format

The prompts now correctly expect and parse JSON arrays like:

```json
["John Smith", "Mary Johnson", "David Wilson"]
```

Instead of getting raw markdown like:

```
```json
["John Smith", "Mary Johnson", "David Wilson"]
```
```

## Testing

All modified files compile without syntax errors:
- ✅ `character_manager.py`
- ✅ `setting_manager.py`

## Future Considerations

- Consider standardizing all LLM responses to use consistent JSON formatting
- Add validation for extracted names (e.g., minimum length, format requirements)
- Implement retry logic for malformed JSON responses
- Add unit tests for JSON parsing edge cases
