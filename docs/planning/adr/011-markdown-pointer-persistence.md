# ADR 011: Markdown-Pointer Persistence Convention

**Date:** 2026-05-03
**Status:** Proposed

## Context

The pipeline persists generated long-form prose inside JSON fields
(`character.sheet`, `setting.chunks.*`, `recap.events`, `outline.summary`,
`state.story_prompt`) and, in one observed case
(`outline.enrichment_suggestions`), wraps a JSON payload inside a markdown
fenced code block that is itself embedded as a string inside another JSON
file — three levels of nested escaping. Both shapes are antipatterns:

- Markdown content stored as JSON-string values is unreadable in editors
  and PR diffs (every newline becomes `\n`, every quote escaped).
- JSON content stored as fenced markdown inside a JSON string requires two
  parses to recover and is easy to corrupt on round-trip.

The wiki memory subsystem (ADR 004) already stores its content as `.md`
files with YAML frontmatter, separating structured metadata from
free-text body. We adopt the same pattern across the rest of the
pipeline's persisted state.

## Decision

Two rules:

1. **Markdown content lives in `.md` files.** A field counts as markdown
   content if it contains paragraph breaks, headings, fenced code blocks,
   or exceeds 500 chars of free text. JSON values referencing a markdown
   body use a pointer object: `{"$ref": "<relative-path>"}`. Path is
   relative to the story root.

2. **Structured payloads are persisted as JSON, never as markdown-wrapped
   JSON.** If an LLM emits a `` ```json `` block, the writer parses it
   and persists the parsed structure as a JSON sub-document or its own
   JSON file referenced by path.

Read access is always mediated by `read_markdown_ref`, which during the
transition window also accepts legacy inline-string content. After the
migration script runs against every committed story, the fallback is
removed and `read_markdown_ref` rejects raw strings.

## Consequences

### Positive

- Markdown bodies are editable in any editor without escape contortions.
- PR diffs of generated content are line-by-line readable.
- Single source of truth: the markdown is on disk in one place; JSON
  carries only the pointer.
- Matches the existing wiki convention (ADR 004); contributors learn one
  rule that applies everywhere.
- `enrichment_suggestions`-style triple-nested escaping is impossible by
  construction.

### Negative

- One additional file write per LLM call (markdown body alongside JSON
  metadata). Disk cost is negligible vs. LLM latency.
- Stories now have many more small `.md` files; users browsing the
  filesystem see a denser tree (mitigated by per-entity subdirectories
  e.g. `characters/<slug>/chunks/`).
- One-shot migration must run against every existing committed story
  before the legacy read fallback can be removed.

### Neutral

- Pointer shape `{"$ref": "..."}` borrows from JSON Schema / OpenAPI
  vocabulary, so external tooling already understands it.
- ChromaDB indexed text is unaffected — embeddings are computed from the
  resolved markdown body, not from the on-disk format.
