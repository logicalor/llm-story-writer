---
date: "2026-04-23"
issue: 138
pr: 139
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## New code should not replicate pre-existing inline import style debt

### Finding

During PR #139 (Handle `PromptLoader.ConfigurationError` in `cmd_generate_handoff`), all three
reviewers raised finding M-W-01: the new `from src.infrastructure.prompt_loader import
PromptLoader` import was placed inline (inside the function body) rather than at module level. The
Coder had matched the style of two pre-existing inline imports already present in
`generate_handoff.py`. The finding was correctly deferred as consistent with the existing file
pattern, with follow-up issue #140 created to clean up all three inline imports together.

### Observation

The Coder placed the new import inline to maintain local file consistency — a reasonable heuristic
that avoids mixed style within a single function. However, the review checklist Phase 2 General
already mandates module-level imports. By matching a pre-existing deviation, the Coder introduced
a third instance of technical debt in that file and created a reviewer obligation (M-W-01) that
required explicit deferral and a follow-up issue.

The correct behaviour is: **new code follows project convention (module-level imports), not local
file deviations**. The Coder should not treat the presence of pre-existing inline imports as
licence to add more. If the file has inline imports, that is existing debt — note it in the
handoff summary under "Out-of-scope observations" (per Rule 11) but write the new import at module
level.

This is distinct from the existing Rule 7 sub-bullet about import removal safety (refl-issue-111).
That sub-bullet covers *removing* imports; this covers *adding* new imports in a file with
existing style debt.

### Suggested Improvement

Add a sub-bullet to coder.agent.md Rule 7's import section:

> - **When adding a new import to a file that already has inline (function-body) imports** — place
>   the new import at module level regardless of the pre-existing inline style. Do not match
>   existing inline placement; matching local deviations introduces new debt and triggers review
>   findings. Record the pre-existing inline imports as an out-of-scope observation for the
>   Orchestrator to track separately.

### Action Taken

Applied: added sub-bullet to Rule 7 import section in `.github/agents/coder.agent.md` — new
imports should be placed at module level even when the file already contains inline imports.
