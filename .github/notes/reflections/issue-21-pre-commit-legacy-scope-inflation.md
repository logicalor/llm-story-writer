---
date: "2026-04-16"
issue: 21
pr: 66
category: agent
targets:
  - ".github/agents/orchestrator-v3.agent.md"
severity: minor
status: active
---

## Pre-commit hooks auto-fixed 156 legacy files — scope inflation variant

### Finding

During issue #21 (Build Custom Commands), a review-fix commit triggered pre-commit hooks (ruff auto-format) that modified 156 files of legacy code. These were not functional changes — they were formatting normalizations applied to files never intentionally edited as part of the task. This inflated the PR diff significantly.

### Observation

This is a new variant of the scope inflation pattern documented in issue #16 (line-ending contamination). The issue #16 reflection proposed a scope validation check in Orchestrator Step 5d. The variants observed so far:

- **Issue #5:** Auto-formatter changes mixed with functional commits (Coder Rule 8 covers this)
- **Issue #16:** Line-ending normalization artifacts from `git checkout` (proposed Step 5d check)
- **Issue #21:** Pre-commit hook auto-formatting legacy files not part of the task

The issue #21 variant is distinct because:
1. The scope inflation happens **during commit** (pre-commit hook), not during editing
2. The Orchestrator's proposed Step 5d check (inspect `git diff --stat` before committing) would **not catch this** — the changes hadn't occurred yet when the audit ran
3. The root cause is that `ruff` reformats any file it touches, and `git add -A` stages everything including auto-fixed files

Mitigation options:
- Add `legacy/` to ruff's exclude list in `pyproject.toml` (prevents ruff from touching legacy files)
- Use `git add` with specific paths instead of `git add -A` to avoid staging unintended changes
- The proposed `.gitattributes` from issue #16 wouldn't help here — this is formatter-driven, not encoding-driven

### Suggested Improvement

When the issue #16 scope validation proposal is applied to Orchestrator Step 5d, add this variant to the common causes list:

```markdown
- **Pre-commit hook auto-formatting** in files outside task scope — if `ruff` or similar tools auto-fix legacy or unrelated files during commit, inspect which files were modified and revert unrelated formatting changes
```

Additionally, consider adding `legacy/` to ruff's exclude configuration as a follow-up item in `deferred.md`.

### Action Taken

No action taken — this extends the pending issue #16 Step 5d proposal. Recorded as supporting evidence and a new scope inflation variant.
