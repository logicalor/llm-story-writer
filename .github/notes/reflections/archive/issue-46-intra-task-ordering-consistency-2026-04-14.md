---
date: "2026-04-14"
issue: 46
pr: 47
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Coder applies operation ordering inconsistently between similar functions in the same tool

### Finding

During issue #46 (outline-generator improvements from PR #45 review), the Coder added savepoint resumability to two operations in `src/tools/outline_generator.py`. In `cmd_expand_chapter()`, the savepoint existence check was correctly placed before `_load_prompt()` — so if a savepoint already existed, the function would return early without incurring a prompt template load. In `cmd_generate_outline()`, the savepoint check was placed *after* `_load_prompt()`, inside the try/except block — meaning a prompt template failure would bypass the savepoint check entirely, and a valid savepoint would still trigger a redundant prompt load.

The Synthesized Review caught this unanimously (Warning severity), and the Coder fixed it in one dispatch by moving the savepoint check before `_load_prompt()` in `cmd_generate_outline()`.

### Observation

This is an **intra-task** variant of the cross-task pattern amnesia documented in issue #6. Prior pattern amnesia observations involved the Coder failing to carry patterns between different tool implementations (issue #3: security patterns, issue #6: atomic writes). This instance is different — the Coder implemented the same pattern (savepoint resumability) in two functions *within the same file, in the same dispatch*, and got the ordering right in one but wrong in the other.

Critically, the pending proposals from prior reflections would not have prevented this:

- **Proposed Rule 10 (prior-tool review):** Addresses cross-tool pattern carry-forward — would not trigger for consistency within a single tool.
- **Existing Rule 9 (security validation):** Covers subprocess/path/input validation patterns, not operation ordering.

The proposed **semantic verification rule** from issue #10 (data-flow tracing before handoff) *would* catch this — if the Coder traces each operation's flow and compares similar operations for consistency, the ordering discrepancy becomes visible. This observation strengthens the case for that proposal and suggests it should explicitly mention intra-tool consistency: when multiple operations share a common pattern (e.g., savepoint resumability, state validation, prompt loading), verify the pattern implementation is consistent across all operations.

### Suggested Improvement

When the issue #10 semantic verification rule is approved and applied to the Coder agent, add explicit guidance about intra-tool consistency. Suggested wording for the rule (extending the proposed text):

> ...Pay special attention to operations that accept user input — confirm the input reaches the LLM prompt or processing logic. **For tools with multiple operations sharing a common pattern (savepoint checks, input validation, prompt loading), verify the pattern is applied consistently across all operations — check ordering, error handling, and early-return conditions.**

No standalone rule change is needed. This observation refines the existing pending proposal from issue #10.

### Action Taken

No immediate action needed — observation recorded to refine the pending semantic verification rule proposal (issue #10, `issue-10-semantic-correctness-gap.md`). Cross-reference added to that note.
