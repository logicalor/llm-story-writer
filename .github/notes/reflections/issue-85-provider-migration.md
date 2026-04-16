---
date: "2026-04-17"
issue: 85
pr: 86
category: agent
targets:
  - ".github/agents/coder.agent.md"
  - ".github/agents/test-writer.agent.md"
severity: major
status: active
---

## Silent exception swallowing in persistent-store write paths — Coder missed critical correctness bug

### Finding

During issue #85 (Replace Ollama SDK with generic OpenAI-compatible provider), the Coder implemented `get_embeddings()` in `OpenAICompatibleEmbeddingProvider` with exception handling that silently returned zero vectors on failure. The original implementation caught exceptions and returned a list of zero-length floats rather than propagating the error. This was not caught by the Coder or Test Writer — it was found in the code review phase instead.

Zero vectors in ChromaDB corrupt the semantic index silently: documents embed without error, but all similarity queries against those entries return meaningless results. This is a data integrity bug with no visible signal at write time.

Secondary findings from the same review:
- **FINDING-007**: `_normalize_base_url()` helper is duplicated verbatim in `openai_compatible_provider.py` and `openai_compatible_embedding_provider.py`. A shared provider utilities module (`src/infrastructure/providers/_utils.py`) would eliminate the drift risk. Follow-up issue needed.
- **FINDING-008**: `_generate_text_non_streaming_no_stats()` is a near-duplicate of `_generate_text_non_streaming()` across `openai_compatible_provider.py`, `lm_studio_provider.py`, and `langchain_provider.py`. Broader refactor required. Follow-up issue needed.

### Observation

The root cause of the silent failure is a well-intentioned but incorrect exception handling strategy: the Coder treated the embedding provider as a best-effort utility (analogous to a logger) rather than a required data pipeline step. In ChromaDB contexts, every embedding write must either succeed or raise — there is no safe degraded mode.

The missing error-path tests also meant this class of bug had no automated safety net. Provider tests covered the happy path only; no tests exercised HTTP 5xx responses, malformed API payloads, or partial failures in batch embedding calls.

This is a new variant of the exception-swallowing anti-pattern specific to infrastructure adapters that write to persistent stores. It is distinct from the `sys.exit()` in shared utilities pattern (issue #14) and from boundary validation (Coder Rule 9), but shares the same failure mode: errors are silently absorbed, leaving downstream data in a corrupt or undefined state.

### Suggested Improvement (1 of 2) — Coder Rule: Persistent-store write paths must propagate failures

Add a new sub-bullet to Coder Rule 9 or as a standalone Rule 11:

```markdown
**Persistent-store write paths:** Infrastructure adapters that write to persistent stores (ChromaDB, databases, file indexes) must never swallow exceptions or return zero/empty/default values on failure. Silent degradation in these contexts corrupts the store without any visible signal. Always propagate: raise the exception or wrap it in a domain error (`ModelProviderError`, `StorageError`, etc.) and re-raise. The caller decides whether to retry, skip, or abort — the adapter must not decide for it.
```

### Suggested Improvement (2 of 2) — Test Writer: Error-path coverage for infrastructure adapters

Add a directive to the Test Writer agent specifying that any provider or infrastructure adapter under test must include tests for all failure paths reachable from public methods:

```markdown
**Infrastructure adapter error paths:** When writing tests for providers, storage adapters, or any infrastructure class with external I/O, always test failure paths: HTTP error responses (4xx, 5xx), malformed/missing fields in API responses, network/connection errors, and empty-result edge cases. Happy-path-only coverage of adapters is insufficient — the error paths are where runtime failures occur.
```

### Action Taken

**Both improvements proposed for approval** — both add new directives to agent files (Coder and Test Writer), which qualifies as major under the severity classification rules.

Technical debt items (FINDING-007, FINDING-008) are not agent system changes — they require follow-up GitHub issues for code refactoring and are out of scope for this reflection note.
