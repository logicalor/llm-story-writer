# Legacy Dependency Cleanup

> Current runtime dependency model after migration cleanup removed obsolete dependencies, temporary archives, and ad-hoc repository artifacts.

## Overview

Issue 26 and PR 98 removed the last legacy runtime dependencies from the active application. Issue 107 and PR 108 finish the repository cleanup by deleting migration leftovers that no longer serve as active references. The current project now runs with a single dependency manifest, direct OpenAI-compatible HTTP providers, and ChromaDB-backed retrieval.

The earlier cleanup removed three important pieces from the active `src/` tree: the dependency-injector container, the LangChain provider, and the application-level `RAGService`. Issue 107 removes the temporary `legacy/` archive that had preserved those files during migration, so retired implementations are no longer kept inside the repository at all.

Issue 107 also deletes obsolete root-level test scripts, helper utilities, duplicate markdown summaries, `requirements-rag.txt`, and the old `Docs/` and `ExamplePrompts/` directories. Documentation and setup guidance should now point only at the active tree under `docs/`, `prompts/`, `src/`, `stories/`, and `tests/`.

Issue 100 and PR 102 finish a smaller follow-on cleanup from the same migration work. After the application-level `RAGService` was removed, one unused `rag_service` propagation path still remained in active strategy construction. That dead wiring has now been removed, so active runtime code no longer carries a placeholder RAG dependency through outline strategy setup.

Issue 99 narrows provider validation to the providers that still have active runtime implementations. `ModelConfig` now accepts only `openai_compatible`, `ollama`, `lm_studio`, and `llama_cpp`. The `ollama` key remains an alias that normalises to the shared OpenAI-compatible provider path.

## Active Runtime Stack

The current dependency split is deliberate.

| Surface | Current implementation | Notes |
|---------|------------------------|-------|
| Core runtime | `requirements.txt` | Single dependency manifest for the active project; runtime depends on `requests`, `chromadb`, `pyyaml`, and `llm-output-parser`, with test packages grouped in the same file |
| LLM access | OpenAI-compatible `/v1` APIs | Ollama, LM Studio, llama.cpp server, vLLM, and similar servers work through the same provider contract |
| Tool orchestration | OpenCode agent + tool system | TypeScript wrappers in `.opencode/tools/` call Python scripts in `src/tools/` directly |
| Retrieval path | `rag-query` tool + ChromaDB collections | Active code no longer exposes a reusable application-layer `RAGService`; configuration is ChromaDB-only with no PostgreSQL or pgvector settings |

## Removed Components

The following components were removed from the repository during migration cleanup:

- dependency-injector container wiring
- LangChain-backed model provider code
- application-level `RAGService`
- temporary `legacy/` migration archive
- root-level `test_*.py` scripts outside `tests/`
- root-level utility scripts such as `migrate_embed.py`, `rag_query_cli.py`, and `setup_rag.sh`
- duplicate root markdown summaries such as `CLEANUP_SUMMARY.md` and `REFACTORING_SUMMARY.md`
- `requirements-rag.txt`
- deprecated `Docs/` and `ExamplePrompts/` directories

Do not restore these components as part of routine feature work. If you need behaviour from the retired pipeline, port the specific logic into the current tool architecture instead of reviving the old integration layer wholesale or recreating deleted repository clutter.

## Developer Guide

### Dependency Changes

When updating dependencies, treat `requirements.txt` as the source of truth for actively imported runtime packages. Add a package only when code in the active tree requires it.

Use these guardrails:

- Prefer direct HTTP clients and small focused libraries over framework-heavy orchestration dependencies
- Keep provider integrations compatible with OpenAI-style `/v1` APIs unless there is a demonstrated need for a vendor-specific path
- Do not reintroduce provider keys that route only through archived integrations; `google`, `openrouter`, `openai`, and `anthropic` are intentionally unsupported in the active runtime
- Add retrieval behaviour through `rag-query` and related tools, not through a resurrected shared RAG service layer
- Treat `requirements.txt` as the only supported install target; do not add a second requirements file for active runtime setup
- Keep setup and config documentation ChromaDB-only; do not document PostgreSQL or pgvector keys that no longer exist in active configuration loaders
- Do not thread unused placeholder dependencies through constructors or factories after a service has been retired from the active runtime
- Wire runtime objects explicitly inside tools or entry points; do not reintroduce a global DI container
- Keep ad-hoc helper scripts out of the repository root; add durable automation under `src/tools/`, `.opencode/tools/`, or documented project scripts instead

### Verification Expectations

Task 26 validation on PR 98 confirmed:

- active `src/` no longer contains `container.py`, `langchain_provider.py`, or `rag_service.py`
- the feature branch test run completed with `308 passed, 14 skipped, 0 failed`
- root documentation now describes the OpenCode-first workflow and archived legacy code accurately

Follow-on validation on PR 102 confirmed that active runtime setup no longer accepts or forwards an unused `rag_service` dependency.

Cleanup validation on PR 108 confirmed that the temporary migration archive, obsolete root scripts, duplicate markdown summaries, and `requirements-rag.txt` are gone, and documentation now points only at active project locations.

## Related

- [Tools Reference](../tools.md)
- [Documentation Index](../README.md)
- [ADR 003: ChromaDB Replaces pgvector](../planning/adr/003-chromadb-replaces-pgvector.md)
- [ADR 006: Replace Ollama SDK with Generic OpenAI-Compatible REST Provider](../planning/adr/006-openai-compatible-provider.md)
- [Migration Tasks](../planning/opencode-migration/tasks.md#task-26-clean-up-legacy-dependencies)