---
date: "2026-04-25"
issue: 181
pr: 192
category: agent
targets:
  - ".github/agents/synthesizing-reviewer.agent.md"
severity: minor
status: archived
---

## False positive: reviewer claims "must call X as a script/subprocess"

### Finding

During the PR #192 review, Gemini raised a Critical finding: the orchestrator must call
`story_assembler.py` as an external script or subprocess rather than calling its functions directly.
The Synthesizing Reviewer correctly downgraded this as a false positive — the correct approach is
importing and calling the underlying helper functions inline, not subprocess invocation of a CLI
entry point.

### Observation

Reviewers occasionally conflate "there is a CLI tool for this" with "the correct integration method
is subprocess invocation". This false positive is structurally similar to the `.vscode/` path
false positive (file not in diff) — in both cases a reviewer constructs a finding that sounds
plausible based on surface-level evidence but fails when checked against the actual codebase
architecture.

The rule for this project is that `cmd_*()` CLI entry points use `sys.exit()` and are not safe
to call from library/orchestration code. The correct integration surface is the underlying
`_helper()` functions. When a reviewer asserts "must call X as a script", the assertion is likely
a false positive unless the codebase explicitly delegates to subprocesses for that operation.

### Suggested Improvement

Add a false-positive filter bullet to the Synthesizing Reviewer's Step 2 (Cross-Reference and
Classify) or the existing false-positive filter block:

> **"Must call X as a script/subprocess" filter:** If a reviewer asserts that an orchestrator or
> library module must call a CLI tool as an external script or subprocess rather than importing its
> functions directly, verify whether (a) the project does use subprocess delegation for that class
> of tool, and (b) the CLI entry point uses `sys.exit()`. In this project, `src/tools/*.py`
> modules expose `cmd_*()` entry points that call `sys.exit()` on error — calling them from
> `src/presentation/` or `src/application/` code is a known anti-pattern. A finding that demands
> subprocess invocation of an internal `src/tools/*.py` module is likely a false positive.
> Downgrade to Suggestion with the note "inline function call is the correct integration surface."

### Action Taken

Applied: Added false-positive filter bullet to `synthesizing-reviewer.agent.md` Step 2.
