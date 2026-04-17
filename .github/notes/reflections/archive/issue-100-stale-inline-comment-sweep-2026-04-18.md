---
date: "2026-04-18"
issue: 100
pr: 102
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Stale inline comment survived feature-removal pass (Rule 7 gap)

### Finding

During issue #100 (PR #102), an inline comment that originally described the purpose of the
`rag_service` parameter survived the implementation pass. The comment described RAG context
injection semantics that no longer applied after the parameter was removed. It was caught by
the GPT reviewer but not by the Coder's self-verification.

### Observation

Coder Rule 7 prescribes a dead-code sweep on newly created or heavily modified files —
targeting unused functions, unreachable branches, and abandoned helpers. It does not explicitly
cover inline comments that describe removed features or parameters. Such comments are not dead
code in the linter sense; they are stale prose that slips through both static analysis and
grep-based sweeps because the *comment text* does not match the removed parameter name.

The pattern: a comment says "passes rag_service for RAG-augmented context injection"; the
parameter is removed; the comment remains; the code now runs differently from what the comment
describes. This is a documentation-correctness issue that lives in source files, not docs.

### Suggested Improvement

Add a sub-bullet to Coder Rule 7:

> - After removing a parameter, service, or feature — scan inline comments in modified files
>   for prose that describes the removed element. Comments describing the purpose of a removed
>   parameter or the integration of a removed service become stale prose the moment the element
>   is removed; they are not caught by linters or by grep sweeps targeting the removed name.

### Action Taken

Applied: added inline comment sweep sub-bullet to Coder Rule 7 in
`.github/agents/coder.agent.md`.
