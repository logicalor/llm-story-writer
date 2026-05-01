---
date: "2026-05-02"
issue: 299
pr: 311
category: agent
targets:
  - ".github/notes/gotchas.md"
  - ".opencode/agents/test-writer.md"
  - ".github/agents-copilot/test-writer.agent.md"
severity: minor
---

## Advisory pipeline phases consume mock slots only when `side_effect` lists are in use

### Finding

`StoryMetadataAgent` runs as three separate advisory phases in `_continue_pipeline` (metadata-outline, metadata-chapter-1, metadata-final). Each instantiation makes 3 LLM calls to `provider.generate_text`. PR #311 correctly patched `StoryMetadataAgent` in `test_characters_phase_writes_sheets_to_disk`, `test_settings_phase_writes_sheets_to_disk`, and `test_characters_phase_skips_failed_sheet_generation` — the three tests that set `provider.generate_text = AsyncMock(side_effect=[...])` explicitly. Other orchestrator tests that use `provider = MagicMock()` were left unpatched and pass because the advisory `try/except Exception` blocks swallow the `TypeError` raised when an unawaitable `MagicMock` is awaited.

### Observation

This is a third scenario in the mock-slot-exhaustion family (gotchas #040 and #043), with a twist: the failure is **conditional on test provider configuration**. Tests using generic `MagicMock()` providers are immune because the advisory guard catches the TypeError. Tests using `AsyncMock(side_effect=[...])` must patch the agent class — the advisory guard swallows the call failure but the mock slot is still consumed, shifting all downstream indices. This conditional immunity makes the pattern harder to reason about than #040/#043, where the fix is always required.

The distinction needs to be documented so future Test Writers know:
- If `provider = MagicMock()` → no patch needed for advisory agents
- If `provider.generate_text = AsyncMock(side_effect=[...])` → must patch all advisory agent classes

### Suggested Improvement

1. Add gotcha #045 to `.github/notes/gotchas.md` documenting the advisory-phase variant of mock slot exhaustion — the conditional immunity based on provider type.
2. Add a companion guidance note to `.opencode/agents/test-writer.md` after the "Function-internal LLM call multiplier" block.
3. Add a companion guidance note to `.github/agents-copilot/test-writer.agent.md` after the "New pipeline phase breaks existing orchestrator tests" block.

### Action Taken

Applied:
- Added gotcha #045 (`gotcha-advisory-phase-mock-slot-conditional-immunity-045`) to `.github/notes/gotchas.md`.
- Added "Advisory pipeline phases and mock slot consumption" guidance block to `.opencode/agents/test-writer.md`.
- Added same guidance block to `.github/agents-copilot/test-writer.agent.md`.
