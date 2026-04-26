# Review Checklist — Shared Protocol

> Shared Phase 2–7 review checklist for agents performing code reviews, both local (diff-based) and PR-based (GitHub API). Used by `code-review-process.md` and `pr-review-process.md`.

---

## Review Phases

### Phase 2 — Code Review

Review each changed source file systematically:

#### General

- [ ] Code follows project conventions defined in `.github/copilot-instructions.md`
- [ ] Naming conventions are consistent with the codebase
- [ ] No overly complex functions — decompose if needed
- [ ] No code duplication — extract shared logic where appropriate
- [ ] Import ordering and placement follows project conventions — imports at module level, not inside functions or loops
- [ ] **Behavioral parity in sibling implementations** — when the PR introduces a new class that mirrors an existing sibling (same interface, analogous use case — e.g., an async provider alongside a sync one), verify that default values, post-processing steps, and error paths match. Silent divergence (e.g., a different `temperature` default for JSON-mode generation, missing think-tag filtering) creates provider-switch hazards for callers that route between implementations. Compare each method's significant branches against the sibling. (Source: issue #159, PR #168 — `OpenAIAsyncProvider` lacked the `temperature=0` override for JSON-mode generation present in `OpenAICompatibleProvider`; only one of three reviewers caught it.)
- [ ] **API signature changes** — if a function, method, or constructor signature changed (parameter added/removed/renamed), grep the workspace for callers: `grep -rn 'ClassName\|function_name' . --include='*.py' --include='*.ts'`; include root-level scripts (`test_*.py`, `demo_*.py`, `migrate_*.py`) — these call `src/` APIs directly and are not in the diff because they were not updated (broken callers never appear in the changed-file list). **Also applies to TypeScript tool wrapper Zod schema changes:** if a Zod field transitions from `.optional()` to required (or a new required field is introduced), grep all agent instruction files for invocations of that tool (`grep -rn 'tool-name' .opencode/agents/ .opencode/skills/`) and verify every call site passes the now-required field — agent call sites live in Markdown files and are never in the diff when the gap is in a pre-existing call site. (Source: issue #133, PR #137 — `operation` made required in `story-assembler`; Phase 8 call site omitted the field and was not in the diff.) **Also applies to tool return-contract changes:** if a tool's default return shape changes (e.g. full content → compact reference, fields added/removed/renamed in the returned dict, list → paginated object), grep all agent instruction files for invocations of the tool (`grep -rn 'tool-name' .opencode/agents/ .opencode/skills/`) and audit each call site's post-call handling. Agent instructions that consume the return value in English prose ("assign the returned text to X", "the tool returns Y") silently continue to run after a return-shape narrowing and persist the wrong value to state. Verify each call site either (a) passes the opt-in flag that preserves the old shape (e.g. `includeContent: true`), or (b) follows the new shape — loads from savepoint, reads the expected nested field, etc. (Source: issue #152, PR #153 — `scene-writer` `revise`/`assemble-chapter` switched to compact refs by default; three agent call sites consumed the old shape and would have written reference JSON into chapter state as prose.)
- [ ] **Asyncio coordination primitives** — for any class that maintains `_closed` state with a queue, sentinel, or Future: (1) verify `_closed` is checked at **every entry point** — write-side (`emit()`, `put_nowait()`) must raise or return early when closed rather than queuing silently; read-side (async generator start, consumer loop entry) must guard with `if self._closed and self._queue.empty(): return` — a sentinel terminates the *current* iteration pass but a re-entrant consumer blocks forever waiting for a second sentinel that will never arrive; (2) if a gate/latch creates its `asyncio.Future` lazily inside `await_decision()`, verify `resolve()` buffers the pending result rather than checking `hasattr(self, "_future")` — lazy Future creation makes pre-await resolution a no-op and causes the waiter to deadlock with no error signal. The correct fix is to hold a `_pending` variable in `__init__` and return it immediately if already set when `await_decision()` is first called. (Source: issue #160, PR #170 — both patterns independently identified by all three reviewers.)
- [ ] **`isinstance()` over `type(x).__name__`** — any conditional that checks `type(x).__name__ == "ClassName"` is fragile: it returns `False` silently for a valid subclass instance (which has a different `__name__`) and breaks with no error when the class is renamed. Always use `isinstance(x, ClassName)` for type dispatch and gate/mode checks. The pattern produces no lint or type error — it fails silently in production when the type hierarchy changes. Import the class if needed to construct the `isinstance()` check. (Source: issue #161, PR #171 — flagged by Claude and Gemini as M-W-01.)
- [ ] **Serialization round-trip completeness** — when a PR adds a new key or variant to any config registry (e.g. a new entry in `valid_providers`, a new enum case, a new subcommand), verify **all three serialization surfaces** are updated: (1) the **validation registry** (`__post_init__` or equivalent — rejects unknown keys at construction time); (2) the **forward serializer** (`to_string()`, `__str__`, `serialize()` — maps the key to its stored/wire representation); (3) the **reverse deserializer** (`from_string()`, `from_dict()`, `deserialize()` — maps stored form back to the key). Missing (1) fails fast at construction. Missing (2) silently writes the wrong stored value. Missing (3) silently fails to reload stored state. Findings in this category are **Warning minimum** — they represent broken state-persistence contracts, not style preferences. A synthesis that receives a Suggestion rating from one model and Warning/Critical from the majority should adopt the majority severity for serialization round-trip defects. (Source: issue #169, PR #178 — `to_string()` hardcoded `"openai-compat"` and `from_string()` lacked `openai-async://` → `openai_async` mapping after adding `openai_async` to `valid_providers`; Claude rated Suggestion, GPT and Gemini rated Warning/Critical.)

#### Architecture

- [ ] Separation of concerns — business logic not in controllers/handlers
- [ ] Proper use of dependency injection where applicable
- [ ] No tight coupling between unrelated modules
- [ ] Follows the project's architectural patterns (see ADRs if any)

#### Data Access

- [ ] Input validation — all user input validated at system boundaries
- [ ] Proper error handling — no swallowed exceptions
- [ ] Database queries are parameterized (no raw user input in queries)
- [ ] Missing indexes on foreign keys and frequently queried columns
- [ ] Migrations have proper rollback support
- [ ] **Batch/composite operations** — if a function wraps multiple state-changing operations, verify: (1) pre-flight snapshot or backup is taken before the batch starts, (2) failures mid-batch trigger rollback or at minimum leave state consistent, (3) a final sync/consistency check runs after the batch completes
- [ ] **LLM JSON parsing guards** — in any code that calls `json.loads()` on LLM output and extracts fields from the result, verify all three guards are present: (1) `isinstance(data, dict)` check immediately after `json.loads()` — valid JSON can parse to a list, number, or `None`, all of which crash on `.get()`; (2) `data.get("key") or {}` / `or []` (not `data.get("key", {})`) — the default argument does not apply when the key is present with an explicit JSON `null` value; (3) `if not isinstance(item, dict): continue` before calling `.get()` on each item in a list extracted from LLM output — the LLM may return scalar values interleaved with objects. All three defects are invisible to ruff, mypy, and type checks; only explicit null-payload tests reveal them. (Source: issue #184, PR #197 — consistency-checker; gotchas #032–034.)

#### Agent Instructions

- [ ] **Tool call contracts** — for any new or modified agent instruction file that includes tool invocations, verify each call against the tool source before accepting: (a) operation names match the Python CLI dispatch (grep `src/tools/*.py` for valid operation values), (b) parameter key names match the Zod field names in the TS wrapper (`.opencode/tools/*.ts`) — mismatched keys pass Zod silently; (c) any omitted parameter is confirmed safe — check the tool's default value and verify it produces correct behaviour in this context (e.g. `mode` defaults to `"outline"` in `critique-runner`; a chapter-context agent that omits `mode` will evaluate the wrong artifact type without erroring); (d) any TS parameter marked `.optional()` that is omitted for a specific operation — verify in the Python source that the field is genuinely optional for the active `operation`; Python tools use conditional validation (`if args.operation == "revise" and not args.scene_num: sys.exit(2)`) that the Zod schema cannot represent; `.optional()` reflects TS schema permissiveness only; (e) any parameter passed to the tool is verified to be consumed by the Python backend for the active operation — TS wrappers may accept parameters via Zod that the Python CLI never reads in certain operation branches; passing an accepted-but-ignored parameter produces silently incorrect results; verify by checking `argparse.add_argument` declarations and the operation dispatch branch in `src/tools/*.py`
- [ ] **Intra-step variable cross-reference** — in multi-step agent workflows, verify that every field name stored in an earlier step (e.g. `Store X as foo_bar`, `record: foo_bar from data.foo_bar`) is used with the **exact same name** in all later steps and in the final return JSON. A mismatch (`store as verdict_code`, return as `verdict`) is a silent schema error: the orchestrator reads the correct key from the returned payload and receives `null` with no tool-level error. Scan each multi-step workflow for stored variable names by searching for `Record`, `Store`, `record:` prose, then verify every reference to that name in later steps and the final JSON schema. (Source: issue #132, PR #136 — `verdict_code` stored in Step 3, `verdict` erroneously in Step 4 return JSON.)
- [ ] **Numbered step continuity** — in agent or skill workflow sections that use a numbered list (`1.`, `2.`, ...), verify the literal numerals are contiguous with no gaps. Markdown ordered-list rendering auto-renumbers in most viewers and visually hides gaps, but LLM agents reading the file at runtime see the source numerals; a list reading `1.`, `2.`, `8.` after a refactor produces ambiguous "next step" reasoning. After any PR that merges, removes, or collapses workflow steps, scan each modified `.opencode/agents/*.md`, `.opencode/skills/*/SKILL.md`, and `.github/agents/*.md` workflow section for `^\d+\.` runs and confirm continuity. Also verify no step uses letter-suffix notation (`2a.`, `2b.`) — letter suffixes create identical parsing risks and are not allowed; promote to a distinct integer step or demote to an indented sub-bullet instead. (Sources: issue #144, PR #145 — `wiki-maintainer.md` left step 8 after a collapse; issue #156, PR #157 — `chapter-outline-expander.md` used `2a.` for a new step; both patterns flagged unanimously.)
- [ ] **Agent call site parameter casing matches Zod schema exactly** — Zod field names are case-sensitive. When an agent or skill instruction file describes a tool call (`Call wiki-extract (operation: ..., chapterNumber: N, ...)`), the parameter keys in the call body must match the camelCase Zod field declarations in the TS wrapper character-for-character. A snake_case rendering of the same word (`chapter_number`) is a distinct key as far as Zod is concerned and produces `Error: <camelCase> is required` at runtime, with the entire workflow becoming non-functional. Do not confuse this with the issue #22 batch-payload convention — direct tool call params are camelCase; JSON keys *inside* a `payload` string use snake_case. (Source: issue #144, PR #145 — `wiki-maintainer.md` Mode 2 used `chapter_number` and `chapter_text_path` while the Zod schema declared `chapterNumber` and `chapterTextPath`; flagged unanimously.)
- [ ] **Multi-path pipeline return convergence** — in agent workflows that branch across multiple generation strategies (e.g. chunked vs. non-chunked) AND have optional loops (e.g. critique enabled/disabled), verify the final return phase references a **single shared variable** updated through each phase, not path-specific named variables. A Phase N return clause naming `merged_outline` for the chunked path and `refined_outline` for the critique path silently discards critique refinements when both paths are active simultaneously. The fix pattern: assign a shared variable (e.g. `current_outline`) at the start of the generation phase and update it at every phase transition; the return phase always returns the shared variable. Reviewers: look for any return spec that names different variables conditioned on which branch was taken. (Source: issue #156, PR #157 — Phase 5 returned `merged_outline` unconditionally on the chunked path, discarding critique-loop refinements; missed by Claude, flagged as Critical by GPT and Gemini.)
- [ ] **Validation guard layer parity** — when a PR introduces validation guards at multiple layers protecting the same invariant (e.g. orchestrator receiving a subagent return value AND the subagent reading its own input from state), verify all guards apply **identical conditions**. A guard at layer A (orchestrator) that rejects `null` and `{}` but omits whitespace-only strings is weaker than a layer B guard (planner) that rejects all three; the partial upstream guard allows invalid values through to layer B — one phase later, after potentially irreversible state writes. Read each guard condition side-by-side against all sibling guards and confirm the conditions match character-for-character. (Source: issue #156, PR #157 — orchestrator initial guard omitted whitespace-only check present in `story-planner`; flagged by GPT and Gemini, missed by Claude.)

---

### Phase 3 — Frontend Review (if applicable)

Review each changed frontend file systematically:

- [ ] Follows the project's component conventions
- [ ] Proper typing — no `any` types (TypeScript projects)
- [ ] Accessibility — ARIA attributes where needed
- [ ] No hardcoded URLs — use routing helpers
- [ ] Error states handled in forms and async operations
- [ ] Loading/processing states shown during async operations
- [ ] **Status/state enum completeness** — for any widget, component, or UI element that renders a finite set of states (status, mode, phase, result), verify a distinct and correct visual representation exists for *every* value in the enum or set — including error, failure, and cancelled states. Trace each non-success exit path through the rendering code and confirm the correct label, colour, and icon are applied. A missing branch typically falls through to the default (often the success branch), producing a misleading "complete" or "ok" indicator on failure. (Source: issue #163, PR #174 — error-state rendered as green "Complete"; caught by GPT reviewer only; Claude and Gemini missed it.)

---

### Phase 4 — Security Review

Check for common security issues:

- [ ] **Authorization** — every action checks permissions
- [ ] **Input validation** — all user input validated
- [ ] **`_validate_story_name()` at story-name entry points** — if the PR introduces a new Python function that accepts a user-supplied story name and constructs file paths from it, verify `_validate_story_name()` from `src/tools/_io.py` is called at the entry boundary. This function rejects path traversal sequences (`../` etc. via `is_relative_to()`) and normalises story directory names to kebab-case. Every existing story-facing tool (savepoint_manager, story_state, wiki tools, critique_runner) uses this guard; a new module that omits it creates a path traversal surface (CWE-22) consistent with two-thirds of review models missing the absence in issue #161. (Source: issue #161, PR #171 — flagged as Warning by GPT only; missed by Claude and Gemini.)
- [ ] **SQL injection** — parameterized queries, no raw SQL with user input
- [ ] **XSS** — no rendering of untrusted HTML content
- [ ] **CSRF** — protection in place for state-changing operations
- [ ] **Mass assignment** — only expected fields are writable
- [ ] **File uploads** — validated type, size, stored securely
- [ ] **Sensitive data** — no credentials, API keys in code
- [ ] **Access control** — proper scoping for multi-user/multi-tenant systems

---

### Phase 5 — Testing Review

Check test coverage:

- [ ] **New features** — have corresponding tests
- [ ] **Test conventions** — follow project testing patterns (see `copilot-instructions.md`)
- [ ] **Edge cases** — error paths tested
- [ ] **No skipped tests** — all tests run
- [ ] **Assertions** — meaningful assertions, not just absence of errors
- [ ] **Live test skip guards** — if the PR adds any live integration tests (`test_*_live.py` or equivalent), verify each test class or function applies the suite-standard `llm_available` fixture from `tests/integration/conftest.py` (or an equivalent `pytest.mark.skipif`). A live test without a skip guard hard-fails on every unprovisioned machine while every other integration test in the suite skips cleanly. The default `pytest` run scoping to `tests/unit/` in `pyproject.toml` is insufficient mitigation — a developer running `pytest tests/` or `pytest tests/integration/` explicitly encounters a hard failure instead of a skip. (Source: issue #159, PR #168 — flagged unanimously by all three reviewers as U-W-01.)

---

### Phase 6 — Performance Review

Check for performance issues:

- [ ] **N+1 queries** — eager loading or batch queries where applicable
- [ ] **Database indexes** — on foreign keys and query columns
- [ ] **Caching** — appropriate for expensive operations
- [ ] **Asset size** — no large unnecessary imports
- [ ] **Pagination** — for large result sets

---

### Phase 7 — Documentation Review

Check documentation:

- [ ] **Docblocks** — public methods documented
- [ ] **README** — updated for new features
- [ ] **ADRs** — architectural changes recorded
- [ ] **Inline comments** — for complex logic
- [ ] **Table/prose parity** — if a new entry (agent, subagent, tool, command) is added to a reference table, verify a corresponding prose subsection (`###`) exists for it in the same document; a table row without a prose section leaves the registry asymmetric and the feature doc incomplete
- [ ] **Code matches docs** — if documentation describes a behavior (validation, fallback, default), verify the implementation actually provides it; a mismatch means the documented contract is a false promise
- [ ] **Code example drift** — if this PR changes the semantics of an API method, removes a method, or makes a field immutable, grep docs (`.github/skills/`, `docs/`, `.github/notes/`) for code examples that use the old pattern; examples using removed or changed methods silently become misleading. **Also when adding a new config registry value** (provider key, model role, valid enum value), grep `docs/features/` and `docs/` for code or YAML blocks that reference the same key namespace — an existing example may omit the new key or use an earlier working name. (Source: issue #169, PR #178 — `docs/features/openai-async-provider.md` used `openai_compatible` key in examples after `openai_async` was the correct key for the new provider.)
- [ ] **Role/taxonomy renames** — if a role or taxonomy name was changed in prose (e.g. a role table), grep the same file for old names in embedded code examples, comments, and annotation blocks; stale names in examples are equally misleading
- [ ] **File paths and links** — verify all file paths, directory tree diagrams, and relative links in documentation exist on disk and resolve correctly from the doc's location
- [ ] **Orchestrator-subagent companion sync** — if this PR adds or removes a subagent dispatch in the orchestrator, verify `story-pipeline/SKILL.md` is updated: (1) the subagent count in the overview sentence ("The pipeline uses N subagents"), (2) the reference table row, and (3) the constraint sentence ("These are the only N subagents the orchestrator may dispatch"); a stale constraint sentence is an authoritative false statement that blocks dispatch of the new agent
- [ ] **Gotcha entries superseded by the PR** — if this PR implements or fixes a behaviour that is described in `.github/notes/gotchas.md`, verify the matching entry has been updated or removed and any ChromaDB-indexed copy is reindexed. Gotchas are an authoritative live knowledge source consulted by planning and debugging agents; a stale entry after a fix-PR misleads agents into defensive workarounds that the new implementation does not need. (Source: issue #152, PR #153 — `gotchas.md` entry #005 still warned about the missing auto-savepoint that the PR added.)
- [ ] **Zod `.describe()` text reflects current semantics** — for any TS tool wrapper whose Python backend changed parameter semantics (required ↔ optional, default value, conditional validation, auto-load behaviour), verify the corresponding Zod field `.describe(...)` string in `.opencode/tools/*.ts` has been updated. The description is surfaced to the LLM at call time and becomes part of the tool contract; a stale description causes over-specification or misuse even when the schema itself is correct. (Source: issue #152, PR #153 — `sceneContent` Zod description said "required for revise" after the backend was changed to auto-load from savepoint when omitted.)
