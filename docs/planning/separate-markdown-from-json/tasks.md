# Task Breakdown: Separate Markdown From JSON Persistence

> Implements [PRD](./prd.md)

**Date:** 2026-05-03

Order: foundation helpers → reader compat layer → per-area write
conversions → migration script → lint gate.

## Tasks

### Task 1: Add `persist_markdown` / `read_markdown_ref` helpers

**Type:** backend
**Estimated scope:** small
**Dependencies:** none

**Description:**
Create `src/tools/_persist.py` exposing:

- `persist_markdown(story_root, relative_path, body) -> dict`
- `read_markdown_ref(story_root, ref) -> str`

Atomic write via existing `_atomic_write`. Pointer shape
`{"$ref": "<relative-path>"}`. `read_markdown_ref` accepts either a
pointer dict or a legacy raw string and returns the markdown body
unchanged in the legacy case.

**Acceptance Criteria:**

- [ ] Helpers exist with type hints
- [ ] Round-trip test (write pointer → read body) passes
- [ ] Legacy-string fallback test passes
- [ ] Path traversal rejected (refuses `..`, absolute paths)

**Key Files:**

- `src/tools/_persist.py`
- `tests/unit/test_persist.py`

---

### Task 2: Document the storage convention + JSON schema

**Type:** backend (docs)
**Estimated scope:** small
**Dependencies:** Task 1

**Description:**
Write `docs/planning/separate-markdown-from-json/convention.md` defining
the pointer shape and the four "this counts as markdown content" rules.
Add `src/application/schemas/markdown_ref.json` so the pointer shape is
machine-validatable.

**Acceptance Criteria:**

- [ ] Convention doc explains rules + examples
- [ ] JSON Schema validates a sample pointer

**Key Files:**

- `docs/planning/separate-markdown-from-json/convention.md`
- `src/application/schemas/markdown_ref.json`

---

### Task 3: Convert character-sheet writes to pointer format

**Type:** backend
**Estimated scope:** medium
**Dependencies:** Task 1

**Description:**
Refactor `_generate_character_sheets` in `src/presentation/orchestrator.py`
and `src/tools/character_manager.py` so:

- `sheet`, each `chunks.<k>`, `summary`, `abridged` are written to
  `characters/<slug>/<unit>.md` files.
- The per-entity JSON stores pointer refs in those positions.
- `name`, `aliases`, `updated_at` stay inline.
- All read sites (search for `["sheet"]`, `["chunks"]`, etc.) call
  `read_markdown_ref`.

**Acceptance Criteria:**

- [ ] New character writes produce pointer JSON + sibling `.md` files
- [ ] Reading a character sheet via existing helpers returns the same
      string content as before
- [ ] Existing inline-format files still load (legacy fallback path)
- [ ] Tests assert no markdown body remains in the JSON

**Key Files:**

- `src/presentation/orchestrator.py`
- `src/tools/character_manager.py`
- `src/presentation/agents/character_evolver.py`
- `tests/unit/test_orchestrator.py`
- `tests/unit/test_character_manager.py`

---

### Task 4: Convert setting-sheet writes to pointer format

**Type:** backend
**Estimated scope:** medium
**Dependencies:** Task 1 (parallel with Task 3)

**Description:**
Same conversion as Task 3 for `_generate_setting_sheets` and
`src/tools/setting_manager.py`. Setting chunk keys differ; layout is
otherwise identical.

**Acceptance Criteria:**

- [ ] Same as Task 3 for settings
- [ ] `setting_evolver.py` no longer feeds the LLM a serialised
      dict-of-markdown blob — it reads the pointer markdown bodies and
      assembles a clean prompt

**Key Files:**

- `src/presentation/orchestrator.py`
- `src/tools/setting_manager.py`
- `src/presentation/agents/setting_evolver.py`
- `tests/unit/test_setting_manager.py`

---

### Task 5: Convert recap files to pointer format

**Type:** backend
**Estimated scope:** medium
**Dependencies:** Task 1

**Description:**
Refactor recap writes (orchestrator chapter loop and
`src/application/strategies/outline_chapter/recap_manager.py` /
`src/tools/recap_manager.py`) so per-chapter recap JSON stores pointer
refs for `events`, `compact`, `sanitised`. Markdown bodies move to
`chapters/chapter_N/recap_<unit>.md`. The
`PipelineState.recaps[<n>]` field becomes a pointer to the per-chapter
recap JSON, not an inline dict.

**Acceptance Criteria:**

- [ ] New recaps write pointer JSON + sibling markdown
- [ ] `pipeline_state.recaps` no longer holds inline content
- [ ] Read sites updated; legacy inline form still loads
- [ ] No fenced code blocks anywhere in recap output

**Key Files:**

- `src/presentation/orchestrator.py`
- `src/application/strategies/outline_chapter/recap_manager.py`
- `src/tools/recap_manager.py`
- `src/presentation/agents/recap_writer.py`
- `tests/unit/test_recap_*.py`

---

### Task 6: Convert outline persistence + fix `enrichment_suggestions` double-encode

**Type:** backend
**Estimated scope:** medium
**Dependencies:** Task 1

**Description:**
Two parts:

1. `chapter_outlines[].summary` becomes a pointer to
   `outline/chapter_N_summary.md`. Inline content moves out of
   `pipeline_state.json`.
2. `outline_result.enrichment_suggestions` — currently a string
   containing `` ```json … `` — is parsed at the write boundary, the
   fenced JSON extracted into a proper Python dict, and persisted as
   `outline/enrichment_suggestions.json`. The `pipeline_state.json`
   field becomes a pointer to that file. Update read sites to load it
   as JSON, not as a string-to-be-parsed.

**Acceptance Criteria:**

- [ ] Outline summaries stored as pointers
- [ ] `enrichment_suggestions` field never contains a fenced code block
- [ ] Test confirms a round-trip preserves the structured suggestions
- [ ] Legacy string form still loads (with one-time parse)

**Key Files:**

- `src/presentation/orchestrator.py` (outline + critique blocks)
- `src/application/pipeline/handoffs.py` (`OutlineResult`)
- `tests/unit/test_orchestrator.py`

---

### Task 7: Convert `state.json::story_prompt` to pointer

**Type:** backend
**Estimated scope:** small
**Dependencies:** Task 1

**Description:**
Move story prompt body to `stories/<story>/prompt.md`. Replace
`state.json::story_prompt` with `{"$ref": "prompt.md"}`. Update
`_apply_prompt` and `_load_story_prompt` to use the helpers.

**Acceptance Criteria:**

- [ ] `_apply_prompt` writes the markdown to `prompt.md` and stores a
      pointer in state
- [ ] `_load_story_prompt` resolves both pointer and legacy inline forms
- [ ] Test covers both forms

**Key Files:**

- `src/presentation/cli/main.py`
- `src/presentation/orchestrator.py`
- `tests/unit/test_cli_main.py`

---

### Task 8: One-shot migration script for existing stories

**Type:** backend (tool)
**Estimated scope:** medium
**Dependencies:** Tasks 3–7

**Description:**
Add `src/tools/migrate_inline_markdown.py`. Behaviour:

- Walks `stories/<story>/` for every story.
- For each known JSON file (character/setting sheets, recaps,
  pipeline_state, state), extracts inline markdown to `.md` siblings
  and rewrites JSON with pointer refs.
- Parses the `enrichment_suggestions` markdown-wrapped-JSON and
  rewrites as a proper JSON sub-document.
- Idempotent — re-running on an already-migrated story is a no-op.
- Dry-run flag (`--dry-run`) prints a plan without writing.
- Atomic writes throughout.

**Acceptance Criteria:**

- [ ] Script runs cleanly on `the-silence-between-the-stars` and
      `breaking-amy` stories; round-trip read of every converted field
      returns identical content
- [ ] Re-running is a no-op
- [ ] `--dry-run` produces a complete plan and writes nothing
- [ ] Test fixture covers edge cases: empty files, partial migrations,
      malformed JSON-in-markdown that can't be parsed (fall back to
      treating as plain markdown)

**Key Files:**

- `src/tools/migrate_inline_markdown.py`
- `tests/unit/test_migrate_inline_markdown.py`

---

### Task 9: CI lint gate — `lint_no_inline_markdown.py`

**Type:** backend (CI)
**Estimated scope:** small
**Dependencies:** Tasks 3–7

**Description:**
Add `scripts/lint_no_inline_markdown.py`. Walks `stories/` and fails if
any JSON value contains a markdown heading, paragraph break, fenced
block, or exceeds the size threshold (with a small allow-list for
short single-paragraph fields). Wire into the existing GitHub Actions
workflow.

**Acceptance Criteria:**

- [ ] Lint script runs and fails when given a JSON file containing
      fenced JSON
- [ ] Allow-list configurable via constant at top of script
- [ ] CI workflow updated to run it on PRs touching `stories/` or any
      `*_writer.py` / `*_manager.py` source file
- [ ] Documented in `docs/testing/integration-tests.md` (or a new
      `docs/testing/lint.md`)

**Key Files:**

- `scripts/lint_no_inline_markdown.py`
- `.github/workflows/ci.yml`
- `docs/testing/lint.md` (new)

---

### Task 10: Audit remaining write sites + remove legacy fallback

**Type:** backend
**Estimated scope:** small
**Dependencies:** Tasks 3–9

**Description:**
After all writes are converted and the migration script has been run
against every committed story, remove the legacy-inline fallback from
`read_markdown_ref` so the codebase is single-format. Search for any
remaining `json.dumps(... markdown ...)` patterns missed by Tasks 3–7
and convert them.

**Acceptance Criteria:**

- [ ] Grep for `json.dumps(...sheet|sheet_text|markdown|recap|content)`
      returns no matches outside of pointer construction
- [ ] `read_markdown_ref` rejects raw-string input with a clear
      `ValueError`
- [ ] All tests still pass

**Key Files:**

- `src/tools/_persist.py`
- Any straggler write sites surfaced by the audit
