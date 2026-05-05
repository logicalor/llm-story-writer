# Extract Events from Chapter

You are extracting events from a completed chapter.

<EXISTING_PAGES>
{existing_pages_index}
</EXISTING_PAGES>

<CHAPTER_TEXT>
{chapter_text}
</CHAPTER_TEXT>

<PRIOR_CHAPTER_CONTEXT>
{prior_recap_context}
</PRIOR_CHAPTER_CONTEXT>

## Task

Return a JSON array of candidate event page objects extracted from the chapter.

## Output schema

```json
[
  {
    "name": "Event Name",
    "type": "event",
    "aliases": [],
    "description": "What happened and why it matters.",
    "confidence": "verified",
    "frontmatter": {
      "event_type": "turning-point",
      "status": "completed",
      "chapter": 1,
      "first_appearance": 1
    }
  }
]
```

## Rules

- Extract only key plot events, turning points, or significant occurrences explicitly established in the chapter text.
- Use `verified` confidence only. This operates on completed chapter text.
- Do not invent facts not stated in the chapter.
- Do not create duplicates of entries already listed in `existing_pages_index`.
- Use `prior_recap_context` to distinguish a "continuation of prior event" from a genuinely new event. If the context is empty, treat all extracted events as potentially new.
- Keep descriptions concise, factual, and grounded in what the chapter states.
- Set `frontmatter.event_type` only from explicit chapter evidence. If not explicit, use an empty string.
- Set `frontmatter.status` only from explicit chapter evidence. If not explicit, use `completed`.
- Set `frontmatter.chapter` to the chapter in which the event occurs when explicit from context.
- Set `frontmatter.first_appearance` only when the chapter clearly establishes it. Otherwise use the current chapter if implied by first introduction.
- Return `[]` when no event entities are found in the chapter.
- Return valid JSON array only. No markdown fences. No commentary.