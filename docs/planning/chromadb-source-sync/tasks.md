# Task Breakdown: ChromaDB Source-Sync Awareness

> Implements [PRD](./prd.md)

**Date:** 2026-05-03

Sequencing: helpers → write-site conversion → read-site refresh hook
→ reconcile CLI → backfill. **Depends on the markdown-pointer plan
(separate-markdown-from-json/) landing first** because
`source_path` references the new on-disk markdown locations defined
there.

## Tasks

### Task 1: Add `_chroma_sync` helper module

**Status:** Implemented in issue #324 / PR #336

**Type:** backend
**Estimated scope:** small
**Dependencies:** none (logically depends on separate-markdown-from-json
Task 1, but helper itself is independent)

**Description:**
Create `src/tools/_chroma_sync.py` with:

- `compute_fingerprint(path: Path) -> tuple[float, str]` — returns
  `(mtime, sha256-hex)`.
- `upsert_from_source(collection, doc_id, source_path, extra_metadata,
  body=None) -> None` — reads file (or uses passed-in body), computes
  fingerprint, upserts with `source_path`, `source_mtime`,
  `source_sha256` injected into metadata.
- `is_stale(collection, doc_id) -> bool` — mtime-fast-path then
  sha256.
- `refresh_if_stale(collection, doc_id) -> bool` — performs the
  upsert when stale.
- `reconcile_collection(collection, source_root, glob_pattern,
  doc_id_from_path) -> ReconcileReport` — sweep.

`ReconcileReport` is a small dataclass with `added`, `updated`,
`deleted`, `unchanged` counts and a `log: list[str]`.

**Acceptance Criteria:**

- [x] All five helpers exist with type hints
- [x] Round-trip tests: index → modify file → `is_stale` returns True
- [x] Mtime-equal-but-content-differs test (touch + content change)
      caught by sha fallback
- [x] Path traversal rejected on `source_path` inputs
- [x] No path = `None` case stores `source_path` as the JSON-null-
      compatible empty string `""` (chroma metadata constraint) and
      `is_stale` returns False for those entries

**Key Files:**

- `src/tools/_chroma_sync.py`
- `tests/unit/test_chroma_sync.py`

---

### Task 2: Convert wiki upserts to use `upsert_from_source`

**Status:** Implemented in issue #324 / PR #336

**Type:** backend
**Estimated scope:** small
**Dependencies:** Task 1, separate-markdown-from-json Task 3 (for stable
on-disk wiki page paths — already correct shape per ADR 004 so OK to
land in parallel)

**Description:**
Replace `_upsert_to_chromadb` in `src/tools/wiki_update.py` with a call
to `upsert_from_source`, passing the wiki page's `.md` source path.
Existing metadata (`name`, `slug`, `type`, etc.) flows in via
`extra_metadata`.

**Acceptance Criteria:**

- [x] Every wiki page upsert records `source_path`, `source_mtime`,
      `source_sha256`
- [x] `_upsert_to_chromadb` is removed or becomes a thin wrapper
- [x] Test: upsert a page → modify the source file → `is_stale` True

**Key Files:**

- `src/tools/wiki_update.py`
- `tests/unit/test_wiki_update.py`

---

### Task 3: Convert `stories-<name>` upserts to use `upsert_from_source`

**Type:** backend
**Estimated scope:** medium
**Dependencies:** Task 1, separate-markdown-from-json Tasks 3–7

**Description:**
Refactor `cmd_index` in `src/tools/rag_query.py` and any other
`stories-<name>` upsert sites so that:

- When the indexed body originates from a known `.md` file (sheet,
  chunk, recap, outline summary), pass `source_path` and let the
  helper compute the fingerprint.
- When the body is synthetic (legacy raw-string), the helper records
  `source_path = ""` and the body's own sha; entry is treated as
  not-stale-on-read.

**Acceptance Criteria:**

- [ ] All known-source upserts carry the three new metadata fields
- [ ] Synthetic entries explicitly record empty `source_path`
- [ ] CLI `story-writer rag index` accepts `--source-path`; if
      omitted, content is treated as synthetic

**Key Files:**

- `src/tools/rag_query.py`
- `tests/unit/test_rag_query.py`

---

### Task 4: Read-side `refresh_if_stale` hook in query paths

**Type:** backend
**Estimated scope:** small
**Dependencies:** Tasks 2, 3

**Description:**
In `src/tools/wiki_search.py`, `src/tools/wiki_snapshot.py`, and
`rag_query.cmd_query`, after the `query` / `get` returns, iterate the
returned ids and call `refresh_if_stale` before returning the result
to the caller. Re-fetch any refreshed ids so the caller sees the
fresh body.

**Acceptance Criteria:**

- [ ] Stale entries detected and refreshed transparently in all three
      read paths
- [ ] Test that hand-edits a markdown source then queries returns the
      edited content
- [ ] No latency regression > a few ms when no entries are stale
      (mtime-fast-path)

**Key Files:**

- `src/tools/wiki_search.py`
- `src/tools/wiki_snapshot.py`
- `src/tools/rag_query.py`
- `tests/unit/test_chroma_sync_read_paths.py`

---

### Task 5: `story-writer rag reconcile` CLI

**Type:** backend
**Estimated scope:** medium
**Dependencies:** Tasks 2, 3

**Description:**
Add a `reconcile` subcommand under `story-writer rag` that walks the
specified collection's source root and runs `reconcile_collection`.
Flags:

- `--story <name>` — required
- `--collection <wiki|rag>` — defaults to both
- `--dry-run` — print the report, do not write
- `--all` — reconcile every story under `stories/`

Output is the `ReconcileReport` rendered as text + JSON.

**Acceptance Criteria:**

- [ ] CLI exists and is documented in `docs/manual.md` and
      `docs/tools.md`
- [ ] Idempotent: second invocation reports zero changes
- [ ] `--dry-run` writes nothing
- [ ] Orphan deletion works (file removed → entry removed)

**Key Files:**

- `src/tools/rag_query.py` (or new `src/tools/rag_reconcile.py`)
- `src/presentation/cli/main.py`
- `docs/manual.md`
- `docs/tools.md`
- `tests/unit/test_rag_reconcile.py`

---

### Task 6: Backfill existing committed stories

**Type:** backend (one-shot)
**Estimated scope:** small
**Dependencies:** Task 5

**Description:**
Run `story-writer rag reconcile --all` against the two committed stories
(`the-silence-between-the-stars`, `breaking-amy`) and commit the
resulting `.chromadb/` updates if the index is checked in (it is git-
ignored — confirm and document either way). If `.chromadb/` is ignored,
this task is the verification step that reconcile produces a clean
report from a fresh checkout.

**Acceptance Criteria:**

- [ ] Reconcile run on both stories completes without errors
- [ ] Subsequent reconcile reports zero changes
- [ ] If `.chromadb/` is committed, the diff is reviewed and committed

**Key Files:**

- `.chromadb/` (verify gitignore status)
- (no source changes)

---

### Task 7: Document the source-sync model

**Type:** backend (docs)
**Estimated scope:** small
**Dependencies:** Tasks 1–5

**Description:**
Add a section to `.github/instructions/chromadb.instructions.md`
explaining: required metadata fields, when read-side refresh kicks in,
when to run reconcile, idempotence guarantees. Update the `chromadb-ops`
skill (`.github/skills/chromadb-ops/SKILL.md`) to reference the helper
module.

**Acceptance Criteria:**

- [ ] Instructions file documents `source_path`/`source_mtime`/
      `source_sha256` contract
- [ ] Skill SKILL.md points contributors at `_chroma_sync` helpers
      rather than direct `collection.upsert` calls

**Key Files:**

- `.github/instructions/chromadb.instructions.md`
- `.github/skills/chromadb-ops/SKILL.md`

---

### Task 8: Integration test — end-to-end edit-and-retrieve

**Type:** backend (integration)
**Estimated scope:** small
**Dependencies:** Tasks 1–5

**Description:**
Add `tests/integration/test_chroma_source_sync.py`:

- Run a tiny pipeline run against a fixture story (or pre-seed
  collections directly).
- Hand-edit a wiki page's `.md` file.
- Query via `wiki_search` and assert the returned body matches the
  edited file.
- Hand-delete a `.md` file; run `reconcile`; assert the entry is
  gone.
- Re-run reconcile; assert the report is empty.

**Acceptance Criteria:**

- [ ] Test exists and passes
- [ ] No reliance on a live LLM (uses pre-built collections /
      fixtures)

**Key Files:**

- `tests/integration/test_chroma_source_sync.py`
- `tests/fixtures/`
