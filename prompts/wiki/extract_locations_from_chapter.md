# Extract Locations from Chapter

You are extracting locations from a completed chapter.

<EXISTING_PAGES>
{existing_pages_index}
</EXISTING_PAGES>

<CHAPTER_TEXT>
{chapter_text}
</CHAPTER_TEXT>

## Task

Return a JSON array of candidate location page objects extracted from the chapter.

## Output schema

```json
[
  {
    "name": "Location Name",
    "type": "location",
    "aliases": [],
    "description": "What this place is and why it matters in the chapter.",
    "confidence": "verified",
    "frontmatter": {
      "location_type": "city",
      "status": "active",
      "first_appearance": 1
    }
  }
]
```

## Rules

- Extract only locations explicitly established in the chapter text.
- Focus on places, settings, and geographic references that matter to the story.
- Use `verified` confidence only. This operates on completed chapter text.
- Do not invent facts not stated in the chapter.
- Do not create duplicates of entries already listed in `existing_pages_index`.
- Keep descriptions concise, factual, and grounded in what the chapter states.
- Set `frontmatter.location_type` only from explicit chapter evidence. If not explicit, use an empty string.
- Set `frontmatter.status` only from explicit chapter evidence. If not explicit, use `active`.
- Set `frontmatter.first_appearance` only when the chapter clearly establishes it. Otherwise use the current chapter if implied by first introduction.
- Return `[]` when no location entities are found in the chapter.
- Return valid JSON array only. No markdown fences. No commentary.