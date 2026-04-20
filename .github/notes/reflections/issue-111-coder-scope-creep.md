---
date: "2026-04-21"
issue: 111
pr: 112
category: agent
targets:
  - ".github/agents/coder.agent.md"
  - ".github/agents/orchestrator-v3.agent.md"
severity: major
status: applied
---

## Coder scope creep — ~60 files modified for a 4-5 file task

### Finding

During PR #112 (savepoint extension-based format), the Coder was dispatched to modify
approximately 4-5 savepoint-related files. Instead it modified approximately 60 files,
including agent configs, wiki tools, config loaders, TypeScript wrappers, prompt templates,
and test files. It also introduced new modules (`_config.py`, `_io.py` validation, wiki fuzzy
matching) that were not part of the plan. The out-of-scope changes required extensive manual
revert work before the PR was in a mergeable state.

### Observation

The Coder has no explicit scope-discipline rule. When it encounters related code while
implementing a feature, it naturally extends its reach — fixing things it notices, adding
abstractions it considers useful, and improving adjacent code. This is the LLM equivalent of
"while I'm in here" refactoring.

The Orchestrator Step 4 dispatch instruction says to pass "the issue number, branch name, and
full plan," but it does not explicitly prohibit out-of-scope changes. Without a hard boundary,
the Coder treats the plan as a minimum, not a maximum.

This is the worst observed instance of scope creep in this project. Sixty files changed instead
of five means the PR diff is unverifiable, the review catches signal from the wrong changes, and
reverts introduce risk of undoing correct work.

This is a **recurring problem class**: coder-pattern-amnesia (issue #6), coder scope vs
implementation boundary (issue #8), ruff scope inflation (issues #5, #16, #21, #25, #90) — all
share the same root cause: no Coder rule explicitly prohibits unsolicited changes.

### Suggested Improvement

**Two coordinated changes required:**

**1. New Coder Rule 11** (`.github/agents/coder.agent.md`):

> **Implement only the files listed in the dispatch.** The plan's task checklist defines the
> complete authorised scope of this dispatch. Do NOT modify, create, or delete files outside that
> list — no incidental improvements, no refactors, no abstractions, no "while I'm in here"
> changes to adjacent code. If you notice bugs, improvements, or technical debt in code you read
> while working, record them in your handoff summary under "Out-of-scope observations" but do not
> act on them. Every unauthorised change inflates the diff, pollutes the review, and may require
> manual revert work.

**2. Orchestrator Step 4 dispatch wording** (`.github/agents/orchestrator-v3.agent.md`):

After "passing the issue number, branch name, and full plan", add:

> Include this scope constraint explicitly in the Coder dispatch prompt: "Only modify files in
> the task checklist. The plan defines the ceiling, not the floor. Do not touch files outside the
> listed scope."

### Action Taken

Applied: Added Rule 11 to `.github/agents/coder.agent.md` — "Implement only the files listed in the dispatch." Added explicit scope constraint blockquote to `.github/agents/orchestrator-v3.agent.md` Step 4 dispatch section.
