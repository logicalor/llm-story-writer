---
date: "2026-04-18"
issue: 99
pr: 101
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
archived_at: "archive/issue-99-provider-branch-dead-code-2026-04-18.md"
---

## Dead code in from_string()-style dispatch after provider removal

### Finding

During issue #99 (PR #101, remove unsupported cloud providers), the `ModelConfig.from_string()`
method contained a conditional branch that handled the `/`-in-model-name format specific to
`openrouter` URIs. After removing the `openrouter` provider from `valid_providers`, this
branch became unconditionally dead — it could never be reached, yet was not removed during
the initial implementation. The synthesized review identified it and it was removed in the
review-fix cycle.

### Observation

Coder Rule 7 prescribes a dead code sweep before handoff, targeting "unused functions,
unreachable branches, abandoned helpers." The existing framing focuses on iterative development
artifacts (helpers written and abandoned mid-task). It does not explicitly address the case where
dead code is *created by removal* — i.e., branches in a factory or dispatch function that were
valid before the task began but become unreachable the moment a variant is deleted.

`from_string()`-style factory methods are the canonical site where this occurs. Each branch
handles a specific string prefix, scheme, or provider name. When a provider is removed, the
branch for its specific format (slash-in-model-name, custom URL suffix, etc.) survives silently
unless the Coder explicitly checks the factory function for orphaned branches.

The general principle applies beyond providers: any `match`/`if-elif` dispatch on a variant
set should be reviewed when a variant is removed.

### Suggested Improvement

Add a targeted clause to Coder Rule 7 covering variant-removal dead code:

> When *removing* a feature variant (provider, subcommand, option, enum case), also review
> `from_string()`-style factory and dispatch functions for conditional branches that handled
> only the removed variant — these become dead code immediately on variant removal and are
> not detected by linters.

### Action Taken

Applied: added clause to Coder Rule 7 for variant-removal dead code in dispatch functions.
