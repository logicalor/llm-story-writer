# PRD: Separate Markdown From JSON Persistence

> Stop persisting markdown content inside JSON fields. JSON keeps structured metadata + file pointers; markdown lives in its own `.md` files. Stop wrapping JSON inside markdown fenced code blocks; if a value is structured, persist it as JSON.

**Date:** 2026-05-03
**Author:** Planner agent
**Status:** Draft

## Problem Statement

The pipeline writes generated long-form prose into JSON fields and, in some
cases, writes JSON-shaped content as a fenced code block inside a markdown
string that itself lives inside another JSON field. Both directions are
antipatterns: humans cannot edit the markdown without escaping every quote
and newline, diffs are unreadable, and downstream code re-parses
double-encoded blobs to recover usable content.

Concrete instances confirmed during research:

1. **Character sheets** (`stories/<story>/characters/<slug>.json`) embed:
   - `sheet`: a full LLM markdown document including `<output>`, headings,
     bullet lists.
   - `chunks.<key>`: markdown bodies for backstory, personality,
     motivation, relationships, skills, arc, current_state.
   - `abridged`: markdown.
   - `summary`: markdown.
2. **Setting sheets** (`stories/<story>/settings/<slug>.json`) — identical
   shape to character sheets, different chunk keys.
3. **Pipeline state** (`stories/<story>/savepoints/pipeline_state.json`)
   embeds:
   - `outline_result.chapter_outlines[].summary`: markdown with bold field
     labels (`**Characters**: ...`).
   - `outline_result.enrichment_suggestions`: a string containing
     `` ```json … ``` `` — JSON wrapped in markdown wrapped in JSON.
   - `recaps[<n>]`: dict whose `events`, `compact`, `sanitised` fields are
     markdown.
4. **Per-chapter recap files** (`stories/<story>/chapters/chapter_N_recap.json`)
   — same dict-of-markdown shape as `recaps` above.
5. **Story state** (`stories/<story>/state.json`) embeds the full story
   prompt markdown under `story_prompt`.
6. **Live runtime in-memory** (`setting_evolver.py`, prompt handlers)
   re-serialises the same dict-of-markdown blob as a prompt payload, so
   the LLM is repeatedly fed escape-laden JSON instead of the underlying
   markdown.

The cost is real: users cannot hand-edit a character's backstory without
escaping; PR diffs are line-level walls of `\n`; the JSON-wrapped-in-
markdown-wrapped-in-JSON case in `enrichment_suggestions` requires two
parses to recover the structured suggestions, and once re-saved through
the round-trip it is easy to corrupt.

## Goals

1. **No markdown content inside JSON values.** Long-form generated text
   lives in `.md` files; JSON references them by relative path.
2. **No JSON content inside markdown fenced blocks that themselves live
   inside JSON.** If a value is structured, persist it as a JSON file or
   sub-key, not as a fenced code block in a string.
3. Migrations are automated — existing stories on disk upgrade without
   manual editing.
4. Existing stories can be upgraded in one pass before runtime reads.
5. New writes only ever produce the new format.

## Non-Goals

- Replacing the JSON savepoint format with YAML or TOML. JSON stays.
- Splitting every short string out of JSON (titles, slugs, tags stay
  inline). The rule applies to **markdown bodies** (multi-line, contains
  headings or lists or fenced blocks) and to **structured payloads**
  wrapped in code fences.
- ChromaDB schema changes. Indexed text stays as it is; only on-disk
  authoritative storage moves.

## User Stories

### Story author

- As a user, I want to open `characters/<slug>/sheet.md` in any editor
  and rewrite a paragraph, then have the next pipeline run pick up my
  edit, so I can iterate manually without round-tripping through JSON.
- As a user, I want the recap for a chapter to be a readable `.md` file
  next to the chapter prose, so I can skim my story's history without a
  JSON viewer.

### Pipeline author / contributor

- As a contributor, when I add a new generation step, I want a single
  helper that says "write this LLM output as markdown and reference it
  from JSON state" so I cannot accidentally re-introduce the antipattern.
- As a contributor, I want a lint script in CI that scans `stories/` and
  fails if a JSON value contains a fenced code block or a multi-line
  markdown body, so regressions are caught before review.

## Proposed Solution

### Two-rule storage convention

**Rule A — Markdown content lives in `.md` files.** A field counts as
markdown content if any of:

- it contains `\n\n` (paragraph break), or
- it contains a markdown heading (`^#{1,6} `), or
- it contains a fenced code block, or
- it exceeds 500 characters of free text.

When writing such a field, the writer must:

1. Compute a stable relative path inside the story directory, e.g.
   `characters/yara-osei/sheet.md`,
   `characters/yara-osei/chunks/backstory.md`,
   `chapters/chapter_3/recap.md`.
2. Atomic-write the markdown to that path.
3. In the JSON, replace the inline content with a pointer object:
   ```json
   { "$ref": "characters/yara-osei/sheet.md" }
   ```
   Pointers are always relative to the story root. The `$ref` key is the
   single recognised marker (familiar from JSON Schema/OpenAPI).

**Rule B — Structured payloads are persisted as JSON, never as
markdown-wrapped JSON.** If a generation step produces JSON content,
the writer parses it and stores it as a JSON sub-document or its own
JSON file. The string `` ```json `` must never appear inside any
persisted JSON value.

### Helper API

Add `src/tools/_persist.py` with two functions:

- `persist_markdown(story_root: Path, relative_path: str, body: str) -> dict`
  — atomic-writes the body to `story_root / relative_path` and returns
  the pointer dict `{"$ref": relative_path}`.
- `read_markdown_ref(story_root: Path, ref: dict[str, str]) -> str` — resolves
  a pointer dict and returns the markdown body. Raw legacy strings now raise
  `ValueError`, so callers must guard pointer reads explicitly and migrate old
  stories before use.

A small JSON Schema (`src/application/schemas/markdown_ref.json`) defines
the pointer shape so contributors and external tools can validate.

### Per-area changes

- **Character / setting sheets:** the per-entity JSON keeps `name`,
  `aliases`, `updated_at`, and pointer refs for `sheet`, `chunks/<k>`,
  `summary`, `abridged`. Markdown bodies move to
  `characters/<slug>/sheet.md`, `characters/<slug>/chunks/<k>.md`,
  `characters/<slug>/summary.md`, `characters/<slug>/abridged.md`.
- **Outline:** `chapter_outlines[].summary` becomes a pointer to
  `outline/chapter_N_summary.md`. `outline_result.base_context` and
  `outline_result.story_elements` become pointers to
  `outline/base_context.md` and `outline/story_elements.md`. The string-encoded
  `enrichment_suggestions` is parsed once at write time and stored as a
  proper JSON sub-document `outline/enrichment_suggestions.json`,
  referenced from `pipeline_state.json` by path.
- **Recaps:** `chapters/chapter_N_recap.json` keeps `chapter_number`,
  `created_at`, plus pointer refs for `events`, `compact`, `sanitised`.
  `pipeline_state.recaps[N]` is **not** stored inline anymore — it
  stores the same per-field pointer dict shape as the on-disk recap JSON.
- **Story prompt:** `state.json::story_prompt` becomes a pointer to
  `prompt.md` at the story root.
- **Wiki pages:** already correctly stored as `.md` with YAML
  frontmatter; no change needed.

### Migration completion

The transition window is closed. `read_markdown_ref` now accepts pointer
dicts only, and legacy inline strings must be converted before runtime use.
Callers guard pointer reads with `isinstance(ref, dict)` and fall back to
empty or existing non-markdown structured values where appropriate.

A one-shot migration script
(`src/tools/migrate_inline_markdown.py`) walks every story's JSON files,
extracts inline markdown to `.md` files, and rewrites the JSON to use
pointers. The `enrichment_suggestions` JSON-in-markdown case is parsed
out and rewritten as a proper JSON sub-document during the same pass.

### Lint

Add `scripts/lint_no_inline_markdown.py` that scans `stories/` and
fails if any JSON value:

- contains a markdown heading marker, or
- contains `\n\n`, or
- contains `` ``` ``, or
- exceeds 500 chars of free text.

Wire into CI gate. Allow-list a small set of fields explicitly known to
be short single-paragraph descriptions (chapter title, tag list, etc.).

## Acceptance Criteria

- [x] `persist_markdown` and `read_markdown_ref` helpers exist and are
      typed.
- [x] All character-sheet writes produce JSON with pointer refs and
      markdown sibling files.
- [x] All setting-sheet writes do the same.
- [x] Outline persistence (`pipeline_state.json::outline_result`) stores
  chapter summaries, `base_context`, and `story_elements` as pointers,
  and `enrichment_suggestions` as a proper JSON sub-document — no
  fenced `` ```json `` strings remain.
- [x] Per-chapter recap files use pointer refs.
- [x] `state.json::story_prompt` is a pointer to `prompt.md`.
- [x] Migration script converts every existing story under `stories/`
      without data loss; a round-trip read returns identical bodies.
- [x] Lint script flags any reintroduction of inline markdown / fenced
      JSON in stories' JSON files; CI fails when triggered.
- [x] Read-site code rejects legacy inline-format stories with a clear
  migration error, and all pointer-backed callers guard reads.
- [x] No regression in the end-to-end happy path; generated story
      output is byte-identical vs. baseline.

## Open Questions

- Should pointer paths be relative to the story root (proposed) or the
  workspace root? Story root keeps stories self-contained and movable;
  defaulting to that.
- Do we want the migration script to be idempotent (re-running on an
  already-migrated story is a no-op)? Yes — required so users can
  safely run it on all stories without tracking which were done.
- Should the wiki maintainer be in scope here? Wiki already uses `.md`
  files with frontmatter, which is the target shape. Out of scope.

## Related

- ADR 004 — progressive wiki memory system (`.md` + YAML frontmatter is
  the precedent we're matching).
- This session: granular checkpointing PRD — both touch the savepoint
  format; granular-checkpointing tasks should land first so the ledger
  field exists before migration rewrites pipeline_state.json.
