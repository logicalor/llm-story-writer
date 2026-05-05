# Extract Factions from Chapter

You are extracting factions from a completed chapter.

<EXISTING_PAGES>
{existing_pages_index}
</EXISTING_PAGES>

<CHAPTER_TEXT>
{chapter_text}
</CHAPTER_TEXT>

## Task

Return a JSON array of candidate faction page objects extracted from the chapter.

## Output schema

```json
[
  {
    "name": "Faction Name",
    "type": "faction",
    "aliases": [],
    "description": "What this faction is and what role it plays.",
    "confidence": "verified",
    "frontmatter": {
      "alignment": "neutral",
      "leader": "Character Name or empty string"
    }
  }
]
```

## Rules

- Extract only factions explicitly established in the chapter text.
- Use `verified` confidence only. This operates on completed chapter text.
- Do not invent facts not stated in the chapter.
- Do not create duplicates of entries already listed in `existing_pages_index`.
- Keep descriptions concise, factual, and grounded in what the chapter states.
- Set `frontmatter.alignment` only from explicit chapter evidence. If not explicit, use `neutral`.
- Set `frontmatter.leader` only when the chapter explicitly identifies one. Otherwise use an empty string.
- Return `[]` when no faction entities are found in the chapter.
- Return valid JSON array only. No markdown fences. No commentary.