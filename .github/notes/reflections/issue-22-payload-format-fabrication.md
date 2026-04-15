---
date: "2026-04-15"
issue: 22
pr: 65
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: major
status: active
---

## Batch payload format fabrication — new variant of issue #19 schema fabrication defect

### Finding

During issue #22 (Build Wiki Maintainer Subagent), the Coder wrote the `wiki-maintenance` SKILL.md with a fabricated batch payload format. The SKILL.md documented an `operations` array structure for the `wiki-update` batch operation, when the actual implementation in `src/tools/wiki_update.py` expects three top-level arrays: `creates`, `updates`, and `timeline_events`. Additionally, field names within the payload used camelCase (`pageType`, `pageName`, `firstAppearance`, `detailLevels`, `mergeBody`) when the Python tool expects snake_case (`page_type`, `page_name`, `first_appearance`, `detail_levels`, `merge_body`). Both issues were caught by the Synthesized Review as S-C-01 and S-C-02 (singular, Gemini only) and verified against source code.

### Observation

This is a **new variant** of the issue #19 schema fabrication defect class. In issue #19, the Coder fabricated tool *parameter names*. Here, the Coder fabricated a *structured payload format* — the internal JSON structure of a parameter value. The distinction matters because:

1. The issue #19 proposed rule (Rule 10/11) says "verify all tool parameter names, types, and descriptions against the actual tool schema files (`.opencode/tools/*.ts` for TypeScript wrappers, `src/tools/*.py` for Python scripts)". This covers parameter names but not the *internal format* of structured parameters like JSON payloads.

2. The batch payload is a JSON string parameter that crosses the TypeScript/Python boundary. The TypeScript wrapper accepts it as a string (`payload`), but the Python tool parses it with specific structural expectations. The source of truth for the payload format is the Python implementation, not the TypeScript schema.

3. The Coder correctly verified tool parameter names (lesson from issue #19) — the tool table in the agent definition uses correct camelCase parameter names matching the TypeScript Zod schema. The failure was in the SKILL.md, which documents the *content* of the `payload` parameter — a level of indirection deeper than what the current proposed rule covers.

4. Only Gemini (1 of 3 reviewers) caught both critical issues by cross-referencing SKILL.md against the actual Python source. Claude and GPT reviewed in isolation. Second consecutive PR where singular findings were genuine criticals — reinforces the value of including all singular findings for verification in the synthesis step.

This reinforces that fabrication is a persistent defect pattern across issues #19 and #22. Each occurrence adds new surface area: parameter names → payload structures → field naming conventions. The proposed Rule 10/11 needs to be broadened from "parameter names" to "all structured data formats" to be durable.

### Suggested Improvement

Expand the proposed Rule 10/11 from issue #19 to also cover structured payload formats. The amended rule text:

```markdown
10. **When writing agent definitions or skill files that reference tools**, verify all tool parameter names, types, and descriptions against the actual tool schema files (`.opencode/tools/*.ts` for TypeScript wrappers, `src/tools/*.py` for Python scripts). Never invent parameter names from memory — always read the schema file. For tool tables in agent definitions, verify every tool mentioned in the workflow prose appears in the table with correct parameter documentation. **For structured parameters** (JSON payloads, config objects, batch formats), verify the internal format and field names against the receiving tool's source code — the TypeScript wrapper only validates the outer parameter; the inner structure is defined by the Python implementation.
```

This is additive to the issue #19 proposal (same rule, broader scope). Both should be applied together.

### Action Taken

Proposed for approval — amends the pending issue #19 Rule 10/11 proposal to also cover structured payload formats.
