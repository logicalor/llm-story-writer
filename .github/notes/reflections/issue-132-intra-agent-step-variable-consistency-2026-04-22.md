---
date: "2026-04-22"
issue: 132
pr: 136
category: instruction
targets:
  - ".github/agents/_shared/review-checklist.md"
severity: minor
status: archived
---

<!-- Archived. Full note in archive/issue-132-intra-agent-step-variable-consistency-2026-04-22.md -->
 not caught by existing review checklist

### Finding

During PR #136 (`feat/issue-132-critique-runner-arc-analysis`), `story-planner.md` Step 3
extracted `verdict_code` from the `run-arc-analysis` response (`data.verdict_code`), but
Step 4's return JSON schema emitted the field as `verdict`. The review found and fixed the
mismatch (the correct key, matching the tool's actual output schema, is `verdict_code`).

The existing Phase 2 "Tool call contracts" checklist item checks that parameter names in tool
invocations match the Zod schema (TS wrapper) and operation names match the Python CLI. However,
it does not check that a field stored in an earlier step (Step 3 `record: verdict_code`) is
used with the exact same name in a later step or in the final return JSON (Step 4 `"verdict": ...`).

### Observation

Multi-step agent workflows create an implicit "variable scope" — field names stored in one step
are references expected to hold in later steps and in the return JSON. A mismatch is a silent
schema error: the orchestrator reads `verdict_code` from the returned payload and receives
`undefined` or `null` without any tool-level validation error. The downstream step at the
orchestrator silently degrades.

The check is distinct from tool parameter contract verification: the mismatch is within the
agent file's own step prose, not between the agent and a tool schema file. The fix is to
add a dedicated intra-step cross-reference check to Phase 2's Agent Instructions section.

### Suggested Improvement

**`review-checklist.md`, Phase 2 Agent Instructions — add after the Tool call contracts item:**

> - [ ] **Intra-step variable cross-reference** — in multi-step agent workflows, verify that
>   every field name stored in an earlier step (e.g. `Store X as foo_bar`,
>   `record: foo_bar from data.foo_bar`) is used with the **exact same name** in all later
>   steps and in the final return JSON. A mismatch (`store as verdict_code`, `return as verdict`)
>   is a silent schema error: the orchestrator reads the correct key from the returned payload
>   and receives `null` with no tool-level error. Scan each multi-step workflow for stored
>   variable names by searching for `Record`, `Store`, `record:` prose, then verify every
>   reference to that name in later steps and the final JSON schema. (Source: issue #132,
>   PR #136 — `verdict_code` stored in Step 3, `verdict` erroneously returned in Step 4.)

### Action Taken

Applied: Added "Intra-step variable cross-reference" checklist item to `review-checklist.md`
Phase 2 Agent Instructions section, immediately after the Tool call contracts item.
