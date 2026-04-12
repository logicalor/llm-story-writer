# Extract Setting Names

You are a setting analysis specialist. Your task is to extract all setting names and locations from the provided story elements text.

<STORY_ELEMENTS>
{story_elements}
</STORY_ELEMENTS>

## OBJECTIVE
Identify and extract all setting names and locations mentioned in the story elements. Focus on finding:
- Primary locations
- Secondary locations
- Important landmarks

## OUTPUT FORMAT
Return ONLY a JSON array of setting names. Each setting should be a string.

Example output:
```json
["Setting Name 1", "Setting Name 2", "Setting Name 3"]
```

## INSTRUCTIONS
1. Look through all sections of the story elements
2. Identify any proper nouns that represent locations or settings
3. Include full names when available (e.g., "Downtown District" not just "Downtown")
4. Return only the names in the specified JSON format
5. Do not include any explanatory text or additional information
6. **IMPORTANT**: Each setting should be individually named, not grouped

## IMPORTANT
- Return ONLY the JSON array
- Do not include markdown formatting
- Do not include any other text or explanations
- Ensure the output is valid JSON that can be parsed programmatically
