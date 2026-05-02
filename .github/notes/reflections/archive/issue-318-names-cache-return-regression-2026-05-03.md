---
date: "2026-05-03"
issue: 318
pr: 330
category: agent
targets:
  - ".github/agents-copilot/coder.agent.md"
  - ".github/agents-openrouter/coder.agent.md"
severity: minor
---

## Names cache path included in return value — return contract not audited before submitting

### Finding

PR #330 (issue #318) introduced a regression where `names_cache_path`
(`stories/<story>/characters/_names.json`) was included in the `written: list[Path]` return
value of `_generate_character_sheets`. The function's contract is to return the paths of
generated character sheet files only; the names cache is an internal implementation artifact
(written to disk so the extraction step can be skipped on resume). The fix added a defensive
filter at the return site:

```python
return [path for path in written if path != names_cache_path]
```

The regression occurred because the Coder added `written.append(names_cache_path)` during the
names-extraction phase (as part of wiring the ledger-gated resume path) without pausing to
verify which paths in `written` belonged to the output contract vs. which were internal state.

**Positive signal from Test Writer:** The Test Writer correctly diagnosed that `_names.json`
now existing on disk is expected new behavior (not a regression) and updated the test assertions
accordingly — asserting `(characters_dir / "_names.json").exists()` and filtering it out of the
"written sheets" count. This validates the "pre-existing test disk-write audit" pattern already
in the Test Writer agent.

### Observation

The failure pattern is: a function accumulates multiple file writes inside a processing loop,
appending each path to a `written` list. The Coder adds a new write (names cache) without
revisiting the list's output contract. The result is callers receiving internal paths mixed into
what should be a clean output set.

This is a routine review step that takes seconds — trace every `written.append()` or equivalent
site, confirm each is part of the function's return contract, and ensure no implementation-detail
paths (caches, temporary state, index files) have been accidentally included.

The defensive filter (`return [path for path in written if path != names_cache_path]`) is the
correct fix when the output contract must exclude specific internal paths. But the better practice
is not to append internal-detail paths to the return buffer in the first place.

### Suggested Improvement

Add a Code Pattern guidance bullet to the Coder agent in the Code Patterns section:

> **Return value accumulation audit:** When implementing a function that accumulates file paths
> (or any collection) in a local buffer (`written: list[Path]`, `results: list[str]`, etc.) and
> returns that buffer, before submitting trace every append site and verify each appended item
> belongs to the function's output contract. Implementation-detail paths — cache files,
> index files, intermediate state written as side-effects — must NOT be appended to the return
> buffer. The caller should receive only the files the function is contracted to produce.
> A defensive exclusion filter at the return site is acceptable when the contract is clear,
> but prefer not appending the non-output path in the first place.
> (Source: issue #318, PR #330 — `names_cache_path` appended to character sheet return list.)

### Action Taken

Applied: added "Return value accumulation audit" guidance to Code Patterns in coder.agent.md
(copilot and openrouter variants).
