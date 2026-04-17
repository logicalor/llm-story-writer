---
date: "2026-04-13"
issue: 8
pr: 33
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: major
status: archived
---

## Coder writes 20 tests that should be Test Writer's responsibility

### Finding

During issue #8 (Build story-state Tool), the Coder wrote 20 comprehensive verification tests in `tests/unit/test_story_state_tool.py`. This is the Test Writer's responsibility — the Orchestrator's Step 5 explicitly delegates test writing to the Test Writer agent.

The tests were well-written and comprehensive, but:
- One test (`test_write_missing_value`) had a missing assertion (caught by Synthesized Review)
- The Test Writer was bypassed entirely — it never had a chance to apply its own research workflow (checking gotchas, querying ChromaDB for patterns, etc.)

### Observation

The **Orchestrator** already has an explicit prohibition: "Never write or edit test files. Always delegate to the Test Writer." However, the **Coder agent** has no matching constraint. The Coder's rules enumerate what it should do (lint, type-check, sweep references, security patterns) but never say "don't write tests."

When a Coder sees an opportunity to write tests alongside implementation, there's no guardrail preventing it. This creates two problems:
1. The Test Writer's specialised research workflow is bypassed
2. Test quality may suffer (as shown by the missing assertion)

The Orchestrator's prohibition prevents the Orchestrator from writing tests — it doesn't prevent the Coder from spontaneously doing so during implementation.

### Suggested Improvement

Add a new rule to the Coder agent (`.github/agents/coder.agent.md`):

```markdown
10. **Do not write verification tests.** If you identify test scenarios during implementation, note them in your handoff summary for the Test Writer. The Orchestrator will dispatch the Test Writer separately. You may create minimal throwaway test scripts for debugging during implementation, but delete them before handoff (per Rule 7).
```

Note: issue #69 (testing-only dispatch) adds a carve-out — testing-only tasks where the entire deliverable is tests are appropriate for Coder dispatch. The rule should include: "unless explicitly dispatched for a testing-only task."

### Action Taken

Proposed for approval — this adds a new numbered rule to the Coder agent. Collated 2026-04-17, pending user approval.
