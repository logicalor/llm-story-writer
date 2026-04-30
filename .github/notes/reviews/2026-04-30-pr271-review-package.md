== REVIEW PACKAGE ==

=== BRANCH ===
fix/issue-263-stale-opencode-tools-refs

=== COMMIT LOG ===
701b036 docs(agents): sweep stale .opencode/tools/ references from agent bodies (#263)
53ccedb docs(agents): additional stale-reference cleanup (#263)

=== CHANGED FILES ===
.opencode/agents/coder.md
.opencode/agents/documenter.md
.opencode/agents/orchestrator-v3.md
.opencode/agents/planner.md

=== DIFF ===
```diff
diff --git a/.opencode/agents/coder.md b/.opencode/agents/coder.md
index ce91d8c..85e67a9 100644
--- a/.opencode/agents/coder.md
+++ b/.opencode/agents/coder.md
@@ -1,5 +1,5 @@
 ---
-description: "Implements code changes for the project — Python domain logic, TypeScript OpenCode tool wrappers, prompt templates, wiki tools, and infrastructure. Dispatched by the Orchestrator during the implementation phase."
+description: "Implements code changes for the project — Python domain logic, prompt templates, wiki tools, and infrastructure. Dispatched by the Orchestrator during the implementation phase."
 model: openrouter/moonshotai/kimi-k2.6
 mode: subagent
 hidden: false
@@ -58,7 +58,7 @@ Read **`.github/agents/_shared/communication.md`** — use caveman for chat/prog
    - **When merging, removing, or collapsing steps inside a numbered workflow section** of an agent or skill file (`.opencode/agents/*.md`, `.opencode/skills/*/SKILL.md`, `.github/agents/*.md`) — renumber every surviving step in the same list so the sequence stays contiguous. Markdown ordered-list rendering auto-renumbers in most viewers and visually masks gaps, but the literal numerals are what LLM agents read at runtime. A list reading `1.`, `2.`, `8.` after a refactor is a defect, not a style issue: agents executing step-tracking reasoning ("now do step N+1") may skip ahead or miscount across the gap. Search the modified file for `^\d+\.` runs after collapsing steps and confirm continuity. (Source: issue #144, PR #145 — Mode 1 and Mode 2 workflows in `wiki-maintainer.md` collapsed steps 1–7 to two but left step 8 unrenumbered.)
    - When deleting a runnable setup or migration script (`setup_*.sh`, `init_*.py`, `migrate_*.py`, `bootstrap.sh`, etc.) — verify that any configuration or setup documentation referencing that script still provides standalone sufficient rebuild guidance after the reference is removed. The script removal may create a _coverage gap_ — the documentation no longer describes any rebuild path at all — not merely a stale reference.
    - **CLI flag `help=` text accuracy and cross-subcommand consistency:** When implementing or modifying a CLI flag (argparse `add_argument(..., help=...)`)， verify (a) the help string accurately reflects what the backend actually does — not design intent — and (b) any flag that appears on multiple subcommands with identical semantics carries the same (or explicitly differentiated) help text on every subcommand. A help string that overstates capability (e.g., "resume from" when the backend only validates against the supplied value and always uses the latest savepoint) is a correctness defect, not a style issue. Divergent help text across subcommands implies different behaviour and confuses users. (Source: issue #187, PR #200 — TUI `--savepoint` help said "resume from" but backend only validates; text differed between `tui` and `resume` subcommands.)
-   - **When deleting TypeScript tool wrappers (`.opencode/tools/*.ts`)** — after deletion, sweep `prompts/agents/` for references to the deleted tool names. Agent prompt files frequently reference tool names directly in workflow prose and step instructions; these become stale references that mislead the runtime agent. Run: `grep -r "deleted-tool-name" prompts/agents/ .github/agents/` for each deleted wrapper. Create a follow-up issue if time-of-deletion updates are out of scope. (Source: issue #162, PR #172 — 17 TS wrappers deleted; `prompts/agents/story-orchestrator.md` and sibling agents still referenced the deleted names; tracked as follow-up issue #173.)
+    - **When deleting Python tool scripts (`src/tools/*.py`)** — after deletion, sweep `prompts/agents/` and `.opencode/agents/` for references to the deleted tool names. Agent prompt files frequently reference tool names directly in workflow prose and step instructions; these become stale references that mislead the runtime agent. Run: `grep -r "deleted-tool-name" prompts/agents/ .opencode/agents/` for each deleted script. Create a follow-up issue if time-of-deletion updates are out of scope.
    - **When creating or substantially editing a planning document, PRD, or ADR** — before committing, verify that every `[text](path)` hyperlink resolves to an actual file in the repository. A link to a file that does not yet exist (e.g., a future ADR like `[ADR 007](./adr/007-python-native-orchestration.md)`) is a dead link defect at commit time. Either create the target file in the same commit, or replace the hyperlink with plain text and append `(to be created)`. (Source: issue #158, PR #167 — PRD committed with two broken references to docs/planning/adr/007-python-native-orchestration.md.)
    - When adding a new `import` statement or refactoring to use a shared module — verify that any import you remove is not still used elsewhere in the same file. A removed import that was also serving another callsite produces a runtime `NameError` that linters do not catch (ruff's `F401` flags only genuinely unused imports; the removed import *was* in use at the other site).
    - **When adding a new import to a file that already contains inline (function-body) imports** — place the new import at module level regardless of the pre-existing inline style. Do not match existing inline placement — matching local deviations introduces new style debt and triggers review findings. Instead, record the pre-existing inline imports as an out-of-scope observation in your handoff summary (per Rule 11) for the Orchestrator to track separately.
@@ -72,7 +72,7 @@ Read **`.github/agents/_shared/communication.md`** — use caveman for chat/prog
    - **Scope-limited commands:** Run formatters and linters only on the files you have modified, not repo-wide. Use `ruff format path/to/file.py` (or a specific directory) rather than `ruff format .`. Repo-wide runs silently format unrelated files, inflating the diff with non-functional changes.
    - **Pre-commit scope audit:** Before committing, run `git diff --name-only` (or `git diff --cached --name-only` after staging) to confirm the changed file list matches your task scope. If `ruff format .` ran and touched out-of-scope files, revert them with `git checkout -- path/to/out-of-scope-file` before committing. (Source: issue #162, PR #172 — `ruff format .` touched `tests/unit/test_openai_async_provider.py` during a review-fix cycle; required manual revert with `git checkout`.)
 9. **Security: subprocess, path, and input validation.**
-   - **TypeScript tool wrappers:** Never use `execSync()` or `exec()` with string concatenation for subprocess calls. Use `execFileSync()` or `spawnSync()` with explicit argument arrays — these bypass the shell and prevent command injection (CWE-78).
+    - **Subprocess invocation:** Never use `execSync()` or `exec()` with string concatenation for subprocess calls. Use `execFileSync()` or `spawnSync()` with explicit argument arrays — these bypass the shell and prevent command injection (CWE-78).
    - **Python tools with file paths:** When resolving user-provided names to file paths, always validate the resolved absolute path starts with the intended base directory using `resolved.resolve()` and `.is_relative_to(base)`. Reject any path that traverses outside the base (CWE-22).
    - **Boundary validation depth:** When validating data at system boundaries (LLM output, file reads, API responses), validate both the container type *and* the element types. E.g., checking `isinstance(result, list)` is insufficient — also verify each element matches the expected type (e.g., `all(isinstance(el, str) for el in result)`).
    - **Shared utility path components:** When writing shared functions (e.g., `_wiki.py`, `_io.py`) that accept parameters used as directory names, glob patterns, or path segments, validate each component individually — not just the final resolved path. Reject `..`, `/`, and characters outside the expected set (e.g., `^[a-z0-9_-]+$` for slugs). Apply `is_relative_to()` as a belt-and-suspenders final check.
@@ -87,7 +87,7 @@ Read **`.github/agents/_shared/communication.md`** — use caveman for chat/prog
     - **Schema conformance** — parameter names, types, and required fields match the actual framework schemas.
     - Grep the project for existing examples of the same artifact type and replicate the integration pattern.
     - **Textual `@work(thread=True)` cancellation messages:** When writing user-facing status messages for Textual threaded worker cancellation, do NOT use the word "cancelled" or any phrasing that implies immediate termination. Textual `@work(thread=True)` workers are OS threads — `worker.cancel()` sets a cancellation flag; the thread continues running until its current phase or iteration completes. The accurate message is "Cancellation requested. Pipeline will finish its current phase before stopping." or equivalent. This generalises to any non-cooperative concurrency model (threads, processes) where cancellation is advisory rather than preemptive. (Source: issue #187, PR #200.)
-    - **When writing or editing any agent or skill content** that includes tool operation names, parameter types, or return formats — verify each against the actual Python source (`src/tools/*.py`) and TypeScript wrapper (`.opencode/tools/*.ts`). Verify: (a) valid operation values by reading the Python dispatch/enum; (b) Zod parameter types (`z.string()` vs `z.object()`) from the TS wrapper; (c) return value shape from Python `return` statements; (d) parameter key names match the exact Zod field names declared in the TS wrapper (`z.object({ step: ... })` means the key is `step:`, not `savepoint:`) — mismatched keys pass Zod silently and produce misleading runtime failures. **Case sensitivity counts as a key mismatch:** Zod field names are case-sensitive, so `chapterNumber` and `chapter_number` are distinct keys — passing the snake_case form when the schema declares camelCase produces `Error: chapterNumber is required` at runtime. The `data` parameter case (issue #22) is the inverse footgun: direct tool call params use camelCase (matching the Zod field) but JSON keys *inside* the `payload` string use snake_case (parsed downstream by Python). When authoring agent step body prose, copy the camelCase Zod field names verbatim from the TS wrapper — do not mirror the Python `--snake-case` CLI flag the script accepts. (Source: issue #144, PR #145 — Mode 2 step body used `chapter_number` / `chapter_text_path` while Zod declared `chapterNumber` / `chapterTextPath`; flagged unanimously by all three reviewers.) (e) when a parameter is marked `.optional()` in the Zod schema, verify in the Python source whether it is unconditionally optional or conditionally required based on the active operation — Python tools frequently use conditional argparse validation (`if args.operation == "X" and not args.param: sys.exit(2)`) that is not reflected in the TS `.optional()` declaration; omitting a conditionally required parameter produces a hard exit at runtime with no indication from the Zod schema. Wrong operation names and mismatched key names cause hard runtime failures invisible to lint or type checks.
+    - **When writing or editing any agent or skill content** that includes tool operation names, parameter types, or return formats — verify each against the actual Python source (`src/tools/*.py`). Verify: (a) valid operation values by reading the Python dispatch/enum; (b) return value shape from Python `return` statements; (c) parameter key names match the exact argument names the Python tool expects — mismatched keys are silently ignored or produce wrong output. **Case sensitivity counts as a mismatch:** passing `chapter_number` when the tool expects `chapterNumber` (or vice versa) causes a runtime failure. The `data` parameter case (issue #22) is the inverse footgun: direct tool call params may use camelCase (matching the OpenCode schema) but JSON keys *inside* the `payload` string use snake_case (parsed downstream by Python). When authoring agent step body prose, copy the parameter names verbatim from the Python `argparse` definition or function signature — do not mirror the Python `--snake-case` CLI flag the script accepts. (Source: issue #144, PR #145 — Mode 2 step body used `chapter_number` / `chapter_text_path` while the schema declared `chapterNumber` / `chapterTextPath`; flagged unanimously by all three reviewers.) (e) when a parameter looks optional in the agent-facing schema, verify in the Python source whether it is unconditionally optional or conditionally required based on the active operation — Python tools frequently use conditional argparse validation (`if args.operation == "X" and not args.param: sys.exit(2)`) that is not reflected in the agent schema; omitting a conditionally required parameter produces a hard exit at runtime. Wrong operation names and mismatched key names cause hard runtime failures invisible to lint or type checks.
 11. **Implement only the files listed in the dispatch.** The plan's task checklist defines the complete authorised scope of this dispatch. Do NOT modify, create, or delete files outside that list — no incidental improvements, no refactors, no abstractions, no "while I'm in here" changes to adjacent code. If you notice bugs, improvements, or technical debt in code you read while working, record them in your handoff summary under "Out-of-scope observations" but do not act on them. Every unauthorised change inflates the diff, pollutes the review, and may require manual revert work.
    - **Test expectation drift:** when your implementation legitimately changes an output contract (savepoint key names, stdout format, internal counts), tests asserting the old values will break. These are **expectation drift** — they are not bugs in the implementation, and fixing them is **in scope** even if test files are not listed in the plan. The rule bars incidental improvements; it does not bar fixing the tests your own implementation breaks. Distinguish from genuine regression failures — if a test reveals an unintended behaviour change, fix the implementation rather than the test.
    - **When a test file is in your dispatch scope** (plan-listed or expectation-drift) — always **extend** the file; never replace or overwrite it. Read the existing file first and record all current test method names; then add new methods or classes only. After writing, confirm every pre-existing method name still appears in the file. Deleting previously passing tests removes regression coverage and requires a full Test Writer re-dispatch to restore. (Source: issue #164, PR #175 — Coder replaced `test_prompt_relocation.py`, deleting 8 passing tests originally written for issue #5.)
@@ -120,19 +120,17 @@ When implementing a feature that spans multiple layers:
 
 1. **Python domain logic first** — entities, value objects, services, strategies in `src/`
 2. **Python tools second** — CLI-callable scripts in `src/tools/`
-3. **TypeScript wrappers third** — OpenCode tool definitions in `.opencode/tools/`
+3. **TypeScript wrappers third** — This step is retired per ADR 007; all tools are Python-native in `src/tools/`.
 4. **Prompt templates last** — Jinja2/text templates in `src/infrastructure/prompts/`
 
 This ensures each layer's dependencies exist before it references them.
 
-**When modifying an existing Python tool's CLI** (adding or removing `--` flags, changing positional arguments) — treat Python tools (step 2) and TypeScript wrappers (step 3) as an **atomic pair**. Read the TypeScript wrapper alongside the Python changes and update the Zod schema AND the `args` builder in `execute()` to expose every new parameter. New Python `--flags` not added to the wrapper schema are silently dropped; the Python tool falls back to defaults and produces wrong output with no error — invisible to lint, type checks, and Python-layer tests.
+**When modifying an existing Python tool's CLI** (adding or removing `--` flags, changing positional arguments) — update the agent-facing schema or dispatch layer that exposes the tool so that every new parameter is surfaced to calling agents. New Python `--flags` not reflected in the agent schema are silently dropped; the Python tool falls back to defaults and produces wrong output with no error — invisible to lint, type checks, and Python-layer tests.
 
 ## Code Patterns
 
 Follow the conventions defined in `copilot-instructions.md` for language-specific patterns.
 
-**TypeScript `data` parameter type:** TS tool wrappers that accept a JSON payload via a `data` parameter may declare it as `z.string()` (agent must pass a serialised JSON string: `data: "{}"`) or `z.object()` (agent passes an object literal: `data: {}`). These are not interchangeable — passing `{}` to `z.string()` causes a Zod validation error. Always read the `z.` declaration in the TS wrapper before documenting call examples or writing agent/skill files that include `data` call syntax.
-
 **Story state JSON loading:** When implementing `_load_story_state` helpers (or any function that reads `state.json` / chapter state files), treat `json.JSONDecodeError` as a fatal error — call `_error()` and exit. Never catch a JSON parse error and return `{}` or any other fallback value. Missing file (`state_path.exists() == False`) is expected on first run and warrants an empty-dict return; corrupt file is a data integrity failure and must surface immediately. Returning `{}` for a corrupt file silently clobbers all existing story progress on the next write.
 
 **Savepoint resume write symmetry:** When an operation writes results to story state (via `_set_nested` + `_write_state_atomic` or equivalent), its savepoint resume path must perform the same write. A resume path that loads from a savepoint and returns immediately without updating story state leaves the two stores out of sync: downstream operations reading state see a missing field even though the savepoint exists. Pattern: load content from savepoint → write to story state → return. Do not treat the resume path as "cache hit, skip side-effects" — the story-state write is not a side-effect of generation; it is a required synchronisation step.
diff --git a/.opencode/agents/documenter.md b/.opencode/agents/documenter.md
index ef3d188..13695d0 100644
--- a/.opencode/agents/documenter.md
+++ b/.opencode/agents/documenter.md
@@ -9,6 +9,7 @@ permission:
     "README.md": "allow"
     "AGENTS.md": "allow"
     ".github/copilot-instructions.md": "allow"
+    ".opencode/agents/**": "allow"
     "**": "deny"
   bash:
     "*": "deny"
@@ -63,7 +64,7 @@ The `docs/` directory should be organised as follows:
 | `docs/setup.md`            | Local development setup instructions                                    |
 | `docs/testing.md`          | Testing guide — test patterns, verification workflow, coverage expectations |
 | `docs/wiki-system.md`      | Wiki memory system — page format, YAML frontmatter, wikilinks             |
-| `docs/tools.md`            | OpenCode tool reference — TypeScript wrappers and Python scripts           |
+| `docs/tools.md`            | OpenCode tool reference — Python scripts           |
 | `docs/features/`           | Feature-specific documentation (one file per major feature)                 |
 | `docs/planning/`           | PRDs, task breakdowns, and planning artefacts                               |
 | `docs/planning/adr/`       | Architecture Decision Records                                               |
@@ -128,7 +129,7 @@ Replace `<old-term>` with the retired, introduced, or renamed layer, component,
 > - For relative links: test they resolve from the doc's directory (e.g., from `docs/` to `.github/` requires `../`).
 > - For tool output formats: read the Python tool's `cmd_*` functions to verify the exact JSON structure returned (dict vs array, field names, status codes).
 > - For file extensions: check the Python tool's save/load logic to verify the actual file format used on disk — do not infer from the domain name.
-> - For inventory tables (tools, collections, agents, categories): cross-check table entries against the actual source of truth on disk (e.g., `ls .opencode/tools/` for tool tables, `ls src/tools/` for script tables). Verify both that every row has a matching file AND that every file has a matching row — pre-existing missing entries compound with new additions to produce wrong counts.
+> - For inventory tables (tools, collections, agents, categories): cross-check table entries against the actual source of truth on disk (e.g., `ls src/tools/` for tool and script tables). Verify both that every row has a matching file AND that every file has a matching row — pre-existing missing entries compound with new additions to produce wrong counts.
 > - For agent family enumerations in prose (e.g., "the researcher family comprises…", "the auditor family and its sub-agents…"): run `ls .opencode/agents/ | grep <family-prefix>` to enumerate all family members before writing the list. A named family includes the parent agent (e.g., `auditor.md`), all model-specific sub-agents (e.g., `auditor-kimi.md`, `auditor-qwen.md`, `auditor-glm.md`), and the synthesizing agent (e.g., `synthesizing-auditor.md`). Do not rely on memory — enumerate from disk. (Source: issue #257, PR #259 — initial doc fix listed only the three auditor sub-agent variants and omitted `auditor.md`.)
 > - No hardcoded URLs — reference the project's routing conventions instead.
 > - Scan the entire file for `TODO`, `[placeholder]`, `...` stubs, and trivially short sections (3 lines or fewer where substance is expected). Remove or complete them before committing.
@@ -188,7 +189,6 @@ Related: [Architecture Overview](./architecture.md#data-model)
 ### Key Files
 
 - `src/tools/tool_name.py` — Python tool script
-- `.opencode/tools/tool-name.ts` — TypeScript OpenCode wrapper
 
 ### Data
 
diff --git a/.opencode/agents/orchestrator-v3.md b/.opencode/agents/orchestrator-v3.md
index 72895a9..c4071b2 100644
--- a/.opencode/agents/orchestrator-v3.md
+++ b/.opencode/agents/orchestrator-v3.md
@@ -248,7 +248,7 @@ Follow the project notes protocol from **`.github/agents/_shared/repo-context.md
 Dispatch a **Researcher** subagent with a prompt that includes:
 
 - The issue title, requirements, and acceptance criteria
-- A list of areas to investigate (relevant to the project's architecture — Python domain logic in `src/`, TypeScript OpenCode tool wrappers in `.opencode/tools/`, wiki system in `stories/*/wiki/`, prompt templates in `src/infrastructure/prompts/`, ChromaDB collections, existing tests in `tests/`)
+- A list of areas to investigate (relevant to the project's architecture — Python domain logic in `src/`, Python tools in `src/tools/`, wiki system in `stories/*/wiki/`, prompt templates in `src/infrastructure/prompts/`, ChromaDB collections, existing tests in `tests/`)
 - Instructions to return a compact summary: file paths found, naming conventions observed, patterns to follow, test patterns, any risks
 
 The Researcher agent returns a research summary. Use it to synthesise the plan — **do not re-read the files yourself**.
@@ -267,12 +267,12 @@ From the research summary, produce:
 
 **Summary** — One paragraph describing the feature/fix, scope, and integration points.
 
-**Affected Areas** — `Python domain logic` / `TypeScript tool wrappers` / `Wiki system` / `Prompt templates` / `Full-stack`; `ChromaDB schema change: yes/no`
+**Affected Areas** — `Python domain logic` / `Python tools` / `Wiki system` / `Prompt templates` / `Full-stack`; `ChromaDB schema change: yes/no`
 
 **Task Checklist (ordered by dependency)**:
 
 - **Infrastructure** (if needed): ChromaDB collection changes, wiki page templates
-- **Implementation**: Python tools, TypeScript wrappers, domain services, prompt templates
+- **Implementation**: Python tools, domain services, prompt templates
 - **Verification tests**: Test file path + list of test methods to write
 
 **Execution Order**: Implementation → Verification tests → Confirm all pass
diff --git a/.opencode/agents/planner.md b/.opencode/agents/planner.md
index e571415..a81b2c3 100644
--- a/.opencode/agents/planner.md
+++ b/.opencode/agents/planner.md
@@ -101,7 +101,7 @@ Build a concrete understanding of the current state:
 
 #### OpenCode Tools (if applicable)
 
-- **TypeScript wrappers**: existing tool definitions in `.opencode/tools/`
+- **Python tools**: existing tool scripts in `src/tools/`
 - **Tool conventions**: naming, parameter patterns, subprocess invocation
 
 #### Wiki System
@@ -232,7 +232,7 @@ Produce an ordered task list to `docs/planning/[feature-slug]/tasks.md`:
 **Key Files:**
 
 - `src/domain/entities/entity.py` — [what changes]
-- `.opencode/tools/tool-name.ts` — [what changes]
+- `src/tools/tool_name.py` — [what changes]
 
 ---
 
@@ -244,7 +244,7 @@ Produce an ordered task list to `docs/planning/[feature-slug]/tasks.md`:
 **Task ordering rules:**
 
 1. Infrastructure/schema changes first (ChromaDB collections, wiki page templates)
-2. Python domain logic before TypeScript wrappers (domain services need to exist before tools can call them)
+2. Python domain logic before tool CLI scripts (domain services need to exist before tools can call them)
 3. Small, independently testable units — each task should be one Orchestrator dispatch
 4. Each task must have acceptance criteria that map directly to test methods
 
```

=== FILE CONTENTS ===

--- .opencode/agents/coder.md ---
