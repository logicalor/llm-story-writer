# Scene Revision

## Your Task
You are rewriting **Scene {scene_num} of Chapter {chapter_num}**. Revise the scene content based on the feedback provided. Produce a complete, improved version of the scene.

## Current Scene Content
<SCENE_CONTENT>
{scene_content}
</SCENE_CONTENT>

## Feedback to Address

The feedback below may have been written against the full chapter (all scenes combined) or may contain targeted notes tagged by scene number, such as `[CRITICAL][Scene 2]` or `[WARNING][Scene 3]`.

**How to read it:**
- Items tagged `[Scene {scene_num}]` are directly relevant to this scene — address them.
- Items tagged with a *different* scene number are not your concern — skip them.
- Untagged items are general chapter-level notes — apply your judgement about whether they affect this scene.

<FEEDBACK>
{feedback}
</FEEDBACK>

## Scene Definition
<SCENE_DEFINITION>
{scene_definition}
</SCENE_DEFINITION>

## Chapter Outline
<CHAPTER_OUTLINE>
{chapter_outline}
</CHAPTER_OUTLINE>

## Scene Continuity
**Previous Scene Summary:**
<LEAD_UP>
{previous_scene}
</LEAD_UP>
*Note: If empty, this is the first scene in the chapter.*

**Next Chapter Context:**
<NEXT_CHAPTER>
{next_chapter_synopsis}
</NEXT_CHAPTER>
*Note: If empty, either this isn't the last scene, or it's the final chapter.*

## Revision Guidelines

### Requirements
- Address ALL points raised in the feedback
- Maintain consistency with the scene definition and chapter outline
- Preserve the core events and plot points of the scene
- Improve quality based on the specific feedback given
- If consistency feedback identifies this scene as duplicating events already covered
  in a prior scene, that feedback supersedes the scene definition — reframe the
  scene to begin from where the previous scene ended, not from the duplicated
  starting point.

### What to Include
- Rich sensory details and vivid descriptions
- Natural, character-appropriate dialogue
- Internal thoughts and emotional depth
- Character development and voice consistency
- Smooth transitions and logical flow

### What NOT to Include
- Commentary about the revision process
- Meta-text about what was changed
- Events beyond the scene definition
- Working notes or thought process

### Prose Style Pitfalls
Avoid formulaic AI-sounding constructions:
- **Negative parallelisms**: Do not frame descriptions as "It's not X, it's Y" or "Not just X, but Y" or "No X, no Y — just Z". State what something *is* directly.
- **Contrast-correction framing**: Don't construct false oppositions to make a point feel more emphatic.
- **Banned words**: Never use the word "hitch" in relation to breath or breathing (e.g. "her breath hitched"). Find a specific, concrete alternative instead.

### Output
Return ONLY the revised scene content. No explanations, no commentary, no before/after comparisons.
