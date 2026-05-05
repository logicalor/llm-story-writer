Decompose the chapter synopsis below into between {scenes_min} and {scenes_max} distinct, non-overlapping scenes.

Choose the scene count based on the actual narrative density of the chapter synopsis. Do not pick an arbitrary number. Use fewer scenes for lean transitional material and more scenes only when the synopsis clearly contains enough meaningful beats to justify them.

## Critical Rule: Scenes Must Advance the Story

Each scene must cover a **different segment of the chapter's timeline**. Scenes are sequential — by the end of scene 1, the events of scene 1 are complete and the story has moved on. Scene 2 begins where scene 1 ended.

**Do not** produce multiple scenes that depict the same event from different angles, in different framings, or with different sensory wrappers. Do not produce alternative takes, reworks, or variations of the same beat. Each scene's `key_events` list must be entirely disjoint from every other scene's `key_events`.

Before finalising, check the array: if you removed any scene, would the chapter lose specific plot information? If two scenes could be swapped without confusing the reader, they overlap — merge or replace one of them.

A useful test: read each scene's `setting` + `ending` in order. The endings should form a chain — the ending of scene N is the starting state of scene N+1. If two scenes share the same opening situation (e.g. "character wakes up", "character is briefed"), that is a duplication, not a decomposition.

Maintain continuity with the surrounding material:
<PREVIOUS_CHAPTER>
{previous_chapter_recap}
</PREVIOUS_CHAPTER>

<NEXT_CHAPTER>
{next_chapter_synopsis}
</NEXT_CHAPTER>

If PREVIOUS_CHAPTER is empty, ignore that section entirely.
If NEXT_CHAPTER is empty, ignore that section entirely.

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
- cover a portion of the chapter's plot that no other scene covers
- begin from the state the previous scene left the world in (not from the chapter's opening situation)
- have a clear POV character or viewpoint anchor
- have a specific setting/location
- contain a concrete conflict or tension
- include the key events that happen in the scene (disjoint from all other scenes' `key_events`)
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
