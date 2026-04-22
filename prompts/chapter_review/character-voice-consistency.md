Write a critique from a character voice consistency specialist's perspective.

Prior character voice samples retrieved from the story's RAG index will be prepended in a `<VOICE_SAMPLES>` block before the chapter outline. You (the caller) assemble this block; the critic should refer to it when evaluating cross-chapter voice drift.

Please critique the following chapter, providing both detailed feedback and a numerical score for each area. Break down your score by the categories below, and briefly justify each category score with specific examples from the chapter.

<OUTLINE>
{outline}
</OUTLINE>

As a character voice consistency specialist, evaluate the chapter based on these criteria:
    - Pacing (15 points): Does each character's dialogue, interiority, and reaction pace feel consistent with how they have spoken and reacted in prior chapters?
    - Details (15 points): Do vocabulary choices, sentence rhythms, and idiosyncratic speech patterns match the established voice samples for each character?
    - Flow (15 points): Do transitions between different characters' point-of-view passages and dialogue exchanges move naturally without jarring tonal shifts?
    - Genre (10 points): Do character voices remain tonally appropriate to the genre across chapters, avoiding drift toward incompatible registers?
    - Consistency (10 points): Are each character's verbal tics, habitual phrasings, and emotional baseline consistent with the voice samples from earlier chapters?
    - Character Arc & Theme (20 points): Where voice drift is intentional (character growth, trauma, revelation), is it clearly motivated and thematically coherent?
    - Structure (15 points): Are character voice contrasts and similarities arranged effectively so the chapter's dramatic beats are reinforced by distinct voices?

For each category, assign a score and provide justification based on character voice consistency standards, referencing specific parts of the chapter and, where relevant, the provided voice samples.

Present your results in this exact format:

## Character Voice Consistency Critique

### Pacing (score/15)
Notes about pacing consistency of character voice across chapters

### Details (score/15)
Notes about vocabulary, speech rhythms, and idiosyncratic voice markers

### Flow (score/15)
Notes about tonal flow between characters and point-of-view transitions

### Genre (score/10)
Notes about genre-fit and tonal register consistency across chapters

### Consistency (score/10)
Notes about verbal tics, habitual phrasings, and emotional baseline drift

### Character Arc & Theme (score/20)
Notes about intentional voice evolution and thematic coherence

### Structure (score/15)
Notes about how voice contrasts reinforce dramatic structure

### Summary
Overall assessment of cross-chapter character voice consistency, identifying any unintentional drift, regression, or missed opportunities for stronger voice differentiation.

IMPORTANT:
- Score each category based on its maximum points (15, 10, or 20)
- Do not include an overall score - this will be calculated automatically
- Just output the critique. No commentary, introduction, or other metadata.
