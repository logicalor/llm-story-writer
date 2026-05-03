<!-- STALE — archived to archive/issue-320-ledger-guard-pattern-2026-05-03.md — delete this file -->
---
date: "2026-05-03"
issue: 320
pr: 332
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
---

## Per-chapter ledger guard pattern not documented as a gotcha

### Finding

PR #332 (issue #320, ADR 010 granular checkpointing Tasks 7–11) introduced the per-chapter
post-processing ledger: `_is_work_item_done(state, phase, item_id)` and
`_mark_work_item_done(state, phase, item_id)`. These helpers gate idempotent per-chapter steps
(final editing, wiki-bootstrap, post-processing) so that a resumed pipeline skips chapters that
were already completed in a prior run.

This is a new recurring pattern in the orchestrator. Future pipeline phase authors will encounter
it and need to understand: (a) which helpers to use, (b) how to form a stable `item_id`, (c) that
`_mark_work_item_done` already saves the savepoint (no redundant `_write_savepoint` needed), and
(d) how to pick a unique `phase` key string.

None of this is documented in the existing knowledge base.

### Observation

Without a gotcha entry, future Coders implementing new per-chapter phases will read the existing
orchestrator code to infer the pattern — but they may miss the savepoint-save side-effect of
`_mark_work_item_done`, or they may choose a `phase` key that collides with an existing phase,
or they may add a redundant `_write_savepoint` call immediately after `_mark_work_item_done`.
All three failure modes are silent (no lint or type error).

### Suggested Improvement

Add gotcha #048 to `.github/notes/gotchas.md` documenting the ledger guard pattern.

### Action Taken

Applied: added gotcha #048 — per-chapter ledger guards — to `.github/notes/gotchas.md`.
