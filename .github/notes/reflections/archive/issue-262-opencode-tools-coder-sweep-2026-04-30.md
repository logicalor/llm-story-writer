---
date: "2026-04-30"
issue: 262
pr: 272
category: agent
targets:
  - ".opencode/agents/coder.md"
  - ".github/agents-copilot/coder.agent.md"
severity: minor
status: archived
---

## Residual Stale `.opencode/tools/` References in Coder Agent

### Finding

PR #272 (issue #262) removed residual stale references to `.opencode/tools/` and "TypeScript wrappers" from `.opencode/agents/coder.md`. The change was a clean two-text-substitution sweep with unanimous reviewer approval and zero actionable findings.

However, the same stale references persist in the dual-runtime counterpart `.github/agents-copilot/coder.agent.md`, which was not modified in the PR. Specific lingering phantom concepts in the Copilot file:

1. **Frontmatter description** — still mentions "TypeScript OpenCode tool wrappers"
2. **Rule 6 bullet** — "When deleting TypeScript tool wrappers (`.opencode/tools/*.ts`)" instead of Python-native tool deletion guidance
3. **Rule 9 security bullet** — TypeScript-specific `execSync()`/`execFileSync()` guidance instead of Python `subprocess.run()` guidance
4. **Rule 10 tool verification bullet** — instructs verifying against "TypeScript wrapper (`.opencode/tools/*.ts`)" and "Zod field names", referencing non-existent files
5. **Implementation Order step 3** — "TypeScript wrappers third — OpenCode tool definitions in `.opencode/tools/`" plus atomic-pair note
6. **Code Patterns section** — "TypeScript `data` parameter type" with Zod schema discussion

### Observation

The dual-run policy states: "Any change to an agent's behaviour must be applied to both runtimes during the transition." Removing phantom references is a behaviour-relevant change — it stops the Coder from attempting to verify against deleted TypeScript wrappers and Zod schemas. The Copilot runtime currently carries the exact same stale guidance that was just cleaned from the OpenCode runtime.

This also reveals a systemic gap in the dual-run sync mechanism: PR #272 was scoped narrowly to the OpenCode file, and the Copilot counterpart was not flagged by reviewers as out of sync. The stale-reference class is now fully retired in `.opencode/agents/` but still active in `.github/agents-copilot/`. A single grep for `.opencode/tools/` across both runtimes would have caught this before merge.

### Suggested Improvement

Apply the same text substitutions to `.github/agents-copilot/coder.agent.md`:
- Remove "TypeScript OpenCode tool wrappers" from the description
- Replace the TypeScript wrapper deletion bullet with the Python-native equivalent (`src/tools/*.py` sweep)
- Replace the TypeScript security bullet with Python subprocess guidance
- Replace the tool verification bullet with Python-only verification language
- Retire step 3 in Implementation Order (match `.opencode/agents/coder.md` line 124)
- Remove the TypeScript `data` parameter type section entirely

### Action Taken

Applied: Synchronized `.github/agents-copilot/coder.agent.md` with the OpenCode counterpart to remove all stale `.opencode/tools/`, TypeScript wrapper, and Zod schema references.
