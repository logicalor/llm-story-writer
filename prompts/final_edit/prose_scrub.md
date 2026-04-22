Analyze Chapter {chapter_number} for sentence-level and paragraph-level prose problems that are worth fixing.

Chapter text:
{chapter_text}

Targets:
- Adverb overuse, especially common offenders such as quickly, suddenly, softly, quietly, sharply, immediately, slowly, carefully, finally, and heavily.
- Filter words and phrases such as "he saw that", "she felt that", "she noticed that", "he heard", "she watched", and similar distancing constructions.
- Repetitive phrase patterns, repeated sentence openings, or echoed wording within the chapter.
- Show-vs-tell imbalance where a sentence tells an emotional or sensory state that should be rendered more directly on the page.

Severity threshold:
- Flag only issues where the proposed change meaningfully improves prose quality.
- Ignore harmless style variance.
- Do not create busywork edits.

Scope constraints:
- Keep every suggestion at sentence or paragraph scope.
- Preserve plot events, entity facts, chronology, and chapter meaning.
- Quote the exact original text for each issue.

Return a JSON object with this shape:
{
  "issues": [
    {
      "type": "adverb|filter_word|repetition|show_tell",
      "original_text": "exact quote from the chapter",
      "suggested_replacement": "improved wording or revision instruction",
      "line_context": "brief nearby context for locating the issue"
    }
  ]
}

IMPORTANT:
Output only the JSON object. No preamble, no markdown fences, no commentary.