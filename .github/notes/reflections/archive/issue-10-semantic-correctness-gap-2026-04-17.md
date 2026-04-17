---
date: "2026-04-14"
issue: 10
pr: 45
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: major
status: archived
---

## Coder implements syntactically correct but semantically broken operations

### Finding

During issue #10 (Build outline-generator Tool), the `cmd_refine()` operation accepted a `--feedback` parameter but silently ignored it — the feedback was never passed to the LLM conversation. This was caught by the Synthesized Review as U-C-01 (Critical), with all three models flagging it. The operation was syntactically valid (no lint errors, no type errors, correct argument parsing) but semantically non-functional — it appeared to accept user feedback for outline refinement but discarded it.

### Observation

This is a new class of Coder defect, distinct from prior findings:

- **Issue #3** — missing security patterns (subprocess injection, path traversal). Fixed by codifying Rule 9.
- **Issue #6** — missing established patterns (atomic writes). Will be addressed by proposed Rule 10.
- **Issue #10** — correct patterns applied, but an operation's core purpose was not fulfilled.

The Coder follows codified patterns reliably (security, atomic writes, error handling, output format). However, it does not appear to mentally trace the data flow of each operation to verify that inputs actually reach their intended destination. In `cmd_refine()`, the `--feedback` argument was parsed, the LLM was called, but the feedback string was never included in the conversation messages sent to the LLM. This is a "wiring bug" — all components exist but are not connected.

This cannot be fixed by adding more pattern rules. Pattern rules enforce structural conventions (how to write files safely, how to call subprocesses, how to validate paths). Semantic correctness — "does this operation actually do what it claims?" — requires the Coder to trace the full data flow from input to output for each operation.

### Suggested Improvement

Add a new rule to the Coder agent (`.github/agents/coder.agent.md`), focused on semantic verification:

```markdown
N. **Before handing off a multi-operation tool**, trace the data flow of each operation: verify that every accepted parameter is actually used in the operation's logic, and that the operation's output reflects its documented purpose. Pay special attention to operations that accept user input (e.g., feedback, queries, modifications) — confirm the input reaches the LLM prompt or processing logic, not just the argument parser.
```

This is complementary to existing rules: Rule 9 ensures secure patterns, proposed Rule 10 ensures established patterns carry forward, and this new rule ensures semantic correctness of the implemented logic.

### Supporting Evidence

- **Issue #46 (PR #47):** Coder applied savepoint-before-prompt ordering correctly in `cmd_expand_chapter()` but incorrectly in `cmd_generate_outline()` — same file, same dispatch. Intra-task variant of pattern inconsistency that data-flow tracing would catch. See `issue-46-intra-task-ordering-consistency.md`. Suggests the proposed rule should explicitly mention intra-tool consistency between similar operations.

### Action Taken

Proposed for approval — this adds a new numbered rule to the Coder agent addressing a class of defect not covered by pattern-matching rules. Collated 2026-04-17, pending user approval.
