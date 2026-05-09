# Generate Initial Outline Skeleton

You are a talented fiction writer creating a story structure. Your task is to create a high-level skeleton outline that maps out all chapters of the story before detailed generation.

<PROMPT>
{prompt}
</PROMPT>

<STORY_ELEMENTS>
{story_elements}
</STORY_ELEMENTS>

<BASE_CONTEXT>
{base_context}
</BASE_CONTEXT>

## Wiki Context (established story facts)

<WIKI_CONTEXT>
{wiki_context}
</WIKI_CONTEXT>

## OBJECTIVE
Create a comprehensive skeleton outline for {desired_chapters} chapters that:
- Maps the complete story arc from beginning to end
- Ensures proper pacing and story structure
- Provides a roadmap for detailed chapter generation
- Maintains consistency with story elements and themes

## STORY STRUCTURE GUIDELINES
Your outline should follow a clear narrative arc:

### Act 1: Setup (approximately first 25% of chapters)
- Establish the world and main characters
- Introduce the central conflict or problem
- End with the inciting incident that sets the story in motion

### Act 2: Rising Action (approximately middle 50% of chapters)
- Develop the conflict through escalating challenges
- Introduce subplots and character development
- Build tension toward the climax

### Act 3: Climax and Resolution (approximately final 25% of chapters)
- Deliver the climactic confrontation
- Resolve the main conflict
- Show character growth and transformation

## SKELETON FORMAT
For each chapter, provide ONLY:

### Chapter [Number]: [Compelling Title]
**Story Arc Position**: [Setup/Rising Action/Climax/Resolution]
**Tension Level**: [Low / Building / High / Peak / Releasing]
**Key Characters**: [Main characters involved, with their role or emotional state at this point]
**Story Beats**:
- [Triggering event — what initiates or defines this chapter's opening condition]
- [Primary development — key action, confrontation, or discovery that forms the chapter's core]
- [Exit condition — how the chapter ends and what it sets up for the chapters ahead]
**Core Purpose**: [2-3 sentences: what this chapter accomplishes, why it matters at this arc position, and how it moves the protagonist's arc forward]
**Planted Seeds**: [Any setup elements introduced here that pay off in later chapters — or "None"]

## PACING CONSIDERATIONS
For your {desired_chapters}-chapter story:
- **Early chapters** (first ~25%, chapters 1-{early_chapters}): Character introduction, world-building, setup
- **Rising action** (~25-75%, chapters {rising_start}-{rising_end}): Complications, character development, rising tension
- **Climax chapters** (~75-90%, chapters {climax_start}-{climax_end}): Major confrontations, revelations, turning points
- **Resolution** (final ~10%, chapters {resolution_start}-{desired_chapters}): Consequences, character growth, story conclusion

## CRITICAL REQUIREMENTS
- Generate EXACTLY {desired_chapters} chapters
- Ensure logical progression from chapter to chapter
- Balance action, character development, and plot advancement
- Create natural story beats and pacing
- Maintain consistency with provided story elements

## OUTPUT FORMAT
Provide a complete skeleton with all {desired_chapters} chapters using the format above. Each entry should be detailed enough to serve as a pacing contract for later chunk generation — richer is better here.

You MUST generate {desired_chapters} chapters.
