---
date: "2026-04-23"
issue: 150
pr: 151
category: agent
targets:
  - ".github/agents/documenter.agent.md"
severity: minor
status: archived
---

## Caching/resumability docs must qualify safety claims with invalidation rules

### Finding

GPT reviewer flagged that the wiki-extract documentation stated "retry is safe" without qualifying that safety depends on source inputs being unchanged. The fix added a note explaining when the cache file must be deleted to force a fresh extraction. The documentation safety claim was directionally true but under-specified.

### Observation

Any feature that caches, memoises, or otherwise short-circuits work based on prior state has an implicit input-stability contract. Docs that promise "safe to retry" without naming that contract mislead callers when inputs change mid-flight (edited source files, modified prompts, provider swaps). The pattern is generally applicable — not unique to wiki-extract.

A one-line addition to the Documenter's verification checklist covering "caching/resumability features" would close this across the project without inflating documenter scope.

### Suggested Improvement

Add a bullet to the Documenter's "Before writing or committing" verification block instructing that any retry-safety or resumability claim in user-facing docs must be accompanied by (a) the input-stability contract under which the claim holds and (b) the explicit recovery action (typically cache-file deletion) when that contract is violated.

### Action Taken

Applied minor addition to `.github/agents/documenter.agent.md` under "Write Documentation" verification bullets. Embedded to `reflections` collection.
