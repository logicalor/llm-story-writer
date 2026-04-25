---
date: "2026-04-25"
issue: 180
pr: 191
category: agent
targets:
  - ".github/agents/test-writer.agent.md"
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Validation baseline PR — four patterns from accumulated mypy/test debt

### Finding

Issue #180 / PR #191 restored the validation baseline after accumulated drift:
- 6 ruff F821 undefined-name errors fixed
- 19 failing unit tests fixed (`story_state.py` cmd_write JSON parsing, `story_assembler` expanded_outline fallback, `wiki_extract` outline savepoint fallback)
- 101 mypy errors across 19 files fixed (interface corrections, type annotations, null guards, dead code removal)
- Post-review regression: `_generate_tags` wrapped LLM response as a single-element list `[response]` instead of calling `json.loads(response)` — a silent semantic error producing no exceptions

Four distinct patterns emerged.

### Observation

**Pattern 1 — Savepoint migration test setup gaps**

When an implementation migrates from reading `state.json` to reading savepoints, tests that only set up `state.json` break silently — the implementation no longer reads the old file for the migrated field. The test must set up the savepoint using the savepoint repository. This is distinct from "savepoint resume write symmetry" (Coder Code Patterns), which addresses production write synchronisation. The gap here is in test fixture setup: tests were written for the state.json world and never updated as the implementation migrated to savepoints. 19 tests broke for this reason.

**Pattern 2 — LLM JSON array parsing: wrap vs. parse**

`_generate_tags` contained the regression `return [response]` instead of `return json.loads(response)`. This produces a single-element list containing the raw LLM string — no exception, no lint error, no type error. The bug is invisible at every validation layer; only a semantic correctness check catches it. The fix is mechanical: when an LLM response is expected to be a JSON array, always call `json.loads()` — never wrap the string in a list literal.

**Pattern 3 — Bare `except:` recurrence**

Bare `except:` clauses (no exception type) replaced with `except Exception:` across the codebase. Ruff E722 catches this — the issue is that lint was not being run regularly, allowing debt to accumulate. Issue #15 recorded this pattern with a threshold: "if recurs in two or more future issues, add sub-bullet to Rule 9." This is the second recurrence. Adding a Rule 9 observability sub-bullet now.

**Pattern 4 — Unused `response = await ...` assignments**

Several `response = await some_method()` patterns where `response` was never read. The fix is dropping the assignment to bare `await some_method()`. Ruff F841 catches unused local variables; mypy also flags some of these. No new rule needed — Rule 1 (lint) and Rule 2 (type-check) catch this if run consistently.

### Suggested Improvement

1. **test-writer.agent.md** — add a named block "Savepoint migration test setup" covering:
   - When testing code migrated from state.json to savepoints, test fixture must set up savepoints via the savepoint repository
   - If implementation provides a fallback path, test both: primary (savepoint) and fallback (state.json)

2. **coder.agent.md Code Patterns** — add "LLM JSON array response parsing" pattern:
   - `json.loads(response)` not `[response]` when expecting a JSON array from LLM output
   - Silent failure mode with no exceptions or lint errors

3. **coder.agent.md Rule 9** — add "Exception handler observability" sub-bullet (honouring issue #15 two-recurrence threshold):
   - Bare `except:` is a lint error (ruff E722); always replace with `except Exception:`
   - `except Exception: pass` must include at least a `print(..., file=sys.stderr)` call

### Action Taken

Applied:
- Added "Savepoint migration test setup" block to `test-writer.agent.md` after "LLM-response parse-error paths".
- Added "LLM JSON array response parsing" Code Pattern to `coder.agent.md` after "Savepoint resume write symmetry".
- Added "Exception handler observability" sub-bullet to Coder Rule 9 after `_validate_story_name()` sub-bullet.
