# Generate Initial Outline Skeleton Chunk

You are a talented fiction writer creating a story skeleton. Your task is to generate a brief skeleton outline for a specific range of chapters within a larger story.

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

<CHUNK_INFO>
Chapters to generate: {chunk_start} to {chunk_end}
Total story chapters: {total_chapters}
</CHUNK_INFO>

<PREVIOUS_CHUNKS>
{previous_chunks}
</PREVIOUS_CHUNKS>

<STORY_SKELETON>
{story_skeleton}
</STORY_SKELETON>

<CONTINUITY_SUMMARY>
{continuity_summary}
</CONTINUITY_SUMMARY>

## OBJECTIVE
Create a brief skeleton outline for chapters {chunk_start} through {chunk_end} that:
- **Uses the STORY_SKELETON as the authoritative pacing contract** — honour the major events, act positions, and character beats already planned for each chapter; do not rush, reorder, or skip ahead in the arc
- **Maintains proper escalation order** as specified in the continuity summary
- Follows logical story progression from previous chapters (if any)
- Maintains consistency with the established story elements and context
- **Respects established pacing and intensity patterns** from previous chunks
- Provides concise chapter overviews suitable for later expansion
- Connects smoothly to the overall story arc

## PACING CONSTRAINT — STORY SKELETON
The STORY_SKELETON above is a pre-planned high-level arc for all {total_chapters} chapters. It is the single source of truth for *what should happen when*. When writing your chunk:
- Match the **Story Arc Position** (Setup / Rising Action / Climax / Resolution) for each chapter in your range
- Honour the **Core Purpose** and **Story Beats** fields — do not introduce events planned for later chapters
- Do not escalate stakes beyond what the skeleton schedules — if the skeleton says "rising tension" for your chunk, the climax must not appear yet
- If the previous chunks have already introduced something scheduled for your range, note it in the first Events beat and advance the skeleton beat logically rather than skipping it entirely

## CONTINUITY REQUIREMENTS
**CRITICAL**: Use the continuity summary to ensure proper story progression:
- **Escalation Order**: Follow the specified escalation requirements - never decrease stakes inappropriately
- **Character Development**: Continue character arcs as specified, maintaining established growth patterns
- **Plot Thread Continuity**: Address active storylines and unresolved elements from previous chunks
- **Pacing Consistency**: Maintain the established rhythm of action/reflection and intensity patterns
- **Thematic Development**: Continue building themes and symbols as established in previous chapters

## STORY STRUCTURE AWARENESS
Refer to the STORY_SKELETON for the authoritative act position of each chapter. The percentages below are a fallback only when no skeleton is available:
- **Early chapters** (first ~25%): Focus on setup, character introduction, inciting incident
- **Middle chapters** (~25-75%): Focus on rising action, complications, character development  
- **Late chapters** (final ~25%): Focus on climax, resolution, character transformation

Your chunk ({chunk_start}-{chunk_end}) covers chapters {chunk_start}/{total_chapters} to {chunk_end}/{total_chapters}. Check the skeleton for the planned arc position of each chapter in this range and write accordingly — do not guess or extrapolate from position alone.

## SKELETON FORMAT

For each chapter in your assigned range, output **exactly** this block — same field order, same labels, same markdown — with no extra prose before or after:

```
### Chapter [Number]: [Primary plot point or development]
**Characters**: [Comma-separated list of characters central to this chapter, noting key role or emotional state]
**Setting**: [Primary setting / location — use the canonical name from story elements]
**Events**:
- [Triggering beat — what sets this chapter in motion, 1 concrete sentence]
- [Development beat — key complication, confrontation, or discovery, 1 concrete sentence]
- [Resolution beat — how this chapter's conflict concludes within the chapter, 1 concrete sentence]
- [Optional 4th beat — subplot thread or secondary character moment; only include if substantive]
**Purpose**: [2-3 sentences: what this chapter accomplishes for the overall story, how it advances the protagonist's arc, and what thematic or emotional weight it carries]
**Consequence**: [2-3 sentences: what changes immediately after this chapter ends, how it raises or alters the stakes, and what it sets up for the chapters ahead]
```

Rules:
- The five bold labels (`**Characters**`, `**Setting**`, `**Events**`, `**Purpose**`, `**Consequence**`) are **mandatory** for every chapter. Do not omit any. Do not rename them. Do not reorder them.
- Write `**Events**` as a bullet list of 2–4 items. Each bullet is one concrete sentence describing a **distinct** story beat — a triggering event, a complication/confrontation/discovery, or a resolution. Do **not** collapse all beats into a single prose paragraph.
- Write all other fields in full sentences. Do **not** merge fields or emit alternate formats (no "Summary:", no JSON).
- Separate chapters with a single blank line.
- Do not include the chapter heading inside a code fence in the actual output — the fence above is illustrative.

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

### ❌ BAD (Vague, Repetitive, Ambiguous, Wrong Format)
```
**Chapter 5**: Sarah learns something important about her past
**Chapter 6**: Sarah discovers more about her background
```
Wrong because: headings use bold instead of `###`, fields are missing, body is a single vague clause.

### ✅ GOOD (Specific, Unique, Clear, Multi-sentence, Correctly Formatted)
```
### Chapter 5: Sarah uncovers her father's secret investigation
**Characters**: Sarah (grieving, uncertain), Uncle Marcus (mentioned), Father (via journal)
**Setting**: The attic of the family home
**Events**:
- While clearing out boxes, Sarah finds a locked briefcase containing her father's correspondence with a private investigator.
- The letters reveal her father believed her mother's death was not an accident and had been secretly building a case.
- Sarah reads enough to understand he was silenced before he could act, converting her grief into a search for answers.
**Purpose**: Converts the maternal-death backstory from accepted tragedy to active mystery, fundamentally redirecting Sarah's grief into purpose. It also reframes every interaction she has had with Uncle Marcus, making the familiar world feel suddenly hostile. The chapter marks the end of Sarah's passive acceptance and the beginning of her as an active investigator.
**Consequence**: Sarah no longer trusts Uncle Marcus and commits to finding the missing case files. The stakes shift from personal loss to potential danger — someone may have known what her father was doing.

### Chapter 6: Sarah confronts Uncle Marcus
**Characters**: Sarah (determined, frightened), Uncle Marcus (evasive, then threatening)
**Setting**: Marcus's study
**Events**:
- Sarah arrives at Marcus's study and confronts him with the letters, demanding answers.
- Marcus deflects with practiced calm until Sarah names the private investigator — his composure breaks and he seizes the letters by force.
- Marcus expels Sarah from the house with an explicit warning to stop asking questions; she overhears him on a phone call that reveals her mother's last employer.
**Purpose**: Closes the "trusted family" safety net and confirms that the threat is real rather than imagined. Marcus's reaction is more revealing than any answer he could have given — Sarah now knows someone powerful enough to intimidate her father is still watching. The confrontation also tests Sarah's courage and she passes, even under pressure.
**Consequence**: Sarah loses her home and her last family connection but gains a concrete lead — the name of her mother's last employer, overheard when Marcus made a phone call thinking Sarah had left. The danger is now explicit and personal.
```

## QUALITY CHECKLIST
Before finalizing your output, verify each chapter meets these criteria:
- ✅ **Continuity Compliance**: Does this chapter follow the escalation and progression specified in the continuity summary?
- ✅ **Proper Escalation**: Are stakes appropriately higher or more complex than previous chapters?
- ✅ **Character Arc Continuity**: Do character developments follow established patterns from previous chunks?
- ✅ **Plot Thread Continuity**: Are active storylines from previous chapters properly addressed?
- ✅ **Pacing Consistency**: Does this chapter maintain the established story rhythm and intensity patterns?
- ✅ **Unique Purpose**: Does this chapter accomplish something different from all others?
- ✅ **Distinct Beats**: Are the Events bullets truly distinct from each other — no two bullets describing the same moment?
- ✅ **Specific Events**: Can someone clearly understand what exactly happens in this chapter?
- ✅ **Clear Actions**: Are the character actions concrete and definitive (not vague)?
- ✅ **Distinct Outcomes**: Does this chapter change something specific in the story?
- ✅ **Thematic Resonance**: Does this chapter contribute to the story's emotional and thematic depth?

## OUTPUT REQUIREMENTS
- Provide detailed skeleton entries for ALL requested chapters
- Use the exact skeleton format specified above
- **PRIORITIZE continuity compliance**: Follow escalation order and progression from continuity summary
- **Apply all guardrails**: No repetition, maximum specificity, complete clarity
- Maintain consistency with established story elements
- Ensure logical progression between chapters that respects previous chunk patterns
- Keep entries concise and suitable for later expansion
- **Each chapter must be DISTINCT and SPECIFIC** in its purpose and events
- **Pass the quality checklist** for every single chapter, especially continuity requirements

DO NOT INCLUDE A SUMMARY, COMMENTARY, OR OTHER HEADERS.  JUST THE FORMATTED OUTPUT.
