## Synthesized Audit — 2026-04-28

**Audit Type:** Codex persona synthesis (Architect + Maintainer + Product Documenter)
**Personas:** GLM 5.1 + Kimi K2.6 + Qwen 3.6
**Persona Agreement Score:** 9/10
**Overall Health:** Needs Attention
**Development Stage:** Python-native migration 80% complete; documentation sweep severely incomplete

### Finding Counts by Consensus

| Consensus         | Critical | Warning | Info |
| ----------------- | -------- | ------- | ---- |
| ★★★ Unanimous     | 3        | 3       | 2    |
| ★★☆ Majority      | 1        | 4       | 3    |
| ★☆☆ Singular      | 0        | 1       | 2    |

### Key Findings

- [U-C-01] `docs/manual.md` claims config lives in `config.md` — file does not exist; actual config is `config.yml` (★★★)
- [U-C-02] Shell scripts (`config.example.sh`, `configs/*.sh`) are dead code referencing removed `opencode` runtime (★★★)
- [U-C-03] Multiple documented pipeline phases have prompts/config but are NOT wired in active orchestrator (★★★)
- [U-W-01] Phase numbering is inconsistent across docs (manual vs orchestrator doc vs SKILL.md) (★★★)
- [U-W-02] `prompts/skills/story-pipeline/SKILL.md` still references OpenCode delegation (line 188) (★★★)
- [U-W-03] `.github/notes/architecture.md` describes removed `.opencode/tools/*.ts` stack (★★★)
- [M-W-01] `config-guide.md` Quick Start references removed OpenCode `/new-story` command (★★☆)
- [M-W-02] `AGENTS.md` lists `quality-reviewer` as active subagent but orchestrator never dispatches it (★★☆)
- [M-W-03] `docs/manual.md` project structure diagram shows `config.md`, populated `services/`, and `.opencode/` (★★☆)
- [M-I-01] Undocumented config flags in `config.yml` (use_improved_recap_sanitizer, randomize_seed, etc.) (★★☆)
- [S-W-01] `README.md` advertises scene generation pipeline, outline critique, and multi-stage recap sanitizer as operational features (★☆☆)
- [S-I-01] `src/presentation/agents/story_orchestrator.py` is vestigial — active orchestrator is `src/presentation/orchestrator.py` (★☆☆)

### Divergences

- [D-01] **README.md feature advertising**: Kimi flagged that `README.md` lists scene generation pipeline, outline critique, and multi-stage recap as operational; GLM and Qwen did not surface this. Assessment: Genuine finding. The README lists these under "Features" without qualification, and the orchestrator does not invoke them. They are tool-ready/config-only, not fully wired.
- [D-02] **Vestigial `story_orchestrator.py`**: Only Qwen noted the confusion of having two orchestrator files. Assessment: Minor but valid — the vestigial agent should be noted in docs or removed.
- [D-03] **Severity of `config-guide.md` OpenCode reference**: Qwen rated this Critical; GLM and Kimi rated it Warning. Assessment: Qwen is correct to elevate it. The config guide is a high-traffic entry point for new users, and its first instruction is to launch a removed runtime. This is a direct onboarding blocker.

### Actions Taken

- Notes updated: `.github/notes/audits/2026-04-28-synthesis.md`
- ChromaDB: findings embedded into `audits` collection

---

# Synthesized Audit Report — Documentation vs. Codebase Reality

## Synthesis Overview

The `llm-story-writer` documentation is in a **high-drift transitional state** following the Python-native migration (ADR 007). All three audit personas independently converged on the same top-level diagnosis: the primary user-facing manual (`docs/manual.md`) is functionally broken for new users due to pervasive references to a non-existent `config.md`, while multiple documented pipeline phases have prompt assets and config flags but are not wired into the active orchestrator. Agreement across the three models was exceptionally high (9/10), with only minor divergence on whether certain findings warrant Critical vs. Warning severity and whether the README oversells unwired features.

**Model Agreement Score:** 9/10

---

## Individual Report Summaries

| Persona | Overall Assessment | Unique Focus Areas | Critical Count | Warning Count |
| ------ | ------------------ | ------------------ | -------------- | ------------- |
| GLM | Concise, structured; strong on config mismatch and dead shell scripts | Phase 7a/7f/7.5 gap enumeration; `--savepoint` semantics confusion | 3 | 3 |
| Kimi | Most comprehensive; deepest architecture analysis | `.github/notes/architecture.md` staleness; README.md advertising unwired features; `.github/notes/` as canonical reference risk | 3 | 5 |
| Qwen | Most aggressive on severity; strong on code-level evidence | Vestigial `story_orchestrator.py`; `config-guide.md` rated Critical; exact line counts for `config.md` references | 3 | 3 |

---

## Development Stage (Consensus)

| Phase | Status | Completion | Agreement |
| -------------------- | ------------------------------ | ---------- | ------------------------ |
| Python-native migration (ADR 007) | Implemented — partial | Headless orchestrator, TUI, async provider, CLI operational | Unanimous |
| Service-layer retirement (ADR 008) | Implemented | `src/application/services/` empty | Unanimous |
| Documentation sweep (PRD Task 10) | Incomplete | `manual.md` and `config-guide.md` contain critical stale references | Unanimous |
| Full pipeline phase map | Partial | Phases 7a, 7d, 7f, 7.5, and Phase 6 initial wiki population are tool-ready but not wired | Unanimous |
| Integration tests | Implemented | E2E headless test and async provider live test exist | Unanimous |

---

## Consensus Findings

### ★★★ Unanimous Findings (All Three Models Agree)

#### [U-C-01] `config.md` does not exist — 10+ references across primary docs
**Severity:** Critical  
**Category:** Documentation  
**Detail:** `docs/manual.md` references `config.md` in at least ten locations (lines 124, 140, 307, 550, 558, 568, 685, 689, 695, 702), often specifying "YAML frontmatter at the top of the file." No `config.md` exists. The active configuration file is `config.yml` (plain YAML, no frontmatter). `README.md` and `config-guide.md` correctly reference `config.yml`, but the comprehensive manual — the document most users will follow — is systematically wrong.  
**Personas:** GLM ✓ Kimi ✓ Qwen ✓  
**Impact:** New users following the manual cannot locate the configuration file and cannot start the system. Direct onboarding blocker.

#### [U-C-02] Shell config scripts are dead code referencing removed `opencode` runtime
**Severity:** Critical  
**Category:** Code Quality / Documentation  
**Detail:** `config.example.sh`, `configs/fast-prototype.sh`, and `configs/high-quality.sh` all print `"ERROR: Legacy CLI (src/main.py) has been removed. Use 'opencode' instead."` and exit 1. They build `CMD` strings with flags like `-ExpandOutline` and `-SceneGenerationPipeline` that do not map to the current `story-writer` CLI. They are listed in the `docs/manual.md` project structure diagram but have no working documentation.  
**Personas:** GLM ✓ Kimi ✓ Qwen ✓  
**Impact:** Users discovering these scripts are misled into thinking `opencode` is still the runtime. Dead code that actively confuses.

#### [U-C-03] Multiple documented pipeline phases have prompts/config but are NOT wired in active orchestrator
**Severity:** Critical  
**Category:** Architecture / Documentation  
**Detail:** `src/presentation/orchestrator.py` (the authoritative runtime per ADR 007) never dispatches: `chapter-outline-expander` (Phase 7a), `quality-reviewer` (Phase 7f), `prose-scrubber` (Phase 7.5), initial wiki population (Phase 6), `recap_manager` (Phase 7d), or the scene generation pipeline (Phase 7b). In each case, the underlying tool and/or prompt asset exists, and in most cases a `config.yml` flag exists, but the orchestrator ignores them. The manual acknowledges some gaps at line 299, but individual feature docs and the README do not consistently flag this.  
**Personas:** GLM ✓ Kimi ✓ Qwen ✓  
**Impact:** Users enabling flags like `expand_outline: true`, `scene_generation_pipeline: true`, or `enable_scrubbing: true` will see zero effect and assume the software is broken. Erodes trust in the configuration system.

#### [U-W-01] Phase numbering is inconsistent across docs
**Severity:** Warning  
**Category:** Documentation  
**Detail:** `docs/manual.md` calls final-edit "Phase 7" and assembly "Phase 8." `docs/features/story-orchestrator.md` calls final-edit "Phase 9." `prompts/skills/story-pipeline/SKILL.md` uses yet another scheme: Init=1, Outline=2, Approval=3, Wiki Init=4, Characters+Settings=5, Wiki Population=6, Chapter Loop=7, Assembly=8, Final Edit=9. The manual also omits the narrative-arc phase from its numbering entirely.  
**Personas:** GLM ✓ Kimi ✓ Qwen ✓  
**Impact:** Developers tracing pipeline behavior across documents encounter confusing off-by-one or off-by-two mismatches. Debugging pipeline state is harder.

#### [U-W-02] `prompts/skills/story-pipeline/SKILL.md` still references OpenCode delegation
**Severity:** Warning  
**Category:** Documentation  
**Detail:** Line 188 states: "The `story-orchestrator` dispatches these by name via OpenCode delegation." OpenCode was fully removed per Issue #164 / ADR 007. The active orchestrator dispatches agents via direct Python `await` calls. This skill file is loaded by agents during pipeline execution.  
**Personas:** GLM ✓ Kimi ✓ Qwen ✓  
**Impact:** Skill reference consumed by LLM agents contains a stale architectural assumption. Could cause the model to attempt non-existent operations.

#### [U-W-03] `.github/notes/architecture.md` describes removed `.opencode/tools/*.ts` stack
**Severity:** Warning  
**Category:** Documentation  
**Detail:** The file is linked from `docs/README.md` as "Architecture Notes" but still lists tool mappings like `prompt-loader` → `.opencode/tools/prompt-loader.ts`, `story-state` → `.opencode/tools/story-state.ts`, etc. It also references `src/infrastructure/container.py` (removed), `PgVectorStore` (removed), and agent registration in `opencode.json` (removed).  
**Personas:** GLM ✓ Kimi ✓ Qwen ✓  
**Impact:** Canonical reference for contributors and automated context ingestion describes a technology stack that no longer exists. Directly contradicts ADR 007 and ADR 008.

#### [U-I-01] Undocumented config flags in `config.yml`
**Severity:** Info  
**Category:** Documentation  
**Detail:** `config-guide.md` does not document: `use_improved_recap_sanitizer`, `use_multi_stage_recap_sanitizer`, `enable_outline_critique`, `outline_critique_iterations`, `log_prompt_inputs`, `randomize_seed` (infrastructure), `max_chunk_size`, `overlap_size` (RAG config).  
**Personas:** GLM ✓ Kimi ✓ Qwen ✓  
**Impact:** Users cannot discover or tune these features from documentation.

#### [U-I-02] `prompts/skills/` has 8+ directories with minimal documentation
**Severity:** Info  
**Category:** Documentation  
**Detail:** `prompts/skills/` contains `character-voice/`, `context-budgeting/`, `final-edit/`, `narrative-arc/`, `outline-structure/`, `scene-writing/`, `story-pipeline/`, `wiki-conventions/`, `wiki-maintenance/`. Only `story-pipeline/SKILL.md` is substantive. The rest are effectively hidden from contributors.  
**Personas:** GLM ✓ Kimi ✓ Qwen ✓  
**Impact:** Skills are part of the agent system but undocumented.

---

### ★★☆ Majority Findings (Two of Three Models Agree)

#### [M-W-01] `config-guide.md` Quick Start references removed OpenCode runtime
**Severity:** Warning → Critical (Qwen dissent elevates)  
**Category:** Documentation  
**Detail:** `config-guide.md` lines 9–12: "Basic Usage: `opencode`" then "Then run `/new-story prompts/YourPrompt.txt` inside OpenCode." The correct entry point is `story-writer tui --story <name>` or `story-writer run --story <name>`.  
**Personas:** GLM ✓ Kimi ✓ Qwen ✓ (Qwen rated Critical; GLM/Kimi rated Warning)  
**Dissenting view:** None — all three found it. Severity split only.  
**Impact:** The config guide is a high-traffic entry point. Users following it will attempt to invoke a removed runtime. Treat as Critical.

#### [M-W-02] `AGENTS.md` lists `quality-reviewer` as active subagent
**Severity:** Warning  
**Category:** Documentation  
**Detail:** `AGENTS.md` states: "Subagents (`outline-planner`, `character-sheet-generator`, `chapter-writer`, `wiki-maintainer`, `quality-reviewer`) handle specialised creative tasks." The orchestrator never dispatches `quality-reviewer`. No `quality_reviewer.py` exists in `src/presentation/agents/`.  
**Personas:** GLM ✓ Kimi ✓ Qwen ✓ (all found it; GLM and Kimi emphasized it more strongly)  
**Impact:** Misleading architectural overview.

#### [M-W-03] `docs/manual.md` project structure diagram is outdated
**Severity:** Warning  
**Category:** Documentation  
**Detail:** The diagram (centered around line 307) lists `config.md` (doesn't exist), `src/application/services/` as populated (actually empty per ADR 008), and `opencode-migration/` as an active planning area (PRD is superseded).  
**Personas:** GLM ✓ Kimi ✓ Qwen ✓ (GLM and Kimi gave this more prominence)  
**Impact:** Misrepresents repository layout to new contributors.

#### [M-W-04] `docs/manual.md` claims config is YAML frontmatter; actual config is plain YAML
**Severity:** Warning  
**Category:** Documentation  
**Detail:** Line 140: "All configuration lives in `config.md` (YAML frontmatter at the top of the file)." `config.yml` is a plain YAML file with no markdown wrapper and no frontmatter delimiters.  
**Personas:** GLM ✓ Qwen ✓ Kimi (implied in C-01 but not isolated)  
**Dissenting view:** Kimi folded this into the broader config filename mismatch rather than calling it out separately.  
**Impact:** Users might try to create a markdown file with frontmatter, which the config loader won't read.

#### [M-I-01] `src/tools/_wiki_api.py`, `critique_parser.py`, `migrate_state_slim.py` undocumented
**Severity:** Info  
**Category:** Documentation  
**Detail:** `_wiki_api.py` provides a typed programmatic wiki API imported by `wiki_extract.py`. `critique_parser.py` is used by `critique_runner.py`. `migrate_state_slim.py` is a one-off migration helper. None appear in `docs/tools.md`.  
**Personas:** GLM ✓ Kimi ✓ Qwen ✓ (all found it; emphasis varied)  
**Impact:** Developers may reinvent or misunderstand existing utilities.

#### [M-I-02] `docs/tools.md` over-promises CLI documentation depth
**Severity:** Info  
**Category:** Documentation  
**Detail:** `docs/tools.md` states: "Read the module's `cmd_*` function or argparse setup before documenting or scripting against its JSON output." `docs/README.md` links to it with the promise: "See [Tools Reference](../tools.md) for full documentation of each tool's arguments, operations, and CLI interface."  
**Personas:** GLM ✓ Kimi ✓ (Qwen noted it as self-acknowledged gap)  
**Impact:** Users must read source to learn CLI interfaces.

---

### ★☆☆ Singular Findings (Only One Model Reported)

#### [S-W-01] `README.md` advertises unwired features as operational
**Severity:** Warning  
**Category:** Documentation  
**Detail:** `README.md` lists under "Features": "Scene generation pipeline," "Outline critique," and "Multi-stage recap sanitizer." While underlying tools and config flags exist, the orchestrator does not invoke scene generation pipeline, outline critique, or multi-stage recap sanitization.  
**Model:** Kimi  
**Assessment:** Genuine finding. The README is the first impression for visitors. It should distinguish between "fully operational" and "tool-ready / awaiting orchestrator integration."

#### [S-I-01] `src/presentation/agents/story_orchestrator.py` is vestigial
**Severity:** Info  
**Category:** Code Quality  
**Detail:** This file exists but the active orchestrator is `src/presentation/orchestrator.py`. The agents-directory file is a thin coordinator with no production callers.  
**Model:** Qwen  
**Assessment:** Genuine but minor. Having two "orchestrator" files is confusing. Should be noted in docs or removed.

#### [S-I-02] `docs/manual.md` ADR index omits 007 and 008
**Severity:** Info  
**Category:** Documentation  
**Detail:** Section 11.4 lists ADRs 001–006 but misses the two most recent and relevant ADRs (007, 008).  
**Model:** Kimi  
**Assessment:** Genuine. The manual should reference the ADRs that define the current architecture.

---

## Divergence Analysis

### [D-01] Topic: `config-guide.md` OpenCode reference severity
**GLM says:** Warning — significant drift, not Critical.  
**Kimi says:** Warning — significant drift, config guide is high-traffic.  
**Qwen says:** Critical — first instruction is to launch a removed runtime; direct onboarding blocker.  
**Assessment:** Qwen is correct. The config guide is a primary entry point. A user following it step-by-step will hit an immediate dead end. Treat as Critical.

### [D-02] Topic: `README.md` advertising unwired features
**GLM says:** Did not surface.  
**Kimi says:** Warning — README lists scene generation pipeline, outline critique, and multi-stage recap sanitizer as operational features, but the orchestrator does not invoke them.  
**Qwen says:** Did not surface.  
**Assessment:** Genuine finding. The README is the project's storefront. It should accurately represent what the active orchestrator delivers vs. what exists as tool-only/config-only infrastructure.

### [D-03] Topic: Vestigial `story_orchestrator.py`
**GLM says:** Did not surface.  
**Kimi says:** Did not surface.  
**Qwen says:** Info — confusing to have two orchestrator files.  
**Assessment:** Minor but valid. The vestigial agent should be documented as deprecated or removed to avoid confusion.

---

## Deviations from Plan (Consensus)

| Claimed Feature | Where Documented | Actual State | Models Flagging |
|-----------------|------------------|--------------|-----------------|
| `config.md` as config file | `manual.md`, `AGENTS.md`, `custom-commands.md` | File does not exist; `config.yml` is real | All 3 |
| `chapter-outline-expander` (Phase 7a) | `story-orchestrator.md`, `chapter-outline-expander.md`, `SKILL.md` | Prompt/tool exist, orchestrator never calls it | All 3 |
| `quality-reviewer` (Phase 7f) | `AGENTS.md`, `SKILL.md` | Prompt exists, no agent implementation, no dispatch | All 3 |
| `prose-scrubber` (Phase 7.5) | `prose-quality-passes.md`, `SKILL.md` | Prompt exists, config flag exists, orchestrator ignores it | All 3 |
| Initial wiki population (Phase 6) | `wiki-maintainer.md`, `SKILL.md` | Tool exists, orchestrator only does directory init | All 3 |
| Recap generation (Phase 7d) | `SKILL.md` | Tool exists, not wired in orchestrator | All 3 |
| Scene generation pipeline | `config.yml`, `README.md`, `SKILL.md` | Tool exists, chapter loop doesn't use scenes | All 3 |
| `src/application/services/` as active layer | `manual.md` project structure | Empty (retired per ADR 008) | All 3 |
| OpenCode as runtime | `config-guide.md`, shell scripts | Removed per ADR 007 | All 3 |

---

## Risk Assessment (Synthesized)

**Critical Risks**
- **Onboarding failure:** New users following `docs/manual.md` or `config-guide.md` will hunt for `config.md` or try to launch `opencode`, fail, and likely abandon the project.
- **Silent feature failures:** Operators setting `expand_outline: true`, `scene_generation_pipeline: true`, `enable_scrubbing: true`, etc., will see zero effect and assume the software is broken.

**Warning Risks**
- **Misleading canonical reference:** `.github/notes/architecture.md` is still linked from `docs/README.md` but describes a removed technology stack. New contributors and automated context ingestion will be misled.
- **Skill file confuses LLM:** `story-pipeline/SKILL.md` line 188 tells the orchestrator to dispatch via "OpenCode delegation." This skill is loaded during actual pipeline execution and could cause the LLM to attempt non-existent operations.
- **Architecture confusion:** Developers reading `manual.md`'s project structure or `AGENTS.md` will expect an active services layer and quality-reviewer subagent that don't exist.

**Info Risks**
- **Documentation maintenance drag:** Every doc update requires checking multiple files (`manual.md`, `story-orchestrator.md`, `config-guide.md`, `README.md`, `AGENTS.md`) because they contradict each other. This multiplies the cost of future changes.
- **Stale artifact pollution:** Broken shell scripts and historical OpenCode docs clutter the repository, increasing the chance someone will reintroduce dead patterns.

---

## Recommended Actions (Prioritized)

1. **[U-C-01] ★★★ Global search-and-replace `config.md` → `config.yml` in `docs/manual.md`; remove "YAML frontmatter" claims**
2. **[U-C-02] ★★★ Delete or rewrite `config.example.sh` and `configs/*.sh` — either map to `story-writer` CLI or remove entirely**
3. **[M-W-01] ★★★ Rewrite `config-guide.md` Quick Start to use `story-writer tui --story <name>` instead of `opencode`**
4. **[U-C-03] ★★★ In `docs/manual.md`, `README.md`, and feature docs, add explicit "Not yet wired in active orchestrator" callouts for: Phase 7a (outline expander), Phase 7d (recap), Phase 7f (quality-reviewer), Phase 7.5 (prose-scrubber), Phase 6 (wiki population), and scene generation pipeline**
5. **[U-W-01] ★★★ Align phase numbering across `manual.md`, `story-orchestrator.md`, and `story-pipeline/SKILL.md` — adopt the orchestrator's sequential numbering as canonical**
6. **[U-W-02] ★★★ Fix `prompts/skills/story-pipeline/SKILL.md` line 188 — replace "OpenCode delegation" with "Python-native orchestrator dispatches via direct async function calls"**
7. **[U-W-03] ★★★ Rewrite `.github/notes/architecture.md` to reflect Python-native stack, or archive it and redirect to ADR 007/008**
8. **[U-W-03] ★★☆ Update `docs/manual.md` project structure diagram to show `config.yml`, empty `src/application/services/`, and current directory layout**
9. **[M-W-02] ★★☆ Remove `quality-reviewer` from `AGENTS.md` subagent list (or add "not yet wired" qualifier)**
10. **[S-W-01] ★★☆ Update `README.md` to distinguish "fully operational" features from "tool-ready / awaiting orchestrator integration"**
11. **[U-I-01] ★★☆ Document missing `config.yml` flags in `config-guide.md`: `use_improved_recap_sanitizer`, `use_multi_stage_recap_sanitizer`, `enable_outline_critique`, `outline_critique_iterations`, `log_prompt_inputs`, `randomize_seed`, `max_chunk_size`, `overlap_size`**
12. **[U-I-02] ★☆☆ Add a `prompts/skills/` index or summary in `docs/README.md`**
13. **[M-I-01] ★☆☆ Add `_wiki_api.py`, `critique_parser.py`, `migrate_state_slim.py` to `docs/tools.md` inventory**
14. **[S-I-01] ★☆☆ Clarify or remove vestigial `src/presentation/agents/story_orchestrator.py`**
15. **[U-I-02] ★☆☆ Move `docs/features/custom-commands.md` and `compaction-plugin.md` to an archived section or add stronger deprecation banners in `docs/README.md`**
