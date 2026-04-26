---
date: "2026-04-26"
issue: 185
pr: 198
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Regex fixes must be validated against the real production file, not only synthetic unit test inputs

### Finding

During PR #198, finding M-W-02 required two Coder dispatches to fix correctly. The first dispatch implemented a window-based negation-aware regex fix that passed the isolated unit test. The Test Writer's verification pass discovered the fix still failed when the negated phrase appeared in the actual production file (a prompt template) because the window size calculation was off for the real file's surrounding context. A second Coder dispatch corrected the window calculation.

### Observation

The root cause is that the unit test used a minimal synthetic input — a short string containing just the phrase under test — while the real prompt file has longer context blocks with different surrounding structure. A window-based regex that works for a 5-word test string may be too narrow for a 200-word real-file neighbourhood. The failure was invisible until the Test Writer ran against the actual file.

This pattern will recur whenever a regex or text parser is fixed using synthetic test strings without verifying against the real data it processes at runtime. The cost is an unnecessary second Coder dispatch and test cycle.

### Suggested Improvement

**`coder.agent.md`** — add a sub-bullet under Rule 2 (or as a standalone inline note after Rule 2) stating:

   - **When fixing a regex or text parsing pattern** — after making the fix, run a quick manual check against the actual production file the pattern targets (e.g., `python -c "import re; print(re.search(PATTERN, open('path/to/real_file').read()))"` or a targeted `grep`). Synthetic unit test strings are typically much shorter and less varied than real file content; a window calculation, lookahead, or anchor that passes a 10-token test may fail on a 500-token real-file neighbourhood. This manual check takes seconds and prevents a second Coder dispatch. (Source: issue #185, PR #198 — window-based negation regex passed synthetic unit test; failed on real prompt file due to narrow window; required second iteration.)

### Action Taken

Applied: added "When fixing a regex or text parsing pattern" sub-bullet to `coder.agent.md` Rule 2.
