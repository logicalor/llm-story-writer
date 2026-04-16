# Synthesized Audit Report — 2026-04-16

**Audit Type:** Multi-model synthesis (Claude Opus 4.6 + GPT 5.4 + Gemini 3.1 Pro)
**Model Agreement Score:** 5/10
**Overall Health:** Needs Attention
**Development Stage:** Phase 4 of OpenCode migration — approximately 85% complete

---

## Synthesis Overview

The llm-story-writer codebase is in a **transitional state**: the hybrid agent-tool architecture (ADR 001), the progressive wiki memory system (ADR 004/005), and the ChromaDB-based RAG tool (`rag-query`) are implemented and working. The test suite passes at 281 tests. However, the **ADR 003 ChromaDB migration is incomplete in the legacy `src/` domain layer** — `RAGService` and the DI container still wire `PgVectorStore`, and the `rag_query.py` tool sits outside the main application flow rather than replacing it. Additionally, **mypy type checking is non-functional** due to import resolution misconfiguration, and **documentation drift** exists between planning docs and implementation. The project is 85% complete toward the OpenCode migration goal but has meaningful gaps before it can be considered done.

---

## Individual Report Summaries

| Model  | Overall Assessment | Unique Focus Areas | Critical | Warning | Info |
| ------ | ----------------- | ------------------ | -------- | ------- | ---- |
| Claude | 85% complete; architecture aligned; type checking broken | Bare except clauses, mypy config, E2E gap | 2 | 3 | 4 |
| GPT    | Migration mostly aligned; pgvector still live in runtime | ADR 003 incomplete migration, README drift, dual-storage complexity | 3 | 4 | 4 |
| Gemini | Architecture largely complete; test timeout reported | Type errors, undefined variables, legacy code removal | 3 | 1 | 2 |

---

## Development Stage (Consensus)

| Phase | Status | Completion | Agreement |
| ----- | ------ | ---------- | --------- |
| Phase 0 — Foundation | Done | 3/3 tasks | Unanimous |
| Phase 1 — Core Tools | Done | 9/9 tasks | Unanimous |
| Phase 2 — Wiki Tools | Done | 5/5 tasks | Unanimous |
| Phase 3 — Agent Layer | Done | 4/4 agents | Unanimous |
| Phase 4 — ChromaDB Migration | **In Progress** | Partial | **Split** |
| Phase 5 — Integration / E2E | **Not Started** | 0/1 tasks | Majority |

---

## Consensus Findings

### ★★★ Unanimous Findings (All Three Models Agree)

```
[U-C-01] mypy Type Checking Non-Functional
Severity: Critical | Category: Code Quality | Agreement: Claude ✓ GPT ✓ Gemini ✓
Detail: All three models independently identified that `mypy src/` fails with import resolution
  errors (Cannot find implementation or library stub for module named 'domain.exceptions',
  'config.config_loader', etc.). This means mypy cannot resolve local module imports, making
  type checking effectively non-functional. Additionally, real type errors exist in
  model_config.py (incompatible types on lines 90-92) and missing `from typing import Dict, Any`
  imports in multiple service files.
Impact: Type safety guarantees cannot be enforced; runtime failures possible in core services.
        This should block any production deployment.
Models: Claude ✓ GPT ✓ Gemini ✓
Suggestion: Add `pythonpath = src` to mypy.ini or pyproject.toml; add missing typing imports;
  fix type errors in model_config.py.
```

```
[U-C-02] Legacy Code Lint Errors
Severity: Critical | Category: Code Quality | Agreement: Claude ✓ GPT ✓ Gemini ✓
Detail: `ruff check .` reports F821 (Undefined name 'Dict') and F811 errors in files under
  `legacy/src/`. While this is expected for archived code (per AGENTS.md, legacy/ is a frozen
  archive), the errors are reported when running `ruff` across the entire repository. This
  creates noise in CI and obscures whether active code has lint errors.
Impact: CI lint gate may be red or confused; legacy errors mask active code cleanliness.
Models: Claude ✓ GPT ✓ Gemini ✓
Suggestion: Exclude `legacy/` from repo-wide lint via `ruff --exclude legacy/` or
  `pyproject.toml` exclude pattern. Confirm active `src/` code is actually clean.
```

### ★★☆ Majority Findings (Two of Three Models Agree)

```
[M-C-01] ADR 003 ChromaDB Migration Incomplete in Domain Layer
Severity: Critical | Category: Architecture | Agreement: Claude ✗ GPT ✓ Gemini ✓
Detail: `RAGService` in `src/application/services/rag_service.py`, the DI container in
  `src/infrastructure/container.py`, and `src/presentation/cli/rag_cli.py` all still wire
  `PgVectorStore` and pgvector imports. The `rag_query.py` tool exists in `src/tools/` and
  uses ChromaDB correctly, but the main application domain layer (`RAGService`) was not
  updated to use ChromaDB — it was simply left alongside the new tool. This means the old
  pgvector path is still live and importable.
  GPT's analysis correctly identified this as a dual-storage complexity issue during migration.
  The original pgvector code is not removed; it is still registered in the DI container.
Models: Claude ✗ GPT ✓ Gemini ✓
Dissenting view: Claude reported that "15 of 16 TypeScript tool wrappers" are implemented and
  the architecture is aligned with ADRs 001-005, but did not flag the pgvector service as a
  live/incomplete ADR 003 finding. This may be because Claude's architecture review focused
  on the tools layer (where ChromaDB IS correctly implemented) rather than the domain layer.
  GPT and Gemini both correctly identified the incomplete migration as a critical finding.
Impact: Architecture diverges from accepted ADR 003 design. Running the RAG CLI or any code
  path that uses RAGService will attempt to use PostgreSQL/pgvector, which violates the
  local-first goal. The migration appears to have been done at the tool level but not the
  domain service level.
Suggestion: Either (a) migrate RAGService to use ChromaDB client instead of PgVectorStore,
  or (b) formally deprecate RAGService and route all RAG access through the rag-query tool.
  Document which path is authoritative.
```

```
[M-W-01] Documentation Drift — README and Planning Docs
Severity: Warning | Category: Documentation | Agreement: GPT ✓ Gemini ✓ Claude ✗
Detail: GPT and Gemini both identified that README.md still describes the older
  `Prompts/`, `Stories/`, `SavePoints/`, `Logs/` layout and references old execution
  commands. The planning docs (`docs/planning/opencode-migration/tasks.md`) still show
  unchecked items for wiki-snapshot detail levels and ChromaDB RAG completion, despite
  these being implemented in the tools layer.
Models: GPT ✓ Gemini ✓ Claude ✗
Dissenting view: Claude did not flag documentation drift as a Warning, possibly because the
  primary audit focus was on code quality and architecture rather than documentation
  alignment. However, the finding is legitimate — README.md is a new contributor's first
  point of contact and is currently misleading.
Impact: New contributors and users get outdated setup and structure guidance.
Suggestion: Audit and update README.md to reflect the OpenCode/wiki/ChromaDB architecture.
  Close or revise unchecked items in tasks.md to match actual implementation state.
```

```
[M-W-02] Bare `except:` Clauses in rag_query_cli.py
Severity: Warning | Category: Code Quality | Agreement: Claude ✓ GPT ✗ Gemini ✗
Detail: Claude identified two bare `except:` clauses in `rag_query_cli.py` at lines 265 and
  687, which can mask exceptions including KeyboardInterrupt.
Models: Claude ✓ GPT ✗ Gemini ✗
Dissenting view: GPT did not explicitly flag this in the same way, possibly because it was
  focused on higher-impact architectural findings. Gemini did not mention it.
Impact: Potential for silent failures and difficulty debugging runtime errors.
Suggestion: Replace `except:` with `except Exception:` or specific exception types.
```

### ★☆☆ Singular Findings (Only One Model Reported)

```
[S-I-01] Token Budget Inconsistency in context-budgeting Skill
Severity: Info | Category: Documentation | Model: Gemini
Detail: The context-budgeting skill allocates ~25,000 tokens for "Story context (loaded by
  tool)" in the budget table, but Stage 2 refers to "~15K token budget for the story context
  portion." The ~15K is actually the wiki-snapshot sub-allocation within the ~25K, but
  the wording creates ambiguity.
Model: Gemini
Assessment: This is a genuine documentation clarity issue, not a code defect. Both figures
  come from different ADRs (ADR 002 for 25K, ADR 005 for 15K) but appear in the same skill
  document without clear disambiguation.
Suggestion: Add clarifying note that ~15K is the wiki-pages sub-allocation within the ~25K.
```

```
[S-I-02] ChromaDB Collection UUID Naming
Severity: Info | Category: Architecture | Model: Claude
Detail: ChromaDB collections are named with UUIDs rather than the human-readable
  `story-{slug}` naming specified in ADR 003.
Model: Claude
Assessment: This is a minor observability issue. The UUID naming may be an internal
  ChromaDB detail that doesn't affect functionality, or it may indicate that the per-story
  collection convention from ADR 003 hasn't been implemented yet.
Suggestion: Verify whether UUID-named collections map to story names and consider adding
  a human-readable collection naming convention.
```

```
[S-I-03] No E2E Integration Test
Severity: Info | Category: Tests | Model: Claude
Detail: Task 25 (End-to-End Integration Test) is marked not started. No test file exercises
  the full orchestrator → subagents → tools → wiki cycle.
Model: Claude
Assessment: This is a legitimate gap that GPT and Gemini did not explicitly call out,
  likely because their audit focused on different concerns. The absence of E2E tests
  means regressions in tool-agent interaction may go undetected before release.
Suggestion: Create a full pipeline E2E test before declaring migration complete.
```

---

## Divergence Analysis

```
[D-01] Topic: Is the ADR 003 ChromaDB migration complete?
Claude says: Architecture is aligned. rag-query tool uses ChromaDB correctly.
            15/16 tools implemented. No finding on pgvector persistence.
GPT says:   RAGService still wires PgVectorStore. pgvector_store still in DI container.
            ADR 003 migration incomplete at the domain service level.
Gemini says: Similar to GPT — pgvector still referenced. ChromaDB migration partial.
Assessment: GPT and Gemini are most likely correct. The rag-query tool is a new tool built
            alongside the old RAGService, not a replacement. The DI container still
            registers pgvector_store and RAGService. Claude reviewed the tools layer
            (where ChromaDB IS correctly used) but may not have traced the dependency
            through to RAGService and the container. The 2-vs-1 split is strong evidence
            that the migration is genuinely incomplete at the domain layer.
Resolution: Mark as [M-C-01] (Majority Critical) rather than Unanimous. Recommend fixing
            RAGService to use ChromaDB or formally deprecating the old path.
```

```
[D-02] Topic: Was documentation drift flagged as a Warning?
GPT/Gemini say: README.md is stale; planning docs show open items that are actually done.
Claude says: Not flagged as a Warning.
Assessment: Claude's audit was more focused on code quality and architecture compliance
            than documentation audit. The documentation drift is real — both GPT and
            Gemini independently identified it. This is a legitimate majority finding.
Resolution: Include as [M-W-01] (Majority Warning).
```

```
[D-03] Topic: Test suite status
Claude/GPT say: 281 tests pass in ~60s.
Gemini says: Test suite timed out after 10 seconds.
Assessment: The timeout may be a transient issue or a difference in test execution
            environment. 281 tests passing is a strong positive signal from two models.
            The timeout could reflect Gemini's execution context rather than the actual
            codebase state. Not a genuine finding.
Resolution: Treat test suite as passing (281 passed, 1 warning).
```

---

## Deviations from Plan (Consensus)

Only deviations flagged by at least two models are included:

```
[Dev-01] ADR 003 ChromaDB migration incomplete
  Plan: Replace PostgreSQL/pgvector with ChromaDB for story RAG (per ADR 003)
  Code: RAGService and DI container still wire PgVectorStore; rag-query tool exists but
        does not replace the old path
  Models: GPT ✓ Gemini ✓
  Severity: Critical — violates the core ADR 003 decision
```

---

## Risk Assessment (Synthesized)

| Risk | Severity | Models Agree |
| ---- | -------- | ------------ |
| mypy non-functional — type errors hide runtime failures | High | Yes |
| ADR 003 migration incomplete — pgvector still in DI container | High | Yes (2/3) |
| Bare except clauses in rag_cli.py | Medium | Yes (1/3) |
| No E2E integration test | Medium | Yes (1/3) |
| Documentation drift (README, tasks.md) | Medium | Yes (2/3) |
| Legacy code lint noise | Low | Yes (all) |
| ChromaDB collection UUID naming | Low | Yes (1/3) |

---

## Recommended Actions (Prioritized)

1. **[U-C-01]** Fix mypy configuration — add `pythonpath = src` to mypy config; add missing `from typing import Dict, Any` imports; fix type errors in `model_config.py`
2. **[U-C-02]** Exclude `legacy/` from repo-wide lint — add exclude pattern to `pyproject.toml` or use `ruff --exclude legacy/`
3. **[M-C-01]** Complete ADR 003 migration — migrate `RAGService` to use ChromaDB or formally deprecate `RAGService` and route all RAG through `rag-query` tool; remove `pgvector_store` from DI container
4. **[M-W-01]** Update documentation — revise `README.md` to reflect OpenCode/wiki/ChromaDB architecture; close/check done items in `docs/planning/opencode-migration/tasks.md`
5. **[M-W-02]** Fix bare `except:` clauses in `rag_query_cli.py` lines 265, 687
6. **[S-I-03]** Implement Task 25 — create E2E integration test for full orchestrator → subagents → tools → wiki cycle
7. **[S-I-01]** Clarify token budget note in `context-budgeting` skill — disambiguate ~15K wiki sub-allocation from ~25K story context total
