---
date: "2026-04-13"
issue: 7
pr: 34
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Positive signals: testing catches bug, security patterns followed, review catches consistency gap

### Finding

During issue #7 (Build savepoint-mgr Tool), three positive signals observed:

1. **Bug found by tests, not review.** A dict round-trip bug in `FilesystemSavepointRepository.load_savepoint()` was caught by the Test Writer's tests — the method returned body text "Data saved in YAML frontmatter above." instead of the frontmatter dict. The Synthesized Review did not flag this. This validates the test-first verification approach: tests probe runtime behaviour that static review misses.

2. **Security patterns followed.** The Coder used `execFileSync` with argument arrays (not `execSync` with string concatenation) and `is_relative_to()` for path validation. This confirms the Rule 9 addition from issue #3 reflection is established practice — second consecutive tool (after issue #8) to follow it correctly.

3. **Review catches consistency gap.** `cmd_clear` lacked a story existence check, unlike save/load/has/list. All three reviewers flagged it (U-W-03). The plan explicitly said to make clear idempotent, but `_make_repo()` would silently create directories — a side effect inconsistent with the other subcommands. This is the review system working as designed.

### Observation

No agent rule changes needed. The testing and review layers are functioning correctly and complementing each other — tests catch runtime bugs, reviews catch design consistency issues.

### Suggested Improvement

No changes. Recorded as positive signal for system health tracking.

### Action Taken

Recorded. No agent changes applied.
