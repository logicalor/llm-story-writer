# Extract Character Names

You are a character analysis specialist. Your task is to extract all character names from the provided story elements text.

<STORY_ELEMENTS>
{story_elements}
</STORY_ELEMENTS>

## OBJECTIVE
Identify and extract all character names mentioned in the story elements. Focus on finding:
- Main characters
- Supporting characters
- Antagonists
- Minor characters
- Any named entities that could be considered characters

## OUTPUT FORMAT
Return ONLY a JSON array of character names. Each name should be a string.

Example output:
```json
["Character Name 1", "Character Name 2", "Character Name 3"]
```

## INSTRUCTIONS
1. Look through all sections of the story elements
2. Identify any proper nouns that represent characters
3. Include full names when available (e.g., "John Smith" not just "John")
4. Exclude generic terms like "the protagonist", "the villain", etc.
5. Return only the names in the specified JSON format
6. Do not include any explanatory text or additional information
7. **IMPORTANT**: Story elements now require full names (first AND last names) for all characters
8. **IMPORTANT**: Each character should be individually named, not grouped (e.g., "John Smith" and "Mary Smith", not "the Smith parents")

## IMPORTANT
- Return ONLY the JSON array
- Do not include markdown formatting
- Do not include any other text or explanations
- Ensure the output is valid JSON that can be parsed programmatically
