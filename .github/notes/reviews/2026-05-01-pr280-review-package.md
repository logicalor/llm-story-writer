== REVIEW PACKAGE ==

=== BRANCH ===
feat/issue-276-direct-prompts

=== COMMIT LOG ===
89addf7 fix(permissions): correct agent edit permission order + remove legacy root files (#276)
a08e8f7 docs(direct-prompts): document agent integration and test changes (#276)
6220025 feat(prompts): create 5 direct-generation prompt templates for Python-native agents (#276)

=== CHANGED FILES ===
.github/notes/gotchas.md
.opencode/agents/browser.md
.opencode/agents/documenter.md
.opencode/agents/orchestrator-v3.md
.opencode/agents/planner.md
.opencode/agents/test-writer.md
AGENTS.md
README.md
Todo.md
config-guide.md
docs/README.md
docs/features/direct-generation-prompts.md
prompts/chapter_review/consistency_check_direct.md
prompts/chapters/write_chapter_direct.md
prompts/final_edit/edit_chapter_direct.md
prompts/outline/arc_assessment_direct.md
prompts/outline/create_direct.md
requirements.txt
src/presentation/agents/chapter_writer.py
src/presentation/agents/consistency_checker.py
src/presentation/agents/final_editor.py
src/presentation/agents/outline_planner.py
src/presentation/agents/story_planner.py
tests/unit/test_chapter_writer_context.py
tests/unit/test_consistency_checker.py

=== DIFF ===
(See /tmp/review_diff.txt for the full diff — too large to inline here.)

=== FILE CONTENTS ===

--- prompts/outline/create_direct.md ---
# Generate Story Outline

You are a talented fiction writer creating a complete story structure. Your task is to produce a chapter-by-chapter outline that maps the full narrative arc from beginning to end.

## Story Prompt
<PROMPT>
{prompt}
</PROMPT>

## Story Elements
<STORY_ELEMENTS>
{story_elements}
</STORY_ELEMENTS>

## Base Context
<BASE_CONTEXT>
{base_context}
</BASE_CONTEXT>

## OBJECTIVE
Create a comprehensive outline for exactly {desired_chapters} chapters that:
- Maps the complete story arc from beginning to end
- Ensures proper pacing and three-act structure
- Provides a roadmap for detailed chapter generation
- Maintains consistency with story elements and themes

## STORY STRUCTURE GUIDELINES
Follow a clear narrative arc:

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

## PACING GUIDE
For your {desired_chapters}-chapter story:
- **Early chapters** (first ~25%, chapters 1-{early_chapters}): Character introduction, world-building, setup
- **Rising action** (~25-75%, chapters {rising_start}-{rising_end}): Complications, character development, rising tension
- **Climax chapters** (~75-90%, chapters {climax_start}-{climax_end}): Major confrontations, revelations, turning points
- **Resolution** (final ~10%, chapters {resolution_start}-{desired_chapters}): Consequences, character growth, story conclusion

## OUTPUT FORMAT
For each chapter, provide exactly:

### Chapter [Number]: [Compelling Title]
[2-3 sentence summary focusing on the main conflict, key character development, and the chapter's contribution to the overall arc. Be specific about what happens and why it matters.]

Continue this format for all {desired_chapters} chapters. Do not group chapters or skip any numbers.

## QUALITY STANDARDS
- Generate EXACTLY {desired_chapters} chapters — no more, no less.
- Ensure logical progression from chapter to chapter with clear cause-and-effect.
- Balance action, character development, and plot advancement.
- Create natural story beats and pacing.
- Keep chapter titles under 10 words.
- Keep each summary to 2-3 sentences maximum.
- Focus on WHAT happens and WHY it matters, not HOW it is written.
- Avoid repetitive plot elements, multiple conflicts per chapter, or verbose descriptions.
- Maintain consistency with the provided story elements.

Produce the complete outline now.

--- prompts/outline/arc_assessment_direct.md ---
# Dramatic Arc Assessment

You are a senior story editor assessing the dramatic arc of a completed story outline. Your task is to produce a qualitative evaluation of the outline's narrative structure, tension curve, promise/payoff logic, and thematic resolution.

## Outline to Assess
<OUTLINE>
{outline}
</OUTLINE>

## Supporting Context
<CRITIC_SUMMARY>
{critic_summary}
</CRITIC_SUMMARY>

<ARC_DISTRIBUTION>
{arc_distribution}
</ARC_DISTRIBUTION>

<PROMISE_PAYOFF>
{promise_payoff}
</PROMISE_PAYOFF>

## ASSESSMENT CRITERIA
Evaluate the outline across these dimensions:

### 1. Overall Arc Health
- Does the story have a clear beginning, middle, and end?
- Is the central conflict introduced early and developed meaningfully?
- Does the resolution feel earned?

### 2. Three-Act Structure
- Are the act boundaries well-placed and proportionally balanced?
- Is the inciting incident positioned correctly in Act 1?
- Does Act 2 carry sufficient dramatic weight (~50-60% of the story)?
- Is the climax positioned at roughly 75-85% through the story?

### 3. Pacing Distribution
- Identify any dead zones (consecutive low-tension chapters).
- Flag pacing cliffs (sudden jumps without build-up).
- Assess whether tension escalates smoothly toward the climax.

### 4. Promise/Payoff Analysis
- Are setups in early chapters resolved later?
- Are there unresolved promises or orphaned payoffs?
- Does foreshadowing lead to satisfying reveals?

### 5. Thematic Resolution
- Are themes introduced early enough?
- Are they meaningfully resolved by the ending?
- Do character arcs align with thematic goals?

### 6. Structural Concerns
- Any critical structural issues that would weaken the story?
- Missing turning points, weak midpoints, or rushed endings?

## OUTPUT FORMAT
Present your assessment in this exact structure:

## Dramatic Arc Assessment

### Overall Score
[Numeric score out of 100, or "N/A" if no critic scores are provided. Base this on structural soundness if quantitative data is absent.]

### 3-Act Structure
[Assessment of act balance, turning-point placement, and climax positioning. Be specific about chapter numbers where possible.]

### Pacing Distribution
[Highlight any dead zones, pacing cliffs, or state clearly if no significant pacing issues are found.]

### Promise/Payoff Analysis
[Count of promises identified, resolved, and unresolved. List any unresolved promises or orphaned payoffs.]

### Thematic Resolution
[Evaluation of whether themes are established early and resolved meaningfully by the end.]

### Structural Concerns
[List any critical structural issues, or state "None identified" if the structure is sound.]

### Recommendations
[Actionable, specific suggestions — e.g., "Consider adding a tension beat to chapters 8-10", "Climax at chapter 22 may feel rushed for a 25-chapter story".]

### Reviewer Verdict
[Exactly one of the following three lines:]
- Reviewer Verdict: ✅ Strong arc - proceed to generation
- Reviewer Verdict: ⚠️ Minor arc concerns - review recommendations before proceeding
- Reviewer Verdict: ❌ Significant arc issues - consider re-generating outline with feedback

Base all claims on the provided outline, not generic story advice. Keep the verdict aligned with the severity of the structural concerns.

--- prompts/chapters/write_chapter_direct.md ---
# Chapter Writing

You are a skilled fiction writer composing a complete chapter of a long-form narrative. Your task is to write the full prose of the assigned chapter — rich, immersive, and ready for readers.

## Chapter Assignment
- **Story:** {story_name}
- **Chapter Number:** {chapter_number}
- **Chapter Title:** {chapter_title}
- **Chapter Summary:** {chapter_summary}

## Story Context
<BASE_CONTEXT>
{base_context}
</BASE_CONTEXT>

<STORY_ELEMENTS>
{story_elements}
</STORY_ELEMENTS>

## Continuity
<PREVIOUS_CHAPTER>
{previous_chapter_summary}
</PREVIOUS_CHAPTER>

<NEXT_CHAPTER>
{next_chapter_summary}
</NEXT_CHAPTER>

## CHARACTER & SETTING CONTEXT
<CHARACTER_CONTEXT>
{character_context}
</CHARACTER_CONTEXT>

<SETTING_CONTEXT>
{setting_context}
</SETTING_CONTEXT>

## YOUR TASK
Write the complete prose for this chapter. The chapter should be **approximately 3000-5000 words** (longer if the story genre calls for it, but avoid excessive bloat).

### Narrative Structure
- **Beginning:** Open with a hook that grounds the reader in the scene and re-establishes the POV character's situation.
- **Middle:** Develop the chapter's central conflict through character interaction, internal tension, or environmental pressure. Escalate naturally.
- **End:** Deliver a turning point or compelling transition that leaves the reader wanting to continue. Avoid tidy resolutions that kill momentum.

### Writing Quality Standards
- **Show, don't tell.** Use sensory details, physical reactions, and dialogue to convey emotion and character state.
- **Distinct character voices.** Each character should have identifiable speech patterns, vocabulary level, and sentence rhythm.
- **POV consistency.** Maintain a single POV within each scene. All observations and internal thoughts must belong to the POV character.
- **Pacing variation.** Alternate between high-tension and quieter moments. Use short sentences for action; longer, reflective passages for emotion.
- **Smooth transitions.** Bridge scenes with connective tissue — a grounding sentence, a time skip, or a perspectival shift.
- **Forward momentum.** Every scene should change something — a relationship, a decision, a piece of knowledge.
- **Thematic resonance.** Let the chapter's events subtly echo the story's larger themes.

### What to Include
- Rich sensory details and vivid descriptions
- Natural, character-appropriate dialogue with subtext
- Internal thoughts and emotional depth
- Character development and voice consistency
- Smooth transitions and logical flow

### What NOT to Include
- Commentary about the writing process
- Meta-text about story structure
- Exposition dumps or info-dumps
- Working notes or thought process
- Content from the guidance sections above (story context, story elements, etc.) — use them for understanding only

## OUTPUT
Return **only** the chapter prose. No commentary, no metadata, no summaries, no markdown formatting beyond standard paragraph breaks. The text should be publishable draft quality.

--- prompts/final_edit/edit_chapter_direct.md ---
# Chapter Prose Polish

You are a senior prose editor performing a final polish pass on a single chapter. Your task is to improve the chapter's clarity, flow, voice consistency, and stylistic polish while preserving every story event and factual detail exactly as written.

## Chapter to Edit
- **Chapter Number:** {chapter_number}
- **Chapter Title:** {chapter_title}

## Prior Chapters Summary
<PRIOR_CHAPTERS>
{prior_chapters_summary}
</PRIOR_CHAPTERS>

## Chapter Text
<CHAPTER_TEXT>
{chapter_text}
</CHAPTER_TEXT>

## SCOPE OF WORK
You may make the following types of changes:
- **Wording refinement:** Improve word choice for clarity, rhythm, and precision.
- **Sentence restructuring:** Fix awkward constructions, improve flow, and vary sentence length.
- **Paragraph reshaping:** Reorganize sentences within paragraphs for better logic and impact.
- **Dialogue polishing:** Sharpen dialogue tags, tighten exchanges, and ensure subtext is clear.
- **Pacing adjustments:** Trim unnecessary repetition or slow passages; tighten transitions.
- **Tonal alignment:** Ensure the prose voice remains consistent with the story's established style.
- **Repetition cleanup:** Remove accidental word repetition or redundant phrasing.

You must NOT:
- Change any plot events.
- Add or remove scenes.
- Alter character facts, continuity facts, timeline facts, or world rules.
- Change the meaning of any sentence.
- Replace the entire chapter unless the chapter is extremely short and requires only light refinement.

## OUTPUT
Return the **complete polished chapter text** — every paragraph, every line of dialogue, every scene. Preserve the structure and events of the original while applying your improvements. The output should be the full chapter, ready to replace the original.

Do not add commentary, explanations, or lists of changes. Return only the polished prose.

--- prompts/chapter_review/consistency_check_direct.md ---
# Narrative Consistency Check

You are a meticulous narrative consistency editor. Your task is to analyze a single chapter for internal and cross-chapter consistency issues — character voice drift, timeline violations, world-rule contradictions, behavioral inconsistencies, and continuity errors.

## Chapter to Analyze
- **Story:** {story_name}
- **Chapter Number:** {chapter_number}

## Chapter Content
<CHAPTER_CONTENT>
{chapter_content}
</CHAPTER_CONTENT>

## Outline Context
<OUTLINE>
{outline}
</OUTLINE>

## CONSISTENCY STANDARDS
Evaluate the chapter against these criteria:

### Character Voice Drift
- Does each character's dialogue, interiority, and reaction pace match their established voice?
- Are vocabulary choices, sentence rhythms, and speech patterns consistent?
- Do characters maintain distinct voices, or do they converge toward a generic narrator voice?

### Timeline Violations
- Do events occur in a logical chronological order?
- Are references to "earlier today," "yesterday," or specific dates consistent with the story timeline?
- Do travel times, preparation times, and reaction times feel believable?

### World-Rule Contradictions
- Do characters act within established world rules (magic systems, technology limits, societal constraints)?
- Are physical laws and environmental details consistent with prior chapters?
- Do political or social structures behave consistently?

### Character Behavior Inconsistencies
- Do characters' actions align with their established traits, motivations, and emotional states?
- Is growth gradual and motivated, or abrupt and unearned?
- Are emotional responses proportional to events?

### Continuity Errors
- Do character names, descriptions, or relationships contradict prior setup?
- Do objects, locations, or conditions change without explanation?
- Are callbacks to prior events accurate?

## OUTPUT FORMAT
Return **only** a JSON object with this exact shape — no preamble, no markdown fences, no commentary:

```json
{
  "issues": [
    {
      "type": "voice_drift|timeline|world_rule|character_behavior|continuity",
      "description": "clear explanation of the inconsistency",
      "severity": "critical|warning|info",
      "location": "paragraph reference or approximate location"
    }
  ],
  "has_critical_findings": true|false
}
```

Severity definitions:
- **critical:** The issue would confuse readers, break immersion, or contradict established facts in a way that undermines the story.
- **warning:** The issue is noticeable but could be interpreted charitably or fixed with minor adjustment.
- **info:** A subtle inconsistency or a suggestion for tighter continuity.

If no issues are found, return:
```json
{"issues": [], "has_critical_findings": false}
```

Return **only** the JSON object. Do not wrap it in markdown code blocks. Do not add any text before or after.

--- src/presentation/agents/outline_planner.py ---
(Full content provided above in file read — see original file for complete source.)

--- src/presentation/agents/story_planner.py ---
(Full content provided above in file read — see original file for complete source.)

--- src/presentation/agents/chapter_writer.py ---
(Full content provided above in file read — see original file for complete source.)

--- src/presentation/agents/final_editor.py ---
(Full content provided above in file read — see original file for complete source.)

--- src/presentation/agents/consistency_checker.py ---
(Full content provided above in file read — see original file for complete source.)

--- tests/unit/test_chapter_writer_context.py ---
(Full content provided above in file read — see original file for complete source.)

--- tests/unit/test_consistency_checker.py ---
(Full content provided above in file read — see original file for complete source.)

== END REVIEW PACKAGE ==
