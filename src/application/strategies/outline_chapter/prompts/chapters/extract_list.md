# Extract Chapter List from Outline

You are tasked with extracting a structured list of chapters from a combined story outline.

## Input
- **Outline**: The complete story outline containing all chapters
- **Base Context**: The foundational story context and setting
- **Story Elements**: Key story elements and themes

## Task
Analyze the outline and extract each chapter as a structured entry. Return the result as a JSON array where each chapter has:
- `number`: The chapter number (integer)
- `title`: The chapter title or heading
- `description`: A brief description of what happens in the chapter

<COMBINED_OUTLINE>
{outline}
</COMBINED_OUTLINE>

## Output Format
Return ONLY a valid JSON array. Do not include any markdown formatting, explanations, or additional text.

Example format:
```json
[
  {
    "number": 1,
    "title": "The Beginning",
    "description": "Introduction to the main character and their world"
  },
  {
    "number": 2,
    "title": "The Call to Adventure",
    "description": "The inciting incident that sets the story in motion"
  }
]
```

## Guidelines
- Extract chapters in the order they appear in the outline
- Use the exact chapter titles/headings from the outline
- Provide concise but descriptive summaries
- Ensure the JSON is valid and properly formatted
- Do not add any commentary or explanations outside the JSON
