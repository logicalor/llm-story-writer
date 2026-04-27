---
date: "2026-04-27"
issue: 214
pr: 220
category: skill
targets:
  - ".agents/skills/documentation-maintenance/SKILL.md"
  - ".agents/skills/code-review/references/checklist.md"
severity: minor
status: archived
---

## Documenter Missed Stale References During Documentation Reconciliation

### Finding

During PR #220 (documentation reconciliation), the Documenter agent missed two stale references that reviewers later caught:

1. **README project structure tree** still referenced an old directory name after a move.
2. **PRD Goal 5** contained a stale term that had been renamed in the implementation.

Additionally, a broken markdown link (ADR 008 filename mismatch) was only caught by a single reviewer, suggesting the review surface was under-utilised.

### Observation

The Documenter dispatch prompt did not explicitly instruct the agent to scan the **entire file** for all occurrences of changed terms. The agent performed section-local edits, which is sufficient for most code changes but insufficient for documentation sweeps where a renamed term may appear in tables, trees, headings, and cross-references across the whole document.

The review cycle for this docs-only PR produced high-value findings, indicating that the review prompt should also emphasise full-file scanning more strongly for documentation changes.

### Suggested Improvement

1. **documentation-maintenance SKILL.md** — Add explicit instructions in the Workflow and Rules sections:
   - "Scan the full file for every occurrence of changed terms; don't assume a single-section edit is sufficient."
   - "When files are renamed or ADR numbers change, verify all internal markdown links still resolve."

2. **code-review checklist** — Add two items under "Docs And Instructions":
   - "Scan the full file for stale references — not only the diff context."
   - "For documentation-only PRs, verify cross-file consistency aggressively; reviewers are the last line of defence against stale references."

### Action Taken

Applied:
- Added full-file scan instruction to `documentation-maintenance/SKILL.md` Workflow step 5 and Rules list.
- Added link-verification reminder to `documentation-maintenance/SKILL.md` Workflow step 6.
- Added full-file scan and docs-only PR emphasis items to `code-review/references/checklist.md` under "Docs And Instructions".
