---
date: "2026-04-24"
issue: 159
pr: 168
category: instruction
targets:
  - ".github/agents/_shared/review-checklist.md"
severity: minor
status: archived
---

## Behavioral parity gap when implementing sibling provider

### Finding

`OpenAIAsyncProvider` was implemented as a direct async counterpart to `OpenAICompatibleProvider`, sharing the same `ModelProvider` interface. However, the async implementation omitted the `temperature=0` override that the sync provider applies when `format_type == "json"`. The sync provider sets `temperature=0` before falling back to `0.7` for other requests (verified at line 468 of `openai_compatible_provider.py`); the async provider instead allowed `options.setdefault("temperature", 0.7)` to apply unconditionally, including for JSON-mode generation.

The practical impact: callers that rely on deterministic JSON responses from `generate_json` or `generate_text(format_type="json")` will see higher temperature variance when routed through the async provider, increasing the likelihood of schema-drifting or malformed generations. Only one of three reviewers (GPT, via S-I-02) caught this.

### Observation

The review checklist has no prompt specifically targeting behavioral parity when a new implementation mirrors a sibling. Phase 2 General covers convention adherence, duplication, and API signature changes — but not the scenario where a new class inherits a known interface alongside an existing concrete implementation, where divergence from the sibling's behavior is not a convention violation or a duplication opportunity, but a correctness gap.

This class of issue is likely to recur as the Python-native migration progresses — each new provider added alongside an existing one is a behavioral parity check candidate.

### Suggested Improvement

Add a bullet to Phase 2 General in the review checklist prompting reviewers to check behavioral parity when the PR introduces a new class that mirrors a sibling.

### Action Taken

Applied: added "Behavioral parity in sibling implementations" checklist item to Phase 2 (General) in `.github/agents/_shared/review-checklist.md`.
