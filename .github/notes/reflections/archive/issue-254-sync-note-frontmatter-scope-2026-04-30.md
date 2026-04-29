---
date: "2026-04-30"
issue: 254
pr: 255
category: agent
targets:
  - ".opencode/agents/auditor-kimi.md"
  - ".opencode/agents/auditor-qwen.md"
  - ".opencode/agents/auditor-glm.md"
severity: minor
status: archived
---

## Auditor variant sync note covers body text only — not frontmatter

### Finding

The sync note present in all three auditor variant files reads: "Any change to this body text **must be applied to all three files in lockstep**." PR #255 (issue #254) corrected a frontmatter divergence — missing `"echo*": "allow"` and `"chroma/*": true` in all six variant files — that the sync note did not guard against. The phrase "body text" implicitly excludes the YAML frontmatter block above the separator.

### Observation

The sync note's purpose is to prevent silent divergence between variant files. Restricting its scope to "body text" leaves frontmatter (permissions, tools, mode, model) unprotected by the warning. A Coder reading the note may reasonably infer that frontmatter changes are exempt from the lockstep requirement. The actual divergence in PR #254 was entirely in the frontmatter, which the note did not cover.

### Suggested Improvement

Replace "Any change to this body text" with "Any change to this body text or other frontmatter" in all three auditor variant files. This makes the sync obligation explicit for both content regions.

### Action Taken

Applied: Expanded sync note phrase from "this body text" to "this body text or other frontmatter" in `auditor-kimi.md`, `auditor-qwen.md`, and `auditor-glm.md`.
