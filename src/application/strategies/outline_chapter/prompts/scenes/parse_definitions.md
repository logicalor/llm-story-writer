# Parse Scene Definitions

Analyze this chapter outline and identify distinct scenes within it:

<CHAPTER_OUTLINE>
{chapter_outline}
</CHAPTER_OUTLINE>

Identify and structure the scenes in this chapter. For each scene, provide:

1. **Scene Title**: A descriptive title for the scene
2. **Scene Description**: Full description of what happens in the scene
3. **Characters & Setting**: Characters present in the scene
4. **Conflict & Tone**: Conflict & tone
5. **Key Events**: All events that occur in the scene
6. **Dialogue**: Examples of dialogue
7. **Resolution & Lead-in**: How the scene closes and leads into the next 

Look for natural breaks in the narrative such as:
- Changes in location
- Time jumps
- Different character perspectives
- Major plot developments
- Scene transitions

Output your response as a valid JSON array of scene objects. Each scene object should have this structure:

```json
[
  {
    "title": "Scene Title",
    "description": "Description of what happens in this scene",
    "characters": ["Character 1", "Character 2"],
    "setting": "Location description",
    "conflict": "Main conflict or tension",
    "tone": "Mood or atmosphere",
    "key_events": ["Event 1", "Event 2", "Event 3"],
    "dialogue": "Example dialogue or conversation",
    "ending": "How the scene resolves / ends",
    "lead_in_to_next_scene": "Describe how the scene ends and connects to the next one",
    "literary_devices": "Describe foreshadowing, symbolism, or other devices, if any"

  }
]
```

If the chapter appears to be a single continuous scene, provide a single scene object with the chapter title and full description.

Ensure your response contains ONLY valid JSON. Do not include any explanatory text, markdown formatting, or other content outside the JSON structure.
