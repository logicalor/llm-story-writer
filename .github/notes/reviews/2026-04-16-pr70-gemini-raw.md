# Code Review Report — PR #70

**Branch:** `feat/issue-68-plugin-type-interfaces`
**Reviewer:** Gemini (Reviewer sub-agent)
**Date:** 2026-04-16

---

## Review Summary

This PR delivers two related objectives under Issue #68: (1) flattening the synthesized review dispatch architecture from depth-2 to depth-1 to resolve the non-responsive VS Code window issue, and (2) adding local TypeScript interface definitions for the compaction plugin's API boundary with OpenCode. The changes are well-structured across agent configuration, shared documentation, plugin code, feature documentation, and verification tests. One file path inconsistency was introduced between the new convention in multi-model-synthesis.md and the pre-existing Step 5 in the Synthesizing Reviewer agent.

**Files Reviewed:** 10
**Findings:** 0 Critical, 1 Warning, 1 Suggestion

---

## Findings

### Critical Findings

None.

### Warning Findings

```
[W-01] Synthesis output file path inconsistent between Orchestrator dispatch and Synthesizing Reviewer Step 5
Category: Correctness
Severity: Warning
File: .github/agents/synthesizing-reviewer.agent.md
Lines: 59
Description: The Synthesizing Reviewer's Step 5 instructs writing the synthesis to
`.github/notes/reviews/YYYY-MM-DD-synthesis.md`, but the new File-Persisted Dispatch
convention in `.github/agents/_shared/multi-model-synthesis.md` and the Orchestrator's
Phase C dispatch prompt both specify `.github/notes/reviews/YYYY-MM-DD-pr{N}-synthesis.md`
(with the `pr{N}` segment). The diff description confirms Steps 2–5 were left "unchanged"
during the refactor, so this stale path was not updated to match the new convention.
In practice, the Orchestrator's dispatch prompt overrides the agent's internal instruction
(it explicitly passes the output path), so runtime behaviour is likely correct. However,
the conflicting internal instruction could confuse the agent or a future maintainer reading
the agent file in isolation.
Suggestion: Update Step 5 in synthesizing-reviewer.agent.md to use the new convention:
  `Write the review summary to .github/notes/reviews/YYYY-MM-DD-pr{N}-synthesis.md`
  — matching the path provided in the dispatch prompt from the Orchestrator.
```

### Suggestions

```
[S-01] Test file docstring references Issue #23 instead of Issue #68 for newly added tests
Category: Documentation
Severity: Suggestion
File: tests/unit/test_compaction_plugin.py
Lines: 1
Description: The file-level docstring reads "Verification tests for Issue #23 — Build
Compaction Plugin", which was correct when the test file was originally created. This PR
adds four new test methods (`test_plugin_context_interface_defined`,
`test_compaction_input_interface_defined`, `test_compaction_output_interface_defined`,
`test_plugin_export_uses_typed_parameters`) as part of Issue #68. The docstring was not
updated to reflect the expanded scope. This is cosmetic — it does not affect test
execution or correctness.
Suggestion: Either append Issue #68 to the docstring (e.g., "Verification tests for
Issue #23/68 — Build Compaction Plugin & Typed API Boundary") or leave a brief comment
above the new test methods indicating they were added for Issue #68.
```

---

## Phase 1 — Structural Review

- **Commit messages** — All three commits follow the convention (`refactor:`, `docs()`, `feat()`) and reference `(#68)`. Clear and descriptive. ✅
- **Branch name** — `feat/issue-68-plugin-type-interfaces` follows the `feat/issue-N-...` pattern. ✅
- **Scope** — 10 files changed, reasonable size. The two objectives (flatten dispatch + typed interfaces) are logically related and appropriately bundled. ✅
- **No unrelated changes** — All changes relate to Issue #68. ✅
- **Numbered step lists** — Orchestrator Steps 0–9, no gaps. Synthesizing Reviewer Steps 1–5, no gaps. ✅
- **File relocation** — No files were moved or renamed. ✅
- **Sibling item orphaning** — Steps 0 and 1 were removed from the Synthesizing Reviewer and replaced with a new Step 1. The renumbering is clean (Steps 1–5, sequential). ✅
- **Stale prose counts** — No numeric counts affected by the changes. ✅
- **`tools:` array coupling** — The `agent` tool was removed from the Synthesizing Reviewer's tools array, and all body text dispatching sub-agents was also removed. The `edit` tool was added to all three reviewer agents' tools arrays, and their body text instructs writing reports using `edit`. Both directions verified. ✅
- **Model-specific variant sync** — The three reviewer agents (`reviewer-claude`, `reviewer-gpt`, `reviewer-gemini`) share identical body text, differing only in `name`, `description`, and `model` fields. ✅
- **Section heading drift** — The Synthesizing Reviewer's description was updated from "coordinator" to "synthesizer" language, matching the new body content. ✅
- **YAML frontmatter section removal** — The `agents:` list was removed from the Synthesizing Reviewer frontmatter. No body text references dispatching agents — references were replaced with file-reading instructions. ✅
- **Agent `model:` field format** — All agent files use scalar string model values (not arrays). ✅
- **Shell snippet safety** — No new shell snippets introduced in agent or skill files. ✅

## Phase 2 — Code Review

### Plugin Code (`.opencode/plugins/story-compaction.ts`)

- The three new interfaces (`PluginContext`, `CompactionInput`, `CompactionOutput`) are minimal and accurately reflect the observed runtime contract. ✅
- `CompactionInput` is intentionally empty — documented as "reserved for future use by OpenCode". ✅
- The `export default` signature and hook handler parameters now use the typed interfaces instead of `any`. ✅
- Remaining `any` usage (`Record<string, any>` in `StoryState`, `parseFrontmatter`) is pre-existing internal code not modified by this PR — out of scope. ✅
- No functional logic changes — this is a pure type annotation refactor. ✅

### Agent Configuration Files

- Orchestrator Step 7 restructured into four clear phases (A–D). The dispatch flow is logically sound: prepare package → dispatch reviewers → dispatch synthesizer → triage. ✅
- Sequential dispatch is explicitly enforced with a bold prohibition on parallel execution. ✅
- The Synthesizing Reviewer correctly no longer lists sub-agents or includes the `agent` tool. ✅
- All three reviewer agents include `execute`, `read`, `edit`, `search`, `todo` in their tools arrays — sufficient for reading the review package and writing the report file. ✅
- `disable-model-invocation: true` and `user-invocable: false` are set on all reviewer agents, preventing direct user invocation. ✅

## Phase 3 — Frontend Review

Not applicable — no frontend changes.

## Phase 4 — Security Review

- No credentials, API keys, or sensitive data in any changed files. ✅
- No new user input handling or attack surface changes. ✅
- The plugin type annotations do not change any security-relevant behaviour. ✅
- Path validation (`isWithinBase`) is pre-existing and unmodified. ✅

## Phase 5 — Testing Review

- Four new test methods verify the three interface definitions and typed parameter usage. ✅
- Tests use regex pattern matching against the TypeScript source, consistent with the existing test pattern in the same file (e.g., `test_plugin_contains_compacting_hook`, `test_plugin_path_validation`). ✅
- Assertions are meaningful — each test validates specific interface members (e.g., `directory?: string`, `context: string[]`), not just the presence of the interface keyword. ✅
- No skipped tests. ✅

## Phase 6 — Performance Review

No performance-relevant changes.

## Phase 7 — Documentation Review

- The new "Plugin API Types" section in `docs/features/compaction-plugin.md` accurately documents all three interfaces with code examples and a usage table. ✅
- The `docs/tools.md` addition is a single bullet point in the Design section for the compaction plugin, accurately summarising the typed API boundary. ✅
- The multi-model-synthesis.md "File-Persisted Dispatch" section is well-written, clearly documents the pattern, benefits, and file path convention. ✅
- File paths and links in documentation resolve correctly. ✅

---

## Overall Assessment

This is a clean, well-structured PR that delivers both the architectural fix (flattening review dispatch to depth-1) and the type safety improvement (plugin API boundary interfaces). The code changes are minimal and focused — three interface definitions and type annotations replacing `any` at the plugin's API boundary. The agent reconfiguration is thorough, with proper coupling between tools arrays and body text.

The single warning (stale file path convention in the Synthesizing Reviewer's Step 5) is low-risk since the Orchestrator's dispatch prompt explicitly provides the correct output path, but should be fixed for consistency. The PR is ready for merge after addressing the warning finding.
