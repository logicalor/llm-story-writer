<!-- Archived — see archive/issue-113-ts-param-type-documentation-2026-04-21.md -->

## TypeScript `data` parameter type (z.string vs z.object) must be verified before documenting call syntax

### Finding

During PR #114, the Synthesized Review raised a type mismatch: the Coder corrected `character-mgr` and `setting-mgr` agent docs to show `data: {} (empty object)` — but the TypeScript wrapper declares `data: z.string().optional()` with description "JSON string input". Passing an object literal (`data: {}`) to a `z.string()` parameter causes a Zod validation error at call time; the correct syntax is `data: "{}"` (a JSON-serialised string).

Two of three reviewer models flagged this (Claude and GPT). The Coder cannot distinguish `z.string()` from `z.object()` by inspecting prose documentation — only reading the Zod schema in the TS wrapper source file reveals the expected type.

### Observation

The `data` parameter pattern — a TS wrapper accepts a string that the Python side deserialises as JSON — is a critically important boundary in this project's hybrid TS/Python architecture. The data flows through two different type systems:

- TypeScript side: `z.string()` — expects a serialised JSON string (`"{}"`)
- Python side: `json.loads(data)` — parses the string back to a dict

When agent or skill documentation shows call examples with `data: {}` (object literal), agents following those examples will produce Zod validation errors on every call. The error appears at the TS boundary, not in the Python logic, making it difficult to trace without source inspection.

This is distinct from the schema fabrication defect class — it is not fabrication but a subtle type representation issue that requires understanding the two-layer architecture. Agent/skill doc authors must check the Zod declaration in the TS source before choosing between `data: {}` and `data: "{}"` in examples.

### Suggested Improvement

**Change — Coder Code Patterns section** (`.github/agents/coder.agent.md`):

Add a note to the Code Patterns section:

> **TypeScript `data` parameter type:** TS tool wrappers that accept a JSON payload via a `data` parameter may declare it as `z.string()` (agent must pass a serialised JSON string: `data: "{}"`) or `z.object()` (agent passes an object literal: `data: {}`). These are not interchangeable — passing `{}` to `z.string()` causes a Zod validation error. Always read the `z.` declaration in the TS wrapper before documenting call examples or writing agent/skill files that include `data` call syntax.

### Action Taken

Applied: added `data` parameter type note to the Code Patterns section of `.github/agents/coder.agent.md`.
