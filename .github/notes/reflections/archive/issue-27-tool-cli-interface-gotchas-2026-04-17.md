---
date: "2026-04-17"
issue: 27
pr: 87
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: archived
---

## Tool CLI interface gotchas — four mandatory-field and no-save surprises

### Finding

During issue #27 (Task 25: End-to-End Integration Test with Wiki), several tool invocations produced unexpected errors or silently did the wrong thing due to undocumented CLI interface constraints. These were discovered through integration test failures, not through code review.

### Observations

**1. `wiki-update append-timeline` — three mandatory fields**

`append-timeline` requires `time`, `chapter`, AND `description` — all three are mandatory. Omitting any one produces an error. The `chapter` field is easy to forget because the other wiki-update subcommands don't require explicit chapter references.

**2. `wiki-lint check-chapter --chapter-text` — path security constraint**

The `--chapter-text` argument must be a path to a real file (not inline text), and that path must be within `STORIES_DIR` (enforced by the `is_relative_to` security check). Attempting to pass a path outside `STORIES_DIR`, or a path to a non-existent file, raises a validation error. The chapter text must be written to a temp file inside the story's directory first.

**3. `character-mgr generate-sheet` and `setting-mgr generate-sheet` — storage-only**

These subcommands write a character/setting sheet JSON to disk but do NOT call the LLM to generate content. They are storage-only operations. Content generation requires a separate direct LLM call first (e.g., via a character-writer or setting-writer prompt), and then the resulting content is passed to `generate-sheet` for persistence.

**4. `scene-writer assemble-chapter` — no implicit savepoint**

`assemble-chapter` assembles scenes into a chapter file but does NOT create a savepoint. After calling `assemble-chapter`, an explicit `savepoint-mgr save` call is required to checkpoint the story state. Assuming the chapter assembly auto-saves is a silent data-loss risk.

### Suggested Improvement

Add these four entries to `.github/notes/gotchas.md` when it is created (per issue #7 reflection). IDs for the `conventions` ChromaDB collection:

- `gotcha-wiki-update-timeline-mandatory-fields-001`
- `gotcha-wiki-lint-chapter-text-path-constraint-002`
- `gotcha-character-setting-mgr-storage-only-003`
- `gotcha-scene-writer-assemble-no-savepoint-004`

### Action Taken

Applied: added all four gotchas to `.github/notes/gotchas.md` (newly created).
