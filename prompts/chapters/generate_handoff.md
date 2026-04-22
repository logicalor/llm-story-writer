# Generate Chapter Handoff Artifact

You are producing a continuity-planning artifact for a story pipeline.

Analyze the expanded outline for chapter {{CHAPTER_NUMBER}} of {{STORY_TITLE}}, titled "{{CHAPTER_TITLE}}".

This is not a narrative summary. Do not write prose recap paragraphs. Extract only structured continuity state that downstream tooling can consume.

Chapter outline to analyze:

<CHAPTER_OUTLINE>
{{CHAPTER_OUTLINE}}
</CHAPTER_OUTLINE>

Return exactly one JSON object with this shape:

```json
{
  "resolved_beats": [
    "string"
  ],
  "obligations": [
    "string"
  ],
  "active_tensions": [
    "string"
  ],
  "timeline": {
    "start": "string",
    "end": "string",
    "duration": "string"
  },
  "character_deltas": [
    {
      "character": "string",
      "change": "string"
    }
  ]
}
```

Field requirements:

- `resolved_beats`: story beats, promises, or setup elements from the outline that this chapter resolves.
- `obligations`: new promises, hooks, mysteries, or commitments introduced here that later chapters must pay off.
- `active_tensions`: unresolved conflicts, pressures, or emotional tensions still in motion after this chapter.
- `timeline.start`: where the chapter begins in narrative time.
- `timeline.end`: where the chapter ends in narrative time.
- `timeline.duration`: elapsed narrative time covered by the chapter.
- `character_deltas`: only meaningful state changes that affect future continuity.

Rules:

- Output valid JSON only. No markdown fences. No commentary.
- Prefer short, concrete strings over vague summaries.
- Keep every array item independently useful for future chapter planning.
- If a section has no items, return an empty array.
- If timeline details are unclear, use best-effort concise strings such as `"unknown"` rather than omitting fields.
- Do not invent events not supported by the outline.