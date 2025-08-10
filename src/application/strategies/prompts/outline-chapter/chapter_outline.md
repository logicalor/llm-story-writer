**Prompt for Chapter Outline Generation**

Please generate a detailed outline for Chapter {chapter_number} based on the provided chapter synopsis, also informed by the provided context.

### Provided Outline
<OUTLINE>
{outline}
</OUTLINE>

Important: 
 - Do not consider points in the outline's story flow to equate to chapters. They are merely a guideline as to the flow.
 - Use the outline to get a feel for the overall tone at the stage in the story flow the chapter is in.
 - Consider the recap (which ends at the end of the previous chapter), provided synopses, and previous chapter outline to be final indicators of story flow.

### Base Context
<CONTEXT>
{base_context}
</CONTEXT>

### Recap
<RECAP>
{recap}
</RECAP>
_note_: if there is no recap here, we are at the first chapter so we don't need to recap.

### Current Chapter's Synopsis
<CHAPTER_SYNOPSIS>
{current_chapter_synopsis}
</CHAPTER_SYNOPSIS>

### Next Chapter's synopsis
<NEXT_CHAPTER_SYNOPSIS>
{next_chapter_synopsis}
</NEXT_CHAPTER_SYNOPSIS>
_note_: if there is no next chapter synopsis here, we are at the last chapter and should lead out accordingly.

### Previous Chapter Outline (if applicable)
<PREVIOUS_CHAPTER_OUTLINE>
{previous_chapter_outline}
</PREVIOUS_CHAPTER_OUTLINE>
_note_: if there is no previous chapter outline here, we are the first chapter.

### Important Notes
  - Favour the chapter synopses over the outline when initially deciding on chapter events
  - Do not repeat any scenes from the previous chapter outline.
  - Only provide the outline in the specified format. Do not include any meta information, summaries, or explanations.
  - Do not reference any chapter titles for scene titles; each scene should have a unique title that succinctly summarizes its content.
  - If the previous chapter synopsis is empty, assume the current chapter is the first chapter and lead in accordingly.
  - If the next chapter synopsis is empty, assume the current chapter is the last chapter and lead out gracefully.

### Instructions:
1. **Focus on Key Elements**: 
   - As you create the outline, ensure that it implicitly addresses the following elements:
   - The central conflict of the chapter.
   - The relationship dynamics between the characters if there are more than one.
   - The setting of the chapter (location).
   - The stakes involved in the conflict (high or low).
   - The goal or resolution related to the conflict.

2. **Continuity**: 
   - Ensure that the events of the first scene in this chapter lead on from the Resolution & Lead-in of the previous chapter (provided in the Previous Chapter Outline).
   - Ensure that the resolution and lead-in of each scene logically connects to the next scene, maintaining a coherent flow throughout the chapter.
   - Consider the events of the next chapter (provided in the Next Chapter Synopsis) to ensure a logical flow into the next chapter.
   - Ensure that scene events do not overlap major themes of any other chapters (synopses provided in ALL_CHAPTERS).
   - Important: remember that the previous chapter is in the past, and the next chapter is in the future. Don't assume future events have already happened.

3. **Structure and Creative Licence**: 
   - IMPORTANT: Don't be concerned restricting the narrative to the synopsis' focus. The subject matter can meander a bit as long as the main focus is covered adequately.
   - IMPORTANT: Think about how you could expand the narrative scope of the chapter using the existing synopsis, weaving in recurring themes or other characters.
   - The DESIRED number of scenes is BETWEEN **three and ten**. 
   - LEAN TOWARD A HIGHER NUMBER OF SCENES.
   - If you think you can creatively expand the synopsis to include more than three scenes, tben you MUST include more scenes.
   - You may include a MAXIMUM of **ten scenes**.

4. **Outline Heading**

Add a heading to the chapter outline, using the following format:

# Chapter {chapter_number}: [The Chapter Title]

5. **Scene Format**: Each scene outline MUST STRICTLY have the fields follow this format:

   ## Scene: [Scene Title]

   - **Characters & Setting:**
     - Character: [Full Character Name - First and Last Name] - [Brief Description]
     - Location: [Scene Location]
     - Date & Time: [When the scene takes place in relation to the story timeline, or the time of day]

   - **Conflict & Tone:**
     - Conflict: [Type & Description]
     - Tone: [Emotional tone]

   - **Key Events:**
     - [Describe important events, actions, or dialogue, including how the scene ends or connects to the next scene.  Use some artistic license to embellish the scene, expanding on the general chapter themes]
   - ** Dialogue:**
     - [If there is to be dialogue between charactes in the scene, provide an example of a dialoge exchange in line with the events]
   - **Literary Devices:**
     - [Describe foreshadowing, symbolism, or other devices, if any]

   - **Resolution & Lead-in:**
     - [Describe how the scene ends and connects to the next one]

6. Repeat the exact scene format for each scene in the chapter. Use the exact chapter heading format, just once at the heading of the outline.

7. IMPORTANT: 
  - Do not embellish beyond the outline format. Focus on providing a clear, structured outline that can be easily followed for writing the chapter.
  - Do not provide any additional commentary, summaries, "final answers", or explanations. Just the chapter outlines in markdown format.
  - Do not repeat the chapter outline.