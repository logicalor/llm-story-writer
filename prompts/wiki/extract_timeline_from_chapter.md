# Extract Timeline from Chapter

You are extracting timeline entries from a completed chapter.

<EXISTING_PAGES>
{existing_pages_index}
</EXISTING_PAGES>

<CHAPTER_TEXT>
{chapter_text}
</CHAPTER_TEXT>

## Task

Return a JSON array of candidate timeline entry page objects extracted from the chapter.

## Output schema

```json
[
  {
    "name": "Short Event Description at Time",
    "type": "timeline_entry",
    "aliases": [],
    "description": "What happened.",
    "confidence": "verified",
    "frontmatter": {
      "timestamp": "",
      "participants": [],
      "chapter": 1
    }
  }
]
```

## Rules

- Extract only timeline entries explicitly established in the chapter text.
- Use exact type `timeline_entry`.
- Use `verified` confidence only. This operates on completed chapter text.
- Do not invent facts not stated in the chapter.
- Do not create duplicates of entries already listed in `existing_pages_index`.
- Keep descriptions concise and factual.
- Set `frontmatter.timestamp` to an ISO-8601 or narrative date/time string only when the chapter explicitly provides or clearly states it. Otherwise use an empty string.
- Set `frontmatter.participants` to a list of kebab-case character slugs only for characters explicitly involved in the event. Use `[]` when none are explicit.
- Set `frontmatter.chapter` to the integer chapter number if the chapter text explicitly identifies it or contains a clear chapter heading. If no chapter number can be determined from the chapter text, use `0`.
- Return `[]` when no timeline entry entities are found in the chapter.
- Return valid JSON array only. No markdown fences. No commentary.