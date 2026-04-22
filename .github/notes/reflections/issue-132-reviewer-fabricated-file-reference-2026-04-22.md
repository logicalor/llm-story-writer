---
date: "2026-04-22"
issue: 132
pr: 136
category: agent
targets:
  - ".github/agents/orchestrator-v3.agent.md"
severity: minor
status: archived
---

<!-- Archived. Full note in archive/issue-132-reviewer-fabricated-file-reference-2026-04-22.md -->
 — singular finding triage gap

### Finding

During PR #136 review, the GPT reviewer cited a `narrative-arc` SKILL.md as a companion
file the PR should have updated. No such file exists. The file reference was fabricated —
the reviewer inferred (incorrectly) that a skill file matching the feature domain would
exist at `.opencode/skills/narrative-arc/SKILL.md`.

The Orchestrator's Phase D singular-finding guidance already says: "may be a false positive,
fix only if clearly valid." The diff-whitespace note covers syntax misreads, but there is
no explicit note about fabricated companion-file references. The triage guidance assumes
the finding refers to real files by default.

### Observation

Companion-file findings (e.g. "this SKILL.md should have been updated") are high-value when
accurate — the `opencode.json` and `story-pipeline/SKILL.md` checklist items exist precisely
because real companion files were missed in reviews. However, a reviewer fabricating a file
path for a non-existent companion is the inverse failure: it creates a follow-up action that
targets a phantom. Without an explicit triage instruction to verify file existence, the
Orchestrator may dispatch a Coder to create or search for a file that was never part of the
actual codebase.

This is the first recorded occurrence. The fix is a single sentence addition to the Phase D
singular-finding guidance.

### Suggested Improvement

**Orchestrator Phase D, `★☆☆ Singular` bullet — extend the triage guidance:**

Append to the existing sentence:

> If the claim references a companion file (e.g. a SKILL.md, config file, or shared process
> file) that should have been updated, verify the file actually exists on disk (`ls path/to/file`
> or `grep -r 'filename'`) before acting on the finding — reviewer models occasionally fabricate
> file paths that do not exist. An update-required finding for a non-existent file is a false
> positive. (Example: issue #132, PR #136 — GPT cited `narrative-arc/SKILL.md` which does not
> exist.)

### Action Taken

Applied: Extended the `★☆☆ Singular` triage bullet in Orchestrator Phase D to include
fabricated file reference guidance.
