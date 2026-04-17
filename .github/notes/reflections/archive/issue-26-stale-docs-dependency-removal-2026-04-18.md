---
date: "2026-04-18"
issue: 26
pr: 98
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
archived_at: "archive/issue-26-stale-docs-dependency-removal-2026-04-18.md"
---

## Stale docs after dependency removal — Rule 6 coverage gap

### Finding

During issue #26 (PR #98, Clean Up Legacy Dependencies), the Coder removed 15 unused packages
from requirements.txt and deleted 3 dead code files (container.py, langchain_provider.py,
rag_service.py). The review found that several documentation files still referenced the removed
dependencies and the architecture they implied:

- LANGCHAIN_PROVIDER_README.md — described langchain integration as if it were still present
- PROVIDERS_README.md — referenced provider classes that no longer exist
- config.md — described configuration patterns incompatible with the new OpenCode-first
  architecture

These were caught by the review and fixed, but were not caught during implementation. Two
follow-up issues (#99, #100) were also correctly created from review findings (valid_providers
cleanup, dead rag_service params) — the review-to-issue pipeline functioned correctly.

### Observation

Coder Rule 6 prescribes a workspace-wide grep after text sweeps, relocations, renames, and
count changes. Its framing is around **file relocation and rename** tasks. When removing a
dependency (e.g., deleting `langchain*` from requirements.txt and deleting the implementation
files), the Coder's model for Rule 6 is "I didn't rename anything, so no grep needed."

Dependency removal is a distinct action that leaves stale documentation in a different way from
relocation: docs that describe the *capabilities or configuration of the removed library* remain
correct in isolation but wrong in context. A grep for the package name (e.g., `langchain`,
`dependency-injector`) across all `.md` files would surface these.

The stale-docs pattern has now occurred in multiple forms: relocation (#4, #5, #30, #12), count
changes (#11, #12, #13), and now dependency removal (#26). The unifying fix across all forms is
the same grep-after-change discipline — the rule needs an explicit branch for dependency removal.

### Suggested Improvement

Add a sub-bullet to Coder Rule 6 explicitly covering dependency removal:

> **When removing a package, library, or service** (deleting from requirements.txt, deleting
> an implementation module, removing an integration) — grep the entire workspace (including .md
> files) for each removed package or service name to find stale documentation references.

This is an additive clarification, not a structural change to Rule 6.

### Action Taken

Applied: added sub-bullet to Coder Rule 6 for dependency removal grep discipline.
