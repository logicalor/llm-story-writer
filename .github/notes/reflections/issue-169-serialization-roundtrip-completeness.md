---
date: "2026-04-25"
issue: 169
pr: 178
category: instruction
targets:
  - ".github/agents/_shared/review-checklist.md"
  - ".github/agents/coder.agent.md"
severity: minor
status: active
---

## Serialization round-trip completeness when adding a new registry key

### Finding

Issue #169 (PR #178) added `openai_async` as a valid key in `ModelConfig`. The original fix correctly updated the validation registry (`__post_init__`), but `to_string()` still hardcoded `"openai-compat"` for all providers and `from_string()` lacked the `openai-async://` → `openai_async` reverse mapping. Both bugs were caught by the review cycle (★★☆ majority — GPT and Gemini rated Warning/Critical; Claude rated Suggestion).

The existing Coder Rule 6 sub-bullet ("audit all enumeration registries") mentions "validation sets in domain code, factory dispatch functions, and README / documentation lists" but does not call out serialization round-trip methods specifically. `to_string()` is a forward serializer; `from_string()` is a reverse deserializer — both switch over the same registry. Without a complete round-trip, stored state cannot be reloaded.

### Observation

Three distinct failure surfaces exist when adding a new key to any config registry:

1. **Validation registry** — `__post_init__` or equivalent; rejects unknown keys at construction time.
2. **Forward serializer** — `to_string()`, `__str__`, `serialize()`: maps the key to its stored/wire representation.
3. **Reverse deserializer** — `from_string()`, `from_dict()`, `deserialize()`: maps the stored form back to the key.

Missing (1) fails fast at construction. Missing (2) silently writes the wrong stored value. Missing (3) silently fails to reload stored state. Missing (2) or (3) produces data corruption with no immediate error signal.

The Coder Rule 6 sub-bullet for "adding a new provider type" lists "factory dispatch functions" but not serialization methods explicitly. The review checklist has no item prompting reviewers to verify all three surfaces.

### Suggested Improvement

1. **Review checklist (Phase 2 General)** — add a checklist item prompting reviewers to verify all three serialization surfaces when a new key/variant is added to a config registry.

2. **Coder Rule 6** — extend the "adding a new provider type" sub-bullet to explicitly mention serialization methods as enumeration registries alongside the existing "factory dispatch functions" example.

### Action Taken

Applied:
- Added `Serialization round-trip completeness` item to Phase 2 General in `.github/agents/_shared/review-checklist.md`.
- Extended Coder Rule 6 "when adding a new provider type" sub-bullet in `.github/agents/coder.agent.md` to list serialization methods explicitly.
