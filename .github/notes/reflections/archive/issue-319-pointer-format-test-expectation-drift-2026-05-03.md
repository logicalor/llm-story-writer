---
date: "2026-05-03"
issue: 319
pr: 331
category: agent
targets:
  - ".github/agents-copilot/coder.agent.md"
  - ".github/agents-openrouter/coder.agent.md"
  - ".agents/skills/test-verification/SKILL.md"
severity: minor
---

## Pointer-format field conversion breaks existing `data["field"]` substring assertions

### Finding

PR #331 (issue #319) converted `character_manager.py`, `setting_manager.py`,
`character_evolver.py`, `setting_evolver.py`, and `orchestrator.py` to write the
`sheet` field as a `{"$ref": "path/to/file.md"}` pointer dict rather than inline
string content (via `persist_markdown` / `read_markdown_ref`).

After the Coder finished, two tests failed:

- `test_character_evolver_updates_sheet_on_material_changes` (in
  `test_character_evolver.py`) — asserted `"Updated hero after meeting villain." in
  updated_data["sheet"]`
- Equivalent assertion in `test_setting_evolver.py`

Both tests broke because `data["sheet"]` is now `{"$ref": "stories/.../sheet.md"}`,
not a string. The Coder did not scan for existing tests that would become
expectation-drift failures after the pointer conversion.

The Orchestrator diagnosed both failures manually and applied fixes (resolve the
pointer, read the `.md` file, assert on file content).

### Observation

This is a predictable pattern for any pointer-format conversion task: **every test
that does `assert substring in data["field"]` against a field being converted to
pointer format becomes an expectation-drift failure the moment the conversion is
applied.** The fix is always the same three-step sequence:

1. Extract: `ref_path = data["field"]["$ref"]`
2. Read: open the file at the story root and read its content
3. Assert: against the file content, not `data["field"]`

This pattern will recur for any future pointer-format conversion (wiki pages, chapter
drafts, outline fields). The Coder should scan existing tests for direct field
substring assertions before submitting a pointer-format change, and fix them in the
same dispatch rather than leaving them for the Orchestrator.

### Suggested Improvement

Add a sub-bullet to Coder Rule 11 ("Test expectation drift") in both
`coder.agent.md` files and to the test-verification SKILL.

### Action Taken

Applied: added sub-bullet to both coder agent files under Rule 11 — "When converting a
JSON field from inline content to a `{"$ref": "path"}` pointer" — with the three-step
fix sequence. (Source: issue #319, PR #331.)
