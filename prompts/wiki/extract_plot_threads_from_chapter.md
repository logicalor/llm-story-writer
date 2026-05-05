# Extract Plot Threads from Chapter

You are extracting plot threads from a completed chapter.

<EXISTING_PAGES>
{existing_pages_index}
</EXISTING_PAGES>

<CHAPTER_TEXT>
{chapter_text}
</CHAPTER_TEXT>

## Task

Return a JSON array of candidate plot thread page objects extracted from the chapter.

## Output schema

```json
[
  {
    "name": "Thread Name",
    "type": "plot_thread",
    "aliases": [],
    "description": "What this plot thread is about.",
    "confidence": "verified",
    "frontmatter": {
      "status": "active"
    }
  }
]
```

## Rules

- Extract only plot threads explicitly established in the chapter text.
- Use exact type `plot_thread`.
- Use `verified` confidence only. This operates on completed chapter text.
- Do not invent facts not stated in the chapter.
- Do not create duplicates of entries already listed in `existing_pages_index`.
- Keep descriptions concise, factual, and grounded in what the chapter states.
- Set `frontmatter.status` to one of `active`, `resolved`, or `dormant`, based only on explicit chapter evidence. If the chapter does not clearly establish another state, use `active`.
- Return `[]` when no plot thread entities are found in the chapter.
- Return valid JSON array only. No markdown fences. No commentary.