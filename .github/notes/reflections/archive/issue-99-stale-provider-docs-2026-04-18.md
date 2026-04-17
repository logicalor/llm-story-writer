---
date: "2026-04-18"
issue: 99
pr: 101
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
archived_at: "archive/issue-99-stale-provider-docs-2026-04-18.md"
---

## Stale provider configuration docs after enum-variant removal

### Finding

During issue #99 (PR #101, remove unsupported cloud providers), the implementation correctly
removed four provider values from `ModelConfig.valid_providers` and cleaned up the associated
dead code. However, two troubleshooting entries in `config.md` that described configuration
examples for the removed providers were not updated. These were caught by the synthesized review
and fixed as part of the review cycle.

### Observation

Coder Rule 6 already requires grepping for stale references after text sweeps, and a sub-bullet
added in issue #26 covers the case of removing a package or library. However, removing an enum
variant or configuration option value is a distinct case — no files are deleted, no
`requirements.txt` changes occur — so the Coder's decision tree does not naturally reach the
Rule 6 grep discipline.

The stale documentation left by provider removal differs from library-removal stale docs:
the provider *name* (e.g., `"openai"`, `"openrouter"`) appears as a prose value in `.md`
configuration examples and troubleshooting sections, not as an import or package reference. These
entries survive import sweeps entirely — they only surface via a deliberate grep for the removed
name in documentation files.

This is the second form of this pattern: issue #26 added the package-removal sub-bullet; this
extends it to cover removing a named variant from a configuration enum or allowed-values list.

### Suggested Improvement

Add a new sub-bullet to Coder Rule 6 (after the existing package/library sub-bullet) covering
the case of removing a provider type, configuration option, or enum variant:

> **When removing a provider type, configuration option, or enum variant** (deleting an entry
> from a `valid_providers` list, removing a subcommand, removing a feature flag value) — grep the
> workspace for the removed name/value in documentation files (`.md`) to find stale
> troubleshooting steps, configuration examples, and capability descriptions. These differ from
> package-removal stale docs: the variant name/value appears only in prose, not in import or
> dependency sweeps.

### Action Taken

Applied: added sub-bullet to Coder Rule 6 for enum variant/configuration option removal.
