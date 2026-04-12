# Generate Initial Outline Skeleton Chunk

You are a talented fiction writer creating a story skeleton. Your task is to generate a brief skeleton outline for a specific range of chapters within a larger story.

<STORY_ELEMENTS>
{story_elements}
</STORY_ELEMENTS>

<BASE_CONTEXT>
{base_context}
</BASE_CONTEXT>

<CHUNK_INFO>
Chapters to generate: {chunk_start} to {chunk_end}
Total story chapters: {total_chapters}
</CHUNK_INFO>

<PREVIOUS_CHUNKS>
{previous_chunks}
</PREVIOUS_CHUNKS>

<CONTINUITY_SUMMARY>
{continuity_summary}
</CONTINUITY_SUMMARY>

## OBJECTIVE
Create a brief skeleton outline for chapters {chunk_start} through {chunk_end} that:
- **Maintains proper escalation order** as specified in the continuity summary
- Follows logical story progression from previous chapters (if any)
- Maintains consistency with the established story elements and context
- **Incorporates relevant enrichment suggestions** to deepen the story beyond its basic scope
- **Respects established pacing and intensity patterns** from previous chunks
- Provides concise chapter overviews suitable for later expansion
- Connects smoothly to the overall story arc

## CONTINUITY REQUIREMENTS
**CRITICAL**: Use the continuity summary to ensure proper story progression:
- **Escalation Order**: Follow the specified escalation requirements - never decrease stakes inappropriately
- **Character Development**: Continue character arcs as specified, maintaining established growth patterns
- **Plot Thread Continuity**: Address active storylines and unresolved elements from previous chunks
- **Pacing Consistency**: Maintain the established rhythm of action/reflection and intensity patterns
- **Thematic Development**: Continue building themes and symbols as established in previous chapters

## ENRICHMENT INTEGRATION
Use the provided enrichment suggestions to enhance your chapter outlines by:
- **Character Development**: Integrate suggested character arcs, backstory reveals, and relationship dynamics
- **World-Building**: Incorporate suggested setting details, cultural elements, and environmental factors
- **Plot Complexity**: Weave in suggested subplots, foreshadowing, and obstacle escalation
- **Thematic Depth**: Include suggested symbolic elements, moral dilemmas, and thematic reinforcement
- **Chapter Placement**: Pay attention to suggested chapter ranges for implementing specific enrichments

## STORY STRUCTURE AWARENESS
Based on your chunk position within the {total_chapters}-chapter story:
- **Early chapters** (first ~25%): Focus on setup, character introduction, inciting incident
- **Middle chapters** (~25-75%): Focus on rising action, complications, character development  
- **Late chapters** (final ~25%): Focus on climax, resolution, character transformation

Your chunk ({chunk_start}-{chunk_end}) represents chapters {chunk_start}/{total_chapters} to {chunk_end}/{total_chapters} of the story.

## SKELETON FORMAT
For each chapter in your assigned range, provide ONLY:

<CHAPTER_LINE>
### Chapter [Number]: [Primary plot point or development]
</CHAPTER_LINE>

Don't include the CHAPTER_LINE tags, but format the chapter line according to its contents

## CONTINUITY REQUIREMENTS
- **Maintain consistency** with story elements and previous chapters
- **Progress the plot** meaningfully in each chapter
- **Develop characters** throughout the chunk
- **Build toward** the overall story climax and resolution
- **Ensure smooth flow** between chapters in your chunk

## GUARDRAILS: PREVENT REPETITION & AMBIGUITY

### AVOID REPETITION
- **No repeated events**: Each chapter must introduce NEW developments, conflicts, or revelations
- **No recycled plot points**: Don't reuse the same type of conflict or discovery across multiple chapters
- **Vary chapter purposes**: Mix action, dialogue, character development, and plot advancement
- **Different settings**: Don't confine multiple consecutive chapters to the same location unless story requires it
- **Escalating stakes**: Each chapter should raise the stakes or deepen the conflict from the previous one

### REQUIRE SPECIFICITY
- **Concrete actions**: Instead of "character learns something important" → "character discovers father's hidden journal revealing family secret"
- **Specific conflicts**: Instead of "tension rises" → "argument erupts over protagonist's decision to leave town"
- **Clear outcomes**: Instead of "situation changes" → "protagonist loses job but gains unexpected ally in former rival"
- **Tangible events**: Instead of "character development occurs" → "protagonist overcomes fear of heights to rescue trapped child"
- **Definitive revelations**: Instead of "truth emerges" → "protagonist discovers they are adopted through overheard conversation"

### CLARITY REQUIREMENTS
- **WHO**: Clearly identify which characters are central to each chapter
- **WHAT**: Specify exactly what happens (concrete actions, decisions, discoveries)
- **WHERE**: Mention the primary setting if it's important to the chapter
- **WHY**: Explain how this chapter advances the overall story
- **CONSEQUENCE**: Indicate what changes as a result of this chapter's events

## CRITICAL INSTRUCTIONS
- Generate EXACTLY the chapters requested ({chunk_start} to {chunk_end})
- Do NOT skip chapters or combine them
- Do NOT generate chapters outside your assigned range
- Maintain consistent quality and detail level across all chapters
- Ensure each chapter serves the overall story progression

## EXAMPLES OF GOOD VS BAD CHAPTER DESCRIPTIONS

### ❌ BAD (Vague, Repetitive, Ambiguous)
**Chapter 5**: Sarah learns something important about her past
**Chapter 6**: Sarah discovers more about her background

### ✅ GOOD (Specific, Unique, Clear)
**Chapter 5**: Sarah discovers her father's secret correspondence revealing he was investigating her mother's disappearance
**Chapter 6**: Sarah confronts her uncle about the lies he told regarding her mother's death

## QUALITY CHECKLIST
Before finalizing your output, verify each chapter meets these criteria:
- ✅ **Continuity Compliance**: Does this chapter follow the escalation and progression specified in the continuity summary?
- ✅ **Proper Escalation**: Are stakes appropriately higher or more complex than previous chapters?
- ✅ **Character Arc Continuity**: Do character developments follow established patterns from previous chunks?
- ✅ **Plot Thread Continuity**: Are active storylines from previous chapters properly addressed?
- ✅ **Pacing Consistency**: Does this chapter maintain the established story rhythm and intensity patterns?
- ✅ **Unique Purpose**: Does this chapter accomplish something different from all others?
- ✅ **Specific Events**: Can someone clearly understand what exactly happens in this chapter?
- ✅ **Clear Actions**: Are the character actions concrete and definitive (not vague)?
- ✅ **Distinct Outcomes**: Does this chapter change something specific in the story?
- ✅ **Enrichment Integration**: Does this chapter incorporate relevant suggestions to deepen the story?
- ✅ **Thematic Resonance**: Does this chapter contribute to the story's emotional and thematic depth?

## OUTPUT REQUIREMENTS
- Provide brief skeleton entries for ALL requested chapters
- Use the exact skeleton format specified above (5 lines per chapter maximum)
- **PRIORITIZE continuity compliance**: Follow escalation order and progression from continuity summary
- **Apply all guardrails**: No repetition, maximum specificity, complete clarity
- Maintain consistency with established story elements
- Ensure logical progression between chapters that respects previous chunk patterns
- Keep entries concise and suitable for later expansion
- **Each chapter must be DISTINCT and SPECIFIC** in its purpose and events
- **Pass the quality checklist** for every single chapter, especially continuity requirements

DO NOT INCLUDE A SUMMARY, COMMENTARY, OR OTHER HEADERS.  JUST THE FORMATTED OUTPUT.
