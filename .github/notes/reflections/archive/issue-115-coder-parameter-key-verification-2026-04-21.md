---
date: "2026-04-21"
issue: 115
pr: 116
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Rule 10 verification checklist omits parameter key name verification — `savepoint:` vs `step:` not caught

### Finding

During PR #116 (feat/issue-115-fix-audit-warnings), the Coder wrote `savepoint:` as the parameter key for savepoint-mgr when the correct key defined in the Zod schema is `step:`. Rule 10's verification checklist covers: (a) valid operation values, (b) Zod parameter types (`z.string()` vs `z.object()`), and (c) return value shape. It does not explicitly include verifying that **parameter key names** match the field names declared in the Zod schema. The Coder checked the conceptual payload structure but did not read the `z.object({ step: ... })` field name.

### Observation

This is a distinct failure mode from type verification (z.string vs z.object) and value-set verification (valid operation names). A parameter key mismatch — using `savepoint:` for a field declared as `step:` — will cause silent failure in Zod's `.optional()` fallback: the field passes schema validation (unknown keys are stripped), but the intended value is never received by the Python tool. Zod does not warn on unrecognised keys in `.passthrough()` or `.strip()` mode; the tool sees `undefined` and uses a default or fails at runtime with a misleading error.

The Rule 10 checklist item list (a)–(c) implicitly covers parameter verification, but the absence of an explicit "key name" item means the Coder may read just the type declaration without checking the declared field name. Adding an explicit item (d) removes ambiguity.

### Suggested Improvement

In `.github/agents/coder.agent.md`, Rule 10 verification sub-bullet, extend the list from three to four items:

Current:
> Verify: (a) valid operation values by reading the Python dispatch/enum; (b) Zod parameter types (`z.string()` vs `z.object()`) from the TS wrapper; (c) return value shape from Python `return` statements.

Add item (d):
> (d) parameter key names match the exact Zod field names declared in the TS wrapper (`z.object({ step: ... })` means the key is `step:`, not `savepoint:`) — mismatched keys pass Zod silently and produce misleading runtime failures.

### Action Taken

Applied: Added item (d) to the Rule 10 verification checklist — parameter key names must be read from the Zod field declarations in the TS wrapper, not inferred from prose.
