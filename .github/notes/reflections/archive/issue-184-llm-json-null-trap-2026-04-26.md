---
date: "2026-04-26"
issue: 184
pr: 197
category: instruction
targets:
  - ".github/notes/gotchas.md"
  - ".github/agents/coder.agent.md"
  - ".github/agents/test-writer.agent.md"
  - ".github/agents/_shared/review-checklist.md"
severity: major
status: archived
---

## LLM JSON null-trap pattern and structured response parsing guards

### Finding

Issue #184 / PR #197 (consistency-checker parse-llm-output) surfaced four related parsing
defects that occur systematically when Python code parses structured JSON returned by an LLM:

1. **`data.get("key", {})` null-trap** — when the LLM returns explicit JSON `null` for a
   field (e.g. `"issues": null`), `data.get("key", {})` returns `None`, not `{}`. The default
   only applies when the key is *absent*. All downstream `.items()`, `for item in ...`, and
   `.get()` calls on `None` crash with `AttributeError` or `TypeError`. Fix:
   `data.get("key") or {}`.

2. **`isinstance(data, dict)` guard after `json.loads()`** — valid JSON can parse to a list,
   number, string, or `None`. After `json.loads()`, code that immediately calls `.get()` without
   checking `isinstance(data, dict)` crashes on any non-dict payload. The LLM can return a
   differently shaped response at any time without warning.

3. **Non-dict list items in LLM JSON** — when iterating a list of objects from LLM output,
   the LLM may return strings or other scalars interleaved with the expected dict objects. Any
   `.get()` call on a str raises `AttributeError`. Fix: add
   `if not isinstance(item, dict): continue` before accessing item fields.

4. **Tests for null-section scenarios** — the standard "LLM-response parse-error paths" block
   in test-writer.agent.md covers `json.loads()` failure (non-JSON string). The null-section
   failure modes (explicit null per-field, non-dict payload, non-dict list items) are distinct
   and equally common in LLM output but have no existing test guidance.

### Observation

The null-trap is the most systematic footgun. It appears in every agent that parses structured
LLM output shaped like `{"section_a": [...], "section_b": {...}}`. The `or {}` / `or []` fix
pattern is mechanical and unconditional — there is no valid case where an LLM-sourced field
should propagate `None` silently into downstream iteration.

The `isinstance(data, dict)` guard is similarly systematic: any JSON parser can receive a
non-dict root and it costs one line to guard. Without it, a single bad LLM response causes an
`AttributeError` that escapes the parser entirely.

All three code patterns are invisible to ruff, mypy, and pylint because the types are
`Any`-valued at parse time. Only runtime testing with explicit null payloads reveals the gaps.

The review checklist has no existing check for these patterns. Three of four known review models
(PR #197) missed at least one of these issues on first pass — the null-trap in particular was
not caught by the initial multi-model review.

### Suggested Improvement

**Minor (auto-apply):**

1. **gotchas.md** — add three entries (032, 033, 034) under a new "LLM JSON Parsing" section
   covering the three code patterns with correct/wrong examples.

2. **coder.agent.md Code Patterns** — add "LLM JSON structured response parsing guards" block
   after the existing "LLM JSON array response parsing" entry, covering all three guards as
   a unified pattern.

3. **test-writer.agent.md** — add "LLM JSON null-section test paths" bullet after the existing
   "LLM-response parse-error paths" block, specifying the three additional test scenarios.

**Major (propose for approval):**

4. **review-checklist.md Phase 2 (Code Review > General)** — add a new checkbox:
   "LLM JSON parsing guards" — reviewer must check for `or {}` / `or []` fallbacks on `.get()`,
   `isinstance(data, dict)` guards after `json.loads()`, and `isinstance(item, dict)` guards
   in list iterations on LLM output.

### Action Taken

Applied:
- Added gotcha entries #032, #033, #034 to `.github/notes/gotchas.md` (new "LLM JSON Parsing" section).
- Added "LLM JSON structured response parsing guards" Code Pattern to `.github/agents/coder.agent.md`.
- Added "LLM JSON null-section test paths" block to `.github/agents/test-writer.agent.md`.
- Embedded all three gotcha entries into `conventions` ChromaDB collection.
- Embedded reflection into `reflections` ChromaDB collection.

Proposed for approval:
- New `review-checklist.md` checkbox for LLM JSON parsing guards (Phase 2, Code Review > General) — see proposal below.
