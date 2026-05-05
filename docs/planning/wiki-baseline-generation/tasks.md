# Task Breakdown: Wiki Baseline Generation — Pre-Story State

> Implements [PRD](./prd.md)

**Date:** 2026-05-06

---

## Tasks

### Task 1: Add `_build_pre_story_excerpt` and wire it into page generation

**Type:** backend
**Estimated scope:** small
**Dependencies:** none

**Description:**

In `src/tools/wiki_generation.py`, add a new helper function `_build_pre_story_excerpt(outline_result, story_root)`. It assembles only `story_elements` and `base_context` from the `OutlineResult` — the pre-story foundation — omitting `summary` and `chapter_outlines`. These two fields are explicitly authored as pre-story content (`story_elements.md` prompt instructs "describe all characters at their initial state at the story's beginning").

Update `generate_character_pages()` to call `_build_pre_story_excerpt()` for the `outline_excerpt` variable passed to `_generate_page()`, while keeping `_build_outline_excerpt()` for the `_extract_entities()` call (entity discovery must still see the full outline to catch all named entities).

Apply the same change to `generate_location_pages()`.

The function signatures of both public functions are unchanged. No pipeline-level changes required.

**Acceptance Criteria:**

- [ ] `_build_pre_story_excerpt(outline_result, story_root)` returns a string built only from `story_elements` and `base_context`; it never includes `summary` or chapter outline data.
- [ ] `generate_character_pages()` uses `_build_pre_story_excerpt()` for the prompt variable passed to `_generate_page()` and `_build_outline_excerpt()` for `_extract_entities()`.
- [ ] `generate_location_pages()` does the same.
- [ ] Unit tests for `_build_pre_story_excerpt`:
  - Returns empty string when both `story_elements` and `base_context` are empty.
  - Returns only `story_elements` text when `base_context` is absent.
  - Returns both sections joined when both are populated.
  - Does **not** include any `chapter_outlines` or `summary` content even when they are populated on the `OutlineResult`.

**Key Files:**

- `src/tools/wiki_generation.py` — add `_build_pre_story_excerpt`; update `generate_character_pages` and `generate_location_pages` call sites
- `tests/unit/test_wiki_generation.py` — add unit tests for `_build_pre_story_excerpt` and verify the integration call site

---

### Task 2: Update `generate_character_page.md` prompt for pre-story framing

**Type:** backend (prompt)
**Estimated scope:** small
**Dependencies:** Task 1

**Description:**

Update `prompts/wiki/generate_character_page.md` to:

1. Rename the template variable from `{outline_excerpt}` to `{pre_story_context}` so the prompt name matches what the code now passes. (The code change in Task 1 updates the variable name; this task makes the prompt consistent.)
2. Add an explicit framing rule: *"Describe this character only as they exist at the **opening** of the story, before any story events occur. Do not describe events that will happen during the story."*
3. Reword the field descriptions:
   - `L3_current_state` → describe the character's condition *at story opening*.
   - `L3_growth_arc` → describe the trajectory and potential arc *inferred from initial conditions* (goals, flaws, pressures) — not events that will unfold.
   - `L3_relationships` → relationships as they stand *at story start*.
4. Update the `Rules` section to add: "All fields describe the character's pre-story state. Do not reference events from the story arc."

This is a prompt-only change; no Python code changes needed in this task.

**Acceptance Criteria:**

- [ ] `{pre_story_context}` is the template variable in the prompt (was `{outline_excerpt}`).
- [ ] A clear rule in the `Rules` section states: "Describe the character only as they exist at the story's opening. Do not describe story events."
- [ ] `L3_current_state`, `L3_growth_arc`, and `L3_relationships` field descriptions reflect pre-story framing.
- [ ] The prompt still produces a valid JSON object matching the existing required-key schema (no keys added or removed).

**Key Files:**

- `prompts/wiki/generate_character_page.md` — variable rename + framing rules

---

### Task 3: Update `generate_location_page.md` prompt for pre-story framing

**Type:** backend (prompt)
**Estimated scope:** small
**Dependencies:** Task 1

**Description:**

Apply the same treatment to `prompts/wiki/generate_location_page.md`:

1. Rename `{outline_excerpt}` → `{pre_story_context}`.
2. Add explicit rule: *"Describe this location only as it exists at the **opening** of the story, before any story events alter it."*
3. Reword `L3_current_state` field description to indicate opening/pre-story condition.
4. Add to `Rules`: "All fields describe the location's pre-story state. Do not describe changes that will occur during the story."

**Acceptance Criteria:**

- [ ] `{pre_story_context}` is the template variable (was `{outline_excerpt}`).
- [ ] A clear rule states the pre-story-only constraint.
- [ ] `L3_current_state` description reflects opening condition.
- [ ] JSON schema (required keys) is unchanged.

**Key Files:**

- `prompts/wiki/generate_location_page.md` — variable rename + framing rules

---

### Task 4: Lint, type-check, and confirm tests pass

**Type:** backend
**Estimated scope:** small
**Dependencies:** Tasks 1, 2, 3

**Description:**

Run the full quality gate:

```bash
ruff check --fix . && ruff format . && mypy src/ && pytest tests/unit/ -v
```

Fix any ruff or mypy issues introduced by Tasks 1–3. Confirm all existing unit tests pass alongside the new tests added in Task 1.

**Acceptance Criteria:**

- [ ] `ruff check` reports zero errors.
- [ ] `mypy src/` reports zero errors.
- [ ] `pytest tests/unit/ -v` reports all tests passing, including new tests from Task 1.

**Key Files:**

- `src/tools/wiki_generation.py`
- `tests/unit/test_wiki_generation.py`
