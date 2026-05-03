# ADR 012: ChromaDB Source-Sync Metadata

**Date:** 2026-05-03
**Status:** Accepted — initial implementation landed for Tasks 1 and 2 in issue #324 / PR #336

## Context

ChromaDB collections (`wiki-<story>`, `stories-<story>`) hold embeddings of
markdown bodies that originate as on-disk `.md` files (per ADR 011).
Those source files are user-editable: the whole point of the markdown-
pointer convention is that authors can hand-edit a character sheet, a
chunk, a recap. Today indexed entries store `name`, `slug`, `type`,
`confidence`, etc. — but no source pointer and no fingerprint, so:

- A user edit to a `.md` file does not invalidate the corresponding
  embedding. Retrieval surfaces stale wording until the LLM re-touches
  the entity.
- A `git checkout` to a different branch leaves embeddings from the
  previous branch in place. The index silently mixes branches.
- There is no way to ask "is this entry consistent with its source?".

We need a deterministic, cheap-to-check answer to that question, applied
both lazily (on read) and eagerly (on a reconcile command).

Two adjacent options were considered:

1. **Inotify / watchdog daemon.** Watches `stories/` for changes and
   re-embeds proactively. Rejected: adds a long-lived process, complicates
   the CLI-only deployment model, fights with git operations that touch
   many files at once.
2. **Cache-bust on any `.md` write by the pipeline.** Already what the
   pipeline does, but does not cover hand-edits or git checkouts which
   are the failure modes.

## Decision

Adopt a **per-document fingerprint + source-pointer** metadata contract
on every indexed document, with **lazy refresh on read** and **eager
reconcile on demand**.

Three new metadata fields on every entry:

- `source_path` — workspace-relative path to the source `.md` file (or
  empty for synthetic content with no file backing).
- `source_mtime` — `stat().st_mtime` at index time. Cheap fast-path.
- `source_sha256` — content hash at index time. Authoritative.

Read paths call `refresh_if_stale(collection, doc_id)` before returning
results. Stale = mtime changed AND sha differs. Refresh re-reads the
file and upserts.

A `story-writer rag reconcile` CLI walks the source tree and reconciles
the whole collection, idempotently.

The contract is enforced by a single helper module `_chroma_sync.py`;
direct `collection.upsert` calls for source-backed content are
disallowed.

## Implementation Status

Issue #324 / PR #336 landed the foundational helper module plus wiki-write
site adoption:

- `src/tools/_chroma_sync.py` now provides `ReconcileReport`,
  `compute_fingerprint()`, `upsert_from_source()`, `is_stale()`,
  `refresh_if_stale()`, and `reconcile_collection()`.
- `src/tools/wiki_update.py` now routes wiki-page ChromaDB writes through
  `upsert_from_source()` and records `source_path`, `source_mtime`, and
  `source_sha256` for wiki pages.

Read-side refresh hooks, reconcile CLI wiring, and broader `stories-<story>`
upsert migration remain follow-on work from the PRD task list.

## Consequences

### Positive

- Hand-edits to `.md` files take effect on the very next query without
  any pipeline run.
- Git branch switches no longer poison the index.
- Single helper API → contributors cannot accidentally bypass the
  contract for new collection types.
- Lazy refresh keeps cost proportional to query traffic on changed
  files; mtime fast-path means unchanged data is essentially free.
- Reconcile gives users a one-shot recovery / first-time-setup tool.

### Negative

- Two extra metadata writes per upsert. Negligible.
- Read latency: per returned id, one `stat()` call (cheap) and, when
  mtime differs, one file read + sha256 (cheap for the small markdown
  files we deal with — typically < 50 KB).
- For chunk-of-file documents, fingerprint must be over the resolved
  slice, not the whole file, or false positives cascade. Helper takes
  an optional anchor parameter.
- Synthetic entries (raw-string upserts with no file source) become a
  special case: `source_path = ""`, refresh-on-read is a no-op. Acceptable
  since these will increasingly be rare under ADR 011.

### Neutral

- No background process. Refresh is purely transactional with reads or
  explicit reconcile.
- Embedding model versioning is out of scope; if we change models we
  rebuild collections.
- Multi-user / multi-checkout coordination is out of scope; reconcile
  is the user's tool for "make this checkout consistent".
