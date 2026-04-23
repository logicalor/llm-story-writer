---
date: "2026-04-24"
issue: 156
pr: 157
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: archived
---

## No gotcha entry for empty story-state outline after chunked generation

### Finding

The failure mode fixed by PR #157 — `outline-generator expand-chapter` completing all iterations without the agent consolidating chunk outlines, leaving `story-state field outline` empty — was not documented in `gotchas.md`. Claude suggested this as S-I-03 in the review synthesis. Future debugging agents may not recognise the cause and attempt incorrect recovery paths.

### Observation

The failure is non-obvious because:
1. `expand-chapter` succeeds and returns data — there is no error signal.
2. Savepoints for each chunk are written correctly by the tool.
3. The empty outline field is only detected downstream: arc analysis fabricates ratings (no text to evaluate), and Phase 7a expands chapters without approved synopsis context.
4. The validation guard in `story-planner` provides the first explicit failure signal — but by then the orchestrator has already attempted to write the field (or failed its own guard).

Documenting this as a gotcha gives future debugging sessions a direct pointer to the class of failure.

### Suggested Improvement

Add gotcha 013 to `.github/notes/gotchas.md` covering the chunked outline consolidation failure pattern.

### Action Taken

Applied: added gotcha 013 "Chunked outline generation: must explicitly concatenate `data.chunk_outline` values — no tool auto-merges" to `.github/notes/gotchas.md`.
