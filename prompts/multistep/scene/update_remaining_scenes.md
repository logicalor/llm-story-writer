# Update Remaining Scene Plans After Drafting

You are revising the remaining scene plan for a chapter after one scene has now been drafted.

Adjust the remaining scene entries to account for what actually happened in the completed scene.

## Completed Scene Title
<COMPLETED_SCENE_TITLE>
{completed_scene_title}
</COMPLETED_SCENE_TITLE>

## Completed Scene Recap
<COMPLETED_SCENE_RECAP>
{completed_scene_recap}
</COMPLETED_SCENE_RECAP>

## Chapter Outline
<CHAPTER_OUTLINE>
{chapter_summary}
</CHAPTER_OUTLINE>

## Remaining Scenes JSON
<REMAINING_SCENES_JSON>
{remaining_scenes_json}
</REMAINING_SCENES_JSON>

## Task
Revise each remaining scene so it stays aligned with the chapter outline while reflecting what actually happened in the completed scene.

For each remaining scene, update only the fields that need adjustment based on the new reality:
- `summary`
- `key_events`
- `ending`

Preserve the existing array order and keep the same overall structure as the input.

## Output Rules
- Return ONLY a valid JSON array
- No markdown fences
- No commentary
- No prose before or after the JSON
- The array length must remain exactly the same as the input
- Each item must remain an object with the same structure as the corresponding input item