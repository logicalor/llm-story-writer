---
date: "2026-04-13"
issue: 6
pr: 35
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: major
status: archived
---

## Coder does not carry forward established patterns to new tool implementations

### Finding

During issue #6 (Build character-mgr Tool), the Coder did not apply atomic writes (`tempfile` + `os.replace`) on the first pass. This pattern was already established in `story_state.py` (issue #8) and explicitly caught/fixed in that review cycle. The Synthesized Review flagged it again (M-W-01, majority confidence), and it was applied retroactively.

This is the same class of problem as issue #3, where the Coder did not apply `execFileSync` with argument arrays or `is_relative_to()` path validation on the first tool — patterns that then had to be codified as Rule 9. The Coder now follows Rule 9 consistently (confirmed in issues #7 and #8), but only because it's an explicit numbered rule. Patterns that exist in prior implementations but aren't yet codified as rules get missed.

### Observation

The Coder's Rule 4 says "Consult `.github/notes/`" and the Conventions & Gotchas section says to "query the ChromaDB `conventions` collection." But:

1. The `conventions` collection doesn't exist yet (issue #7 reflection, still pending approval).
2. Even if it did, atomic writes aren't documented in any `.github/notes/` file.
3. There's no rule telling the Coder to review prior tool implementations for established patterns.

The root cause: codified rules (Rule 9) get followed. Ad-hoc patterns from prior implementations don't carry forward unless explicitly surfaced. The Coder doesn't proactively reference prior tools as implementation precedents.

Two-pronged fix needed:
1. **Short-term (this proposal):** Add a Coder rule requiring prior-tool review before implementing a new tool.
2. **Long-term:** Create the `conventions` collection with established patterns so the Coder's existing ChromaDB query workflow surfaces them automatically.

### Suggested Improvement

Add a new rule to the Coder agent (`.github/agents/coder.agent.md`), after Rule 9:

```markdown
10. **Before implementing a new tool**, review the most recent prior tool implementation in `src/tools/` for established patterns — atomic writes, error handling, validation, output format conventions. Apply the same patterns unless the task requirements differ. If you deviate from an established pattern, document why in your handoff summary.
```

This is complementary to the `conventions` collection proposal (issue #7 reflection). The rule provides an immediate mechanical check; the collection provides long-term semantic recall.

### Action Taken

Proposed for approval — this adds a new numbered rule to the Coder agent. Collated 2026-04-17, pending user approval.
