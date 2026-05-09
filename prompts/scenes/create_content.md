# Scene Content Generation

## Your Task
You are writing Scene {scene_num} of Chapter {chapter_num}. Generate a complete, engaging scene based on the provided outline.

## Core Requirements
- **Word Count**: 750-1500 words (mandatory)
- **Output**: Only the scene content - no commentary, metadata, or summaries
- **Scope**: Stay within the scene outline boundaries - expand creatively but don't add new events
- **Context Usage**: All other information below is for writing guidance only - do not include it in your scene content

## Scene Outline
**THIS IS YOUR CONTENT BLUEPRINT - THE ONLY THING THAT DEFINES WHAT TO WRITE**
Expand on it creatively, but don't go beyond what's defined here.
<SCENE_OUTLINE>
**Scene {scene_num}**
```json
{scene_definition}
```
</SCENE_OUTLINE>

## Writing Guidance (NOT Content)
The following sections provide context to help you write the scene appropriately. Use them to understand tone, style, and continuity, but DO NOT include their content in your scene.

**Story Context:**
Use this to understand the overall story constraints and tone.
<BASE_CONTEXT>
{base_context}
</BASE_CONTEXT>

## Chapter Outline
Use this to understand what happens in the rest of this chapter.
<CHAPTER_OUTLINE>
{chapter_outline}
</CHAPTER_OUTLINE>

**Story Elements:**
Reference these broader story elements for consistency.
<STORY_ELEMENTS>
{story_elements}
</STORY_ELEMENTS>

**Scene Continuity:**
**Previous Scene Summary:**
<LEAD_UP>
{previous_scene}
</LEAD_UP>
*Note: If empty, this is the first scene of the first chapter. Continue naturally from the story's opening.*
*If populated for scene 1 of a non-first chapter, this is the closing scene of the previous chapter — use it to bridge the chapter transition.*

**Next Chapter Context:**
<NEXT_CHAPTER>
{next_chapter_synopsis}
</NEXT_CHAPTER>
*Note: If empty, either this isn't the last scene, or it's the final chapter.*

## Writing Guidelines

### Content Sources
- **Primary Source**: The scene outline above - this defines what events to write about
- **Secondary Sources**: All other information is for understanding context, tone, and style only

### What to Include
- Rich sensory details and vivid descriptions
- Natural, character-appropriate dialogue
- Internal thoughts and emotional depth
- Character development and voice consistency
- Smooth transitions and logical flow

### What NOT to Include
- Commentary about the writing process
- Meta-text about story structure
- Events beyond the scene outline
- Exposition or spoilers
- Working notes or thought process
- **Content from the guidance sections above** (story context, chapter outline, story elements, etc.)

### Prose Style Pitfalls
Avoid formulaic AI-sounding constructions:
- **Negative parallelisms**: Do not frame descriptions as "It's not X, it's Y" or "Not just X, but Y" or "No X, no Y — just Z". These read as LLM-generated. State what something *is* directly, without first denying what it isn't.
- **Contrast-correction framing**: Avoid writing as though clearing up a misconception the reader doesn't have. Don't construct false oppositions to make a point feel more emphatic.
- **Banned words**: Never use the word "hitch" in relation to breath or breathing (e.g. "her breath hitched"). Find a specific, concrete alternative instead.

### Creative Boundaries
- **WITHIN the outline**: Add depth, details, dialogue, and emotional richness
- **BEYOND the outline**: Never add new events, actions, or plot developments
- **Think of it as**: Expanding a skeleton into a full body, but not adding new limbs
- **Guidance sections**: Use them like a style guide, not a content source

### Scene Ending — Hard Stop
The scene definition's `ending` field defines the **last moment** of this scene. Your prose must stop there.
- Do not write past the `ending` into events that belong to the next scene.
- The `lead_in_to_next_scene` field is a handoff note for the *next* scene's writer — do not narrate it. At most, let the final sentence of your prose gesture toward it atmospherically.
- If you find yourself writing what the `lead_in_to_next_scene` describes, you have gone too far. Stop and cut back.

## Final Instructions
1. Write 750-1500 words of pure scene content
2. Expand creatively on the scene outline
3. Stay within the defined scene boundaries
4. Ensure smooth flow and narrative coherence
5. Write the final content that readers will read

## Output
Generate only the scene content. No additional text, commentary, or formatting instructions.
