---
date: "2026-04-30"
issue: 254
pr: 255
category: agent
targets:
  - ".opencode/agents/researcher-kimi.md"
  - ".opencode/agents/researcher-qwen.md"
  - ".opencode/agents/researcher-glm.md"
severity: minor
status: archived
---

> **Archived.** See canonical copy: `archive/issue-254-researcher-variants-missing-sync-note-2026-04-30.md`


### Finding

The three researcher variant files (`researcher-kimi.md`, `researcher-qwen.md`, `researcher-glm.md`) have no sync note. The three auditor variants have carried a sync note since their creation. PR #255 (issue #254) added missing permissions to all six variant files, revealing that researcher variants are structurally parallel to auditor variants but lack the same protective annotation.

### Observation

Without a sync note, future Coders editing researcher variants have no inline prompt to apply changes in lockstep. The auditor variants demonstrate that even with a sync note, frontmatter divergences can slip through — but without one, both body text and frontmatter edits are unprotected. The researcher family is identically at risk.

### Suggested Improvement

Add a sync note equivalent to the auditor sync note to all three researcher variant files, referencing the correct variant filenames and parent agent relationship.

### Action Taken

Applied: Added sync note (matching auditor format, adjusted for researcher filenames) to `researcher-kimi.md`, `researcher-qwen.md`, and `researcher-glm.md`.
