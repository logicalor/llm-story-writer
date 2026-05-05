You are generating a planned wiki page for character `{character_name}` in story `{story_name}`.

<OUTLINE_EXCERPT>
{outline_excerpt}
</OUTLINE_EXCERPT>

## Task

Return one JSON object describing this character for the story wiki.

Required keys:

```json
{
  "slug": "snake_case_slug",
  "page_name": "Display Name",
  "aliases": ["Optional Alias"],
  "L1": "One-sentence quick reference summary, 300 characters or fewer.",
  "L2": "A rich paragraph of roughly 1500 characters describing the character as established by the outline.",
  "L3_background": "Paragraph.",
  "L3_personality": "Paragraph.",
  "L3_motivations": "Paragraph.",
  "L3_relationships": "Paragraph.",
  "L3_skills": "Paragraph.",
  "L3_growth_arc": "Paragraph.",
  "L3_current_state": "Paragraph."
}
```

## Rules

- Base every field on the outline excerpt only.
- Do not invent facts not supported by the outline.
- `slug` must be snake_case derived from the character name.
- `page_name` should be the display name used in the outline.
- `aliases` must be a JSON array of strings. Use `[]` when none are explicit.
- `L1` is concise and glanceable.
- `L2` is one detailed paragraph for quick wiki reading.
- Every `L3_*` field must contain prose, not bullet lists.
- If the outline leaves a section thin, write a cautious paragraph describing only what is implied.
- Return valid JSON only. No markdown fences. No commentary.