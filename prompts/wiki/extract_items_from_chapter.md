# Extract Items from Chapter

You are extracting items from a completed chapter.

<EXISTING_PAGES>
{existing_pages_index}
</EXISTING_PAGES>

<CHAPTER_TEXT>
{chapter_text}
</CHAPTER_TEXT>

## Task

Return a JSON array of candidate item page objects extracted from the chapter.

## Output schema

```json
[
  {
    "name": "Item Name",
    "type": "item",
    "aliases": [],
    "description": "What this item is, its properties, significance.",
    "confidence": "verified",
    "frontmatter": {
      "owner": "slug-of-owner or empty string",
      "status": "intact"
    }
  }
]
```

## Rules

- Extract only items explicitly established in the chapter text.
- Use `verified` confidence only. This operates on completed chapter text.
- Do not invent facts not stated in the chapter.
- Do not create duplicates of entries already listed in `existing_pages_index`.
- Keep descriptions concise, factual, and grounded in what the chapter states.
- Set `frontmatter.owner` only when the chapter explicitly identifies the owner. Use a kebab-case slug for that owner. Otherwise use an empty string.
- Set `frontmatter.status` from explicit chapter evidence when possible. If the chapter does not establish a different state, use `intact`.
- Return `[]` when no item entities are found in the chapter.
- Return valid JSON array only. No markdown fences. No commentary.