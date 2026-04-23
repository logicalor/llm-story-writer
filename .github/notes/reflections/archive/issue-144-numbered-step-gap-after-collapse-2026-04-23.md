---
date: "2026-04-23"
issue: 144
pr: 145
category: instruction
targets:
  - ".github/agents/_shared/review-checklist.md"
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Numbered step gaps after collapsing or removing workflow steps

### Finding

PR #145 collapsed the wiki-maintainer Mode 1 and Mode 2 workflows from seven detailed steps into two tool-delegated steps, but left the surviving "Establish wikilinks" / "Chapter boundary check" step as `8.`. Both lists ended up reading `1.`, `2.`, `8.` — a six-number gap in the middle of a numbered sequence. Two of three reviewers flagged this as Critical and the third as Suggestion. The shared review checklist had no item covering numbered-step-list integrity.

### Observation

Numbered step gaps in agent instruction files are a distinct defect class from prose count staleness (issue #124) and from intra-step variable name drift (issue #132):

- **Count staleness** is about numerals in prose (`"9-phase pipeline"`).
- **Variable drift** is about field names referenced across steps.
- **Step-number gaps** appear when a numbered step is removed or merged and the downstream step numbers are not renumbered. Markdown ordered-list rendering masks the gap visually (most renderers auto-renumber), so the defect is invisible in preview but plain in the source. LLMs reading the source as text — including the agents who load these files — see the literal numerals.

The risk is real for small models executing step-tracking reasoning ("now do step N+1") — a jump from `2.` to `8.` produces ambiguous "next step" behaviour.

This is distinct from Coder Rule 6's count-staleness sub-bullet because the gap is intra-file structural, not a count repeated across documents. It belongs in the review checklist as an Agent Instructions item, with a matching Coder reminder when refactoring numbered workflows.

### Suggested Improvement

1. Add an "Intra-file numbered step continuity" item under Phase 2 → Agent Instructions in `.github/agents/_shared/review-checklist.md`.
2. Add a sub-bullet to Coder Rule 7 (dead-code sweep section, which already covers orphaned-control-flow after mass deletion) extending the same instinct to numbered step lists when merging or removing steps in agent or skill workflow sections.

### Action Taken

Applied:
- Added "Numbered step continuity" item to the Phase 2 Agent Instructions section of `.github/agents/_shared/review-checklist.md`, citing PR #145.
- Added a sub-bullet to Coder Rule 7 in `.github/agents/coder.agent.md` covering renumbering after step removal/merge in numbered workflow sections.
