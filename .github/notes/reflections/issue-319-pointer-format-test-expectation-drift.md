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
`coder.agent.md` files:

> **When converting a JSON field from inline content to a `{"$ref": "path"}` pointer**
> — scan existing tests for assertions of the form `assert substring in data["field"]`
> or `data["field"] == expected_string` against the converted field. These become
> expectation-drift failures immediately on conversion. Fix them in the same dispatch:
> (1) extract `ref_path = data["field"]["$ref"]`, (2) read the referenced `.md` file
> from the story directory, (3) assert against the file content. Do not leave pointer
> expectation-drift for the Orchestrator to diagnose. (Source: issue #319, PR #331.)

Also add a bullet to the Assertions section of `.agents/skills/test-verification/SKILL.md`:

> For fields written as pointer format (`{"$ref": "path/to/file.md"}`): never assert
> directly on `data["field"]`. Resolve via `ref_path = data["field"]["$ref"]`, read
> the `.md` file, then assert on the file content.

### Action Taken

Applied: sub-bullet added to Coder Rule 11 in both `coder.agent.md` files;
pointer-resolution assertion note added to `test-verification/SKILL.md`.
