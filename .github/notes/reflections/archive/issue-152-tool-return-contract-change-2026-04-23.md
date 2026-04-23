---
date: "2026-04-23"
issue: 152
pr: 153
category: instruction
targets:
  - ".github/agents/_shared/review-checklist.md"
severity: minor
status: archived
---

## Tool return-contract change requires agent call-site sweep (distinct from parameter-signature changes)

### Finding

PR #153 changed `scene-writer` operations `generate`, `revise`, and `assemble-chapter` so
they return a compact savepoint reference by default (`{scene_ref, char_count,
savepoint_step}`) with full prose only when `includeContent: true` is passed. No Zod field
was added or made required, so the existing "API signature changes" and "TS Zod schema
required-field" caller-sweep triggers in `review-checklist.md` did not fire. All three
review models (Claude, GPT, Gemini) unanimously identified that `final-editor.md` and
`prose-scrubber.md` still instructed the LLM to "replace the in-memory chapter text with
the returned text" after calling `revise`. With the new default return shape, that
instruction silently writes a compact reference JSON to `current_chapter_text` and
persists it as the chapter body — silent state corruption that propagates to recap,
wiki, and final assembly. Claude additionally found `quality-reviewer.md` with the
identical pattern, and flagged `chapter-writer.md` step 8 as lacking an explicit
prose-retrieval step after the `assemble-chapter` return-shape change.

Related but separate findings from the same synthesis:

- `gotchas.md` entry #005 explicitly described the previous behaviour ("assemble-chapter
  creates no savepoint") which this PR fixes by adding an automatic savepoint. The
  gotcha became a false authoritative statement that would mislead future agents into
  making redundant saves. The PR did not update it until review surfaced the drift.
- The TS wrapper Zod `.describe()` text for `sceneContent` still read "required for
  revise" even though the Python backend now auto-loads from savepoint when omitted.
  Zod descriptions are live documentation consumed by the LLM at call time.

### Observation

Three distinct review-checklist gaps:

1. **Return-contract change trigger is missing.** The existing Phase 2 "API signature
   changes" bullet reads "if a function, method, or constructor signature changed
   (parameter added/removed/renamed)" — framed entirely around *inputs*. It does not
   cover the case where the *return shape* changes (e.g. full content → compact
   reference, single value → dict, list → paginated object). Callers that literally
   consume the return value break silently when the shape narrows, and agent
   instruction files are the most vulnerable because they encode the consumption
   pattern in English prose ("assign the returned text to X"). There is no existing
   trigger for reviewers to grep agent files when a tool's default return shape
   changes.

2. **Stale gotcha after fix-PR is not explicitly checked.** Phase 7 has
   "Code matches docs" but nothing directs reviewers to grep `.github/notes/gotchas.md`
   when a PR fixes a previously-documented gotcha. `gotchas.md` is loaded by the
   planning/debugging agents as a live knowledge source; a stale entry is an active
   hazard, not passive debt.

3. **Zod `.describe()` semantic drift is not covered.** The existing
   "Code matches docs" bullet is targeted at `.md` documentation. TS wrapper
   `.describe(...)` strings are not `.md` but are effectively documentation surfaced
   to the LLM. When Python backend semantics change (required → optional, shape
   narrowed), the matching Zod description string must be swept. This is adjacent to
   the existing issue #117 "TS wrapper / Python CLI sync" lesson but focused on the
   description text rather than the schema itself.

### Suggested Improvement

**`review-checklist.md` Phase 2 General section — extend the "API signature changes"
item** to include return-contract changes:

> **Also applies to tool return-contract changes:** if a tool's default return shape
> changes (e.g. full content → compact reference, fields added/removed/renamed in the
> returned dict, list → paginated object), grep all agent instruction files for
> invocations of the tool (`grep -rn 'tool-name' .opencode/agents/ .opencode/skills/`)
> and audit each call site's post-call handling. Agent instructions that consume the
> return value in English prose ("assign the returned text to X", "the tool returns
> Y") silently continue to run after a return-shape narrowing and persist the wrong
> value to state. Verify each call site either (a) passes the opt-in flag that
> preserves the old shape (e.g. `includeContent: true`), or (b) follows the new
> shape — loads from savepoint, reads the expected nested field, etc. (Source:
> issue #152, PR #153 — `scene-writer` `revise`/`assemble-chapter` switched to
> compact refs by default; three agent call sites consumed the old shape and would
> have written reference JSON into chapter state as prose.)

**`review-checklist.md` Phase 7 Documentation Review — add two bullets:**

- **Gotcha entries superseded by the PR** — if this PR implements or fixes a behaviour
  that is described in `.github/notes/gotchas.md`, verify the matching entry has been
  updated or removed and any ChromaDB-indexed copy is reindexed. Gotchas are an
  authoritative live knowledge source consulted by planning and debugging agents;
  a stale entry after a fix-PR misleads agents into defensive workarounds that the
  new implementation does not need. (Source: issue #152, PR #153 — `gotchas.md`
  entry #005 still warned about the missing auto-savepoint that the PR added.)
- **Zod `.describe()` text reflects current semantics** — for any TS tool wrapper
  whose Python backend changed parameter semantics (required ↔ optional, default
  value, conditional validation, auto-load behaviour), verify the corresponding
  Zod field `.describe(...)` string in `.opencode/tools/*.ts` has been updated. The
  description is surfaced to the LLM at call time and becomes part of the tool
  contract; a stale description causes over-specification or misuse even when the
  schema itself is correct. (Source: issue #152, PR #153 — `sceneContent` Zod
  description said "required for revise" after the backend was changed to
  auto-load from savepoint when omitted.)

### Action Taken

Applied: all three additions to `.github/agents/_shared/review-checklist.md` (one Phase 2
extension, two Phase 7 bullets). Changes preserve existing formatting and cite
issue #152 / PR #153 as the source.
