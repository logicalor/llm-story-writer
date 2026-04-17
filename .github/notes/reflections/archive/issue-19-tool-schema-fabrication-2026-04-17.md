---
date: "2026-04-15"
issue: 19
pr: 63
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: major
status: archived
---

## Coder fabricates tool parameter names instead of verifying against actual schema

### Finding

During issue #19 (Build Scene Writer Subagent), the Coder wrote the `.opencode/agents/chapter-writer.md` agent definition referencing tools with invented parameter names. The `wiki-snapshot` tool was referenced with 5 incorrect parameter names (`story_name`, `chapter_number`, `scene_number`, `setting`, `tokenBudget`) and 2 missing parameters. The Synthesized Review caught this as S-W-01 — the parameter names in the agent definition did not match the actual `.opencode/tools/wiki-snapshot.ts` schema.

### Observation

This is a **new class** of Coder defect, distinct from prior patterns:

- **Issue #3/6 — pattern amnesia:** Coder fails to apply established patterns from prior implementations. Fixed by Rule 9 and proposed Rule 10.
- **Issue #10 — semantic correctness:** Coder writes syntactically valid but functionally broken code (wiring bugs). Pending semantic verification rule.
- **Issue #19 — schema fabrication:** Coder invents reference data instead of consulting the source of truth.

The root cause is that writing agent definitions is a **documentation-adjacent** task — the Coder treats parameter names as prose to be drafted rather than facts to be looked up. The Coder has no rule requiring verification of external schema references when writing agent or skill files.

This is particularly impactful because agent definitions are consumed by other agents at runtime. Incorrect parameter names cause tool invocation failures that surface later, far from the original authoring context — making them expensive to debug.

The existing Rule 6 (text sweep after changes) doesn't cover this because no prior text is being replaced — the parameters are freshly authored. The issue is **fabrication**, not **staleness**.

### Suggested Improvement

Add a new rule to the Coder agent (`.github/agents/coder.agent.md`), after the existing rules:

```markdown
10. **When writing agent definitions or skill files that reference tools**, verify all tool parameter names, types, and descriptions against the actual tool schema files (`.opencode/tools/*.ts` for TypeScript wrappers, `src/tools/*.py` for Python scripts). Never invent parameter names from memory — always read the schema file. For tool tables in agent definitions, verify every tool mentioned in the workflow prose appears in the table with correct parameter documentation. **For structured parameters** (JSON payloads, config objects, batch formats), verify the internal format and field names against the receiving tool's source code — the TypeScript wrapper only validates the outer parameter; the inner structure is defined by the Python implementation.
```

Note: this rule was expanded in issue #22 to cover structured payload formats. Both should be applied together as a single combined rule.

### Action Taken

Proposed for approval — adds a new numbered rule to the Coder agent. See also issue-22-payload-format-fabrication for the expanded rule text. Collated 2026-04-17, pending user approval.
