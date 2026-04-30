# PRD: Python Agent Prompt Repair — Eliminate Tool-Calling Prompts from LLM Execution Path

> The Python-native LLM story generation pipeline currently feeds tool-calling workflow prompts (intended for OpenCode/Copilot runtimes) directly to LLMs via `stream_text()`, causing every agent to output its internal reasoning about which tools to call instead of producing actual creative content (outlines, chapters, etc.).

**Date:** 2026-04-30
**Author:** Planner agent
**Status:** Draft

---

## Problem Statement

When [ADR 007](./adr/007-python-native-orchestration.md) eliminated OpenCode and moved orchestration into pure Python, the migration moved `.opencode/agents/*.md` files to `prompts/agents/` and loaded them via `load_agent_prompt()` as system prompts with "no content changes." This was fundamentally incorrect.

Those `prompts/agents/*.md` files are **tool-calling workflow specifications** — they instruct an agent runtime to call tools (`outline-generator`, `critique-runner`, `scene-writer`, `wiki-snapshot`, etc.) in sequence, pass data between them, and manage savepoints. When fed directly to an LLM without a tool executor, the model does the only thing it can: **role-play the workflow**, outputting step-by-step narration of which tools it would call and why.

### Evidence

The TUI shows the `outline-planner` agent output after the user runs `story-writer tui`:

```
### Phase 1: Prompt Analysis

I am calling `outline-generator` to perform a multi-step analysis...

* `operation`: "analyze-prompt"
* `name`: "The Silence Between Stars"

(Self-correction/Note: I will wait for the tool output to proceed to Phase 2.)
```

This continues indefinitely — the LLM never produces an actual outline because it was told to call tools that don't exist in its execution context.

### Affected Scope

All Python agent classes in `src/presentation/agents/` that call `load_agent_prompt("{agent-name}")` are broken:

| Agent Class | Loads | Expected Output | Actual Output |
|-------------|-------|-----------------|---------------|
| `OutlinePlannerAgent` | `outline-planner.md` | Chapter outline | Tool-calling narration |
| `StoryPlannerAgent` | `story-planner.md` | Arc assessment | Tool-calling narration |
| `ChapterWriterAgent` | `chapter-writer.md` | Chapter prose | Tool-calling narration |
| `FinalEditorAgent` | `final-editor.md` | Edited prose | Tool-calling narration |
| `ConsistencyCheckerAgent` | `consistency-checker.md` | JSON issue list | Tool-calling narration |

The `WikiMaintainerAgent` is **not** affected because it does not use an LLM system prompt — it calls `update_wiki_from_chapter()` directly, which loads generation prompts internally.

The `StoryOrchestratorAgent` is vestigial (returns a static phase list) and also unaffected.

---

## Root Cause Analysis

### Two Prompt Paradigms Were Conflated

The codebase contains **two entirely different categories** of prompt templates that were treated as interchangeable:

1. **Generation prompts** (`prompts/outline/`, `prompts/chapters/`, `prompts/final_edit/`, etc.) — Tell an LLM to *write creative content*. These are the actual prompts used to invoke the model for creative work. They contain instructions like "Create a comprehensive story outline" with variable placeholders like `{prompt}`, `{story_elements}`, `{desired_chapters}`.

2. **Agent workflow prompts** (`prompts/agents/*.md`) — Tell an **agent runtime framework** (OpenCode, Copilot) how to coordinate tools, subagents, and savepoints. They contain sections like "Tools", "Workflow", "Phase 1 — Call `outline-generator` with operation: `analyze-prompt`". These were never meant to be fed directly to an LLM.

### The Migration Error

[ADR 007, Decision point 4](adr/007-python-native-orchestration.md):

> "Agent definitions: The existing `.opencode/agents/*.md` files are relocated to `prompts/agents/` and loaded at startup as system prompt strings (frontmatter stripped). No content changes."

This decision assumed that agent prompts and generation prompts were the same thing. They are not. The "no content changes" clause prevented anyone from noticing or fixing the mismatch.

---

## Goals

1. **Every Python agent must use a generation prompt** when calling the LLM, not an agent workflow prompt.
2. **Agent workflow prompts remain valuable** as documentation of the intended multi-step pipeline, but they must be clearly separated from LLM execution prompts.
3. **Minimal code change** — we should not rewrite the entire pipeline. The fix is a prompt substitution with minor user-prompt construction changes.
4. **Preserve skills** — `prompts/skills/*.md` documents quality constraints, output formats, and conventions. These should continue to be referenced by generation prompts.
5. **No regression** — the `WikiMaintainerAgent` and `StoryOrchestratorAgent` continue working as-is.

---

## Non-Goals

- **Not rewriting the legacy Python tools** (`outline_generator.py`, `scene_writer.py`, `critique_runner.py`, etc.) — they work correctly and are called deterministically by the orchestrator.
- **Not re-implementing OpenCode tool-calling** — the Python-native architecture intentionally avoids this.
- **Not changing pipeline phase ordering** — orchestrator sequencing in `src/presentation/orchestrator.py` is correct.
- **Not deleting `prompts/agents/*.md`** — they remain valuable as pipeline documentation and for any future agent runtime.

---

## Proposed Solution

### High-Level Strategy

For each broken agent, replace the `load_agent_prompt("{agent-name}")` call with a prompt that directly instructs the LLM to produce the agent's creative output. Where the existing prompt library has suitable generation prompts, use them. Where only fragments exist, compose them.

### Mapping: Broken Agent → Correct Prompt Source

| Agent | Broken System Prompt | Correct Prompt Source | Notes |
|-------|----------------------|----------------------|-------|
| `OutlinePlannerAgent` | `prompts/agents/outline-planner.md` | `prompts/outline/create_skeleton.md` | Skeleton-style outline; variables `{prompt}`, `{desired_chapters}`, `{story_elements}`, `{base_context}` |
| `StoryPlannerAgent` | `prompts/agents/story-planner.md` | NEW: `prompts/outline_arc/arc_synthesis.md` | Ask the LLM to assess dramatic arc given outline text |
| `ChapterWriterAgent` | `prompts/agents/chapter-writer.md` | `prompts/scenes/create_content.md` | Full chapter prose generation |
| `FinalEditorAgent` | `prompts/agents/final-editor.md` | `prompts/final_edit/voice_consistency_pass.md` | Chapter-level prose polish |
| `ConsistencyCheckerAgent` | `prompts/agents/consistency-checker.md` | NEW: `prompts/chapter_review/character-voice-consistency.md` | Detect narrative inconsistencies |

### Approach for Each Agent

#### OutlinePlannerAgent

**Current:** Loads `outline-planner.md` which tells the LLM to call `outline-generator analyze-prompt`.

**Fix:** Use `prompts/outline/create_skeleton.md` as the system prompt. In the orchestrator (or agent), populate template variables: `{prompt}` (the user's story prompt), `{desired_chapters}` (from settings), `{early_chapters}`, `{rising_start}`, `{rising_end}`, `{climax_start}`, `{climax_end}`, `{resolution_start}` (computed from desired_chapters). For now, `{story_elements}` and `{base_context}` can be empty or contain a brief placeholder since the full analysis pipeline is not wired.

**Alternative fallback:** If `create_skeleton.md` is too complex (requires variables the current agent doesn't construct), use `prompts/outline/create.md` which is simpler and also a direct generation prompt.

#### StoryPlannerAgent

**Current:** Loads `story-planner.md` which tells the LLM to call `critique-runner run-critics` and `critique-runner run-arc-analysis`.

**Fix:** The orchestrator already calls `critique_runner.py` deterministically for the numeric quality scores. The `StoryPlannerAgent`'s actual purpose in the current pipeline is to produce a **narrative arc assessment** — a qualitative prose evaluation of promise/payoff, tension curve, and pacing. This is an LLM creative task, not a tool-calling task.

Replace with a direct prompt asking the LLM to analyse the dramatic arc given the outline text. This can be composed from `prompts/outline_arc/arc_synthesis.md` and `prompts/outline_arc/promise_payoff.md`.

#### ChapterWriterAgent

**Current:** Loads `chapter-writer.md` which tells the LLM to call `scene-writer parse-definitions`, `wiki-snapshot`, `recap-manager`, etc.

**Fix:** Use `prompts/scenes/create_content.md` as the system prompt. This prompt already tells the LLM to write scene content given context variables. The agent already constructs a basic user prompt with the chapter outline and character/setting context. The user-prompt construction logic is mostly correct; only the system prompt is wrong.

#### FinalEditorAgent

**Current:** Loads `final-editor.md` which tells the LLM to call `scene-writer scrub-analyze`, `rag-query`, `savepoint-mgr`, etc.

**Fix:** Use `prompts/final_edit/voice_consistency_pass.md` as the system prompt. This is a direct prose-polish prompt that operates chapter-by-chapter. The agent's per-chapter processing loop is correct; only the system prompt is wrong.

#### ConsistencyCheckerAgent

**Current:** Loads `consistency-checker.md` which tells the LLM to call `wiki-lint`, `wiki-search`, `rag-query`, `story-state`.

**Fix:** The orchestrator already runs `wiki_lint.py` deterministically. The `ConsistencyCheckerAgent`'s role is to produce a **qualitative narrative consistency assessment** (character voice drift, timeline violations, world-rule contradictions). Replace with a direct prompt asking the LLM to check the chapter for consistency issues and return JSON.

Existing `prompts/chapter_review/character-voice-consistency.md` and `prompts/chapter_review/chapter-character-consistency.md` provide good starting material.

---

## Implementation Plan

### Phase 1: Create Direct Generation Prompts

For each broken agent, create or compose a clean generation prompt file. These new files live alongside existing generation prompts, not in `prompts/agents/`.

| New/Modified Prompt | Contains |
|---------------------|----------|
| `prompts/outline/create_direct.md` | Direct LLM system prompt for outline generation (adapted from `create_skeleton.md`) |
| `prompts/outline/arc_assessment_direct.md` | Direct LLM system prompt for dramatic arc analysis |
| `prompts/chapters/write_chapter_direct.md` | Direct LLM system prompt for chapter writing (adapted from `scenes/create_content.md`) |
| `prompts/final_edit/edit_chapter_direct.md` | Direct LLM system prompt for final edit pass |
| `prompts/chapter_review/consistency_check_direct.md` | Direct LLM system prompt for consistency checking + JSON output spec |

Each prompt:
- Has NO tool names, NO workflow phases, NO "call X with operation Y" language
- Has clear creative instructions and output format
- References `prompts/skills/` conventions where applicable
- Uses `{variable}` placeholders for dynamic content

### Phase 2: Update Agent Classes

Modify each Python agent class:
1. Change `_get_system_prompt()` to load the new direct generation prompt
2. Keep the existing `run()` method signature and structure
3. Adjust user-prompt construction if the new prompt requires different variable substitution
4. Keep stream-to-TUI logic unchanged

### Phase 3: Update Orchestrator Integration

Verify that the orchestrator (`src/presentation/orchestrator.py`) still passes the right arguments to each agent. No changes expected — the agent `run()` signatures stay stable.

### Phase 4: Verify Fix

Run `story-writer tui --story test-fix --prompt prompts/sample-story.md` and observe:
- Outline phase produces actual outline text (chapter titles and summaries), not tool-calling narration
- Chapter generation produces prose, not narration
- Arc assessment produces qualitative feedback, not narration

---

## Acceptance Criteria

- [ ] `OutlinePlannerAgent` produces a chapter-by-chapter outline when given a story prompt
- [ ] `StoryPlannerAgent` produces a qualitative arc assessment (not tool narration) when given an outline
- [ ] `ChapterWriterAgent` generates chapter prose (not tool narration) when given an outline entry
- [ ] `FinalEditorAgent` produces edited prose (not tool narration) when given a chapter draft
- [ ] `ConsistencyCheckerAgent` returns a JSON issue list (not tool narration) when given chapter content
- [ ] `WikiMaintainerAgent` continues to work unchanged
- [ ] TUI streaming output shows flowing creative text, not structured tool-call plans
- [ ] No references to tool names (`outline-generator`, `critique-runner`, `scene-writer`, `wiki-snapshot`) appear in LLM output
- [ ] The entire pipeline from `init` to `assembly` completes successfully on a short story (~3 chapters)

---

## Open Questions

1. **Should we retire `load_agent_prompt()` entirely?** After this fix, `load_agent_prompt()` will be unused in the Python-native runtime. It was designed to load `prompts/agents/*.md` files. The function could be deleted, or it could be repurposed to load the new direct prompts. Recommendation: keep it but point it at a new directory `prompts/python_agents/`.
2. **Should `prompts/agents/*.md` be moved or renamed?** They are documentation, not executable prompts. Recommendation: move to `docs/agents/` or rename to `*.workflow.md` to make their non-executable nature obvious.
3. **The full multistep analysis pipeline** (prompt analysis → 8 analysis chunks → story elements → outline) is not wired in the active orchestrator. The simplified direct outline prompt loses that analytical depth. Should we wire the analysis pipeline first, or accept a simpler direct prompt for now? Recommendation: accept simpler direct prompt now; wire multistep analysis as a future enhancement tracked separately.
4. **Quality review and prose-scrubber** agents are listed in the pipeline skill but not wired in the orchestrator. Since they are not called by Python code, they don't need fixing now.

---

## Related

- [ADR 007: Python-Native Orchestration](adr/007-python-native-orchestration.md) — original migration decision that caused this issue
- [ADR 008: Retire Application Services Layer](adr/008-retire-application-services-layer.md) — architecture status
- [Story Pipeline Skill](../prompts/skills/story-pipeline/SKILL.md) — documents active vs unwired phases
