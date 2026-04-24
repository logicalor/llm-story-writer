---
date: "2026-04-25"
issue: 163
pr: 174
category: instruction
targets:
  - ".github/agents/_shared/review-checklist.md"
severity: minor
status: archived
---

## Error-state rendering gap: GPT caught green "complete" on error; Claude and Gemini missed it

### Finding

The TUI status indicator rendered a green "✓ Complete" label when the pipeline ended with
an error status. The condition branch for the error state was absent — the error case fell
through to the default "complete" branch. GPT reviewer flagged this as a Correctness Warning;
Claude and Gemini did not mention it.

The root cause is a review blind spot: reviewers focus on happy-path rendering (what the widget
looks like on success) and are less likely to mentally trace all terminal states through the
rendering logic. Error paths in UI components are low-frequency and easy to miss when the diff
only shows the happy-path being added.

### Observation

This is a recurring pattern: error-state UI rendering is under-reviewed because:
1. It requires enumerating all non-happy exit states — not just the one being implemented.
2. Visual evidence requires running the code with a real error scenario.
3. The failure mode (green "complete" on error) does not crash and is not tested by default.

The asymmetry across reviewers (GPT caught it, Claude/Gemini did not) suggests the existing
Phase 3 checklist does not adequately prompt reviewers to audit error-state rendering paths.

### Suggested Improvement

Add a Phase 3 checklist item to `.github/agents/_shared/review-checklist.md`:

> **Status/state enum completeness** — for any widget, component, or UI element that renders
> a finite set of states (status, mode, phase, result), verify a distinct and correct visual
> representation exists for *every* value in the enum or set — including error, failure, and
> cancelled states. Trace each non-success exit path through the rendering code and confirm
> the correct label, colour, and icon are applied. A missing branch typically falls through to
> the default (often the success branch), producing a misleading "complete" or "ok" indicator
> on failure.

### Action Taken

Applied: Added status/state enum completeness check to Phase 3 of review-checklist.md.
