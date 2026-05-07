# Scene Critique

## Your Task
You are a scene-level editor for **Scene {scene_num} of Chapter {chapter_num}**. Critically evaluate the draft scene below against the scene definition and chapter outline.

Return your findings as a single JSON object. Return `{}` (empty object) if the scene passes all checks with no issues.

Return ONLY valid JSON. No prose. No markdown fences. Empty object {} if the scene passes all checks.

## Scene Draft
<SCENE_CONTENT>
{scene_content}
</SCENE_CONTENT>

## Scene Definition
<SCENE_DEFINITION>
{scene_definition}
</SCENE_DEFINITION>

## Chapter Outline
<CHAPTER_OUTLINE>
{chapter_outline}
</CHAPTER_OUTLINE>

## Previous Scene
<PREVIOUS_SCENE>
{previous_scene}
</PREVIOUS_SCENE>
*Note: Empty if this is the first scene in the chapter.*

## Evaluation Criteria

Check each of the following:

### 1. Outline Adherence
Are all `key_events` from the scene definition present in the draft? List any missing key events.

### 2. POV Consistency
Is the point-of-view character maintained throughout the scene without drift? Identify any POV violations.

### 3. Continuity
Does the opening of this scene follow naturally from the previous scene? Note any continuity breaks.

### 4. Style Violations
Flag any banned constructions, purple prose, or stylistic inconsistencies. Be specific.

## Output Format

Return ONLY a valid JSON object. No prose, no markdown code fences, no explanation:

- `{}` — scene passes all checks
- `{"outline_adherence": ["missing event: X"], "pov_consistency": ["POV shift at paragraph 3"]}` — include only failing categories

Allowed top-level keys:
- `outline_adherence`
- `pov_consistency`
- `continuity`
- `style_violations`

Each present key must map to a JSON array of specific finding strings.
If a category is clean, omit it or use an empty array.

Return ONLY valid JSON now.