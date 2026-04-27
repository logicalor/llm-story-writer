# Task Breakdown: Python-Native Orchestration and TUI

> Implements [PRD](./prd.md). Supersedes OpenCode harness per [ADR 007](../adr/007-python-native-orchestration.md).

**Date:** 2026-04-24

Task ordering rule: infrastructure (LLM client, prompt loader) → orchestration core → TUI → cleanup. Each task is Orchestrator-sized (one issue → branch → PR). Tasks are numbered for dependency tracking, not for strict sequential execution — tasks marked with independent dependencies may run in parallel.

---

## Tasks

### Task 1: Relocate agent system prompts and add frontmatter-stripping loader

**Type:** backend
**Estimated scope:** small
**Dependencies:** none

**Description:**

Move all files from `.opencode/agents/*.md` to `prompts/agents/*.md` preserving filenames and content. Add `src/infrastructure/prompts/agent_prompt_loader.py` that reads a Markdown file, strips YAML frontmatter (content between two `---` delimiters at file start), and returns the body as a stripped string. Expose a `load_agent_prompt(name: str) -> str` function and a module-level cache.

**Acceptance Criteria:**

- [ ] `.opencode/agents/` is empty or deleted; all content now lives under `prompts/agents/`
- [ ] `load_agent_prompt("story-orchestrator")` returns the body of `prompts/agents/story-orchestrator.md` with no frontmatter
- [ ] Files without frontmatter are returned verbatim
- [ ] Malformed frontmatter (missing closing `---`) raises a clear `ValueError`
- [ ] Unit test covers: with-frontmatter, without-frontmatter, malformed-frontmatter, missing-file

**Key Files:**

- `.opencode/agents/*.md` → `prompts/agents/*.md` (move)
- `src/infrastructure/prompts/agent_prompt_loader.py` (new)
- `tests/unit/test_agent_prompt_loader.py` (new)

---

### Task 2: Add AsyncOpenAI-based streaming model provider

**Type:** backend
**Estimated scope:** medium
**Dependencies:** none

**Description:**

Add `src/infrastructure/providers/openai_async_provider.py` implementing the existing `ModelProvider` interface using `openai.AsyncOpenAI`. Support token-by-token streaming via async generators. Expose `stream_chat(messages, model, **kwargs) -> AsyncGenerator[str, None]` and `complete_chat(...)` (non-streaming convenience). Pull `base_url` and `api_key` from the existing `config.yml` loader; default `api_key` to `"lm-studio"` if unset. Configure `timeout`, `max_retries`, and optional custom `httpx.AsyncClient`.

Do not remove the existing synchronous `OpenAICompatibleProvider` — parallel existence is required for incremental migration.

**Acceptance Criteria:**

- [ ] `OpenAIAsyncProvider` implements `ModelProvider` interface
- [ ] `stream_chat()` yields content deltas as they arrive (verified by token count > 1 for any non-trivial response)
- [ ] Connection errors, timeouts, and HTTP 5xx raise `ModelProviderError` with the underlying exception chained
- [ ] Empty `api_key` config value is replaced with `"lm-studio"` before client construction
- [ ] Integration test (marked `@pytest.mark.integration`) streams from live LM Studio and asserts > 1 chunk received

**Key Files:**

- `src/infrastructure/providers/openai_async_provider.py` (new)
- `src/application/interfaces/model_provider.py` (confirm streaming signature; extend if absent)
- `tests/unit/test_openai_async_provider.py` (new, mocked)
- `tests/integration/test_openai_async_provider_live.py` (new, live)

---

### Task 3: Define typed pipeline handoff objects

**Type:** backend
**Estimated scope:** small
**Dependencies:** none

**Description:**

Create `src/application/pipeline/handoffs.py` with dataclasses/Pydantic models representing the structured payloads passed between pipeline phases: `OutlineResult`, `ChapterDraft`, `WikiUpdateBatch`, `ApprovalDecision`, `PipelineState`. Each type encapsulates the minimum data needed for the next phase to run. Prefer dataclasses unless a field requires runtime validation.

**Acceptance Criteria:**

- [ ] All handoff types are defined and importable from `src/application/pipeline/handoffs`
- [ ] Each type has a docstring documenting which phase produces it and which phase consumes it
- [ ] `PipelineState` round-trips through JSON (`to_dict` / `from_dict`) for savepoint persistence
- [ ] Unit test confirms round-trip equality for each type

**Key Files:**

- `src/application/pipeline/__init__.py` (new)
- `src/application/pipeline/handoffs.py` (new)
- `tests/unit/test_pipeline_handoffs.py` (new)

---

### Task 4: Build approval gate and streaming bus primitives

**Type:** backend
**Estimated scope:** small
**Dependencies:** Task 3

**Status:** implemented in Issue #160 / PR #170

**Description:**

Create `src/presentation/pipeline_primitives.py`. Implement:

1. `ApprovalGate` — async primitive with `.await_decision() -> ApprovalDecision` and `.resolve(decision)`. Backed by `asyncio.Future`. Includes a `NullApprovalGate` subclass that auto-resolves with `ApprovalDecision.APPROVE` (for batch mode).
2. `TokenStreamBus` — async primitive wrapping `asyncio.Queue`. Producer side: `.emit(delta: str)`. Consumer side: async iterator. Includes `.close()` to signal end of stream.
3. `WikiContextBus` — structured-event companion to `TokenStreamBus`. Producer side: `.emit(event: WikiContextEvent)` where events describe entity matches, wikilink traversal steps, and detail-level selections. Consumer side: async iterator. The headless runner uses a no-op consumer; the TUI (Task 8) drains into the wiki panel.

All three primitives are transport-agnostic — the TUI and headless runner both consume them.

**Acceptance Criteria:**

- [x] `ApprovalGate.await_decision()` blocks until `.resolve()` is called and returns the provided decision
- [x] `NullApprovalGate` returns `APPROVE` immediately without blocking
- [x] `TokenStreamBus` forwards all emitted deltas in order to the consumer
- [x] `WikiContextBus` forwards all emitted events in order to the consumer
- [x] Closing any bus terminates its async iterator cleanly
- [x] Unit tests cover: single-consumer, null gate, close-before-consume, close-mid-consume, wiki event emit

**Key Files:**

- `src/presentation/pipeline_primitives.py` (new)
- `tests/unit/test_pipeline_primitives.py` (new)

---

### Task 5: Build Python pipeline orchestrator (headless)

**Type:** backend
**Estimated scope:** large
**Dependencies:** Tasks 1, 2, 3, 4

**Status:** implemented in Issue #161 / PR #171

**Description:**

Create `src/presentation/orchestrator.py`. Model each former OpenCode agent as an async callable in `src/presentation/agents/` (one file per agent). Each agent:

- Loads its system prompt via `load_agent_prompt()`
- Receives typed input (e.g., `OutlineBrief`) and returns typed output (e.g., `OutlineResult`)
- Calls into `src/application/services/` for heavy work
- Emits tokens via an injected `TokenStreamBus` during LLM streaming

The orchestrator drives phases sequentially: Init → Outline → [Outline Approval Gate] → Narrative Arc → Characters → Settings → Chapter Loop (per chapter: generate → [Chapter Approval Gate] → apply revisions) → Final Edit → Assembly. Orchestrator accepts injected `ApprovalGate` and `TokenStreamBus` (or their Null equivalents).

Leverage the existing `src/application/strategies/outline_chapter/` code where practical — this is effectively the pre-OpenCode orchestrator and can be revived and wrapped.

**Acceptance Criteria:**

- [x] `run_pipeline(story_name, gate, bus)` executes the implemented headless phases and returns a final `PipelineState`
- [x] Each implemented phase writes a savepoint on successful completion
- [x] An approval gate resolved with `REJECT` halts the pipeline cleanly with a status in `PipelineState`
- [x] An approval gate resolved with `REVISE(feedback)` re-runs the current phase with the feedback appended to the prompt
- [x] Token streaming is visible via the injected bus during LLM calls
- [x] Unit tests with stubbed services cover: happy path, rejection at outline gate, revision at chapter gate, resume from savepoint

Current implementation note: Issue #185 / PR #198 adds the PRD's narrative-arc and final-edit phases to `src/presentation/orchestrator.py`. `resume_pipeline(savepoint_name=...)` validates the requested savepoint name but always resumes from the single latest `pipeline_state.json` snapshot. Named savepoints are validation-only; they are never restored as historical checkpoints (issue #215).

**Key Files:**

- `src/presentation/orchestrator.py` (new)
- `src/presentation/agents/__init__.py` (new)
- `src/presentation/agents/outline_planner.py` (new)
- `src/presentation/agents/chapter_writer.py` (new)
- `src/presentation/agents/wiki_maintainer.py` (new)
- `src/presentation/agents/consistency_checker.py` (new)
- `src/presentation/agents/story_orchestrator.py` (new — the top-level agent, largely vestigial)
- `tests/unit/test_orchestrator.py` (new)

---

### Task 6: Wire CLI entry points and remove legacy stub

**Type:** backend
**Estimated scope:** small
**Dependencies:** Task 5

**Status:** implemented in Issue #162 / PR #172

**Description:**

Replace the `NotImplementedError` stub in `src/presentation/cli/main.py` with an argparse-based entry point exposing three subcommands: `tui` (launch Textual app — implemented in Task 8), `run --batch` (headless pipeline via `NullApprovalGate`), and `resume` (load latest savepoint and continue). Add a `story-writer` console script entry in `pyproject.toml`.

The `tui` subcommand should import lazily so that `run` and `resume` work before the TUI module is implemented.

**Acceptance Criteria:**

- [x] `python -m src.presentation.cli.main run --story test_story --batch` executes the full pipeline headlessly and exits with code 0
- [x] `python -m src.presentation.cli.main resume --story test_story` loads the latest savepoint and continues
- [x] `--help` prints coherent usage for all subcommands
- [x] Console script `story-writer` works after `pip install -e .`
- [x] Unit test invokes the argparse parser and verifies subcommand dispatch

Current implementation note: `run` accepts `--batch` for CLI compatibility, but `_cmd_run()` currently always uses `NullApprovalGate()`, so runs are headless even when the flag is omitted. The `tui` subcommand is wired with a lazy import and currently exits with a helpful message until the Textual app lands.

**Key Files:**

- `src/presentation/cli/main.py` (rewrite)
- `src/presentation/cli/argument_parser.py` (extend)
- `pyproject.toml` (add `[project.scripts]` entry)
- `tests/unit/test_cli_main.py` (new)

---

### Task 7: Delete TypeScript tool wrappers and confirm direct Python execution

**Type:** backend
**Estimated scope:** small
**Dependencies:** Task 5

**Status:** implemented in Issue #162 / PR #172

**Description:**

Delete all files under `.opencode/tools/*.ts`. Verify that the orchestrator (Task 5) imports and calls the underlying `src/tools/*.py` and `src/application/services/` modules directly, with no subprocess invocation. Retain the standalone CLI behaviour of `src/tools/*.py` for ad-hoc shell use (argparse entry points stay).

**Acceptance Criteria:**

- [x] `.opencode/tools/` is empty except for `.gitkeep`
- [x] `grep -r "subprocess" src/presentation/` returns no results (orchestrator must not shell out)
- [x] Ad-hoc execution `python -m src.tools.wiki_search --story test ...` still works
- [x] No test fails because of the deletion

Current implementation note: runtime orchestration now imports Python modules directly from `src/presentation/` and `src/tools/`. The standalone `src/tools/*.py` CLIs remain available for shell use.

**Key Files:**

- `.opencode/tools/*.ts` (delete)

---

### Task 8: Build Textual TUI shell with streaming output and approval gate

**Type:** frontend
**Estimated scope:** large
**Dependencies:** Tasks 4, 5, 6

**Description:**

Create `src/presentation/tui.py`. Textual `App` with CSS grid layout:

- Header: story title + savepoint indicator
- Left panel: phase list with per-phase status (pending/running/complete/error)
- Center panel: `RichLog` streaming LLM output token-by-token
- Right panel (toggleable): wiki context — entity matches, wikilink traversal results, and detail-level selections for the phase being executed
- Footer: `Input` widget hidden by default; revealed when an approval gate is active

A `@work(thread=True)` worker runs the orchestrator synchronously (bridging `asyncio.run` inside the worker thread). A `TokenStreamBus` subscriber forwards deltas to `RichLog.write` via `call_from_thread()`. A TUI-backed `ApprovalGate` implementation reveals the `Input` widget, awaits `Input.Submitted`, and resolves the gate. A `WikiContextBus` primitive (companion to `TokenStreamBus`, added in Task 4's wake) forwards context-assembly events to the wiki panel.

Keybindings: `Ctrl+C` graceful cancel (cancels worker, writes in-flight savepoint), `Ctrl+S` manual savepoint, `Ctrl+W` toggle wiki context panel, `Enter` submit approval.

**Acceptance Criteria:**

- [ ] `python -m src.presentation.cli.main tui --story test_story` launches the app
- [ ] LLM output is visible streaming token-by-token in the right panel during chapter generation
- [ ] Phase list updates in real time as phases transition
- [ ] Approval gate reveals input widget; typing `approve` / `reject` / `revise <text>` resolves the gate
- [ ] Wiki context panel updates in real time during phases that assemble context (chapter generation, wiki maintenance)
- [ ] `Ctrl+W` toggles the wiki panel visibility
- [ ] `Ctrl+C` cleanly cancels and exits with a final savepoint written
- [ ] Snapshot test using Textual's `Pilot` covers: initial render, phase transition, streaming append, wiki panel update, gate activation, approval submission

**Key Files:**

- `src/presentation/tui.py` (new)
- `src/presentation/tui_primitives.py` (new — `TextualApprovalGate`, token bridge)
- `tests/unit/test_tui.py` (new, uses `textual.pilot`)

---

### Task 9: Remove OpenCode runtime artefacts and update build configuration

**Type:** full-stack
**Estimated scope:** small
**Dependencies:** Tasks 7, 8

**Status:** implemented in Issue #164 / PR #175

**Description:**

Delete OpenCode and Node.js runtime artefacts:

- `.opencode/` (directory)
- `opencode.json`
- `package.json`, `package-lock.json`
- `tsconfig.json`
- `vitest.config.ts`
- `skills-lock.json` (if OpenCode-specific)
- `node_modules/` entries in `.gitignore` (retain entries themselves for safety, just ensure no referenced node_modules)

Update `pyproject.toml` to reflect Python-only toolchain. Pin:

- `textual>=6.0,<7.0`
- `openai>=1.0`
- `httpx` (transitive, but pin lower bound)
- Keep existing `pydantic`, `pyyaml`, `chromadb` pins

Current implementation note: `.opencode/`, `opencode.json`, `package.json`, `package-lock.json`, `tsconfig.json`, and `vitest.config.ts` are deleted. `pyproject.toml` now declares `textual>=6.0,<7.0` and `openai>=1.0`, and `requirements.txt` pins `textual>=6.0,<7.0`. `skills-lock.json` remains because it is not part of the removed OpenCode runtime surface.

**Acceptance Criteria:**

- [x] Listed OpenCode and Node.js runtime files/directories are removed
- [x] `pyproject.toml` declares all new dependencies
- [x] Fresh clone + `pip install -e .` produces a working `story-writer` console command
- [x] No references to `.ts`, `node`, `npm`, `opencode` in `pyproject.toml`, `README.md`, or top-level config

**Key Files:**

- Various deletions
- `pyproject.toml` (edit)
- `.gitignore` (review)

---

### Task 10: Update documentation — remove OpenCode references, document new entry points

**Type:** documentation
**Estimated scope:** medium
**Dependencies:** Task 9

**Description:**

Update all documentation to reflect the new Python-native architecture:

- `README.md`: new quick-start with `pip install -e .` and `story-writer tui` / `story-writer run --batch`
- `AGENTS.md`: rewrite the Architecture section; remove "Tools are TypeScript wrappers" language; add Textual TUI + Python orchestrator description
- `.github/copilot-instructions.md`: remove OpenCode references from stack table, reword conventions, drop TypeScript/ESLint guidance
- `docs/manual.md`: rewrite the usage section for TUI and CLI
- `docs/tools.md`: remove or rewrite — no longer describing TypeScript wrappers
- `docs/features/*.md`: remove OpenCode-specific terminology; rename "agent" to "pipeline phase" where appropriate
- `docs/planning/opencode-migration/`: add a top-level note marking the doc set as superseded by `docs/planning/python-native-migration/`

**Acceptance Criteria:**

- [ ] `grep -ri "opencode" README.md AGENTS.md docs/ .github/` returns no hits except in `docs/planning/opencode-migration/` and `docs/planning/adr/` (historical records)
- [ ] `grep -ri "TypeScript" README.md AGENTS.md docs/` returns no hits
- [ ] `docs/planning/opencode-migration/` has a top-level `SUPERSEDED.md` or prominent banner pointing to the new PRD/ADR
- [ ] A new operator can follow `README.md` to install and run a story end-to-end in the TUI

**Key Files:**

- `README.md`
- `AGENTS.md`
- `.github/copilot-instructions.md`
- `docs/manual.md`, `docs/tools.md`, `docs/features/*.md`
- `docs/planning/opencode-migration/SUPERSEDED.md` (new)

---

### Task 11: End-to-end integration test against LM Studio

**Type:** testing
**Estimated scope:** medium
**Dependencies:** Tasks 5, 6, 7

**Description:**

Add `tests/integration/test_end_to_end_headless.py`. Uses a minimal two-chapter story prompt, runs `python -m src.presentation.cli.main run --story e2e_test --batch` against a live LM Studio endpoint, and asserts:

- Exit code 0
- All expected savepoints exist (`init`, `outline`, at least one chapter savepoint, `assembly`)
- Final assembled story file exists and contains at least two chapter headers
- Test completes within 10 minutes on the target local LLM

Marked `@pytest.mark.integration @pytest.mark.slow` so CI can skip by default.

**Acceptance Criteria:**

- [ ] Test file runs standalone via `pytest tests/integration/test_end_to_end_headless.py -v -m integration`
- [ ] On a fresh working copy with LM Studio running, test passes reliably
- [ ] Test cleans up its `e2e_test` story directory on both success and failure

**Key Files:**

- `tests/integration/test_end_to_end_headless.py` (new)
- `tests/integration/conftest.py` (extend if needed for LM Studio health check)

---

### Task 12: Remove OpenCode plugins and runtime harness

**Type:** backend
**Estimated scope:** small
**Dependencies:** Task 9

**Status:** implemented in Issue #164 / PR #175

**Description:**

Delete `.opencode/plugins/story-compaction.ts` and `.opencode/_run.ts`. Both are OpenCode-internal:

- `story-compaction.ts` estimates token budgets for OpenCode's conversation-history compaction. The Python harness has no free-floating orchestrator conversation to compact (pipeline phases are bounded LLM calls).
- `_run.ts` is subprocess-invocation boilerplate for running Python tools from OpenCode, obsolete once the orchestrator calls Python in-process.

No Python port required. This task is effectively covered by Task 9's deletion of `.opencode/`, but is tracked separately so the rationale is explicit in commit history.

Current implementation note: deleting `.opencode/` removed both `.opencode/plugins/story-compaction.ts` and `.opencode/_run.ts` with no Python replacement.

**Acceptance Criteria:**

- [x] `.opencode/plugins/` is deleted
- [x] `.opencode/_run.ts` is deleted
- [x] Commit history captures this task and the PRD rationale

**Key Files:**

- `.opencode/plugins/story-compaction.ts` (delete)
- `.opencode/_run.ts` (delete)

---

### Task 13: Migrate or remove OpenCode commands and skills

**Type:** backend
**Estimated scope:** small
**Dependencies:** Task 9

**Status:** implemented in Issue #164 / PR #175

**Description:**

Review `.opencode/commands/` and `.opencode/skills/`. Determine retention on a per-file basis:

- Commands that compose tool calls: reimplement as CLI subcommands or helper functions if still valuable.
- Skills that are operator reference material: relocate to `docs/` as Markdown guides if still valuable.

Conservative default: delete unless explicitly preserved.

Current implementation note: `.opencode/commands/` and `.opencode/skills/` are deleted. Reusable command prompt bodies now live in `prompts/agents/continue.md` and `prompts/agents/regenerate.md`. Reusable skill references now live under `prompts/skills/`.

**Acceptance Criteria:**

- [x] `.opencode/commands/` and `.opencode/skills/` are empty or deleted
- [x] Any preserved content has been relocated under `prompts/agents/` or `prompts/skills/`
- [x] `.github/skills/` (if OpenCode-specific) is reviewed for the same treatment

**Key Files:**

- `.opencode/commands/*.md`, `.opencode/skills/*.md` (delete or relocate)

---

## Execution Order Summary

**Parallel batch A (independent):** Tasks 1, 2, 3

**Parallel batch B (depend on A):** Task 4 (needs 3)

**Sequential:** Task 5 (needs 1, 2, 3, 4) → Task 6 (needs 5) → Task 7 (needs 5) → Task 8 (needs 4, 5, 6)

**Cleanup batch (depend on 7, 8):** Task 9 → Task 10, 11 (parallel) → Tasks 12, 13 (parallel cleanup)

Suggested delivery cadence: one task per PR, merged to a long-lived `feat/python-native` branch. Final PR merges the branch to `main` after Task 11 passes.
