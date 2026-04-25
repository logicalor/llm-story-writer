---
date: "2026-04-25"
issue: 169
pr: 178
category: instruction
targets:
  - ".github/agents/_shared/review-checklist.md"
severity: minor
status: archived
---

## Stale feature-doc code examples — registry-key additions not covered by existing rule

### Finding

`docs/features/openai-async-provider.md` contained code examples using `openai_compatible` as the provider key where `openai_async` was correct. Claude flagged this as a singular Warning (S-02); the finding was valid. The review was triggered because a reviewer read the feature doc during Phase 7 documentation review, not because any checklist item prompted it.

The existing **Code example drift** checklist item (Phase 7) reads:

> "if this PR changes the semantics of an API method, removes a method, or makes a field immutable, grep docs … for code examples that use the old pattern"

This condition is triggered by **changing or removing** something. Adding a new registry key is distinct — no existing key was changed or removed; the feature doc simply used the wrong key for the new provider, because the doc was written before the correct key name was finalised or was never updated after renaming.

### Observation

"Code example drift" has three triggers in the current checklist: API semantic change, method removal, field immutability change. A fourth is missing: **registry key addition**. When a new valid key is added (provider, model role, enum value), existing feature docs may demonstrate the key space with an example that either:
- Lists only the old key(s), omitting the new one, or
- Uses an outdated name for the new key (e.g. `openai_compatible` instead of `openai_async`).

Both cases produce misleading documentation that is not caught by "did we remove something?" logic. The feature doc remains internally consistent but is wrong relative to the new registry state.

### Suggested Improvement

Extend the **Code example drift** checklist item in Phase 7 to add a registry-key-addition trigger:

> "Also when adding a new config registry value (provider key, model role, valid enum value), grep `docs/features/` and `docs/` for code or YAML blocks that reference the same key namespace — an existing example may omit the new key or use an earlier working name. (Source: issue #169, PR #178 — `docs/features/openai-async-provider.md` used `openai_compatible` key in examples after `openai_async` was the correct key for the new provider.)"

### Action Taken

Applied: extended the `Code example drift` item in Phase 7 of `.github/agents/_shared/review-checklist.md` with the registry-key-addition trigger clause.
