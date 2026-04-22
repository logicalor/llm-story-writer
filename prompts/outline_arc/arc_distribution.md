Analyze the dramatic weight distribution across this story outline.

<OUTLINE>
{outline}
</OUTLINE>

Treat the outline as the authoritative source. If it is JSON, infer the chapter count, chapter numbers, and dramatic shape from each `chapter_synopsis`. If it is prose, infer the same structure as carefully as possible.

Your task:
- Identify the approximate three-act boundaries for the full story.
- Rate each chapter's dramatic intensity on a 1-5 scale based on conflict, reversals, escalation, and consequence.
- Identify any dead zones: consecutive chapters with low dramatic intensity or weak escalation.
- Identify the climax chapter and assess whether it lands at roughly 75-85% through the story.
- Assess whether Act II carries roughly 50-60% of the story's dramatic content. Use the chapter intensity map to justify the conclusion.

Guidelines:
- Use approximate percentages when exact math is not possible.
- Be concrete. Reference chapter numbers and synopsis-level evidence.
- Intensity scale:
  - 1 = setup, low tension, little conflict movement
  - 2 = mild friction or transition
  - 3 = meaningful tension or complication
  - 4 = major escalation, revelation, or setback
  - 5 = peak tension, decisive reversal, or climax-level pressure
- If the outline is thin, state the uncertainty but still provide the best assessment possible.

Present your results in this exact format:

## Arc Distribution Analysis

### Act Boundaries
Act I: Chapters 1-N (N% of story)
Act II: Chapters N-M (M% of story)
Act III: Chapters M-end (Z% of story)

### Chapter Intensity Map
Chapter 1: [intensity 1-5] - [brief reason]
...

### Issues Found
- [dead zones, mis-positioned climax, unbalanced acts]

### Climax Assessment
Position: Chapter N (X% through story)
Verdict: [Well-positioned / Too early / Too late]

IMPORTANT:
- Output only the analysis.
- Keep the chapter intensity map complete for every chapter.
- If no major issues are found, say so explicitly in the Issues Found section.