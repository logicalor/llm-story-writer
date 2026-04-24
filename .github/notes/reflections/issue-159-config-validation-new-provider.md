---
date: "2026-04-24"
issue: 159
pr: 168
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## New provider key not added to ModelConfig validation registry

### Finding

`OpenAIAsyncProvider.get_supported_providers()` returns `["openai_async"]`, but `ModelConfig.__post_init__` only accepts `"openai_compatible"` as a valid provider key. The provider was implemented and the `get_supported_providers()` contract was fulfilled, but the corresponding validation registry was not updated in the same PR. Any `ModelConfig(provider="openai_async", ...)` call raises a `ValidationError` at runtime. A follow-up issue (#169) was required to track the fix.

The Coder's Rule 6 already has a sub-bullet for **removing** an enum variant or provider key (issue #99, PR #101): grep docs for stale references. There is no parallel sub-bullet for **adding** a new variant — specifically, checking whether annotation registries and validation sets must be updated to accept the new value in the same PR.

### Observation

The pattern is the mirror image of the removal case: when removing a variant, the risk is stale documentation; when adding a variant, the risk is silent rejection by validation guards that were not updated together with the implementation. In this project, `ModelConfig.__post_init__`, the README provider key list, and `get_supported_providers()` are co-dependent surfaces that must stay in sync. Updating one without the others creates an internal contract mismatch.

The fix was deferred to issue #169, which is acceptable — but the deferral reveals that the Coder had no rule prompting an audit of the validation registry when adding a new provider key.

### Suggested Improvement

Add a sub-bullet to Coder Rule 6 for adding a new provider type, enum variant, or configuration option: audit all enumeration registries (validation sets, README lists, factory dispatch) and update them in the same PR, or explicitly create a follow-up issue for any registry that cannot be updated in scope.

### Action Taken

Applied: added sub-bullet to Rule 6 in `.github/agents/coder.agent.md` after the existing "When removing a provider type, configuration option, or enum variant" sub-bullet.
