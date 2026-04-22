---
name: final-edit
description: Post-assembly prose quality pass for voice consistency, pacing, and sentence-level scrubbing. Use when operating as final-editor or prose-scrubber.
version: 1.0.0
---

# Final Edit Skill

This skill defines the final prose-polish layer that runs after chapter drafting. It covers chapter-level voice consistency, pacing, and cross-chapter coherence checks plus sentence-level prose scrubbing for adverbs, filter words, repetition, and show-vs-tell drift. Every pass is surgical. The goal is to improve readability and stylistic consistency without changing story events or factual content.

## Scope Constraints

- Permitted scope: sentence, paragraph, and local chapter-level prose revision.
- Allowed changes: wording refinement, rhythm adjustment, paragraph reshaping, dialogue/action balance tuning, line-level tonal alignment, repetition cleanup.
- Forbidden changes: new plot events, removed plot events, changed entity facts, changed timeline facts, changed world rules.
- Forbidden output pattern: wholesale chapter replacement or full-chapter rewrites.
- If a problem cannot be fixed surgically at prose scope, mark it `needs_review` instead of forcing a rewrite.

## Pass Types

| Pass | Scope | When | Agent |
|------|-------|------|-------|
| Voice Consistency | Chapter | Post-assembly, per chapter | final-editor |
| Pacing | Chapter | Post-assembly, per chapter | final-editor |
| Cross-Chapter Coherence | Manuscript | Post-assembly | final-editor |
| Prose Scrub | Sentence/Paragraph | Per-chapter post-generation | prose-scrubber |

## Output Format

Both agents work from JSON issue lists.

Shared envelope:

```json
{
  "issues": []
}
```

Final-editor issue shape:

```json
{
  "type": "voice_consistency|pacing|cross_chapter_coherence",
  "location": "paragraph reference",
  "description": "clear prose issue description",
  "suggested_fix": "targeted revision instruction"
}
```

Prose-scrubber issue shape:

```json
{
  "type": "adverb|filter_word|repetition|show_tell",
  "original_text": "exact quote",
  "suggested_replacement": "improved wording or revision instruction",
  "line_context": "brief nearby context"
}
```

## Revision Budget

Each pass produces targeted revisions via `scene-writer` with `operation: revise`; max 3 revision calls per chapter per pass type.

For the standalone `prose-scrubber` subagent, the scrub pass may extend to 5 revision calls per chapter when the orchestrator explicitly invokes Phase 7.5.

Batch and merge nearby issues when possible. Prefer one precise revision request over multiple overlapping calls.

## Status Tokens

- `clean` — no meaningful issues found.
- `revised` — one or more targeted prose changes applied.
- `needs_review` — issue exists but exceeds permitted prose scope.