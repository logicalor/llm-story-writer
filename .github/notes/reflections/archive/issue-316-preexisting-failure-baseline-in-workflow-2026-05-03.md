---
date: "2026-05-03"
issue: 316
pr: 328
category: instruction
targets:
  - ".github/agents/_shared/local-workflow.md"
severity: major
status: archived
---

## Pre-existing failure baseline step missing from local-workflow.md

### Finding

During PR #328 (issue #316), 16 pre-existing test failures were confirmed before making any changes by running `git stash && pytest ... && git stash pop`. The deferred.md entry (from issue #162) documents this technique, but `local-workflow.md` — the shared workflow reference included in every agent that makes commits — contains no mention of it.

Agents reading only `local-workflow.md` (the normal case during implementation) have no guidance to establish a pre-existing failure baseline before writing their first commit.

### Observation

The technique is widely known within the project (documented in deferred.md and ChromaDB), but it lives in a "deferred ideas" file rather than an actionable workflow instruction. Without it in `local-workflow.md`, each agent must independently discover the pattern or rediscover the confusion that arises when test failures appear and it's unclear whether they are new or pre-existing.

Proactively baselining before the first commit:
- Eliminates ambiguity about which failures were introduced by the PR
- Prevents unnecessary investigation of pre-existing failures
- Saves time during PR review (reviewers don't need to re-verify baseline status)

### Suggested Improvement

Add a "Pre-existing failure baseline" subsection to `local-workflow.md` under the verification / local-first workflow section. Proposed content:

```markdown
## ⛔ PRE-EXISTING FAILURE BASELINE — MANDATORY BEFORE FIRST COMMIT

Before making any code changes on a feature branch, establish a failure baseline:

```bash
git stash && pytest tests/ -v 2>&1 | tail -20 && git stash pop
```

If the branch has no stashed changes yet, run `pytest tests/ -v` directly.

**Record the number of failures observed.** Any failures that reproduce on the stashed state are
pre-existing and must NOT be attributed to this PR. If the failure count after implementation
exceeds the baseline, investigate immediately — those are regressions introduced by this PR.

**Why this matters:** Pre-existing failures create noise in PR reviews. Establishing a baseline
before the first commit prevents confusion and saves review cycles.
```

### Action Taken

Proposed for approval — structural addition to a shared workflow instruction file used by all agents.
Archived during issue #317 collation (2026-05-03). Major proposal remains pending approval.
