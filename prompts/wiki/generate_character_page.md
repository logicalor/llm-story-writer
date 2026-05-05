You are generating a planned wiki page for character `{character_name}` in story `{story_name}`.

<PRE_STORY_CONTEXT>
{pre_story_context}
</PRE_STORY_CONTEXT>

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
  "L3_relationships": "Paragraph (relationships as they stand at story start).",
  "L3_skills": "Paragraph.",
  "L3_growth_arc": "Paragraph (potential arc trajectory inferred from initial conditions — not events that will unfold).",
  "L3_current_state": "Paragraph (character's condition at story opening)."
}
```

## Rules

- Describe this character only as they exist at the **opening** of the story, before any story events occur. Do not describe events that happen during the story.
- All fields must reflect the character's pre-story state.
- Base every field on the pre-story context only.
- Do not invent facts not supported by the outline.
- `slug` must be snake_case derived from the character name.
- `page_name` should be the display name used in the outline.
- `aliases` must be a JSON array of strings. Use `[]` when none are explicit.
- `L1` is concise and glanceable.
- `L2` is one detailed paragraph for quick wiki reading.
- Every `L3_*` field must contain prose, not bullet lists.
- If the outline leaves a section thin, write a cautious paragraph describing only what is implied.
- Return valid JSON only. No markdown fences. No commentary.