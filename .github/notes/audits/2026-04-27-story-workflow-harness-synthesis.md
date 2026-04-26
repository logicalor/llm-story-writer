## Synthesized Audit — 2026-04-27

**Audit Type:** Codex persona synthesis  
**Scope:** Story creation workflow harness remediation block, GitHub issues #180-#203 plus follow-up PRs #206-#209  
**Personas:** Architect + Maintainer + Product Documenter  
**Persona Agreement Score:** 8/10  
**Overall Health:** At Risk  
**Development Stage:** Python-native story workflow harness — core phase stubs mostly filled, but end-to-end run still blocked

### Synthesis Overview

Issues #180-#203 materially improved the Python-native harness. The previous no-op assembly, characters/settings, wiki persistence, consistency parsing, final-edit, narrative-arc, CLI/TUI resume, E2E assertion, documentation drift, dependency hygiene, and dead-service findings were either fixed or explicitly retired by ADR 008.

The work is not yet spec-compliant or functionally complete. The live headless E2E currently fails after chapter 1 because the orchestrator never initializes the wiki before `WikiMaintainerAgent` calls `run_batch()`. The validation baseline is also not green: `mypy src/` fails in `openai_async_provider.py` with OpenAI SDK 2.x typing errors. Documentation and prompt surfaces still describe phases that the active orchestrator does not run, including wiki initialization, initial wiki population, chapter-outline-expander, quality-reviewer, and prose-scrubber.

### Individual Report Summaries

| Persona | Overall Assessment | Unique Focus Areas | Critical Count | Warning Count |
| --- | --- | --- | ---: | ---: |
| Architect | Architecture is cleaner after ADR 008, but the runtime sequence still violates wiki and full-pipeline assumptions. | ADR 007/008 alignment, missing wiki init, unimplemented quality phases, shallow savepoint semantics | 1 | 3 |
| Maintainer | Unit/lint/format health is good; type and live integration health are red. | `mypy src/`, live E2E failure, test blind spots, SDK dependency drift | 2 | 2 |
| Product Documenter | Docs acknowledge some scope gaps, but top-level README/PRD/prompt references still overpromise. | README claims, PRD status drift, story-pipeline skill drift, operator-facing resume semantics | 1 | 4 |

### Development Stage

| Phase | Status | Completion | Agreement |
| --- | --- | --- | --- |
| Validation baseline (#180/#191) | In Progress | ruff/format/unit pass; mypy fails | Unanimous |
| Runtime artifact output (#181/#193/#192/#206) | Done | chapter files and `story.md` written, resume backfills missing chapters | Unanimous |
| Character/settings context (#182/#194) | Done with graceful degradation | sheets generated and read by chapter writer; malformed extraction yields no context | Majority |
| Wiki persistence (#183/#195/#196/#207) | Blocked in pipeline | typed API exists; orchestrator lacks required wiki initialization | Unanimous |
| Consistency checking (#184/#197) | Partial | parses JSON; non-critical issues are not surfaced by orchestrator | Majority |
| Narrative arc + final edit (#185/#198) | Done, lightweight | phases run; arc score/metrics are placeholders | Majority |
| E2E test hardening (#186/#199) | Partial | disk output assertions added; current live E2E fails before completion | Unanimous |
| CLI/TUI UX fixes (#187/#200) | Mostly Done | batch flag documented, TUI resume wired; arbitrary savepoint restore remains absent | Majority |
| Service-layer retirement (#188/#201/#202/#203/#208/#209) | Done | ADR 008 accepted, services removed or relocated | Unanimous |
| Documentation sync (#189) | Partial | several docs fixed; README/PRD/prompt surfaces still conflict with active runtime | Majority |

### Consensus Findings

#### Unanimous

[U-C-01] Headless story creation fails because wiki initialization is not wired  
Severity: Critical  
Category: Workflow  
Detail: The active orchestrator enters chapter wiki maintenance at `src/presentation/orchestrator.py:508`, where `WikiMaintainerAgent.run()` calls `update_wiki_from_chapter()` (`src/presentation/agents/wiki_maintainer.py:64-76`). That path reaches `run_batch()`, which raises `ValueError("wiki not initialised")` when `stories/<story>/wiki/` does not exist (`src/tools/wiki_update.py:411-422`). `wiki_init.py` provides an idempotent initializer (`src/tools/wiki_init.py:22-80`), but `_continue_pipeline()` never calls it. A live run of `pytest tests/integration/test_end_to_end_headless.py -q -m integration` failed with `RuntimeError: Wiki update failed for story='e2e-test' chapter=1: wiki not initialised`.  
Personas: Architect yes | Maintainer yes | Product Documenter yes  
Impact: The harness cannot complete a normal fresh story run against a live endpoint, so the workflow is not functional despite unit tests passing.  
Suggested action: Add an idempotent wiki-init phase before chapter generation or before the first wiki update, then extend orchestrator/E2E coverage to assert wiki initialization and at least one persisted wiki artifact.

[U-C-02] Validation baseline is still red under current dependencies  
Severity: Critical  
Category: Build  
Detail: `ruff check .` passed and `ruff format --check .` reported 147 files formatted. `pytest tests/unit -q` passed with `522 passed, 1 warning`. `mypy src/` failed with six errors in `src/infrastructure/providers/openai_async_provider.py`: `messages` is typed as `list[dict[str, str]]` where OpenAI 2.x expects chat completion param unions, and the `create()` response is not narrowed between `ChatCompletion` and `AsyncStream[ChatCompletionChunk]` (`openai_async_provider.py:186`, `191`, `209`, `214`, `310`, `315`).  
Personas: Architect yes | Maintainer yes | Product Documenter yes  
Impact: Issue #180/#191 claimed a restored green baseline, but current `mypy src/` no longer passes. The repository rule to run lint and type checks after changes cannot be satisfied.  
Suggested action: Update `OpenAIAsyncProvider` typing for the installed OpenAI SDK, pin OpenAI to the version the provider was written against, or isolate SDK response casts in a typed adapter with regression tests.

#### Majority

[M-W-01] The implemented pipeline remains smaller than the authoritative story-pipeline spec  
Severity: Warning  
Category: Planning  
Detail: The current orchestrator sequence is `init -> outline -> narrative-arc -> characters -> settings -> chapter-loop -> final-edit -> assembly` (`src/presentation/orchestrator.py:373-580`). It does not run wiki initialization, initial wiki population, chapter-outline-expander, quality-reviewer, or prose-scrubber. The gap is acknowledged in `docs/manual.md:294` and `docs/features/story-orchestrator.md:223-229`, while `prompts/skills/story-pipeline/SKILL.md:7`, `136-143`, and `175-185` still describe the broader nine-phase pipeline plus Phase 7.5 and the ten subagents.  
Personas: Architect yes | Maintainer no | Product Documenter yes  
Dissenting view: Maintainer treats this as a scope boundary unless a runtime failure proves otherwise; wiki initialization is covered separately as a blocker.  
Impact: A prompt-compliant or docs-compliant operator will expect phases and quality gates that the Python harness does not execute.  
Suggested action: Decide whether the active harness spec is the reduced orchestrator slice or the full story-pipeline skill. If reduced, mark inactive phases explicitly as future work in prompt/skill surfaces; if full, create follow-up implementation issues.

[M-W-02] Consistency warnings are parsed but not surfaced  
Severity: Warning  
Category: Code Quality  
Detail: `_extract_consistency_result()` returns populated `issues` while keeping `passed=True` when `has_critical_findings` is false (`src/presentation/agents/consistency_checker.py:74-97`). Tests codify that behavior for a warning semantic finding (`tests/unit/test_consistency_checker.py:81-102`). The orchestrator only emits consistency findings when `not consistency_result["passed"]` (`src/presentation/orchestrator.py:495-505`), so warning/info findings are silently dropped even though they were parsed.  
Personas: Architect no | Maintainer yes | Product Documenter yes  
Dissenting view: Architect accepts advisory non-critical findings as non-blocking, but agrees they should remain visible if parsed.  
Impact: The consistency gate is no longer a total no-op, but it still hides lower-severity continuity problems from operators and downstream quality passes.  
Suggested action: Emit any non-empty `issues` list, while reserving `passed=False` for critical/blocking status.

[M-W-03] Documentation and planning sources still overstate or contradict the active implementation  
Severity: Warning  
Category: Documentation  
Detail: `docs/planning/python-native-migration/prd.md` is still `Status: Draft` and says services are preserved and called directly (`prd.md:20-25`, `100-129`) even though ADR 008 retires services (`docs/planning/adr/008-retire-application-services-layer.md:27-31`). README says the wiki is updated after each scene (`README.md:203`) while the active orchestrator updates after each chapter and currently fails without wiki initialization. README also lists `src/application` as "use cases and services" (`README.md:157`) after the services package was retired.  
Personas: Architect yes | Maintainer no | Product Documenter yes  
Dissenting view: Maintainer considers docs secondary to the current failing runtime and type checks.  
Impact: New contributors will infer the wrong architecture and operators will expect wiki behavior that is not currently true.  
Suggested action: Refresh the PRD status/current-state section and README architecture/wiki language to match ADR 008 and the actual orchestrator path.

[M-W-04] Resume validates named savepoints but cannot restore historical snapshots  
Severity: Warning  
Category: Workflow  
Detail: `resume_pipeline()` loads only `stories/<story>/savepoints/pipeline_state.json` (`src/presentation/orchestrator.py:622-655`). If `savepoint_name` is provided, it checks membership in `state.savepoints` but does not load an older snapshot (`src/presentation/orchestrator.py:640-644`). The limitation is documented in `docs/features/story-orchestrator.md:172-179` and CLI help says the name is "to validate against" (`src/presentation/cli/argument_parser.py:41-45`).  
Personas: Architect yes | Maintainer yes | Product Documenter no  
Dissenting view: Product Documenter accepts this because current user-facing docs avoid promising historical restore.  
Impact: The workflow can resume the latest state, but not a user-selected historical savepoint. This is acceptable only if explicitly treated as out of scope.  
Suggested action: Either keep the current wording and remove historical-savepoint expectations from planning docs, or implement per-savepoint snapshots.

#### Singular

[S-W-01] Final-edit and narrative-arc metrics are placeholders  
Severity: Warning  
Category: Code Quality  
Detail: `StoryPlannerAgent` stores `overall_score=0.0` and derives `verdict_code` heuristically from plain text (`src/presentation/agents/story_planner.py:111-116`). `FinalEditorAgent` reports `total_issues_found=0` and `total_revisions_made=len(edited_chapters)` without parsing edit metrics (`src/presentation/agents/final_editor.py:102-107`).  
Personas: Architect no | Maintainer yes | Product Documenter no  
Assessment: This is not blocking if those phases are intentionally lightweight, but it weakens claims that these are real quality gates rather than streamed advisory passes.  
Impact: Future reporting or gate thresholds built on these fields will be misleading.  
Suggested action: Rename fields/docs as placeholders or parse structured agent output with tests.

### Divergence Analysis

[D-01] Is the reduced orchestrator slice acceptable?  
Architect says: The missing phases mean the harness is still not aligned with the story-pipeline spec.  
Maintainer says: Missing phases are acceptable if documented, except wiki initialization because it breaks E2E.  
Product Documenter says: The current docs split the difference too much: some files acknowledge the reduced slice, others still present the full pipeline.  
Assessment: Maintainer is right for immediate runtime priority; Architect and Product Documenter are right for spec compliance.  
Resolution: Treat wiki initialization as a critical blocker and the other missing phases as documented-but-unresolved planning drift.

[D-02] Should shallow named-savepoint resume be a defect?  
Architect says: It is incomplete relative to savepoint language and operator expectations.  
Maintainer says: It is not a runtime bug because latest-state resume works and names are only validated.  
Product Documenter says: Current CLI help is honest enough.  
Assessment: The behavior is acceptable only if "named savepoint" continues to mean validation, not rewind.  
Resolution: Include as a warning, not a critical.

### Deviations From Plan

- ADR 007 and the PRD planned direct service-layer calls; ADR 008 explicitly superseded that direction and the service layer has now been retired.
- The full story-pipeline prompt/skill phase map still includes chapter-outline-expander, quality-reviewer, and prose-scrubber, while the active orchestrator omits them.
- Wiki maintenance was implemented before orchestrator-level wiki initialization, causing a fresh-run integration failure.
- Validation claims in issue/PR summaries are stale under the current dependency set because `mypy src/` fails.

### Risk Assessment

Technical risk is high until wiki initialization is wired: fresh headless runs fail after chapter generation. Build risk is medium-high because OpenAI SDK type drift breaks `mypy src/`. Product and workflow risk is medium because README, PRD, and prompt/skill surfaces still describe broader behavior than the harness executes. Architecture risk has improved: ADR 008 made the service-layer retirement explicit and the old dead code is gone. Test risk remains medium because unit tests mock `WikiMaintainerAgent` in orchestrator tests and therefore missed the missing wiki initialization path.

### Recommended Actions

1. Fix [U-C-01]: add idempotent wiki initialization to the orchestrator and add a focused regression test that does not mock away wiki maintenance.
2. Fix [U-C-02]: restore `mypy src/` against the installed OpenAI SDK or pin the SDK version.
3. Strengthen the live E2E after wiki init: assert `story.md`, chapter files, initialized wiki directory, and at least one expected wiki artifact or a clear empty-update condition.
4. Surface all parsed consistency issues, not only `passed=False` critical results.
5. Reconcile `README.md`, `docs/planning/python-native-migration/prd.md`, `prompts/skills/story-pipeline/SKILL.md`, and `prompts/agents/story-orchestrator.md` around the current-vs-target pipeline.
6. Decide whether named savepoint restore remains validation-only or becomes real historical restore.

### Actions Taken

- Issues created: none.
- Notes updated: `.github/notes/audits/2026-04-27-story-workflow-harness-synthesis.md`
- ChromaDB: key findings added to `audits` collection.

