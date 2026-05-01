---
date: "2026-05-02"
issue: 298
pr: 310
category: agent
targets:
  - ".opencode/agents/test-writer.md"
  - ".github/notes/gotchas.md"
severity: minor
---

## Function-internal LLM call expansion breaks orchestrator test mock slots

### Finding

During issue #298 (PR #310), `_generate_character_sheets` and `_generate_setting_sheets` were extended to call the LLM multiple times per entity — full sheet, 7 chunk prompts, abridged, and summary — totalling 10 LLM calls per entity instead of 1. Two orchestrator tests (`test_characters_phase_writes_sheets_to_disk`, `test_settings_phase_writes_sheets_to_disk`) had `side_effect` lists sized for the old single-call behaviour. Both tests failed immediately after implementation because the mock was exhausted before the downstream assertions ran. The Test Writer required a second dispatch to fix the mock lists.

This is a variant of gotcha #040 ("new pipeline phase consumes mock slots") but with a distinct trigger: not adding a new agent/phase, but expanding the internal LLM call count of an existing function.

### Observation

Gotcha #040 documents the "new pipeline phase" scenario and prescribes patching agent classes to prevent slot consumption. That guidance is sound but does not cover the "same function, more internal calls" scenario. When a function like `_generate_character_sheets` changes from 1 to N internal LLM calls, every test that exercises a code path running through that function inherits a silent contract change in its `side_effect` list.

The pattern recurs whenever implementation depth is increased on an existing function. Without explicit guidance, Test Writers will size `side_effect` lists based on the old call count, producing stale mocks that only fail at runtime.

### Suggested Improvement

1. **Extend `gotchas.md`** — add gotcha #043 covering "function-internal LLM call expansion" as a companion to #040. Distinguish trigger (refactoring existing function vs inserting new phase) and prescribe the same fix: patch agent class to bypass internal call count, or document explicit per-entity call multiplier in the test.

2. **Add guidance block to `.opencode/agents/test-writer.md`** — after the "LLM-response parse-error paths" block, add a named block: **`Function-internal LLM call multiplier`** advising Test Writers to grep the implementation for `generate_text` call sites within the target function before sizing a `side_effect` list, and to document the expected call count as a comment in the test.

### Action Taken

Applied: Added gotcha #043 to `.github/notes/gotchas.md`. Added `Function-internal LLM call multiplier` guidance block to `.opencode/agents/test-writer.md`.
