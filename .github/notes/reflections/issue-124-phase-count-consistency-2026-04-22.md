---
date: "2026-04-22"
issue: 124
pr: 130
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

<!-- Archived. Full note in archive/issue-124-phase-count-consistency-2026-04-22.md -->

## Pipeline phase count expressions not covered by Rule 6 count-staleness grep

### Finding

During PR #130, three documentation files contained stale phase count strings after adding Phase 2.5:
- `docs/README.md` — "9-phase story generation lifecycle" (still said 9 after Phase 2.5 added total to 10)
- `docs/features/custom-commands.md` — "nine-phase pipeline" (stale word form)
- `.github/notes/architecture.md` — phase count in description was not updated

These were caught by review (M-S-01 majority finding, S-I-03 singular finding). Coder Rule 6 already says "when adding or removing an item from a set that may be counted or inventoried in documentation, grep for the old count (e.g., 'Four tools', '4 tools')". However, this guidance is insufficient for pipeline phase counts because:

1. **Word and hyphenated forms** — pipeline phases are expressed as `"9-phase"`, `"nine-phase"`, `"nine primary phases"` — not bare numbers. A grep for `"9"` or `"ten"` will not reliably catch these patterns.
2. **Compound adjective form** — `"9-phase story generation lifecycle"` buries the count inside a noun phrase. Standard numeric sweep misses it.
3. **No explicit high-risk file list** — the files that contain phase count strings are known and recurrent; naming them in the sub-bullet eliminates guesswork.

### Observation

Coder Rule 6 correctly identifies the pattern (count-staleness on item addition) but the generic guidance does not translate to pipeline phase counts in practice. The Coder may run `grep -r "9" .` and miss all hyphenated and word-form occurrences. A specific sub-bullet naming the search patterns and known high-risk files closes the gap.

This is a second-occurrence: the feature docs for custom-commands.md (issue #129/123 era docs) also lagged the phase count, and the SKILL.md phase count in PR #130 was the unanimous blocker. The pattern is structurally recurrent: every time a new phase is added, phase count strings scatter across 5+ files.

### Suggested Improvement

**Coder Rule 6 — add a pipeline phase count sub-bullet at the end of Rule 6's sub-bullets:**

> - **When adding a new story pipeline phase or sub-phase** (a Phase N or Phase N.5 entry) — grep the workspace for all phase count expressions in both numeral and word form before wrapping up. Phase counts appear as hyphenated adjectives and prose sentences that are not caught by a standard number grep alone (a search for `"9"` will not match `"nine-phase"`). Search for the old count in all surface forms: `"9-phase"`, `"nine-phase"`, `"nine primary phases"`, `"9 primary phases"` and their equivalents for the new total. Known high-risk files: `docs/README.md`, `docs/features/story-orchestrator.md`, `docs/features/custom-commands.md`, `.github/notes/architecture.md`, `.opencode/skills/story-pipeline/SKILL.md`.

### Action Taken

Applied: Added pipeline phase count sub-bullet to Coder Rule 6, at the end of Rule 6's sub-bullets, immediately before Rule 7 begins.
