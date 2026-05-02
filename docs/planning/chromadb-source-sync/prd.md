# PRD: ChromaDB Source-Sync Awareness for Editable Markdown

> Treat indexed markdown as a derived view of on-disk source files. Track source path + content fingerprint per indexed document so any out-of-band edit (user manual edit, external tool, git checkout) is detected and the index is refreshed before the stale embedding is used in retrieval.

**Date:** 2026-05-03
**Author:** Planner agent
**Status:** Draft

## Problem Statement

ChromaDB collections (`wiki-<story>`, `stories-<story>`) are populated by
the pipeline at write time. The indexed `documents` value is a snapshot of
the markdown body at the moment the LLM produced it. After indexing, two
things can drift the source:

1. **User hand-edits.** The whole point of the markdown-pointer convention
   (ADR 011) is that a human can open `characters/yara-osei/sheet.md`,
   rewrite a paragraph, and save. The pipeline never re-indexes that page
   unless the LLM happens to touch it again, so retrieval continues to
   surface the LLM's stale wording.
2. **External tools / git operations.** A `git checkout` to a different
   branch swaps the on-disk markdown but leaves the embedding from the
   previous branch in place; subsequent retrieval mixes branches.

Today neither failure surfaces — the upsert path stores `name`, `slug`,
`type`, `confidence`, `first_appearance` on `wiki-<story>` and `story`,
`content_type`, `doc_id`, `chapter_num` on `stories-<story>`, but no
source-of-truth pointer (path) and no fingerprint (mtime or content hash).
Reads cannot distinguish "this embedding matches the current file" from
"this embedding was correct three commits ago".

## Goals

1. Every indexed document carries enough metadata to answer "is this entry
   stale relative to its source file?" deterministically and cheaply.
2. The retrieval path checks staleness before returning embeddings; stale
   entries are refreshed (re-embedded from current source) before use.
3. A standalone reconcile command rebuilds a collection by walking the
   source filesystem — useful for first-time setup, branch switches, or
   recovery after a manual edit binge.
4. Reconcile is idempotent and incremental: unchanged documents are not
   re-embedded.
5. Backfill the existing two stories on disk without a wipe-and-rebuild.

## Non-Goals

- Live filesystem watching. We refresh **on read** (lazy) and on
  **explicit reconcile** (eager). No `inotify` / `watchdog` daemon.
- Tracking edits inside JSON state files. Those are the pipeline's own
  data; the user is not expected to hand-edit them. ADR 011 plus this
  PRD only address `.md` source files indexed into ChromaDB.
- Cross-collection sync (e.g. cascading character sheet edits to
  per-chapter recap embeddings). Each indexed doc is responsible for its
  own source.
- Embedding model versioning. If we change embedding models that's a
  full rebuild and out of scope here.
- Cross-branch / multi-user coordination. Single-user, single-checkout
  semantics.

## User Stories

### Story author

- As a user, I edit `characters/yara-osei/sheet.md` to rewrite her
  backstory. On the next pipeline run (or RAG query), retrieval reflects
  my edit, not the LLM's old wording.
- As a user, I switch to a different git branch. Running
  `story-writer rag reconcile --story X` rebuilds stale entries; running
  a query without reconcile auto-refreshes touched entries on first hit.
- As a user, I want a `--dry-run` option on reconcile so I can preview
  what would be re-embedded.

### Pipeline author / contributor

- As a contributor, the wiki maintainer agent should not need to track
  staleness manually — the index helper does it on every read.
- As a contributor, when I add a new collection type, I want the same
  source-pointer + fingerprint metadata applied automatically by the
  helper, not duplicated by hand.

## Proposed Solution

### Metadata extension

Every indexed document carries three new metadata fields:

| Key             | Type     | Meaning |
| --------------- | -------- | ------- |
| `source_path`   | `str`    | Relative path from workspace root to the source markdown file. |
| `source_mtime`  | `float`  | `stat().st_mtime` of the source file at index time. |
| `source_sha256` | `str`    | SHA-256 of the source file contents at index time, hex digest. |

`source_mtime` is the cheap-fast comparison; `source_sha256` is the
authoritative one. Most reads use mtime only; sha256 is checked when
mtime indicates change (covers git-checkout case where mtime can lie or
match across branches), and is the canonical record.

### Indexing helper

Add `src/tools/_chroma_sync.py` exposing:

- `upsert_from_source(collection, doc_id, source_path, extra_metadata) -> None`
  — reads the file, computes mtime + sha, calls `collection.upsert`.
  Replaces direct `collection.upsert` calls in `wiki_update.py` and
  `rag_query.py` for any document whose body comes from a markdown file.
- `is_stale(collection, doc_id) -> bool` — fetches the entry's metadata,
  compares against current file mtime; if mtime changed, falls through
  to sha256 comparison; returns True when content hash differs.
- `refresh_if_stale(collection, doc_id) -> bool` — atomic refresh; returns
  True when an upsert was performed.
- `reconcile_collection(collection, source_dir) -> ReconcileReport` —
  full sweep: enumerate source files, compare against indexed entries,
  upsert-changed and delete-orphaned, return a report.

### Retrieval-side check

`wiki_snapshot.py`, `wiki_search.py`, and `rag_query.py` (the three
query-side callers) call `refresh_if_stale` for every doc-id returned by
a `query` / `get` before returning results to the caller. Cost is
bounded by `n_results`; a typical query returns ≤10 ids, so we do at
most 10 stat() calls and 0–10 sha256 reads of small files.

To keep the latency cheap when nothing has changed, the helper short-
circuits on mtime equality without reading the file body.

### Reconcile CLI

`story-writer rag reconcile --story <name> [--collection <wiki|rag>] [--dry-run]`
walks every source file under `stories/<name>` (filtered by the
collection's source-dir convention) and reconciles. Output is the
`ReconcileReport` (added/updated/deleted/unchanged counts + per-doc
log lines). Idempotent.

### Backfill

A one-shot `story-writer rag reconcile --all` rebuilds every existing
collection's metadata. Documents whose body matches the source remain;
documents that lost their source are deleted; documents whose source
changed are re-embedded.

### What about doc-ids whose source isn't a single file?

Some `stories-<story>` entries (chapter prose snippets, outline chunks)
do not map 1:1 to a single source file but to a slice of one. Two
sub-cases:

- **Chunk of a known file** (e.g. recap section). Helper accepts
  `source_path` + optional `source_anchor` (key/heading); fingerprint is
  the sha256 of the resolved slice, not the whole file. Mtime still
  comes from the file.
- **Synthetic content with no source file** (rare; legacy upsert paths
  that pass raw strings). Helper falls back to `source_path = None` and
  records only a content sha256 of the supplied body. These entries
  cannot go stale via source edit; they are refreshed only when the
  pipeline re-upserts.

### Backward compatibility

Entries indexed before this change have no `source_path`. The helper
treats missing fields as "unknown source — re-embed on next pipeline
write, do not touch on read". Reconcile re-embeds them with full
metadata.

## Acceptance Criteria

- [ ] `_chroma_sync.upsert_from_source`, `is_stale`, `refresh_if_stale`,
      `reconcile_collection` exist with type hints and unit tests
- [ ] All wiki-page upserts go through `upsert_from_source` (or a tiny
      wrapper) and record `source_path`, `source_mtime`, `source_sha256`
- [ ] All `stories-<story>` upserts whose body originates from a known
      file do the same; synthetic entries explicitly record
      `source_path: null`
- [ ] `wiki_search`, `wiki_snapshot`, `rag_query` call `refresh_if_stale`
      on returned ids before returning
- [ ] A test that hand-edits a wiki markdown file and then issues a
      query asserts the retrieved document body matches the edited file
- [ ] `story-writer rag reconcile --story X` exists, is idempotent, and
      its `--dry-run` mode never writes
- [ ] Reconcile correctly deletes orphaned entries (markdown file
      removed) and updates entries whose sha differs
- [ ] Existing entries without metadata fields load without errors;
      reconcile upgrades them
- [ ] No regression on the happy-path index/query end-to-end test

## Open Questions

- Should a stale-detection on read also bump a counter / log line for
  observability? Probably yes, gated behind a debug flag — defer.
- For the chunk-of-file case, do we standardise the anchor format
  (heading slug vs. byte range)? Plan: heading-slug for human-readable
  source spans (recaps, outline summaries); revisit only if a chunk
  needs sub-heading granularity.
- Does the migration from PRD "Separate Markdown From JSON" affect the
  source_path layout? Yes — pointer paths land first, then this PRD
  uses those same paths. Sequence in the task list.

## Related

- ADR 004 — progressive wiki memory system
- ADR 011 (proposed, this session) — markdown-pointer persistence —
  defines the `.md` source layout this PRD relies on
- ADR 010 (proposed, this session) — granular checkpointing — orthogonal,
  no direct dependency
