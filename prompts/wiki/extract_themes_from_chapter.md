# Extract Themes from Chapter

You are extracting themes from a completed chapter.

<EXISTING_PAGES>
{existing_pages_index}
</EXISTING_PAGES>

<CHAPTER_TEXT>
{chapter_text}
</CHAPTER_TEXT>

## Task

Return a JSON array of candidate theme page objects extracted from the chapter.

## Output schema

```json
[
  {
    "name": "Theme Name",
    "type": "theme",
    "aliases": [],
    "description": "How this theme manifests in the chapter.",
    "confidence": "verified",
    "frontmatter": {}
  }
]
```

## Rules

- Extract only themes explicitly established in the chapter text.
- Use `verified` confidence only. This operates on completed chapter text.
- Do not invent facts not stated in the chapter.
- Do not create duplicates of entries already listed in `existing_pages_index`.
- Keep descriptions concise, factual, and tied to explicit chapter evidence.
- Do not infer broad thematic meaning unless the chapter directly supports it.
- Return `[]` when no theme entities are found in the chapter.
- Return valid JSON array only. No markdown fences. No commentary.