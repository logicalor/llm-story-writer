# Extract World Rules from Chapter

You are extracting world rules from a completed chapter.

<EXISTING_PAGES>
{existing_pages_index}
</EXISTING_PAGES>

<CHAPTER_TEXT>
{chapter_text}
</CHAPTER_TEXT>

## Task

Return a JSON array of candidate world rule page objects extracted from the chapter.

## Output schema

```json
[
  {
    "name": "Rule Name",
    "type": "world_rule",
    "aliases": [],
    "description": "The rule as it appears in the chapter.",
    "confidence": "verified",
    "frontmatter": {}
  }
]
```

## Rules

- Extract only world rules explicitly established in the chapter text.
- Use exact type `world_rule`.
- Use `verified` confidence only. This operates on completed chapter text.
- Do not invent facts not stated in the chapter.
- Do not create duplicates of entries already listed in `existing_pages_index`.
- Keep descriptions concise, factual, and limited to the rule as the chapter states it.
- Return `[]` when no world rule entities are found in the chapter.
- Return valid JSON array only. No markdown fences. No commentary.