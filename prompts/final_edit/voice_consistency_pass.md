Analyze the following single chapter against the manuscript's established prose style and recent continuity context.

Chapter text:
{chapter_text}

Prior chapters summary:
{prior_chapters_summary}

Your task:
- Evaluate voice consistency relative to the manuscript's established style.
- Identify pacing issues, including scene length imbalance, weak or abrupt tension arcs, and dialogue-to-action ratio problems.
- Identify cross-chapter coherence issues that manifest inside this chapter, including POV drift, character voice drift, tonal inconsistency, and transitions that no longer match prior chapter setup.
- Focus on prose and paragraph execution only.

Scope constraints:
- Do not propose plot-event changes.
- Do not change entity facts, continuity facts, timeline facts, or world rules.
- Do not replace the whole chapter.
- Suggest only surgical prose-level or paragraph-level fixes that preserve the existing story events and factual content.
- Use paragraph references for locations, such as "opening paragraph", "paragraph 7", or "final two paragraphs".

Return a JSON object with this shape:
{
  "issues": [
    {
      "type": "voice_consistency|pacing|cross_chapter_coherence",
      "location": "paragraph reference",
      "description": "clear explanation of the prose problem",
      "suggested_fix": "targeted prose-level revision instruction"
    }
  ]
}

Flag only issues where a targeted prose revision would materially improve clarity, flow, tone, or stylistic continuity.

IMPORTANT:
Output only the JSON object. No preamble, no markdown fences, no commentary.