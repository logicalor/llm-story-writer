---
date: "2026-04-14"
issue: 13
pr: 49
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Stale prompt template count — sixth occurrence, compliance vs accuracy

### Finding

During issue #13 (Build critique-runner Tool), `docs/tools.md` had the wrong prompt template count again. This is the sixth occurrence across PRs #4, #5, #11, #12, #48, #49. The Synthesized Review caught it (U-W-01) and it was corrected to 117.

### Observation

This pattern has evolved across its six occurrences:

| PR | Issue | Nature | Rule 6 Status |
| -- | ----- | ------ | -------------- |
| #4 | #4 | Stale path, not count | Pre-Rule 6 |
| #5 | #5 | Stale path after relocation | Pre-Rule 6 expansion |
| #11 | #11 | Wrong count ("Four tools" → Five) | Rule 6 didn't cover counted sets |
| #12 | #12 | Wrong count (131 → 132) | Rule 6 covers it, not applied |
| #48 | #12 | Wrong count again | Rule 6 covers it, not applied |
| #49 | #13 | Wrong count again | Rule 6 covers it, Coder changed count to wrong number |

Key refinement from PR #49: the user reports the Coder "keeps changing the count to the wrong number." This is distinct from the Coder not running the count check at all. Previous reflections (issue #12 system health) assumed non-compliance — the Coder not running the grep. But if the Coder is actively updating the count and getting it wrong, the issue is **accuracy of the count method**, not **compliance with the rule**.

Possible causes:
- The Coder counts prompt files but uses the wrong glob pattern (e.g., missing subdirectories or counting non-prompt `.md` files)
- The Coder counts before adding new files rather than after
- The Coder miscounts due to context window limitations

No rule text change will fix a counting accuracy problem. The review system catches this reliably (6/6 occurrences caught). The cost is one review-fix cycle (~30 seconds per occurrence).

### Suggested Improvement

No rule text change. The rule is clear, the Coder is attempting compliance, and the review system catches failures reliably. This is an acceptable cost given the review backstop. If a future pattern emerges where the Coder consistently uses a wrong counting method, a specific counting procedure could be added — but that level of prescription is premature.

### Action Taken

No action needed — observation recorded. Pattern tracked for future monitoring.
