# Extract Characters from Chapter

You are extracting characters from a completed chapter.

<EXISTING_PAGES>
{existing_pages_index}
</EXISTING_PAGES>

<CHAPTER_TEXT>
{chapter_text}
</CHAPTER_TEXT>

## Task

Return a JSON array of candidate character page objects extracted from the chapter.

## Output schema

```json
[
  {
    "name": "Character Name",
    "type": "character",
    "aliases": [],
    "description": "Who this character is and what role they play in the chapter.",
    "confidence": "verified",
    "frontmatter": {
      "gender": "unknown",
      "role": "Primary role in story or chapter",
      "status": "active",
      "first_appearance": 1
    }
  }
]
```

## Rules

- Extract only characters explicitly established in the chapter text.
- Focus on names, roles, physical descriptions, and relationships explicitly mentioned.
- Use `verified` confidence only. This operates on completed chapter text.
- Do not invent facts not stated in the chapter.
- Do not create duplicates of entries already listed in `existing_pages_index`.
- Keep descriptions concise, factual, and grounded in what the chapter states.
- Set `frontmatter.gender` only from explicit chapter evidence. If not explicit, use `unknown`.
- Set `frontmatter.role` to the clearest explicit role or function shown in the chapter. If unclear, use an empty string.
- Set `frontmatter.status` only from explicit chapter evidence. If not explicit, use `active`.
- Set `frontmatter.first_appearance` only when the chapter clearly establishes it. Otherwise use the current chapter if implied by first introduction.
- Return `[]` when no character entities are found in the chapter.
- Return valid JSON array only. No markdown fences. No commentary.