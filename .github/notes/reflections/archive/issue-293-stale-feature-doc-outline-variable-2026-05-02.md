---
date: "2026-05-02"
issue: 293
pr: 305
category: instruction
targets:
  - "docs/features/direct-generation-prompts.md"
severity: minor
status: active
---

## ConsistencyCheckerAgent `outline` variable description stale after PR #305

### Finding

After PR #305 plumbed real outline data into `ConsistencyCheckerAgent`, the feature doc
`docs/features/direct-generation-prompts.md` still described the `outline` computed variable as:

> `outline` — currently empty string (reserved for future use)

That comment predated the fix. The variable is no longer empty — it is now populated by
`_extract_outline_text(outline_result, chapter_number)`, which prefers `chapter_details[N-1]`,
falls back to `chapter_outlines[N-1]`, and returns `""` only when neither is present.

### Observation

"Reserved for future use" annotations in feature docs become stale the moment the feature ships.
When the Documenter is not dispatched (or a narrowly-scoped fix is merged without a doc pass),
these markers persist indefinitely. Reviewers may then cite them as architecture references and
incorrectly conclude the field is unused.

### Suggested Improvement

Update the `outline` bullet under ConsistencyCheckerAgent in `docs/features/direct-generation-prompts.md`
to describe actual behaviour: populated by `_extract_outline_text()` from `OutlineResult`, with
`chapter_details` preferred over `chapter_outlines`, empty string when neither is available.

### Action Taken

Applied: updated the `outline` variable description in `docs/features/direct-generation-prompts.md`
to reflect the real behaviour introduced in PR #305.
