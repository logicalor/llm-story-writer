# Task Breakdown: Migrate Agentic Framework from GitHub Copilot to Opencode

> Implements [PRD](./prd.md). Each task below is sized for a single Orchestrator dispatch (issue → branch → implement → verify → PR).

**Date:** 2026-04-29

## Sequencing rules

1. Bootstrap (Task 1) must land before any agent or rule migration so Opencode can load at all.
2. Confirm provider/model IDs (Task 2) must complete before agent frontmatter is finalised in Tasks 5–8 (avoids 24 rewrites if the provider strings are wrong).
3. The agent migration is split into four batches (Tasks 5, 6, 7, 8) by family so each PR is reviewable. Task 4 (Orchestrator V3 itself) is a prerequisite for all four batches and must land first. Task 5 (orchestrator's specialist sub-agents: Coder, Test Writer, Documenter, Browser, Reflection) goes first among the four batches because these agents are dispatched _by_ the orchestrator and need a working orchestrator to test through.
4. Rules and dual-run validation (Tasks 9, 10) come after agents because they exercise the full topology.

## Tasks

### Task 1: Bootstrap `opencode.json` and chroma MCP

**Type:** backend (config)
**Estimated scope:** small
**Dependencies:** none

**Description:**

Create the root-level Opencode configuration file with the JSON schema reference, default model, instructions array, plugin list, and one MCP server entry for `chroma`. This task is the minimum needed for `opencode` to start in the project root and report a clean configuration. No agents are migrated yet; the goal is a green start.

The MCP entry must translate the existing `.github/mcp.json` chroma server using `type: "local"`, the merged `command:` array, and `enabled: true`. Use `{env:VAR}` interpolation if any chroma argument depends on an environment variable.

Add `opencode-rules@latest` to the `plugin:` array even though no rule files exist yet — this validates plugin resolution as part of the bootstrap.

Confirm whether the existing `.gitignore` excludes `.opencode/` runtime caches (Opencode may write transient state under `.opencode/`). If it does not, add an appropriate `.gitignore` block in this task.

**Acceptance Criteria:**

- [ ] `opencode.json` exists at the project root and validates against `https://opencode.ai/config.json`.
- [ ] Running `opencode --version` followed by `opencode run "list available agents"` from the project root completes without configuration errors.
- [ ] The `chroma` MCP server is reachable from inside an Opencode session against the existing `.chromadb/` data (verify with a one-shot `chroma_list_collections` call).
- [ ] `.gitignore` excludes any transient Opencode runtime state but commits `opencode.json`, `.opencode/agents/`, and `.opencode/rules/`.

**Key Files:**

- `opencode.json` — new
- `.gitignore` — possibly updated

---

### Task 2: Configure OpenRouter provider and confirm model IDs

**Type:** backend (config / research)
**Estimated scope:** small
**Dependencies:** Task 1

**Description:**

Configure Opencode to use OpenRouter as the provider and confirm the exact model slug for each of the three models used across the 24 agents:

| Copilot display name | Expected OpenRouter slug |
|---|---|
| `MoonshotAI: Kimi K2.6 (openrouter)` | `moonshotai/kimi-k2` or similar |
| `Qwen: Qwen3.6 Plus (openrouter)` | `qwen/qwen3.6-plus` or `qwen/qwen3-235b-a22b` |
| `Z.ai: GLM 5.1 (openrouter)` | `z.ai/glm-5.1` or `zhipuai/glm-5.1` |

OpenRouter provides an OpenAI-compatible endpoint (`https://openrouter.ai/api/v1`). Configure Opencode with a `providers:` or `model:` block pointing at that endpoint with an `OPENROUTER_API_KEY` environment variable. Verify each slug by running a minimal completion request against the Opencode CLI.

Note — tavily and context7 are **user-level** MCP servers (Q1 resolved). Do NOT add them to the project `opencode.json`. Instead, document the entries that each developer must add to their personal `~/.config/opencode/opencode.json`, plus the required `TAVILY_API_KEY` env var.

Record confirmed model slugs in a `.github/notes/opencode-provider-mapping.md` note — this file is consumed by Tasks 4–8 to ensure accurate frontmatter.

**Acceptance Criteria:**

- [ ] `.github/notes/opencode-provider-mapping.md` records the exact Opencode model identifier for each of the three OpenRouter models.
- [ ] A minimal `opencode run "hello"` using each confirmed model ID completes without a model-resolution error.
- [ ] `opencode.json` configures OpenRouter as the default provider (base URL, API key env-var reference).
- [ ] `opencode.json` does NOT contain tavily or context7 MCP entries.
- [ ] User-level setup instructions for tavily and context7 are documented in `docs/features/opencode-runtime.md` (stub acceptable here; Task 10 finalises it).

**Key Files:**

- `.github/notes/opencode-provider-mapping.md` — new
- `opencode.json` — updated with OpenRouter provider config

---

### Task 3: Translate ChromaDB instructions to an opencode-rules file

**Type:** backend (config)
**Estimated scope:** small
**Dependencies:** Task 1

**Description:**

Create `.opencode/rules/chromadb.md` mirroring the content of `.github/instructions/chromadb.instructions.md`, but with `globs:` frontmatter in place of `applyTo:`. Verify the `opencode-rules` plugin loads it correctly by triggering an Opencode session that touches a file matching `src/**/*.py` and confirming the rule body appears in context.

Do not delete `.github/instructions/chromadb.instructions.md` — it stays in place for the dual-run period.

**Acceptance Criteria:**

- [ ] `.opencode/rules/chromadb.md` exists with `globs: ["src/**/*.py"]` frontmatter and the same body content as the Copilot original.
- [ ] An Opencode session touching a file under `src/` injects the ChromaDB rule into context (verify by asking the agent to recite the ChromaDB collection list — it must come from the rule, not memory).
- [ ] An Opencode session touching only files outside `src/` (e.g. `docs/`) does not inject the rule.
- [ ] `.github/instructions/chromadb.instructions.md` is unchanged.

**Key Files:**

- `.opencode/rules/chromadb.md` — new

---

### Task 4: Migrate the Orchestrator V3 agent

**Type:** backend (agent prompt)
**Estimated scope:** medium
**Dependencies:** Tasks 1, 2

**Description:**

Translate `.github/agents-openrouter/orchestrator-v3.agent.md` to `.opencode/agents/orchestrator-v3.md`. Migration steps for this single agent:

1. Drop the `name:` frontmatter field — the filename `orchestrator-v3.md` becomes the agent name.
2. Replace `model:` with the confirmed OpenRouter model ID from Task 2 (Kimi K2.6).
3. Replace the `tools:` array with:
   - `mode: primary` (this is a top-level user-facing agent)
   - `permission:` block with `edit: allow`, `bash:` map allowing safe commands (`pytest*`, `ruff*`, `git diff*`, `git log*`, `mypy*`, `gh*`) and asking for everything else, `task:` block explicitly allow-listing every sub-agent the orchestrator dispatches (Test Writer, Coder, Reviewer (Qwen), Reviewer (Kimi), Reviewer (GLM), Synthesizing Reviewer, PR Reviewer, Documenter, Browser, Reflection)
   - `tools:` map enabling `chroma/*` for ChromaDB recall
4. Replace every Copilot-prefixed GitHub tool name in the prompt body (`github/create_branch`, `github/issue_read`, etc.) with equivalent `gh` CLI commands (Q3 resolved — no GitHub MCP server). This is a prompt-content edit, not just a frontmatter edit.
5. Update the prompt body's reference to `runSubagent` (Copilot's tool name) to use Opencode's Task tool dispatch language.
6. Leave references to `.github/agents/_shared/*.md` files unchanged — those shared files are still loaded the same way.
7. Leave references to `.github/skills/github-issues/SKILL.md` unchanged for the dual-run period; do not move skill content yet.

This task migrates exactly one agent because the orchestrator is the most complex and most dispatched-from agent. Validating it in isolation surfaces schema and dispatch issues early.

**Acceptance Criteria:**

- [ ] `.opencode/agents/orchestrator-v3.md` exists with valid Opencode frontmatter.
- [ ] `permission.task` is an explicit allowlist matching the `agents:` list in the Copilot original.
- [ ] No occurrence of `github/<tool-name>` remains in the prompt body; replacement strategy applied consistently.
- [ ] Manually invoking `@orchestrator-v3` in Opencode TUI lists the agent and accepts a simple ad-hoc command (e.g. "read issue #1 and summarise it") without errors.
- [ ] `.github/agents-openrouter/orchestrator-v3.agent.md` is unchanged.

**Key Files:**

- `.opencode/agents/orchestrator-v3.md` — new

---

### Task 5: Migrate orchestrator's specialist sub-agents

**Type:** backend (agent prompts)
**Estimated scope:** medium
**Dependencies:** Task 4

**Description:**

Migrate the specialist agents that the Orchestrator V3 dispatches during the standard development lifecycle. One file per agent under `.opencode/agents/`:

- `coder.md`
- `test-writer.md`
- `documenter.md`
- `browser.md`
- `reflection.md`

For each:

1. Drop `name:`; filename = agent name.
2. Set `mode: subagent` and `hidden: false` (these can also be invoked directly by the user).
3. Convert `tools:` to `permission:` map per the agent's needs (Coder gets `edit: allow`, `bash: allow` for pytest/ruff/mypy; Test Writer same scope but `edit:` restricted to `tests/`; Documenter restricted to `docs/`; Browser allowed only `bash` to invoke `agent-browser`; Reflection gets `edit: allow` for `.github/notes/` and `chroma/*` MCP).
4. Replace any Copilot-prefixed tool names in the prompt body.
5. Set `permission.task` to deny everything for these agents (they do not dispatch others).

Two pitfalls to flag from `.github/agents-openrouter/coder.agent.md`: it contains extensive prose about `.opencode/tools/*.ts` deletion that is historical context — leave it untouched, but verify nothing references currently non-existent files.

**Acceptance Criteria:**

- [ ] All five files exist under `.opencode/agents/` with valid frontmatter.
- [ ] Each agent's `permission:` map is the minimal capability surface required by its body prompt.
- [ ] Each agent's `permission.task` is `deny` for all (no nested dispatch).
- [ ] Dispatching each agent through Orchestrator V3 in Opencode produces output comparable to the Copilot equivalent.
- [ ] `.github/agents-openrouter/<agent>.agent.md` files are unchanged.

**Key Files:**

- `.opencode/agents/coder.md` — new
- `.opencode/agents/test-writer.md` — new
- `.opencode/agents/documenter.md` — new
- `.opencode/agents/browser.md` — new
- `.opencode/agents/reflection.md` — new

---

### Task 6: Migrate the Reviewer family (Synthesized Review pipeline)

**Type:** backend (agent prompts)
**Estimated scope:** medium
**Dependencies:** Task 4

**Description:**

Migrate the four agents that implement the Synthesized Review workflow and the standalone PR Reviewer:

- `reviewer-kimi.md`
- `reviewer-qwen.md`
- `reviewer-glm.md`
- `synthesizing-reviewer.md`
- `pr-reviewer.md`

Source files: `.github/agents-openrouter/reviewer-kimi.agent.md`, `reviewer-qwen.agent.md`, `reviewer-glm.agent.md`, `synthesizing-reviewer.agent.md`, `pr-reviewer.agent.md`.

Special migration rules:

1. Each independent reviewer (Kimi / Qwen / GLM) gets `mode: subagent`, `permission.task: deny`, `permission.edit: allow` (it must write its raw report to `.github/notes/reviews/`), `permission.bash` allowing safe inspection commands (`git diff*`, `git log*`, `git show*`).
2. The Synthesizing Reviewer must have `permission.task: deny` for all to enforce the file-persisted dispatch pattern from PR #70 (no nested sub-agent dispatch).
3. The model field on each independent reviewer must use the confirmed OpenRouter model ID for its specific model — `reviewer-kimi` = Kimi K2.6, `reviewer-qwen` = Qwen3.6 Plus, `reviewer-glm` = GLM 5.1. Mismatched model IDs invalidate the review.
4. The PR Reviewer gets `mode: primary` (user-invocable directly) and `permission.bash` allowing `gh pr*` CLI commands.
5. Replace `runSubagent` references in the orchestrator's review-step instructions if missed in Task 4 — this task is the last opportunity to fix them.

**Acceptance Criteria:**

- [ ] All five files exist with valid frontmatter and correct model IDs.
- [ ] Synthesizing Reviewer has `permission.task: deny` for all entries (depth-1 dispatch invariant preserved).
- [ ] A full Synthesized Review against an existing PR under Opencode produces three raw reports plus a synthesis file in `.github/notes/reviews/YYYY-MM-DD-pr{N}-*.md`.
- [ ] PR Reviewer can be invoked manually via `@pr-reviewer` and posts review comments to a draft PR (verify against a test PR).

**Key Files:**

- `.opencode/agents/reviewer-kimi.md` — new
- `.opencode/agents/reviewer-qwen.md` — new
- `.opencode/agents/reviewer-glm.md` — new
- `.opencode/agents/synthesizing-reviewer.md` — new
- `.opencode/agents/pr-reviewer.md` — new

---

### Task 7: Migrate the Researcher family

**Type:** backend (agent prompts)
**Estimated scope:** small
**Dependencies:** Task 4
**Status:** Completed via PR #242

**Description:**

Migrate the five-agent research family:

- `researcher.md` (single-model standalone, `mode: primary`)
- `researcher-kimi.md` (`mode: subagent`)
- `researcher-qwen.md` (`mode: subagent`)
- `researcher-glm.md` (`mode: subagent`)
- `synthesizing-researcher.md` (`mode: primary`, `permission.task` allow-listing the three sub-researchers, no other dispatch)

Source files: `.github/agents-openrouter/researcher.agent.md`, `researcher-kimi.agent.md`, `researcher-qwen.agent.md`, `researcher-glm.agent.md`, `synthesizing-researcher.agent.md`.

Each independent researcher needs `tools` enabling Tavily MCP (`io.github.tavily-ai/tavily-mcp/*`) and Context7 (`io.github.upstash/context7/*`). Because tavily and context7 are user-level MCP servers, the `tools:` scope in the agent frontmatter is sufficient for routing — the developer's personal `~/.config/opencode/opencode.json` must declare both servers for them to resolve. Confirm the Opencode MCP server names match these IDs from the Tavily / Context7 MCP documentation.

The Synthesizing Researcher dispatches the three independent researchers — its `permission.task` must allow exactly those three names and deny all others.

The standalone `researcher.md` is the simpler single-model variant; it has `permission.task: deny` for all.

**Acceptance Criteria:**

- [x] All five files exist with valid frontmatter and correct model IDs.
- [x] Tavily and Context7 MCP tool scoping is configured per agent.
- [x] Synthesizing Researcher's `permission.task` is an explicit allowlist of the three sub-researcher names.
- [x] A multi-model research run reproduces the file-persisted pattern (or returns reports in-memory for synthesis, matching the existing Copilot behaviour).

**Key Files:**

- `.opencode/agents/researcher.md` — new
- `.opencode/agents/researcher-kimi.md` — new
- `.opencode/agents/researcher-qwen.md` — new
- `.opencode/agents/researcher-glm.md` — new
- `.opencode/agents/synthesizing-researcher.md` — new

---

### Task 8: Migrate the Auditor family and remaining standalone agents

**Type:** backend (agent prompts)
**Estimated scope:** medium
**Dependencies:** Task 4
**Status:** Completed via PR #243

**Description:**

Migrate the remaining eight agents:

Auditor family (5):
- `auditor.md` (`mode: primary`)
- `auditor-kimi.md` (`mode: subagent`)
- `auditor-qwen.md` (`mode: subagent`)
- `auditor-glm.md` (`mode: subagent`)
- `synthesizing-auditor.md` (`mode: primary`, `permission.task` allow-listing the three sub-auditors)

Source files: `.github/agents-openrouter/auditor.agent.md`, `auditor-kimi.agent.md`, `auditor-qwen.agent.md`, `auditor-glm.agent.md`, `synthesizing-auditor.agent.md`, `planner.agent.md`, `contemplator.agent.md`, `sprint-runner.agent.md`.

Standalone agents (3):
- `planner.md` (`mode: primary`, no production-code edit, allowed to write only to `docs/planning/` and `.github/notes/`)
- `contemplator.md` (`mode: primary`, `permission.edit: deny`, may dispatch `synthesizing-researcher` only)
- `sprint-runner.md` (`mode: primary`, `permission.task` allow-listing only `orchestrator-v3`)

Completion note: PR #243 added `auditor.md`, `auditor-kimi.md`, `auditor-qwen.md`, `auditor-glm.md`, `synthesizing-auditor.md`, `planner.md`, `contemplator.md`, and `sprint-runner.md`. After that merge, `.opencode/agents/` reached the planned inventory of 24 Markdown agent files.

`permission.edit` for Planner must be a path-scoped allow (only `docs/planning/**`, `.github/notes/**`) — Planner is explicitly forbidden from writing production code in its Copilot prompt body. If Opencode does not support glob-scoped edit permissions, replace with `edit: ask` and rely on the prompt body to enforce the boundary.

Sprint Runner's job is to dispatch Orchestrator V3 for one issue at a time — `permission.task` should allow only `orchestrator-v3` and deny all others.

**Acceptance Criteria:**

- [x] All eight files exist with valid frontmatter and correct model IDs.
- [x] Synthesizing Auditor preserves the depth-1 invariant with an explicit `permission.task` allowlist for `Auditor Kimi`, `Auditor Qwen`, `Auditor Glm`, and `Reflection`.
- [ ] Planner cannot edit files outside `docs/planning/` and `.github/notes/` (verified by an attempted edit in a smoke test).
- [x] After this task, `.opencode/agents/` contains exactly 24 files matching the inventory in `.github/agents-openrouter/` (excluding the README).

**Key Files:**

- `.opencode/agents/auditor.md` — new
- `.opencode/agents/auditor-kimi.md` — new
- `.opencode/agents/auditor-qwen.md` — new
- `.opencode/agents/auditor-glm.md` — new
- `.opencode/agents/synthesizing-auditor.md` — new
- `.opencode/agents/planner.md` — new
- `.opencode/agents/contemplator.md` — new
- `.opencode/agents/sprint-runner.md` — new

---

### Task 9: Dual-run validation and end-to-end smoke test

**Type:** validation
**Estimated scope:** medium
**Dependencies:** Tasks 5, 6, 7, 8

**Description:**

Run a small, reversible end-to-end validation under Opencode that exercises the full Orchestrator V3 lifecycle on a real but trivial issue. Steps:

1. Create a low-risk issue (e.g. fix a typo in `docs/`).
2. Invoke `@orchestrator-v3` with the issue number under Opencode.
3. Allow it to run through Steps 1–8 of its workflow, including Synthesized Local Review.
4. Verify each step produces the same artefacts as the Copilot equivalent (issue, branch, commits, tests, docs update, raw review reports, synthesis report, reflection note).
5. Capture any deviations and either fix in this PR or open follow-up issues.

Also validate:
- `@synthesizing-researcher` runs end-to-end against a small research brief.
- `@auditor` runs a quick healthcheck.
- ChromaDB recall queries still work from inside agent sessions.

This is a validation task, not a coding task. Its output is a dual-run report saved to `.github/notes/opencode-dual-run-validation.md` with a per-agent pass/fail row.

**Acceptance Criteria:**

- [ ] `.github/notes/opencode-dual-run-validation.md` exists with a row for each of the 24 agents and a verdict (pass / fail / not-tested-this-cycle).
- [ ] At least the Orchestrator V3 lifecycle row, the Synthesizing Researcher row, and the Auditor row are pass.
- [ ] All failures have either a fix in this PR or a follow-up issue linked.
- [ ] No `.github/agents-openrouter/` or `.github/agents-copilot/` files were modified during validation (dual-run integrity preserved).

**Key Files:**

- `.github/notes/opencode-dual-run-validation.md` — new

---

### Task 10: Document the Opencode runtime and dual-run policy

**Type:** documentation
**Estimated scope:** small
**Dependencies:** Task 9

**Description:**

Write `docs/features/opencode-runtime.md` covering:

- How to install and authenticate Opencode for this project
- The `opencode.json` structure and the `.opencode/` directory layout
- The relationship between `.opencode/agents/` (active runtime) and `.github/agents-copilot/` (preserved Copilot artefacts, not deleted)
- The `opencode-rules` plugin and how `.opencode/rules/chromadb.md` reproduces `applyTo`-style scoping
- The dual-run policy: any change to an agent must be applied to both runtimes during the dual-run period; one canonical source will be chosen later in a separate decision
- A quick-reference table mapping each Copilot agent file to its Opencode counterpart

Update `docs/README.md` to add a link to the new feature doc and a note that the Copilot artefacts are preserved alongside the Opencode runtime.

Update `AGENTS.md` to mention that the project runs under both Copilot and Opencode during the dual-run period, with the Opencode runtime as the active development surface.

Do **not** modify `.github/copilot-instructions.md` — Copilot continues to work and that file remains its source of truth.

**Acceptance Criteria:**

- [ ] `docs/features/opencode-runtime.md` exists and renders correctly.
- [ ] `docs/README.md` lists the new feature page under the **Features** section.
- [ ] `AGENTS.md` mentions the dual-run setup in a new "Runtimes" subsection or paragraph.
- [ ] The migration mapping table includes all 24 agents with their old and new paths.

**Key Files:**

- `docs/features/opencode-runtime.md` — new
- `docs/README.md` — updated
- `AGENTS.md` — updated
