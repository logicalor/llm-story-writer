---
date: "2026-04-18"
issue: 107
pr: 108
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Config docs lose rebuild guidance when setup scripts are deleted

### Finding

During PR #108, removing `setup_rag.sh` (a setup/bootstrap script) left `config.md` with
insufficient rebuild guidance — the documentation had relied on the removed script for its
"how to rebuild" instructions. The gap was caught by review; the Orchestrator fixed it directly
rather than creating a follow-up issue.

### Observation

Coder Rule 6's stale-docs sub-bullets address the problem of *stale references* — places where
a removed package or script name still appears in documentation. They correctly catch sentences
like "Run `setup_rag.sh` to initialise the index."

This case is distinct: after the stale reference is removed, the documentation may no longer
describe *any* path to rebuild the functionality. The reference wasn't just wrong — it was the
only instruction. Removing it creates a *coverage gap* rather than a stale-text problem.

The distinction matters: grep sweeps for the removed script name will find and clear stale
references, but won't reveal that the cleared section now provides no guidance at all. A coverage
gap requires a read-and-assess step, not a search-and-replace step.

The pattern will recur on any project with setup/migration scripts: `setup_*.sh`,
`init_*.sh`, `migrate_*.py`, `bootstrap.sh`, etc. are common documentation anchors for
infrastructure rebuild workflows.

### Suggested Improvement

Add a sub-bullet to Coder Rule 7 in `.github/agents/coder.agent.md`:

> When deleting a runnable setup or migration script (`setup_*.sh`, `init_*.py`,
> `migrate_*.py`, `bootstrap.sh`, etc.) — verify that any configuration or setup documentation
> referencing that script still provides standalone sufficient rebuild guidance after the
> reference is removed. Removing the script creates a potential _coverage gap_, not just a stale
> reference: the documentation may no longer describe any rebuild path at all.

### Action Taken

Applied: added Rule 7 sub-bullet about config documentation coverage gaps after setup script
deletion to `.github/agents/coder.agent.md`. Embedded this reflection into the `reflections`
ChromaDB collection.
