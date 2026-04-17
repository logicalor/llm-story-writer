---
date: "2026-04-16"
issue: 25
pr: 72
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: active
---

## Schema fabrication defect class absent — 3rd consecutive confirmation

### Finding

During issue #25 (Context Budgeting & Wiki Skills), three new skill files were created (context-budgeting, wiki-conventions, wiki-maintenance refinement) with content faithfully reproduced from ADRs 004 and 005. No schema fabrication occurred — all page type schemas, frontmatter specs, scoring formulas, and configuration references matched their source documents.

### Observation

This is the **third consecutive issue** where the schema fabrication defect class (identified in issues #19 and #22) was absent:

1. **Issue #18** — Schema verification applied correctly (first confirmation)
2. **Issue #22** — Fabrication recurred in payload format (new variant caught, fixed)
3. **Issue #25** — No fabrication in three new skill files (third confirmation)

The streak suggests that the informal lesson has stabilised for skill authoring when source material (ADRs, existing docs) is available. The user explicitly noted "content was faithfully reproduced from ADRs" — having concrete source documents to reference may be a key factor in preventing fabrication, versus the issue #19/22 cases where the Coder was reconstructing tool schemas from memory.

This positive signal further supports the pending Rule 10/11 proposal (issue #19) as a formal backstop, but suggests the rule's impact will be strongest for cases where no explicit source document exists (tool parameter schemas, payload formats) rather than for ADR-sourced content.

### Suggested Improvement

No rule change needed. The pending issue #19/22 schema verification rule proposal remains the correct long-term fix. This observation narrows the highest-risk surface: fabrication is most likely when the Coder must reconstruct structured data from memory rather than copying from a source document.

### Action Taken

No action needed — positive signal recorded. Third confirmation of informal carry-forward for schema fabrication defect class.
