You are generating a planned wiki page for location `{location_name}` in story `{story_name}`.

<PRE_STORY_CONTEXT>
{pre_story_context}
</PRE_STORY_CONTEXT>

## Task

Return one JSON object describing this location for the story wiki.

Required keys:

```json
{
  "slug": "snake_case_slug",
  "page_name": "Display Name",
  "aliases": ["Optional Alias"],
  "L1": "One-sentence quick reference summary, 300 characters or fewer.",
  "L2": "A rich paragraph of roughly 1500 characters describing the location as established by the outline.",
  "L3_geography": "Paragraph.",
  "L3_history": "Paragraph.",
  "L3_atmosphere": "Paragraph.",
  "L3_inhabitants": "Paragraph.",
  "L3_significance": "Paragraph.",
  "L3_current_state": "Paragraph (condition at story opening)."
}
```

## Rules

- Describe this location only as it exists at the **opening** of the story, before any story events alter it.
- All fields must reflect the location's pre-story state.
- Base every field on the pre-story context only.
- Do not invent facts not supported by the outline.
- `slug` must be snake_case derived from the location name.
- `page_name` should be the display name used in the outline.
- `aliases` must be a JSON array of strings. Use `[]` when none are explicit.
- `L1` is concise and glanceable.
- `L2` is one detailed paragraph for quick wiki reading.
- Every `L3_*` field must contain prose, not bullet lists.
- If the outline leaves a section thin, write a cautious paragraph describing only what is implied.
- Return valid JSON only. No markdown fences. No commentary.