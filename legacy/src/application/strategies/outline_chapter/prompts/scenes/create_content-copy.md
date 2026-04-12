# Generate Scene Content

You are writing Scene {scene_num} of Chapter {chapter_num}.

**Scene Information:**
<SCENE_OUTLINE>
**Scene {scene_num}**
```json
{scene_definition}
```
</SCENE_OUTLINE>
_Use this as the outline for the scene content you write_

**Chapter {chapter_num} Context:**
<CHAPTER_OUTLINE>
{chapter_outline}
</CHAPTER_OUTLINE>
_Use this to understand where this scene fits into the chapter_

**Story Context:**
<BASE_CONTEXT>
{base_context}
</BASE_CONTEXT>
_Use this to understand the overall constraints of the story_

**Full Story Elements:**
<STORY_ELEMENTS>
{story_elements}
</STORY_ELEMENTS>
_Use this to understand the broader elements of the story_

**Character Information:**
<CHARACTER_SHEETS>
{character_sheets}
</CHARACTER_SHEETS>
_If provided, use these to understand the characters involved in the chapter_

**Setting Information:**
<SETTING_SHEETS>
{setting_sheets}
</SETTING_SHEETS>
_If provided, use these to understand the settings in which scenes take place_

**Previous Chapter Recap:**
<PREVIOUS_RECAP>
{previous_recap}
</PREVIOUS_RECAP>
_Use this to understand things that have happened up until this chapter_
_note_: If there is no previous recap, then this is the first chapter

**Previous Scene Contents:**
<PREVIOUS_SCENE_CONTENT>
{previous_scene}
</PREVIOUS_SCENE_CONTENT>
_Use this to understand last scene's events. Don't copy the content - it is just a reference!_
_note_: If there is no previous scene, then we are at the first scene in the chapter

**Next Scene Outline:**
<NEXT_SCENE_OUTLINE>
{next_scene_definition}
</NEXT_SCENE_OUTLINE>
_Use this to understand next scene's events and how to lead out of this scene_
_note_: If there is no previous scene, then we are at the last scene in the chapter

**Next Chapter Synopsis:**
<NEXT_CHAPTER>
{next_chapter_synopsis}
</NEXT_CHAPTER>
_If we are the last scene for this chapter, use this to undersand how to lead in to the next chapter_
_note_: If this is empty then we are either not at the last scene of this chapter, or we are at the last chapter

Write this scene with the following guidelines:

1. **Focus**: Keep the scene focused on the specific events described in the scene description
2. **Coherence**: Ensure the scene flows logically and maintains narrative coherence
3. **Pacing**: Match the pacing appropriate for this scene's position in the chapter
4. **Character Voice**: Maintain consistent character voices and development
5. **Setting**: Include vivid but concise setting details
6. **Dialogue**: Use natural, character-appropriate dialogue
7. **Transitions**: Provide smooth transitions to and from this scene
8. **No Exposition**: No exposition or spoilers
9. **Length**: VERY IMPORTANT --> MUST BE 750-1500 words for this scene <-- VERY IMPORTANT!

IMPORTANT: Write JUST the scene content.  No commentary, headings, or markdown.
