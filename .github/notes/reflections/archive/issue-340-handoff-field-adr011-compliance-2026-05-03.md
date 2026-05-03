---
date: "2026-05-03"
issue: 340
pr: 341
category: agent
targets:
  - ".github/agents-copilot/coder.agent.md"
severity: minor
---

## New handoff field with markdown content requires tri-part ADR 011 compliance

### Finding

Issue #340 / PR #341 fixed a compliance gap: `OutlineResult.base_context` and
`OutlineResult.story_elements` were listed in ADR 011 as fields that must be persisted as
markdown pointer refs (`{"$ref": "path"}`), but neither the type annotation in
`handoffs.py`, the migration script `migrate_inline_markdown.py`, nor the orchestrator
read paths had been updated when the fields were originally added to the dataclass. The
fix required three coordinated changes: type widening in `handoffs.py`, a new migration
branch in `migrate_inline_markdown.py`, and updated read paths in `orchestrator.py`.

### Observation

The existing coder Rule 11 sub-bullet covers **converting an existing field** from inline
to `$ref` (test expectation drift). No rule covers the case of **adding a new field** that
contains markdown content — the tri-part obligation (type widening + migration coverage +
orchestrator read path) was implicit and unguided. A developer adding a field follows the
existing dataclass defaults (`str = ""`), which is syntactically valid but ADR
011-non-compliant. The gap is invisible to lint and mypy: both accept a plain `str` field.
The consequence is that story state persisted after the field was added contains raw
inline markdown rather than a portable `$ref` pointer — correct only by accident for new
stories that have never been migrated.

### Suggested Improvement

Add a sub-bullet to Rule 6 in `.github/agents-copilot/coder.agent.md` immediately after
the existing `"When converting a JSON field from inline content to a {"$ref": "path"}
pointer"` sub-bullet in Rule 11. (Or alternatively, add to Rule 6 under the field-change
cluster.) The guidance should enumerate the three required co-changes and cite this issue
as source.

### Action Taken

Applied: added sub-bullet to Rule 6 in both `.github/agents-copilot/coder.agent.md` and
`.github/agents-openrouter/coder.agent.md` under the field-operations cluster —
"When adding a new field to a pipeline handoff dataclass that stores markdown content" —
documenting the tri-part obligation (type widening, migration coverage, orchestrator read
path). Minor improvement auto-applied.
