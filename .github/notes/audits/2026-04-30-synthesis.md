## Synthesized Audit — 2026-04-30

**Audit Type:** Multi-model synthesis (Auditor Kimi, Auditor Qwen, Auditor Glm)
**Model Agreement Score:** 8/10
**Overall Health:** Needs Attention
**Development Stage:** Migration structurally complete — 24/24 agents migrated, static validation passed; live functional parity unvalidated.

### Finding Counts by Consensus

| Consensus         | Critical | Warning | Info |
| ----------------- | -------- | ------- | ---- |
| ★★★ Unanimous     | 0        | 4       | 5    |
| ★★☆ Majority      | 1        | 1       | 1    |
| ★☆☆ Singular      | 0        | 1       | 2    |

### Key Findings

- [U-W-01] Stale `.opencode/tools/` references across 4 agent bodies — coder.md, orchestrator-v3.md, planner.md, documenter.md (★★★)
- [U-W-02] Old model names (Claude/GPT/Gemini) in synthesizer output templates — synthesizing-auditor.md and synthesizing-researcher.md (★★★)
- [U-W-03] Contemplator lacks `gh*` bash permission while body claims GitHub API access and references `github/search_issues` (★★★)
- [U-W-04] Task 9 live dual-run validation incomplete — Orchestrator V3, Synthesizing Researcher, Auditor never tested in Opencode TUI (★★★)
- [M-C-01] Qwen rates contemplator GitHub permission gap as Critical; Kimi and GLM rate as Warning (★★☆)
- [S-W-01] Documenter.md references `.github/copilot-instructions.md` in edit scope — acceptable during dual-run but needs cleanup post-transition (★☆☆)
- [S-I-01] Kimi notes `head*`/`tail*` permission inconsistency across model-variant families (★☆☆)
- [S-I-02] GLM notes reviewer/browser agents lack explicit `tools:` blocks (★☆☆)

### Divergences

- [D-01] Contemplator severity: Qwen rates Critical (functional gap blocks core workflow); Kimi/GLM rate Warning (instruction stale but agent partially functional). Assessment: Qwen is correct — without `gh*` permission, the contemplator cannot execute its Phase 2 GitHub research under Opencode. However, the agent can still perform other phases (git log, codebase scanning). Compromise: treat as Warning with high operational impact.
- [D-02] ADR 009 status: GLM suggests advancing to "Accepted" now; Kimi/Qwen caution that acceptance requires live validation. Assessment: Qwen/Kimi are correct per ADR 009's own text. Keep "Proposed" until Task 9 live validation completes.
- [D-03] Synthesizer model name scope: All three agree on the finding but differ in severity. Kimi calls it Warning (confusing output), Qwen Warning (low impact), GLM Warning (undermines credibility). Assessment: Unanimous on severity. This is a pure cleanup task.

### Actions Taken

- Issues created: none (awaiting user hand-off decision)
- Notes updated: `.github/notes/audits/2026-04-30-synthesis.md`
- ChromaDB: findings embedded into `audits` collection

---

## Synthesized Audit Report — Opencode Development Agentic Stack

### Synthesis Overview

The Opencode development agentic stack migration is structurally complete: all 24 agent files exist under `.opencode/agents/` with valid frontmatter, correct OpenRouter model IDs, appropriate permission scopes, and dual-run inventory parity maintained across all three runtime directories. The `opencode.json` configuration is minimal and correct, and `docs/features/opencode-runtime.md` is comprehensive and current. However, significant content hygiene issues persist: stale references to the deleted `.opencode/tools/` directory appear in four agent bodies, synthesizer output templates still use old model names (Claude/GPT/Gemini), and the contemplator agent cannot execute its GitHub research workflow under Opencode due to missing `gh*` bash permission. Most critically, Task 9's live functional parity validation has never been performed — the entire 24-agent topology has only passed static structural analysis, leaving the migration's behavioural correctness unproven. ADR 009 remains "Proposed" as a result.

**Model Agreement Score:** 8/10 — near-total agreement on finding substance with minor severity divergences (Contemplator gap rated Critical by Qwen, Warning by Kimi/GLM) and one singular finding each.

### Individual Report Summaries

| Model  | Overall Assessment | Unique Focus Areas | Critical Count | Warning Count | Info Count |
| ------ | ------------------ | ------------------ | -------------- | ------------- | ---------- |
| Kimi   | Structurally complete; stale content and unvalidated runtime | `head*`/`tail*` permission parity; test_opencode_artefacts_deleted test regression | 0 | 6 | 3 |
| Qwen   | Structurally complete; permission gap and validation deficit | Contemplator rated Critical; documenter copilot-instructions.md reference | 2 | 4 | 7 |
| GLM    | Structurally complete; stale inherited content | ADR 009 "Accepted" proposal; reviewer `tools:` block absence | 0 | 6 | 6 |

### Development Stage (Consensus)

| Phase | Status | Completion | Agreement |
| ----- | ------ | ---------- | --------- |
| Task 1 — Bootstrap `opencode.json` | Done | AC met | Unanimous |
| Task 2 — OpenRouter provider + model IDs | Done | AC met | Unanimous |
| Task 3 — ChromaDB rules translation | Done | AC met | Unanimous |
| Task 4 — Orchestrator V3 migration | Done | AC met (no live TUI) | Unanimous |
| Task 5 — Specialist sub-agents | Done | AC met | Unanimous |
| Task 6 — Reviewer family | Done | AC met | Unanimous |
| Task 7 — Researcher family | Done | AC met | Unanimous |
| Task 8 — Auditor family + standalones | Done | AC met (Planner smoke test unchecked) | Majority |
| Task 9 — Dual-run validation + smoke test | Partial | Static passed; live TUI untested | Unanimous |
| Task 10 — Documentation | Partial | opencode-runtime.md complete; companion docs stale | Unanimous |
| ADR 009 status | Proposed | Structurally complete; acceptance blocked by Task 9 | Unanimous |

### Consensus Findings

#### ★★★ Unanimous Findings (All Three Models Agree)

```
[U-W-01] Stale `.opencode/tools/` references across four agent bodies
Severity: Warning
Category: Documentation
Detail: References to the deleted `.opencode/tools/` directory and "TypeScript OpenCode tool wrappers" persist in:
  - `coder.md` line 2 (description) and line 123 (implementation order)
  - `orchestrator-v3.md` line 251 (dispatch prompt)
  - `planner.md` line 104 (Phase 2 research) and line 235 (task template)
  - `documenter.md` line 131 (verification instruction) and line 191 (feature doc template)
Models: Kimi ✓ Qwen ✓ GLM ✓
Impact: Agents instructed to verify or modify files in a non-existent directory will waste context tokens, produce confused output, or hallucinate tool interfaces.
Suggested action: Remove or replace all `.opencode/tools/` references with `src/tools/` equivalents.
```

```
[U-W-02] Old model names (Claude/GPT/Gemini) in synthesizer output templates
Severity: Warning
Category: Documentation
Detail: `synthesizing-auditor.md` (lines 99-102, 126, 139, 153, 163-165, 204) and `synthesizing-researcher.md` (lines 173-175) use "Claude", "GPT", "Gemini" in output format tables and divergence analysis templates. The actual sub-agents are Kimi, Qwen, and GLM.
Models: Kimi ✓ Qwen ✓ GLM ✓
Impact: Synthesized reports will contain incorrect model attribution, undermining credibility and traceability of multi-model synthesis.
Suggested action: Replace all occurrences with "Kimi", "Qwen", "GLM".
```

```
[U-W-03] Contemplator lacks `gh*` bash permission while body claims GitHub API access
Severity: Warning
Category: Workflow / Permission
Detail: `contemplator.md` line 44 lists "GitHub API — for issue/PR activity" as a capability, and line 81 instructs use of `github/search_issues` (a Copilot tool name). However, `permission.bash` (lines 7-22) only allows: git log/status/diff/branch, grep, find, ls, cat, wc, head, tail, pip, python, echo. No `gh*` entry exists.
Models: Kimi ✓ Qwen ✓ GLM ✓
Impact: The contemplator cannot execute its Phase 2 GitHub research workflow under Opencode. The `github/search_issues` reference is a Copilot tool name with no Opencode equivalent.
Suggested action: Replace `github/search_issues` with `gh issue list --search ...` and add `"gh*": "allow"` to `permission.bash`.
```

```
[U-W-04] Task 9 live dual-run validation incomplete
Severity: Warning
Category: Validation
Detail: `.github/notes/opencode-dual-run-validation.md` confirms all 24 agents pass static structural validation. However, Task 9 acceptance criteria require live verification of: Orchestrator V3 full lifecycle, Synthesizing Researcher end-to-end, Auditor quick healthcheck, ChromaDB recall from agent sessions, and Planner edit-scope smoke test. All five remain "not-tested-this-cycle".
Models: Kimi ✓ Qwen ✓ GLM ✓
Impact: The migration is structurally complete but behaviourally unvalidated. ADR 009 cannot advance to "Accepted" without this evidence. Unknown runtime defects may exist in dispatch, permission enforcement, or MCP routing.
Suggested action: Schedule a live Opencode TUI session to validate at minimum Orchestrator V3, Synthesizing Researcher, and Auditor workflows.
```

#### ★★☆ Majority Findings (Two of Three Models Agree)

```
[M-C-01] Contemplator GitHub permission gap rated Critical by Qwen
Severity: Critical (Qwen) / Warning (Kimi, GLM)
Category: Workflow / Permission
Detail: Same substance as [U-W-03] — the contemplator cannot execute GitHub research due to missing `gh*` permission and unmigrated `github/search_issues` reference.
Models: Kimi ✓ (Warning) Qwen ✓ (Critical) GLM ✓ (Warning)
Dissenting view: None — all three agree on the finding. Severity split: Qwen argues this blocks a core workflow (Phase 2); Kimi/GLM argue the agent can still perform other phases and the issue is configuration rather than structural.
Impact: High operational impact if the contemplator is invoked frequently for issue triage. Low impact if invoked only for codebase reflection.
Suggested action: Fix permission and reference as per [U-W-03]. Severity should be treated as Warning given the agent retains partial functionality.
```

```
[M-W-01] coder.md description references deleted TypeScript wrappers
Severity: Warning
Category: Documentation
Detail: `coder.md` frontmatter `description` (line 2) states: "Implements code changes for the project — Python domain logic, TypeScript OpenCode tool wrappers, prompt templates, wiki tools, and infrastructure." The TypeScript wrappers were deleted per ADR 007.
Models: Kimi ✓ Qwen ✓ GLM ✓ (all agree, but GLM categorizes under Info; Kimi/Qwen as Warning)
Dissenting view: GLM treats this as Info because the description field is metadata, not executable. Kimi/Qwen treat as Warning because it appears in `opencode run "list available agents"` output.
Impact: Misrepresents the agent's scope to users listing available agents.
Suggested action: Remove "TypeScript OpenCode tool wrappers" from the description.
```

#### ★☆☆ Singular Findings (Only One Model Reported)

```
[S-W-01] Documenter.md references `.github/copilot-instructions.md` in edit scope
Severity: Warning
Category: Documentation
Detail: `documenter.md` includes `.github/copilot-instructions.md` in its edit-scope allowlist (line 11) and references it in companion-document sweep instructions (line 108). This is Copilot-specific documentation.
Model: Qwen
Assessment: This is intentional during the dual-run period — the file exists and is maintained for Copilot. It should be flagged for cleanup when the dual-run period ends and a canonical runtime is chosen. Not an immediate issue.
Suggested action: Add a TODO comment or deferred cleanup note. No action needed now.
```

```
[S-I-01] Permission parity: `head*`/`tail*` not consistently present across model-variant families
Severity: Info
Category: Convention
Detail: Some agents (reviewer-kimi, reviewer-qwen, reviewer-glm) include `head*` and `tail*` in `permission.bash`; others (synthesizing-reviewer, test-writer) do not. Divergence flagged in issue #252 / PR #253.
Model: Kimi
Assessment: This is a minor convention inconsistency. It does not break functionality but reduces uniformity across the agent fleet.
Suggested action: Apply permission parity rule from issue #254 consistently.
```

```
[S-I-02] Reviewer/browser agents lack explicit `tools:` blocks
Severity: Info
Category: Configuration
Detail: The three reviewer sub-agents (`reviewer-kimi.md`, `reviewer-qwen.md`, `reviewer-glm.md`), `synthesizing-reviewer.md`, and `browser.md` do not have a `tools:` frontmatter block.
Model: GLM
Assessment: This is likely cosmetic — Opencode likely defaults to no MCP access when `tools:` is absent. However, explicit declaration improves readability and alignment with the documented pattern in `opencode-runtime.md`.
Suggested action: Add explicit `tools:` blocks for clarity.
```

### Divergence Analysis

```
[D-01] Topic: Contemplator severity rating
Kimi says: Warning — the agent can still perform git log, codebase scanning, and other phases. The GitHub research is one of several capabilities.
Qwen says: Critical — the contemplator's Phase 2 workflow is non-functional. The agent cannot fulfill its core mandate of recent activity analysis without GitHub access.
GLM says: Warning — the permission gap and unmigrated reference are real but the agent retains partial functionality.
Assessment: Qwen is correct that the Phase 2 workflow is broken, but Kimi/GLM are correct that the agent is not fully non-functional. The finding should be treated as a high-impact Warning rather than a Critical structural failure. The severity difference reflects different weightings of "partial functionality" vs "broken primary workflow."
Resolution: Classify as [U-W-03] Warning with explicit note about high operational impact.
```

```
[D-02] Topic: ADR 009 acceptance timing
Kimi says: Keep "Proposed" until Task 9 completes. ADR 009's own text requires live functional parity.
Qwen says: Keep "Proposed" — acceptance is blocked by unmet AC.
GLM says: Advance to "Accepted" now; the migration is structurally complete. Track remaining live validation as a follow-up task.
Assessment: Kimi/Qwen are correct. ADR 009 explicitly states: "The dual-run period ends in a future, separate decision once Opencode has been demonstrated to reproduce the full Synthesized Review and Synthesized Research workflows." No such demonstration has occurred. Advancing the ADR prematurely would make a binding decision on unvalidated runtime behaviour.
Resolution: Keep ADR 009 as "Proposed". Create a dedicated follow-up issue for Task 9 live validation.
```

```
[D-03] Topic: coder.md description severity
Kimi says: Warning — stale description appears in agent listing output.
Qwen says: Warning — misrepresents agent scope.
GLM says: Info — description is metadata, not executable.
Assessment: All three identify the same defect. The severity difference reflects whether the description field is treated as user-facing (Warning) or internal (Info). Since `opencode run "list available agents"` surfaces descriptions to users, Kimi/Qwen's Warning rating is more appropriate.
Resolution: Classify as Warning-adjacent Info — suggest fixing as part of the stale-reference sweep.
```

### Deviations from Plan (Consensus)

| Plan Requirement | What the Code Does | Models Flagging |
|---|---|---|
| Task 9 AC: Orchestrator V3 = pass | "not-tested-this-cycle" | Unanimous |
| Task 9 AC: Synthesizing Researcher = pass | "not-tested-this-cycle" | Unanimous |
| Task 9 AC: Auditor = pass | "not-tested-this-cycle" | Unanimous |
| ADR 009: `github/<tool-name>` replaced with `gh` CLI | `contemplator.md` still references `github/search_issues` | Unanimous |
| ADR 007: No TypeScript wrappers exist | 4 agents reference `.opencode/tools/` | Unanimous |
| Task 8 AC: Planner edit-scope smoke test | Unchecked | Majority (Kimi, GLM) |

### Risk Assessment (Synthesized)

**Technical Risks (Medium-High):**
- **Untested Opencode runtime [U-W-04]:** The entire 24-agent topology has zero live execution evidence. Permission enforcement, sub-agent dispatch, MCP tool routing, and prompt interpretation are unproven in the target runtime. This is the single highest-risk item.
- **Contemplator GitHub gap [U-W-03]:** A primary agent cannot execute a core workflow under Opencode. Fixes are trivial (add `gh*` permission, replace tool reference) but unaddressed.
- **Stale content misleading agents [U-W-01, U-W-02]:** References to deleted files and old model names will cause confusion during agent execution, potentially wasting context and producing incorrect outputs.

**Process Risks (Medium):**
- **ADR 009 governance gap [U-W-04]:** The binding architecture decision for the primary runtime remains unofficial. This creates ambiguity about whether the migration decisions are enforceable.
- **Dual-run drift (Low-Medium):** The dual-run policy requires every agent change to be applied to both runtimes. No automated check exists to detect drift. The stale references suggest the Copilot source may also need cleanup.

**Dependency Risks (Low):**
- **Developer-local MCP servers:** Tavily and Context7 must be configured in `~/.config/opencode/opencode.json`. If missing, researcher and auditor families will fail. No pre-flight check validates this.
- **OpenAI SDK typing:** Prior audit found `mypy src/` fails with 6 errors in `openai_async_provider.py`. This was not re-verified in this audit cycle (sandbox restrictions) but remains a known issue.

### Recommended Actions (Prioritized)

1. **[U-W-03] ★★★ Fix Contemplator GitHub capability** — Replace `github/search_issues` with `gh issue list` and add `"gh*": "allow"` to `permission.bash`. One-line permission fix unblocks a primary agent.

2. **[U-W-01] ★★★ Sweep stale `.opencode/tools/` references** — Remove or replace references in `coder.md`, `orchestrator-v3.md`, `planner.md`, and `documenter.md`. Update `coder.md` description and implementation order.

3. **[U-W-02] ★★★ Update synthesizer model names** — Replace "Claude/GPT/Gemini" with "Kimi/Qwen/GLM" in `synthesizing-auditor.md` and `synthesizing-researcher.md`.

4. **[U-W-04] ★★★ Complete Task 9 live validation** — Run end-to-end smoke tests for Orchestrator V3, Synthesizing Researcher, and Auditor under Opencode TUI. Record results in `.github/notes/opencode-dual-run-validation.md`. This is the single most important action to advance the migration.

5. **[M-W-01] ★★☆ Fix coder.md description** — Remove "TypeScript OpenCode tool wrappers" from the frontmatter description.

6. **[S-W-01] ★☆☆ Documenter Copilot reference** — Flag `.github/copilot-instructions.md` reference for cleanup when dual-run ends.

7. **[S-I-01] ★☆☆ Permission parity sweep** — Apply `head*`/`tail*` consistently across model-variant families.

8. **[S-I-02] ★☆☆ Add explicit `tools:` blocks** — Add to reviewer and browser agents for clarity.
