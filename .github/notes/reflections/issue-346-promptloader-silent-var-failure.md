---
date: "2026-05-04"
issue: 346
pr: 347
category: instruction
targets:
  - ".github/notes/gotchas.md"
  - ".opencode/agents/coder.md"
  - ".opencode/agents/test-writer.md"
severity: minor
status: archived

## PromptLoader `.replace()` Silent Placeholder Failure and Downstream Cascade

### Finding

During issue #346 (PR #347), a critical bug class was identified by the Claude reviewer in `test_prompt_verification.py`: the test passed stale variable names to a renamed template. `PromptLoader` uses string `.replace("{variable_name}", value)` — not Python `format()` — so unresolved `{variable}` placeholders remain as literal text in the rendered prompt without raising any exception. Tests passed. The prompt sent to the LLM was malformed.

Four related patterns were observed in this session:

1. **PromptLoader uses `.replace()`, not `format()`** — unresolved `{variable}` placeholders silently survive into the prompt sent to the LLM. No exception, no warning.
2. **Three-surface cascade on template variable rename** — renaming a `{variable_name}` in a `prompts/` template requires updating all three surfaces in the same commit: (a) the template file, (b) the Python code passing keys to `load_prompt()` / `PromptLoader`, and (c) integration/prompt-verification tests that construct the variable dict.
3. **Mock return type schema fidelity** — when mocking agent return values in orchestrator tests, the mock dict must match the actual return type's field value types. For example, `{"events": ""}` (string, as the real agent returns) must not be mocked as `{"events": []}` (list). Type mismatches cause downstream consumers to fail with `TypeError` or produce wrong output while the mocked test passes.
4. **`str(value or "")` for nullable LLM output fields** — when persisting optional or nullable LLM output fields to disk, `str(value or "")` is safer than `str(value)`: the former coerces `None` or falsy values to `""` rather than the string `"None"`.

### Observation

Pattern 1 is a project-specific silent failure class with no analog in standard Python. Because `PromptLoader` is the project's canonical prompt-loading mechanism, any agent or Coder that renames a template variable without updating all three surfaces produces a malformed prompt at runtime. Existing test infrastructure does not guard against this — a test that checks the rendered prompt for expected content words will pass even if `{new_variable}` is left unreplaced, as long as the expected words appear in the non-variable parts.

Pattern 2 extends the existing "text sweep" guidance in coder.md Rule 6 with a concrete three-surface requirement specific to prompt templates.

Pattern 3 is a testing discipline gap — the existing test-writer.md guidance covers null sections, non-dict payloads, and mixed list items, but does not address type fidelity between mock return values and the actual agent return schema.

Pattern 4 is a narrow Python coding convention applicable whenever a field's value may be `None` (e.g., LLM output that the LLM sometimes omits, or a field that wasn't populated on a short-circuit path).

### Suggested Improvement

1. **gotchas.md** — Add gotcha #055 documenting the PromptLoader `.replace()` behaviour, the three-surface update requirement, and a test guard pattern (`assert "{" not in rendered`).
2. **coder.md** — Add a sub-bullet to Rule 6 immediately after the "When moving data into a new field or message" bullet covering the three-surface PromptLoader template variable rename requirement.
3. **test-writer.md** — Add a bullet near the "LLM JSON null-section test paths" section about mock return type schema fidelity.
4. **coder.md** (pattern 4) — Add a sub-bullet in Rule 9 or Rule 6 about `str(value or "")` for nullable persistence. (Deferred to next session — already at the 3-file limit for minor improvements.)

### Action Taken

Applied (3 minor improvements):
- Added gotcha #055 to `.github/notes/gotchas.md`
- Added PromptLoader three-surface sub-bullet to `.opencode/agents/coder.md` Rule 6
- Added mock return type schema fidelity note to `.opencode/agents/test-writer.md`
