# Extract Characters from Chapter Outline

You are a character analysis specialist. Your task is to extract ONLY the named characters that appear in the **Characters & Setting** sections of the provided chapter outline.

<CHAPTER_OUTLINE>
{chapter_synopsis}
</CHAPTER_OUTLINE>

## OBJECTIVE
Extract ONLY characters that meet ALL of these criteria:
1. **Listed in "Characters & Setting" sections** - Look for lines that start with "Character:" or "- Character:"
2. **Have full names** - Must include both first and last name (e.g., "John Smith")
3. **Are actual named people** - Not abstract references, titles, or generic descriptions

## WHAT TO INCLUDE
- ✅ "Character: Amy Harris - 11-year-old girl" → Extract "Amy Harris"
- ✅ "Character: David Harris - her father" → Extract "David Harris" 
- ✅ "- Character: Sarah Thompson - teacher" → Extract "Sarah Thompson"

## WHAT TO EXCLUDE
- ❌ "Character: Amy - young girl" → Skip (no last name)
- ❌ "Character: The Doctor - elderly man" → Skip (no actual name)
- ❌ "Character: Mrs. Johnson" → Skip (no first name)
- ❌ Characters mentioned elsewhere in the outline but not in "Characters & Setting" sections

## OUTPUT FORMAT
Return ONLY a JSON array of character names. Each name should be a string.

Example output:
```json
["Amy Harris", "David Harris", "Sarah Harris"]
```

## EXTRACTION PROCESS
1. **Scan for "Characters & Setting" sections** - Look for headers like "- **Characters & Setting:**" or "**Characters & Setting:**"
2. **Find character lines** - Look for lines that start with "Character:" or "- Character:"  
3. **Extract full names only** - Must have both first AND last name
4. **Verify it's a person's name** - Not a title, role, or generic description
5. **Return in JSON format** - Array of strings with full names only

## STRICT RULES
- **ONLY extract from "Characters & Setting" sections** - Ignore character mentions elsewhere
- **REQUIRE full names** - Both first and last name must be present
- **NO titles or roles** - Skip "The Doctor", "Mrs. Smith", "Captain Jones" 
- **NO partial names** - Skip "Amy", "David", "Sarah" without last names
- **NO generic descriptions** - Skip "the protagonist", "her father", "the teacher"

## EXAMPLE

**Input outline excerpt:**
```
## Scene: Morning Routine

- **Characters & Setting:**
  - Character: Amy Harris - 11-year-old girl with a sketchbook
  - Character: David Harris - her father, woodworker  
  - Character: The Teacher - elderly woman
  - Location: Family kitchen
  
Amy talks to her father about school...
```

**Correct output:**
```json
["Amy Harris", "David Harris"]
```

**Note:** "The Teacher" is excluded because it's not a full name.

## IMPORTANT
- Return ONLY the JSON array
- Do not include markdown formatting  
- Do not include any other text or explanations
- Ensure the output is valid JSON that can be parsed programmatically
- If no characters with full names are found, return an empty array: []
