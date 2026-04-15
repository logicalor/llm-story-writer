---
date: "2026-04-15"
issue: 22
pr: 65
category: instruction
targets:
  - ".github/agents/coder.agent.md"
severity: major
status: active
---

## CamelCase/snake_case dual naming convention across TypeScript/Python boundary

### Finding

During issue #22 (Build Wiki Maintainer Subagent), the SKILL.md used camelCase field names (`pageType`, `pageName`, `firstAppearance`, `detailLevels`, `mergeBody`) in batch payload JSON examples. The wiki-update tool's TypeScript wrapper uses camelCase for its Zod schema parameters (matching TypeScript conventions), but the batch `payload` parameter is a JSON string parsed by the Python implementation, which expects snake_case (`page_type`, `page_name`, `first_appearance`, `detail_levels`, `merge_body`). Caught by Synthesized Review as S-C-02 (singular, Gemini only).

### Observation

This project has a systemic dual naming convention at the TypeScript/Python boundary:

- **Agent invocation parameters** → camelCase (matching TypeScript Zod schema): `pageType`, `pageName`, `detailLevels`
- **Internal payload data** → snake_case (matching Python implementation): `page_type`, `page_name`, `detail_levels`

The distinction is:
- The TypeScript wrapper accepts named arguments via Zod validation — these use camelCase
- Any parameter that contains a structured JSON string (like `payload`) bypasses TypeScript validation and is parsed directly by Python — the internal structure uses snake_case

This creates a footgun when authoring SKILL.md files or agent definitions that include JSON payload examples. The agent calls the tool with camelCase parameter names, but must construct the payload JSON with snake_case keys. Both conventions are correct in their respective contexts, but the boundary is invisible unless explicitly documented.

The S-C-02 finding was singular (Gemini only) — Claude and GPT reviewed the SKILL.md in isolation without cross-referencing the Python source. This is the second finding in PR #65 where cross-file verification was required to detect the issue, caught by exactly one reviewer. Pattern: correctness issues requiring cross-file reference are the primary source of singular-but-genuine critical findings.

### Suggested Improvement

Add a note to the Coder agent's "Conventions & Gotchas" section as an interim measure (pending gotchas.md creation per issue #7 reflection):

```markdown
> **Naming convention at TypeScript/Python boundary:** Tool parameter names in agent definitions and tool tables use camelCase (matching TypeScript Zod schema). Structured JSON payloads passed *through* a string parameter and parsed by Python use snake_case (matching Python conventions). When writing SKILL.md payload examples, verify field naming against the Python tool's parser, not the TypeScript wrapper's Zod schema.
```

When `gotchas.md` is created (issue #7, status: active/major), this should also be recorded there as a permanent gotcha entry.

### Action Taken

Proposed for approval — documents a systemic naming convention footgun requiring an interim Coder agent note and a future gotchas.md entry.
