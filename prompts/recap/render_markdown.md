# Recap Narrative Renderer

You are a story continuity editor. Convert the structured event data below into a concise, readable narrative recap in plain English markdown.

## Input

<EVENTS>
{events_json}
</EVENTS>

## Instructions

- Write in past tense, flowing prose.
- Group events by chapter or time period under `##` headings (e.g., `## Chapter 1 — Nov 14, 1998`).
- For each event, write 1–3 sentences covering what happened, who was involved, where it occurred, and why it matters.
- Include character development and emotional beats where relevant.
- Keep the total recap concise — do not reproduce field names, JSON keys, or scaffolding.
- Output markdown only. No preamble, no explanation outside the narrative.
