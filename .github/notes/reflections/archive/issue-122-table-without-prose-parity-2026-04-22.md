---
date: "2026-04-22"
issue: 122
pr: 126
category: instruction
targets:
  - ".github/agents/_shared/review-checklist.md"
severity: minor
status: archived
---

## Table entry without prose subsection — documentation parity gap

### Finding

PR #126 added `character-sheet-generator` to three normative agent registry tables (AGENTS.md, docs/features/story-orchestrator.md, the story-pipeline SKILL.md) but initially omitted a `### character-sheet-generator` prose subsection in docs/features/story-orchestrator.md. The Subagents table became a four-row table while only three agents had corresponding named sections below it. All three reviewers unanimously flagged the asymmetry (U-W-01); it was fixed before merge.

### Observation

This is a recurring risk whenever a documentation PR adds rows to reference tables: the table is the high-visibility, search-friendly surface, so it receives the edit — but the accompanying prose block (subsection, detail description, links) is easy to forget. The asymmetry is not caught by lint tools or tests, only by a human or review model noticing the mismatch between table row count and prose subsection count.

The pattern is especially sharp for Subagents/Tools/Commands sections in feature docs, where the convention is: one row in the table → one `###` subsection below.

### Suggested Improvement

Add a table/prose parity check to Phase 7 (Documentation Review) in the shared review checklist. Reviewers — and review sub-agents — should explicitly verify that each new table row has a corresponding prose section (or that the absence is deliberate and noted).

### Action Taken

Applied: added `**Table/prose parity**` checklist item to Phase 7 — Documentation Review in `.github/agents/_shared/review-checklist.md`.
