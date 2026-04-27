---
date: "2026-04-26"
issue: 184
pr: 197
severity: major
status: archived
---

## LLM JSON null-section trap — silent data loss on missing keys

### Finding

PR #197 (issue #184) fixed `story_assembler.py` LLM JSON parsing where the model returned a JSON object with only some expected sections populated (e.g., `{"title": "Foo", "content": "..."}`) but omitted `summary` entirely. The existing `if "summary" in parsed:` guard was incorrectly written as `if parsed.get("summary"):` — when the key was present with value `null`/`None`, the guard evaluated to False and silently skipped the section, producing assembled output missing the summary block.

### Observation

Three distinct failure modes exist when parsing LLM-structured JSON:

1. **Key absent** — model omitted the key entirely; `parsed.get("key")` returns `None`.
2. **Key present, value null** — model included `"key": null`; `parsed.get("key")` returns `None`.
3. **Key present, value empty string** — model included `"key": ""; `parsed.get("key")` returns `""` (truthy).

Guard `if parsed.get("key"):` conflates (1) and (2) with (3) — it treats null and absent the same, but empty string as present. For assembly fields where empty string is a valid explicit value and null/absent should fallback to a default, the correct guard is `if "key" in parsed and parsed["key"] is not None:`.

### Suggested Improvement

1. **coder.agent.md** — add Code Pattern: "LLM JSON structured response parsing guards"
2. **test-writer.agent.md** — add "LLM JSON null-section test paths" block
3. **gotchas.md** — add entries #032, #033, #034 under new "LLM JSON Parsing" section
4. **review-checklist.md** — propose new Phase 2 checkbox for LLM JSON parsing guards

### Action Taken

Applied:
- Added gotcha entries #032, #033, #034 to `.github/notes/gotchas.md` (new "LLM JSON Parsing" section).
- Added "LLM JSON structured response parsing guards" Code Pattern to `.github/agents/coder.agent.md`.
- Added "LLM JSON null-section test paths" block to `.github/agents/test-writer.agent.md`.

Proposed for approval:
- New review-checklist.md checkbox for LLM JSON parsing guards (Phase 2, Code Review > General).
