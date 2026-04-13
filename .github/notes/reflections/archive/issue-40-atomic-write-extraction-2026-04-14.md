---
date: "2026-04-14"
issue: 40
pr: 43
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Shared utility extraction validates pattern carry-forward improvement proposals

### Finding

During issue #40 (Extract atomic write to shared module), the duplicated `_atomic_write()` function was extracted from `character_manager.py` and `setting_manager.py` into `src/tools/_io.py`. Synthesized Review found zero critical issues — one warning about consolidating duplicated tests into `tests/unit/test_io.py` (tracked as follow-up).

### Observation

This is the resolution of the atomic write saga spanning issues #8 → #6 → #11 → #39 → #40:

1. **#8** — atomic write pattern established in `story_state.py`
2. **#6** — Coder copy-pasted it to `character_manager.py` instead of extracting (pattern amnesia)
3. **#11** — copy-pasted again to `setting_manager.py` (carry-forward worked, but via duplication)
4. **#39** — same `os.unlink` bug in both copies proved duplication is a defect multiplier
5. **#40** — extracted to shared `_io.py`, eliminating the duplication

The extraction reinforces three pending proposals:
- **Coder Rule 10 (prior-tool review, issue #6)** — reviewing prior tools would have caught the duplication opportunity earlier
- **Conventions collection (issue #7)** — "use shared utilities over copy-paste" should be a codified pattern
- **Coder Rule 11 (no test writing, issue #8)** — the duplicated tests mirror the duplicated implementation; Test Writer would have centralised them

No agent changes needed from this issue specifically — this is a positive signal that the existing review system correctly identified the extraction opportunity.

### Suggested Improvement

No direct agent/skill/instruction changes. The existing pending proposals (issues #6, #7, #8) cover the systemic improvements. The test consolidation follow-up is a coding task, not an agent system change.

### Action Taken

No action needed — positive signal recorded. Reinforces pending major proposals. Archived 2026-04-14.
