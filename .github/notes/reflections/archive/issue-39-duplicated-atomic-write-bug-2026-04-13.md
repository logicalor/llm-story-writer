---
date: "2026-04-13"
issue: 39
pr: 41
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Duplicated _atomic_write() causes same bug in two files

### Finding

During issue #39 (Guard unlink in atomic write), the same `os.unlink(tmp)` bug existed in both `character_manager.py` and `setting_manager.py` because `_atomic_write()` was copy-pasted between them. The fix (`try/except OSError: pass`) had to be applied identically in both files.

### Observation

This is a direct consequence of pattern carry-forward via copy-paste rather than shared utility extraction. The Coder correctly applied atomic writes in both tools (validating issue #11's positive signal), but the duplication meant a single bug manifested in two places. Follow-up issue #42 already tracks extracting `_atomic_write()` into a shared utility.

Positive signals:
- Process worked correctly: bug found, fixed in both locations, two tests added, 86 tests pass, unanimous review
- Follow-up issue created proactively for root cause (duplication)
- Reinforces the pending Rule 10 proposal (issue #6) — shared patterns should eventually be extracted, not just reviewed

No agent system changes needed. The existing proposals (issue #6 Rule 10, issue #7 conventions collection) would help prevent this class of duplication from growing.

### Suggested Improvement

No new improvement — existing proposals from issues #6 and #7 address the root cause.

### Action Taken

Recorded as validation note. No agent changes applied. Archived immediately.
