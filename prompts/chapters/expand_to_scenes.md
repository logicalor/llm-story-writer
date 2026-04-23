Decompose the chapter synopsis below into between {scenes_min} and {scenes_max} distinct scenes.

Choose the scene count based on the actual narrative density of the chapter synopsis. Do not pick an arbitrary number. Use fewer scenes for lean transitional material and more scenes only when the synopsis clearly contains enough meaningful beats to justify them.

Maintain continuity with the surrounding material:
- Previous chapter recap: {previous_chapter_recap}
- Next chapter synopsis: {next_chapter_synopsis}

If {previous_chapter_recap} is empty, ignore that section entirely.
If {next_chapter_synopsis} is empty, ignore that section entirely.

Use the following story grounding for voice, setting, tone, and continuity:

## Story Elements
{story_elements}

## Base Context
{base_context}

## Chapter Synopsis
{chapter_synopsis}

Return ONLY a valid JSON array. Do not include prose, markdown fences, explanations, or notes before or after the array.

Every scene object must include ALL of these exact field names:
- title
- description
- characters
- setting
- conflict
- tone
- key_events
- dialogue
- ending
- lead_in_to_next_scene
- literary_devices

Each scene must:
- represent a distinct story unit with a clear beginning-to-end progression
- have a clear POV character or viewpoint anchor
- have a specific setting/location
- contain a concrete conflict or tension
- include the key events that happen in the scene
- end in a way that naturally leads into the next scene when applicable
- preserve voice, tone, and world consistency from the story elements and base context

Use this schema exactly:

```json
[
  {
    "title": "Scene Title",
    "description": "...",
    "characters": ["Character 1"],
    "setting": "Location name",
    "conflict": "...",
    "tone": "...",
    "key_events": ["Event 1"],
    "dialogue": "Snippet or summary of key dialogue",
    "ending": "...",
    "lead_in_to_next_scene": "...",
    "literary_devices": "..."
  }
]
```
