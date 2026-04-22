---
date: "2026-04-22"
issue: 133
pr: 137
category: instruction
targets:
  - ".github/agents/_shared/review-checklist.md"
severity: minor
status: archived
---

## TS Zod schema making field required breaks existing agent call sites — not covered by API signature changes item

### Finding

During PR #137, `operation` was transitioned from absent/optional to a **required** field in
the `story-assembler` TypeScript wrapper's Zod schema (the union `z.enum(["assemble",
"generate-handoff"])`). Phase 7g was correctly updated to pass `operation: "generate-handoff"`,
but the pre-existing Phase 8 call site — which invoked `story-assembler` with only `storyName`
— was not updated. At runtime Phase 8 would fail Zod validation with no manuscript produced.

All three review models (Claude, GPT, Gemini) caught this unanimously as a Critical.

### Observation

The `review-checklist.md` Phase 2 "API signature changes" item says:

> if a function, method, or constructor signature changed (parameter added/removed/renamed),
> grep the workspace for callers

This is framed in Python-centric terms ("function, method, or constructor"). It does not
explicitly mention TypeScript tool wrapper Zod schema changes as a trigger. A reviewer may
not recognise that adding a required Zod field is a signature change requiring a caller sweep
over all agent instruction files that invoke the tool.

Agent instruction call sites live in `.opencode/agents/*.md` — not in `.py` or `.ts` files.
A grep for Python callers silently misses all agent-file invocations. The checklist needs an
explicit sub-trigger for TS wrapper schema changes.

### Suggested Improvement

**`review-checklist.md` Phase 2 General section — extend the API signature changes item** to
add an explicit TS wrapper sub-trigger:

> Also applies to TypeScript tool wrapper Zod schema changes: if a field transitions from
> `.optional()` to required (or a new required field is introduced), grep all agent instruction
> files for invocations of that tool
> (`grep -rn 'tool-name' .opencode/agents/ .opencode/skills/`) and verify every call site
> passes the now-required field. Agent call sites live in Markdown files and are never in the
> diff when the gap is in a pre-existing call site. (Source: issue #133, PR #137 — `operation`
> made required in `story-assembler`; Phase 8 call site omitted the field and was not in the
> diff.)

### Action Taken

Applied: Extended the "API signature changes" item in `review-checklist.md` Phase 2 General
section to include a TS Zod schema sub-trigger for agent instruction call site sweeps.
