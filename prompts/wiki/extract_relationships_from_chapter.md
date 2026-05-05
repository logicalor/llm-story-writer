# Extract Relationships from Chapter

You are extracting relationships from a completed chapter.

<EXISTING_PAGES>
{existing_pages_index}
</EXISTING_PAGES>

<CHAPTER_TEXT>
{chapter_text}
</CHAPTER_TEXT>

## Task

Return a JSON array of candidate relationship page objects extracted from the chapter.

## Output schema

```json
[
  {
    "name": "Entity A ↔ Entity B",
    "type": "relationship",
    "aliases": [],
    "description": "Nature of the relationship.",
    "confidence": "verified",
    "frontmatter": {
      "participants": ["entity-a-slug", "entity-b-slug"],
      "relationship_type": "ally"
    }
  }
]
```

## Rules

- Extract only relationships explicitly established in the chapter text.
- Use `verified` confidence only. This operates on completed chapter text.
- Do not invent facts not stated in the chapter.
- Do not create duplicates of entries already listed in `existing_pages_index`.
- Format `name` exactly as `Entity A ↔ Entity B` using the `↔` symbol.
- Set `frontmatter.participants` to exactly two kebab-case slugs derived from the participant entity names.
- Set `frontmatter.relationship_type` only from explicit chapter evidence. Keep it short and factual, such as `ally`, `enemy`, `family`, `romantic`, or `mentor` when the chapter clearly supports that label.
- Keep descriptions concise and factual.
- Return `[]` when no relationship entities are found in the chapter.
- Return valid JSON array only. No markdown fences. No commentary.