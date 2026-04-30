# Task Breakdown: Python Agent Prompt Repair

> Implements [PRD: Python Agent Prompt Repair](prd.md)

**Date:** 2026-04-30
**Author:** Planner agent
**Status:** Draft

---

## Tasks

### Task 1: Design Direct Generation Prompt Templates

**Type:** backend (prompt design)
**Estimated scope:** medium
**Dependencies:** none

**Description:**
For each of the 5 broken agents, compose a clean prompt template that instructs the LLM directly to produce creative content (outlines, chapters, edits, assessments) without any tool-calling or agent-workflow language. These templates must reference existing skill documents (quality constraints, output format conventions) and use `{variable}` placeholders for dynamic content.

New files to create:
- `prompts/outline/create_direct.md` — Direct outline generation system prompt
- `prompts/outline/arc_assessment_direct.md` — Direct arc quality assessment system prompt
- `prompts/chapters/write_chapter_direct.md` — Direct chapter writing system prompt
- `prompts/final_edit/edit_chapter_direct.md` — Direct chapter editing system prompt
- `prompts/chapter_review/consistency_check_direct.md` — Direct consistency checking system prompt

Each prompt must:
1. Contain no tool names, no "call X with operation Y", no phase-by-phase workflow narration
2. Reference `prompts/skills/` documents for quality constraints where applicable
3. Define clear output format (narrative outline, prose, JSON, etc.)
4. Accept variables via `{variable}` syntax matching `PromptLoader` substitution

**Acceptance Criteria:**
- [ ] All 5 prompt files are created and free of tool-calling language
- [ ] Each file references at least one skill document for quality/format constraints
- [ ] A spot-check of each file confirms output format is explicitly specified
- [ ] `ruff check` passes on the repository (no syntax changes expected yet, just baseline)

**Key Files:**
- `prompts/outline/create_direct.md` — new
- `prompts/outline/arc_assessment_direct.md` — new
- `prompts/chapters/write_chapter_direct.md` — new
- `prompts/final_edit/edit_chapter_direct.md` — new
- `prompts/chapter_review/consistency_check_direct.md` — new

---

### Task 2: Fix OutlinePlannerAgent Prompt Loading

**Type:** backend
**Estimated scope:** small
**Dependencies:** Task 1

**Description:**
Modify `OutlinePlannerAgent` to load the new direct generation prompt (`prompts/outline/create_direct.md`) instead of `prompts/agents/outline-planner.md`. Ensure the orchestrator (or agent itself) populates required template variables (`{prompt}`, `{desired_chapters}`, `{story_elements}`, `{base_context}`, and computed chapter position markers). The agent's `run()` signature and TUI streaming behavior must remain unchanged.

**Acceptance Criteria:**
- [ ] `OutlinePlannerAgent._get_system_prompt()` loads `prompts/outline/create_direct.md`
- [ ] The agent populates all required template variables before calling the LLM
- [ ] Running the outline phase in TUI produces actual chapter outline text (titles, summaries, act structure), not tool-calling narration
- [ ] No references to `outline-generator`, `critique-runner`, or `scene-writer` appear in the LLM output
- [ ] Unit test for `OutlinePlannerAgent` passes (`pytest tests/unit/test_outline_planner_agent.py -v`)

**Key Files:**
- `src/presentation/agents/outline_planner.py`
- `src/presentation/orchestrator.py` (variable population logic, if necessary)

---

### Task 3: Fix ChapterWriterAgent Prompt Loading

**Type:** backend
**Estimated scope:** small
**Dependencies:** Task 1

**Description:**
Modify `ChapterWriterAgent` to load `prompts/chapters/write_chapter_direct.md` instead of `prompts/agents/chapter-writer.md`. The agent already constructs user prompts with outline and setting context — verify that the variable names match the new prompt template. Update `agent_prompt_loader.py` references or replace entirely with `PromptLoader`.

**Acceptance Criteria:**
- [ ] `ChapterWriterAgent._get_system_prompt()` loads the new direct prompt
- [ ] User-prompt construction in `run()` matches template variables
- [ ] TUI chapter-generation phase produces actual prose, not tool-calling narration
- [ ] No tool names appear in chapter output
- [ ] `pytest tests/unit/test_chapter_writer_agent.py -v` passes

**Key Files:**
- `src/presentation/agents/chapter_writer.py`
- `src/infrastructure/prompts/agent_prompt_loader.py` (deprecate or redirect)

---

### Task 4: Fix StoryPlannerAgent Prompt Loading

**Type:** backend
**Estimated scope:** small
**Dependencies:** Task 1

**Description:**
Modify `StoryPlannerAgent` to use `prompts/outline/arc_assessment_direct.md` for its qualitative arc assessment. The orchestrator already runs `critique_runner.py` for numeric scores; this agent's role is to provide the prose-level dramatic arc analysis. Ensure the agent receives the outline text and outputs structured feedback.

**Acceptance Criteria:**
- [ ] `StoryPlannerAgent` loads direct generation prompt
- [ ] Outputs qualitative narrative arc assessment (tension curve, promise/payoff, pacing) instead of tool narration
- [ ] TUI shows flowing analysis text, not "Calling `critique-runner`"
- [ ] `pytest tests/unit/test_story_planner_agent.py -v` passes

**Key Files:**
- `src/presentation/agents/story_planner.py`

---

### Task 5: Fix FinalEditorAgent Prompt Loading

**Type:** backend
**Estimated scope:** small
**Dependencies:** Task 1

**Description:**
Modify `FinalEditorAgent` to use `prompts/final_edit/edit_chapter_direct.md` for chapter-level prose polish. The agent's per-chapter processing loop is correct; only the system prompt needs replacement.

**Acceptance Criteria:**
- [ ] `FinalEditorAgent` loads direct generation prompt
- [ ] TUI final-edit phase shows edited prose, not tool narration
- [ ] `pytest tests/unit/test_final_editor_agent.py -v` passes

**Key Files:**
- `src/presentation/agents/final_editor.py`

---

### Task 6: Fix ConsistencyCheckerAgent Prompt Loading

**Type:** backend
**Estimated scope:** small
**Dependencies:** Task 1

**Description:**
Modify `ConsistencyCheckerAgent` to use `prompts/chapter_review/consistency_check_direct.md`. The orchestrator already runs `wiki_lint.py` for wiki validation; this agent provides qualitative narrative consistency assessment (character voice drift, timeline violations, world-rule contradictions). Output must be a JSON issue list.

**Acceptance Criteria:**
- [ ] `ConsistencyCheckerAgent` loads direct generation prompt
- [ ] Outputs JSON list of consistency issues, not tool narration
- [ ] TUI shows structured issue list, not "Calling `wiki-lint`"
- [ ] `pytest tests/unit/test_consistency_checker_agent.py -v` passes

**Key Files:**
- `src/presentation/agents/consistency_checker.py`

---

### Task 7: Deprecate or Remove `load_agent_prompt()` Infrastructure

**Type:** backend (cleanup)
**Estimated scope:** small
**Dependencies:** Tasks 2–6

**Description:**
`load_agent_prompt()` in `src/infrastructure/prompts/agent_prompt_loader.py` was purpose-built to load `prompts/agents/*.md` files as LLM system prompts. After Tasks 2–6, it will be unused in the Python-native runtime. Either delete the file (and `load_agent_prompt()`) or replace its implementation to load the new direct prompts from a cleaner path. If deletion is chosen, update any import references.

**Acceptance Criteria:**
- [ ] `agent_prompt_loader.py` is either deleted or its implementation replaced
- [ ] No import errors anywhere in `src/`
- [ ] `mypy src/` passes
- [ ] `ruff check --fix .` passes

**Key Files:**
- `src/infrastructure/prompts/agent_prompt_loader.py`

---

### Task 8: Orchestrator Integration Verification

**Type:** full-stack (integration)
**Estimated scope:** small
**Dependencies:** Tasks 2–7

**Description:**
Run the full `story-writer tui` pipeline end-to-end on a short story (≤ 3 chapters) and verify that every phase produces correct output. Confirm that `WikiMaintainerAgent` and `StoryOrchestratorAgent` continue working unchanged.

**Acceptance Criteria:**
- [ ] `story-writer tui --story test-fix --prompt prompts/sample-story.md` completes all pipeline phases without errors
- [ ] Outline phase produces actual outline text
- [ ] Chapter-writing phase produces actual prose
- [ ] Arc assessment phase produces qualitative feedback
- [ ] Final edit phase produces polished prose
- [ ] Consistency check phase produces JSON issue list
- [ ] TUI streaming output shows flowing creative text throughout, not tool-plan text
- [ ] No tool names (`outline-generator`, `critique-runner`, `scene-writer`, `wiki-snapshot`, `recap-manager`) appear in any LLM-generated output

**Key Files:**
- `src/presentation/orchestrator.py`
- `src/presentation/cli/main.py`

---

### Task 9: Update `.mdc` Rule Files and Manual Documentation

**Type:** documentation
**Estimated scope:** small
**Dependencies:** Tasks 2–8

**Description:**
Update the `.mdc` copilot rules in `.copilot/rules/` to reflect the new prompt architecture (direct generation vs. agent workflow). Update `docs/manual.md` if it references `prompts/agents/` as executable prompts. Clarify that `prompts/agents/*.md` are workflow specifications for agent runtimes, not direct LLM prompts.

**Acceptance Criteria:**
- [ ] Copilot rules no longer treat `prompts/agents/*.md` as directly loadable LLM prompts
- [ ] `docs/manual.md` accurately describes the prompt architecture
- [ ] A note is added somewhere (README or manual) explaining the two prompt categories

**Key Files:**
- `.copilot/rules/prompts.mdc`
- `docs/manual.md`
- `README.md` (optional)

---

## Task Ordering Summary

```
Task 1 —► Task 2 —► Task 3 —► Task 4 —► Task 5 —► Task 6
(prompts)  (outline)  (chapter)  (story)    (editor)   (checker)
              │          │          │          │          │
              └──────────┴──────────┴──────────┴──────────┘
                                   ▼
                              Task 7 (cleanup)
                                   ▼
                              Task 8 (integration)
                                   ▼
                              Task 9 (docs)
```

All agent fixes (Tasks 2–6) depend on Task 1 but are independent of each other and can be implemented in parallel.
