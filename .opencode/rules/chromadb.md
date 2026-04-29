---
globs: ["src/**/*.py"]
---
<!-- Source: .github/instructions/chromadb.instructions.md — keep in sync -->

# ChromaDB — Agent Reference


ChromaDB is a **derived semantic index** over the authoritative Markdown knowledge base in `.github/notes/`. Never write to ChromaDB without first writing to the Markdown source.

---

## Collections

| Collection | Scope | Source Files | Managed By |
|------------|-------|-------------|------------|
| **`conventions`** | Gotchas, patterns, architecture, domain | `gotchas.md`, `patterns.md`, `architecture.md`, `domain.md` | Orchestrator, Reflection |
| **`reflections`** | Agent system improvement notes | `.github/notes/reflections/` | Reflection |
| **`audits`** | Audit reports and findings | `.github/notes/audits/` | Contemplator, Synth Auditor, Auditor |
| **`codebase`** | Feature docs, ADRs, skills, modules | `docs/`, `.github/skills/`, `docs/planning/adr/` | Documenter |
| **`tests`** | Test patterns, fixtures, failure learnings | `docs/testing/`, test files | Test Writer |

---

## Metadata Schemas

### `conventions`

| Field | Type | Examples |
|-------|------|---------|
| `category` | string | `gotcha`, `pattern`, `architecture`, `domain` |
| `source_file` | string | `.github/notes/gotchas.md` |
| `severity` | string | `info`, `warning`, `critical` |
| `tags` | string | `"tenancy,security,fillable"` |
| `entry_number` | string | `"19"` |
| `indexed_at` | string | `2026-03-18` |

### `reflections`

| Field | Type | Examples |
|-------|------|---------|
| `issue` | string | `"194"` |
| `severity` | string | `minor`, `major` |
| `category` | string | `agent`, `skill`, `instruction` |
| `target` | string | `.github/skills/e2e-testing/SKILL.md` |
| `status` | string | `active`, `archived` |
| `date` | string | `2026-03-16` |
| `source_file` | string | `.github/notes/reflections/issue-194-….md` |

### `audits`

| Field | Type | Examples |
|-------|------|---------|
| `audit_date` | string | `2026-03-10` |
| `audit_type` | string | `solo`, `synthesis` |
| `confidence` | string | `unanimous`, `supermajority`, `majority`, `singular` |
| `domain` | string | `security`, `architecture`, `testing`, `permissions` |
| `source_file` | string | `.github/notes/audits/2026-03-10-synthesis.md` |

### `codebase`

| Field | Type | Examples |
|-------|------|---------|
| `doc_type` | string | `feature`, `adr`, `skill`, `module`, `planning` |
| `module` | string | `activities`, `core`, `tenancy`, `auth` |
| `phase` | string | `phase-1`, `phase-2`, `interim` |
| `source_file` | string | `docs/features/activities.md` |
| `indexed_at` | string | `2026-03-18` |

### `tests`

| Field | Type | Examples |
|-------|------|---------|
| `test_type` | string | `unit`, `integration`, `e2e` |
| `domain` | string | `auth`, `stories`, `generation`, `permissions` |
| `fixture_type` | string | `user`, `story`, `chapter` |
| `source_file` | string | `tests/unit/test_user_management.py` |
| `indexed_at` | string | `2026-03-18` |

---

## Per-Story Collections

Each story has a dedicated ChromaDB collection named `stories-{story_name}` (e.g. `stories-my-story`). These collections are created automatically by `rag-query` on first index.

| Collection | Name Pattern | Managed By |
|------------|-------------|------------|
| **Per-story RAG** | `stories-{story_name}` | `rag-query` tool (story-orchestrator, wiki-maintainer) |

### Per-Story Collection Metadata Schema

| Field | Type | Examples |
|-------|------|---------|
| `story` | string | `"my-story"` |
| `content_type` | string | `"outline"`, `"chapter"`, `"character"`, `"setting"`, `"wiki"`, `"recap"`, `"raw-chapter"` |
| `doc_id` | string | `"outline"`, `"chapter-1"`, `"character-elena"`, `"chapter-3-raw"` |
| `chapter_num` | integer | `1`, `3` (optional, for chapter-related content) |

### Per-Story Document ID Conventions

| Content Type | ID Pattern | Example |
|-------------|------------|---------|
| `outline` | `outline` | `outline` |
| `chapter` | `chapter-{N}` | `chapter-1` |
| `character` | `character-{slug}` | `character-elena` |
| `setting` | `setting-{slug}` | `setting-northwood-village` |
| `wiki` | `wiki-{slug}` | `wiki-elena-vasquez` |
| `recap` | `recap-chapter-{N}` | `recap-chapter-3` |
| `raw-chapter` | `chapter-{N}-raw` | `chapter-3-raw` |

**`raw-chapter`** — full accepted chapter text embedded after Phase 7g acceptance. Used by `consistency-checker` for cross-chapter factual continuity analysis and by the `character-voice` critic mode for voice sample retrieval.

---

## Document ID Conventions

IDs are stable and slugified. Re-indexing the same source produces the same IDs (upsert behaviour).

| Collection | Pattern | Example |
|------------|---------|---------|
| conventions | `{category}-{slug}-NNN` | `gotcha-config-env-loading-011` |
| conventions | `arch-{slug}` | `arch-clean-architecture-layers` |
| conventions | `domain-{slug}` | `domain-story-generation-flow` |
| reflections | `refl-issue-{N}-{slug}` | `refl-issue-194-e2e-session-reuse` |
| audits | `audit-{date}-{type}-{domain}-NNN` | `audit-2026-03-10-synthesis-security-001` |
| codebase | `{doc_type}-{module}-{slug}` | `feature-activities-rsvp-workflow` |
| codebase | `adr-{number}-{slug}` | `adr-004-module-framework` |
| codebase | `skill-{name}` | `skill-multi-tenancy` |
| tests | `{test_type}-{domain}-{slug}` | `e2e-auth-login-flow` |
| tests | `fixture-{slug}` | `fixture-e2e-tenant-seeding` |

---

## Standard Query Patterns

Use these patterns to query ChromaDB before planning or implementing. Prefer reading from `.github/notes/` for structured data; use ChromaDB for semantic/fuzzy recall.

### Before Planning (Orchestrator, Planner, Contemplator)

```
chroma_query_documents(collection_name="conventions", query_texts=["<feature or fix description>"], n_results=10)
chroma_query_documents(collection_name="reflections", query_texts=["<feature domain>"], n_results=5, where={"status": {"$eq": "active"}})
chroma_query_documents(collection_name="audits", query_texts=["<feature domain>"], n_results=5)
```

### Before Implementing (Coder)

```
chroma_query_documents(collection_name="conventions", query_texts=["<task description>"], n_results=10, where={"$or": [{"category": {"$eq": "gotcha"}}, {"category": {"$eq": "pattern"}}]})
```

### Before Writing Tests (Test Writer)

```
chroma_query_documents(collection_name="tests", query_texts=["<test domain>"], n_results=5)
chroma_query_documents(collection_name="conventions", query_texts=["<feature name> test patterns"], n_results=5)
```

### Before Documenting (Documenter)

```
chroma_query_documents(collection_name="codebase", query_texts=["<feature name>"], n_results=5)
```

### After Writing to .github/notes/

Always embed new knowledge into the appropriate ChromaDB collection using `chroma_add_documents`. See the ID conventions and metadata schemas above. Use `chroma_update_documents` for updates to existing entries.

---

## Standard Write Pattern

After appending knowledge to `.github/notes/`:

1. **Ensure collection exists** — `chroma_create_collection` (idempotent)
2. **Embed** — `chroma_add_documents` with stable ID, metadata, and content
3. **For updates** — `chroma_update_documents` with the same stable ID

```
chroma_add_documents:
  collection_name: "conventions"
  documents: ["Never put tenant_id in $fillable — BelongsToTenant auto-assigns it."]
  metadatas: [{"category": "gotcha", "source_file": ".github/notes/gotchas.md", "severity": "critical", "tags": "tenancy,security,fillable", "entry_number": "19", "indexed_at": "2026-03-18"}]
  ids: ["gotcha-tenant-id-not-fillable-019"]
```

**Constraints:**

- Never write to ChromaDB without first writing to the Markdown source
- Never delete from `conventions` or `reflections` — only update or add
- Always include `source_file` in metadata for traceability
- `indexed_at` = when the entry was last embedded, not when it was authored

## Standard Read Pattern

1. **Query semantically** — `chroma_query_documents` with natural-language description, `n_results: 10`
2. **Filter by metadata** — use `where` clauses when the domain is known
3. **Incorporate results** into the plan or implementation context

```
chroma_query_documents:
  collection_name: "conventions"
  query_texts: ["activity participant tenant scoping policy"]
  n_results: 10
  where: {"$or": [{"category": {"$eq": "gotcha"}}, {"category": {"$eq": "pattern"}}]}
```

## Query Operators

**Metadata filters (`where`):**

```json
{"category": "gotcha"}
{"$and": [{"category": {"$eq": "gotcha"}}, {"severity": {"$eq": "critical"}}]}
{"$or": [{"category": {"$eq": "gotcha"}}, {"category": {"$eq": "pattern"}}]}
```

**Document content filters (`where_document`):**

```json
{"$contains": "tenant_id"}
{"$not_contains": "deprecated"}
```

---

## Chunk Granularity

| Source | Granularity |
|--------|------------|
| `gotchas.md`, `patterns.md` | One document per numbered entry |
| `architecture.md`, `domain.md` | One document per `##` heading |
| `reflections/` | One document per reflection file |
| `audits/` | One document per finding within an audit report |
| `docs/` feature/skill files | One document per `##` section |
| Test files | One document per test class summary |

---

## Bootstrapping

To rebuild the index from scratch:

1. Create all 5 collections — `chroma_create_collection` for each
2. Index `conventions` — parse `gotchas.md` (by entry), `patterns.md` (by `##`), `architecture.md`, `domain.md`
3. Index `reflections` — each file in `.github/notes/reflections/` and `archive/`
4. Index `audits` — each audit report, split by finding
5. Index `codebase` — `docs/features/*.md`, `docs/planning/adr/*.md`, `.github/skills/*/SKILL.md`
6. Index `tests` — `docs/testing.md`, `docs/testing/*.md`, test class summaries

To reindex a single collection: delete it, recreate it, re-run its bootstrap step.
