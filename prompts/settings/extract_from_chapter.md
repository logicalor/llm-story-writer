# Extract Settings from Chapter Synopsis

You are a setting analysis specialist. Your task is to extract all setting/location names that appear or are mentioned in the provided chapter synopsis.

<CHAPTER_SYNOPSIS>
{chapter_synopsis}
</CHAPTER_SYNOPSIS>

## OBJECTIVE
Identify and extract all setting/location names mentioned in the chapter synopsis. This includes:
- Primary locations where scenes take place
- Secondary locations that are mentioned or referenced
- Buildings, rooms, or specific places
- Geographic locations (cities, regions, etc.)
- Any named places that could be considered settings

## OUTPUT FORMAT
Return ONLY a JSON array of setting names. Each name should be a string.

Example output:
```json
["Setting Name 1", "Setting Name 2", "Setting Name 3"]
```

## INSTRUCTIONS
1. Look through the entire chapter synopsis carefully
2. Identify any proper nouns that represent locations or settings
3. Include specific place names when available
4. Exclude generic terms like "the house", "the office", etc. unless they have specific names
5. Return only the names in the specified JSON format
6. Do not include any explanatory text or additional information
7. **IMPORTANT**: Use specific names when they are provided (e.g., "Blackwood Manor" not just "manor")
8. **IMPORTANT**: Each setting should be individually named

## IMPORTANT
- Return ONLY the JSON array
- Do not include markdown formatting
- Do not include any other text or explanations
- Ensure the output is valid JSON that can be parsed programmatically
- If no settings are found, return an empty array: []
