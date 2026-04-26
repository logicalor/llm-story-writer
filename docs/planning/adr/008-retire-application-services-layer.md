# ADR 008: Retire the Application Services Layer

**Date:** 2026-04-26
**Status:** Accepted — supersedes Goal 2 / Task 5 of the Python-Native Migration PRD

## Context

ADR 007 stated that the Python-native orchestrator would preserve `src/application/services/` as the main orchestration layer and call those services in-process. The repository did not converge on that design. The active Python-native path lives in `src/presentation/agents/`, where core generation agents call `provider.stream_text()` directly, `WikiMaintainerAgent` delegates straight to `src/tools/wiki_extract.py`, and `StoryOrchestratorAgent` is a thin vestigial coordinator. No active presentation-layer code routes through `src/application/services/`.

The result is a documented architecture that differs from the implemented one. Most files under `src/application/services/` now have no production callers, little or no dedicated test coverage, and overlapping behavior with the presentation-layer agents or tool scripts that replaced them. The only exception is `critique_parser.py`, which remains on an active tool path because `src/tools/critique_runner.py` imports `CritiqueParser` directly.

| Service file | Approx. lines | Test coverage status | Active callers |
| --- | ---: | --- | --- |
| `chapter_service.py` | 19 | None found | None |
| `rag_integration_service.py` | 559 | No direct behavior tests; removal regression tests exist | None |
| `story_info_service.py` | 147 | None found | None |
| `story_generation_service.py` | 139 | None found | None |
| `outline_service.py` | 191 | None found | None |
| `critique_service.py` | 272 | Limited smoke coverage only in `tests/unit/test_critique_service.py` | None |
| `critique_parser.py` | 265 | Active parser coverage in `tests/unit/test_critique_service.py` | `src/tools/critique_runner.py` |
| `reranker_service.py` | 304 | None found | None |
| `model_reranker_service.py` | 242 | None found | None |
| `content_chunker.py` | 324 | None found | Only imported by inactive `rag_integration_service.py` |

This inventory shows a retired-by-implementation layer: valuable domain entities remain in `src/domain/`, but the service layer no longer defines the running system's control flow.

## Decision

Choose **Option B**: formally retire `src/application/services/` as an architectural layer. The repository will treat the service files above as dead code, except for `critique_parser.py`, which is retained because `src/tools/critique_runner.py` depends on it today.

This decision does not change the status of `src/application/strategies/`. The strategies layer is out of scope for this ADR and will be evaluated separately. This ADR addresses only the mismatch between ADR 007 and the implemented Python-native orchestration path.

## Consequences

### Positive

- Removes roughly 2,200 lines of dead or bypassed code once follow-up cleanup issues delete the retired files.
- Eliminates confusion about the intended orchestration path: presentation agents and tools are the active integration surface, not dormant services.
- Aligns the repository with the Python-native migration as implemented: lean, single-language, direct agent-to-provider or agent-to-tool flows.

### Negative

- Retiring `CritiqueService` removes the in-service six-critic outline evaluation loop. That quality-pass behavior is deferred to a future focused issue that can reintroduce it as a standalone quality-pass tool if still needed.
- Retiring `OutlineService` defers its multi-step outline conversation logic rather than preserving it behind an unused abstraction.
- Retiring `RerankerService` and `ModelRerankerService` defers application-layer RAG reranking until a concrete caller justifies a smaller, tested replacement.

## Retirement Plan

### Files to delete

- `src/application/services/chapter_service.py` — unimplemented stub; no callers.
- `src/application/services/rag_integration_service.py` — bypassed by direct tool usage and already surrounded by removal-oriented tests.
- `src/application/services/story_info_service.py` — no active callers.
- `src/application/services/story_generation_service.py` — no active callers.
- `src/application/services/outline_service.py` — behavior duplicated by presentation agents.
- `src/application/services/critique_service.py` — no active callers; quality loop deferred. Note: `tests/unit/test_critique_service.py::test_critique_service_has_dict_any_imports` reads this file via `ast.parse()` and must be deleted alongside the source file.
- `src/application/services/reranker_service.py` — no active callers.
- `src/application/services/model_reranker_service.py` — no active callers.
- `src/application/services/content_chunker.py` — only feeds retired `rag_integration_service.py`.

### Files to retain

- `src/application/services/critique_parser.py` — retain until `src/tools/critique_runner.py` is refactored away from it or an equivalent parser is moved to a more appropriate layer.

Deletion work is tracked separately from this ADR and should proceed through focused cleanup issues so each removal can be validated against the remaining tool and test surface.

## Supersession

This ADR partially supersedes Goal 2 and Task 5 of the Python-Native Migration PRD in `docs/planning/python-native-migration/`. The original principle of preserving valuable domain logic remains in force for `src/domain/` and other active layers. The change here is narrower: `src/application/services/` is no longer treated as a preserved orchestration layer because the implementation never adopted it.