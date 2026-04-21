---
date: "2026-04-21"
issue: 113
pr: 114
category: agent
targets:
  - ".github/agents/coder.agent.md"
  - ".github/agents/_shared/review-checklist.md"
severity: minor
status: archived
---

## Tool interface defects — operation names and return formats require source validation; companion files missed in concept sweep

### Finding

During issue #113 (Fix all critical agent-tool interface defects), the Coder was dispatched to correct stale operation names, wrong return format assumptions, and undocumented parameters across several agent and skill files. The Synthesized Review found four additional issues the Coder missed:

1. Stale savepoint operation names (`restore` → `load`) in `outline-structure/SKILL.md` — a companion file not listed in the task plan.
2. Two residual `restore` prose references in `story-orchestrator.md` not caught in the first pass.
3. Stale operation in `story-pipeline/SKILL.md` — another companion file not in the task spec.
4. The `data: {}` vs `data: "{}"` mismatch (z.string type) — the Coder corrected agent docs to use `data: {}` (object literal) in a tool whose TS wrapper declares `data: z.string().optional()` (expects a JSON string).

This is the **third occurrence** of the schema-fabrication / source-not-consulted defect class. Issues #19 (parameter name fabrication) and #22 (payload format fabrication) both identified this pattern and proposed a Rule 10 for the Coder — that proposal never reached applied status.

### Observation

Two root causes combine to produce these misses:

**Root cause 1 — Source not consulted when editing existing docs.**
The Coder treats editing agent/skill documentation as a prose task — it updates the names it was told to update, without reading the Python source (`src/tools/*.py`) and TypeScript wrappers (`.opencode/tools/*.ts`) to verify: (a) valid operation enum values, (b) Zod parameter types, and (c) return value structure. Stale operation names and wrong return format assumptions cause hard runtime failures that are not caught until pipeline execution.

**Root cause 2 — Companion files not identified via search.**
When a concept is fixed across multiple agent/skill files, the Coder relies on the task plan to enumerate the complete set of files. The task plan rarely names every file that mentions the concept — companion SKILL.md files, shared process files (`_shared/*.md`), and agent body text all independently document the same interface. A targeted grep across `.github/` and `.opencode/` before starting is the only reliable way to discover the full set.

This pattern has persisted across three issues (#19, #22, #113) with progressively broader surface area: parameter names → payload formats → operation names and return types. The third occurrence confirms informal lesson retention is insufficient; explicit rules are required.

### Suggested Improvement

**Change 1 — Coder Rule 10 extension** (`.github/agents/coder.agent.md`):

Add a new bullet to Rule 10 (Framework integration verification):

> - **When editing existing agent or skill files** that reference tool operation names, parameter types, or return formats — verify each against the actual Python source (`src/tools/*.py`) and TypeScript wrapper (`.opencode/tools/*.ts`). Do not assume existing documentation is current. Verify: (a) valid operation values by reading the Python dispatch/enum; (b) Zod parameter types (`z.string()` vs `z.object()`) from the TS wrapper; (c) return value shape from Python `return` statements. Stale operation names and wrong return format assumptions cause hard runtime failures invisible to lint or type checks.

**Change 2 — Coder Rule 6 extension** (`.github/agents/coder.agent.md`):

Add a new sub-bullet to Rule 6 (text sweep after changes):

> - **When fixing a named concept across agent or skill files** (renaming an operation, correcting a parameter format, updating a workflow step name) — do not rely on the task spec to enumerate all affected files. Run `grep -r "concept_name" .github/ .opencode/` before starting to discover ALL files that mention the concept. Skill files (`SKILL.md`), shared process files (`_shared/*.md`), and agent body text all independently repeat tool interface details; the task plan rarely names them all. Missing companion files are the most common source of residual stale references after a concept fix.

**Change 3 — Review checklist Phase 1** (`.github/agents/_shared/code-review-process.md`):

Add a new Phase 1 item:

> - [ ] **Companion file concept sweep** — when any agent or skill file is edited to fix a tool operation name, parameter name, or return format, grep for the old name across the full `.github/` and `.opencode/` directories (`grep -rn "old_name" .github/ .opencode/`) and verify every occurrence has been updated. Companion SKILL.md files and `_shared/*.md` files routinely document the same interface independently and are missed when the fix targets only the files named in the PR description.

### Action Taken

Applied:
- Extended Coder Rule 10 with a new bullet about verifying operation names, Zod types, and return shapes against source files when editing existing agent/skill docs.
- Extended Coder Rule 6 with a new sub-bullet about grepping `.github/` and `.opencode/` for ALL files mentioning a concept before starting a concept fix.
- Added a companion file concept sweep item to Phase 1 of `code-review-process.md`.
