---
date: "2026-04-14"
issue: 53
pr: 55
category: agent
targets: []
severity: minor
status: archived
---

## Clean shared-utility refactor confirms pipeline maturity and partial pattern-amnesia mitigation

### Finding

Issue #53 (PR #55) extracted `_validate_story_name` from 14 tool files into the shared `src/tools/_io.py` module (which already contained `_atomic_write`). Pure refactor: 76 insertions, 165 deletions — net reduction of ~89 lines. Synthesized review found one pre-existing style issue: unguarded `sys.path.insert(0, ...)` calls in files touched by the refactor. These were fixed by adding `if X not in sys.path:` guards. All 194 tests pass.

One residual remains: `src/tools/prompt_loader.py` still has an unguarded `sys.path.insert` at line 9, but was not in scope for this PR.

### Observation

This is the second clean refactor-only issue through the full Orchestrator pipeline (after issue #50 / PR #51). Both passed Synthesized Review with minimal findings and zero regressions, confirming the pipeline handles non-feature work without friction.

The `_io.py` shared module now centralises two of the most-duplicated patterns across all tools: path-traversal validation (`_validate_story_name`) and atomic file writes (`_atomic_write`). This directly mitigates the "Coder pattern amnesia" theme from issue #6 — new tool implementations can import these patterns rather than re-implementing them. The Coder's existing Rule 10 (prior-tool review) is complemented by importable shared utilities that make the correct pattern the path of least resistance.

The `sys.path.insert` guard fix is part of a recurring systemic pattern noted in issue #12's system-health reflection ("Pre-existing mypy issues with sys.path-based imports across all tools — systemic, not agent issue"). The refactor opportunistically cleaned up 13 of the 14 files; `prompt_loader.py` remains as the sole unguarded instance.

### Suggested Improvement

No agent or instruction changes needed. The shared utility pattern is self-reinforcing — `_io.py` exists, tools import from it, and new tools will naturally follow the same pattern. The remaining `prompt_loader.py` sys.path guard is a standalone code cleanup, not an agent system issue.

### Action Taken

No action needed — recorded as positive pipeline health signal and pattern-amnesia mitigation confirmation. Archived immediately.
