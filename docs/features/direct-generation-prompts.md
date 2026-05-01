# Direct-Generation Prompts

> Clean, tool-free prompt templates for Python-native LLM execution, replacing workflow-spec prompts that caused agents to role-play tool-calling instead of producing creative content.

## Overview

The Python-native story generation pipeline previously loaded agent workflow prompts (`prompts/agents/*.md`) directly into LLM system messages. Those files were written for OpenCode and Copilot agent runtimes — they contain tool names, phase instructions, and savepoint logic. Without a tool executor, the LLM role-played the workflow and output step-by-step narration instead of creative content.

Issue #276 / PR #280 fixes this by introducing direct-generation prompts that instruct the LLM to produce creative output directly — outlines, prose, edits, and structured analysis — with no tool-calling language. Agents now load these prompts via `PromptLoader` (from `src/infrastructure/prompts/prompt_loader.py`), which supports `{variable}` substitution for dynamic context injection at runtime. Agents send minimal user messages and place all creative instruction in the system prompt, eliminating any ambiguity about the LLM's role.

## Two Prompt Paradigms

The repository now maintains two distinct prompt categories:

| Category | Location | Audience | Content |
|----------|----------|----------|---------|
| **Agent workflow prompts** | `prompts/agents/*.md` | OpenCode, Copilot, and human readers | Tool-calling specifications, phase sequences, runtime coordination |
| **Direct-generation prompts** | `prompts/outline/`, `prompts/chapters/`, `prompts/final_edit/`, `prompts/chapter_review/` | Python-native agents and LLMs | Creative instructions, output formats, `{variable}` placeholders |

`prompts/agents/*.md` remain valuable as pipeline documentation and for any future agent runtime. They are **not** deleted or deprecated — they are simply no longer fed to the LLM by the Python-native orchestrator.

## Direct-Generation Prompt Inventory

| Prompt File | Purpose | Loaded By | Output |
|---|---|---|---|
| `prompts/outline/create_skeleton.md` | High-level outline skeleton generation with pacing-variable guidance | `OutlinePlannerAgent` | Skeleton outline text plus parseable chapter skeletons |
| `prompts/outline/expand_chapter_detail.md` | Expand one chapter from the skeleton into a detailed beat block | `OutlinePlannerAgent` | Per-chapter outline detail written to disk and returned in `OutlineResult.chapter_details` |
| `prompts/outline/strip_elements.md` | Strip scaffold elements from the skeleton for downstream enrichment notes | `OutlinePlannerAgent` | Outline cleanup text stored in `OutlineResult.enrichment_suggestions` |
| `prompts/outline/create_direct.md` | Fallback single-call outline generation when outline expansion is disabled | `OutlinePlannerAgent` | Narrative outline (chapter titles + summaries) |
| `prompts/outline/arc_assessment_direct.md` | Qualitative dramatic arc assessment (tension, promise/payoff, pacing) | `StoryPlannerAgent` | Structured prose assessment with verdict |
| `prompts/chapters/write_chapter_direct.md` | Full chapter prose generation with character/setting context | `ChapterWriterAgent` | Chapter prose (~3000–5000 words) |
| `prompts/final_edit/edit_chapter_direct.md` | Chapter-level prose polish (voice, pacing, dialogue) | `FinalEditorAgent` | Polished chapter prose |
| `prompts/chapter_review/consistency_check_direct.md` | Narrative consistency analysis (voice drift, timeline, world rules) | `ConsistencyCheckerAgent` | JSON issue list |

## Prompt Loading

Python-native agents load direct-generation prompts through `PromptLoader` in `src/infrastructure/prompts/prompt_loader.py`:

```python
from infrastructure.prompts.prompt_loader import PromptLoader

loader = PromptLoader(prompts_dir="prompts")
system_prompt = loader.load_prompt(
    "chapters/write_chapter_direct",
    variables={
        "chapter_number": "1",
        "chapter_title": "The Signal",
        "chapter_summary": "...",
        "story_name": "my-story",
        "base_context": "...",
        "character_context": "...",
        "setting_context": "...",
    },
)
```

`PromptLoader` supports both `{variable}` and `{{variable}}` substitution syntax and caches loaded prompt bodies for the process lifetime.

### Legacy Loader

`load_agent_prompt()` in `src/infrastructure/prompts/agent_prompt_loader.py` was removed in PR #284 (issue #277). It originally loaded `prompts/agents/*.md` and stripped YAML frontmatter, but all Python-native agents now use `PromptLoader` from `src/infrastructure/prompts/prompt_loader.py` instead.

## Agent Integration

Each active direct-generation prompt is loaded by a specific Python-native agent in `src/presentation/agents/`. The agents compute runtime variables and inject them into the system prompt via `PromptLoader.load_prompt()`. Every agent sends a minimal user message (e.g., "Write the chapter now.") while placing all creative instruction in the system prompt.

### OutlinePlannerAgent

`src/presentation/agents/outline_planner.py`

- **Loads when `expand_outline=true`:** `outline/create_skeleton.md`, then `outline/expand_chapter_detail.md` once per chapter, then `outline/strip_elements.md`
- **Loads when `expand_outline=false`:** `outline/create_direct.md`
- **Computed variables:**
  - `prompt` — the story prompt, optionally appended with revision feedback
  - `desired_chapters` — from `GenerationSettings.wanted_chapters`
  - `early_chapters`, `rising_start`, `rising_end`, `climax_start`, `climax_end`, `resolution_start` — act-boundary values derived mathematically from `wanted_chapters`
  - `story_elements`, `base_context` — story-foundation outputs forwarded by the orchestrator into both outline modes
  - `previous_chunks`, `continuity_summary`, `chunk_start`, `total_chapters` — per-chapter expansion variables for `expand_chapter_detail`
- **User messages:**
  - Skeleton stage: `{"role": "user", "content": "Please generate the complete outline."}`
  - Detail stage: `{"role": "user", "content": "Please expand chapter N."}`
  - Strip stage: `{"role": "user", "content": "Please strip the outline elements."}`
- **Persistence:** Writes `stories/<story>/outline/skeleton.md` plus `stories/<story>/outline/details/chapter_{N}.md`. Existing detail files are reused so resumed runs skip already-expanded chapters.
- **Output parsing:** The skeleton or direct output is parsed by `_parse_chapter_outlines()` into chapter dicts. The returned `OutlineResult` now carries `chapter_skeletons`, `chapter_details`, and `enrichment_suggestions` in addition to the summary, genre, and themes.

### StoryPlannerAgent

`src/presentation/agents/story_planner.py`

- **Loads:** `outline/arc_assessment_direct.md`
- **Computed variables:**
  - `outline` — the `OutlineResult.summary` plus a JSON dump of `outline_result.chapter_outlines`
  - `critic_summary`, `arc_distribution`, `promise_payoff` — currently empty strings (reserved for future use)
- **User message:** `{"role": "user", "content": "Provide your assessment."}`
- **Output parsing:** `_parse_verdict()` extracts a verdict code (`significant_issues`, `minor_concerns`, or `strong`) from the prose response.

### ChapterWriterAgent

`src/presentation/agents/chapter_writer.py`

- **Loads:** `chapters/write_chapter_direct.md`
- **Computed variables:**
  - `chapter_number`, `chapter_title`, `chapter_summary` — from the current chapter outline
  - `story_name` — the story identifier
  - `character_context` — aggregated from JSON sheets in `stories/{story}/characters/*.json` (reads `name`, prefers `abridged`, falls back to `summary`, then falls back to the first 300 chars of `sheet`)
  - `setting_context` — aggregated from JSON sheets in `stories/{story}/settings/*.json` (same logic as characters)
  - `base_context` — combined `## Characters` and `## Settings` sections
  - `previous_chapter_summary`, `next_chapter_summary` — from adjacent chapter outlines
  - `story_elements` — currently empty string (reserved for future use)
- **User message:** `{"role": "user", "content": "Write the chapter now."}`
- **Output:** Returns `ChapterDraft` with full prose, title, and word count.
- **Security:** Sanitises `story_name` against path traversal (`..`, `/`, `\`) before building filesystem paths.

### FinalEditorAgent

`src/presentation/agents/final_editor.py`

- **Loads:** `final_edit/edit_chapter_direct.md`
- **Computed variables:**
  - `chapter_text` — the full raw draft content
  - `chapter_number`, `chapter_title` — from the `ChapterDraft`
  - `prior_chapters_summary` — a summary of all previously approved chapters (first 200 chars of their content with line breaks replaced by spaces), excluding the current chapter
- **User message:** `{"role": "user", "content": "Return the polished chapter."}`
- **Output:** Returns `FinalEditResult` with edited chapters. If the LLM returns empty text, the original chapter content is preserved.

### ConsistencyCheckerAgent

`src/presentation/agents/consistency_checker.py`

- **Loads:** `chapter_review/consistency_check_direct.md`
- **Computed variables:**
  - `chapter_content` — the raw chapter text
  - `story_name`, `chapter_number` — story identifier and chapter index
  - `outline` — populated by `_extract_outline_text(outline_result, chapter_number)`: prefers `chapter_details[N-1]` (JSON-serialised), falls back to `chapter_outlines[N-1]`, returns `""` when neither is present
- **User message:** `{"role": "user", "content": "Return the JSON consistency report."}`
- **Output parsing:** `_extract_consistency_result()` first attempts the new direct-generation JSON format (`{"issues": [...], "has_critical_findings": bool}`), then falls back to the legacy format (`wiki_lint_findings`, `semantic_findings`, `cross_chapter_findings`). It also strips JSON markdown fences automatically.
- **Returns:** A dict with `issues` (list) and `passed` (bool).

## Test Coverage

Two existing unit tests were updated to reflect the PromptLoader-based prompt loading:

### `tests/unit/test_chapter_writer_context.py`

This test verifies that character and setting context are correctly injected into the system prompt during chapter writing. The PR updated:

- **Assertion target change:** Tests now inspect the `system` message content instead of the `user` message, reflecting the shift from workflow-spec prompts (previously loaded via `load_agent_prompt` into user messages) to direct-generation prompts (loaded via `PromptLoader` into system messages).
- **Covered scenarios:**
  - Character sheet context injection (`test_chapter_writer_includes_character_context`)
  - Setting sheet context injection (`test_chapter_writer_includes_setting_context`)
  - Graceful handling when no sheets exist (`test_chapter_writer_no_context_when_no_sheets`)

### `tests/unit/test_consistency_checker.py`

This test verifies the consistency checker's JSON parsing and agent integration. The PR updated:

- **Patched path change:** The test now patches `infrastructure.prompts.prompt_loader.PromptLoader.load_prompt` instead of the removed `load_agent_prompt`, reflecting the new loader pattern used by `ConsistencyCheckerAgent`.
- **Covered scenarios:**
  - No-issues response parsing (`test_extract_consistency_result_no_issues`)
  - Critical findings detection (`test_extract_consistency_result_with_critical_findings`)
  - Malformed JSON graceful fallback (`test_extract_consistency_result_malformed_json_fallback`)
  - JSON-inside-markdown-fence handling (`test_extract_consistency_result_json_in_fence`)
  - Null section fallback (`test_extract_consistency_result_null_sections_fallback`)
  - Non-dict payload handling (`test_extract_consistency_result_non_dict_payload`)
  - Async stream emission and end-to-end agent run (`test_run_emits_tokens_and_returns_parsed_result`)

## Design Rules for Direct Prompts

Every direct-generation prompt follows these constraints:

- **No tool names** — no references to `outline-generator`, `critique-runner`, `scene-writer`, `wiki-snapshot`, etc.
- **No workflow phases** — no "Phase 1 — Call X with operation Y" language
- **No self-correction notes** — no "(Self-correction: I will wait for the tool output)"
- **Clear creative instructions** — the LLM knows exactly what to write
- **Explicit output format** — narrative outline, prose, or JSON schema specified
- **`{variable}` placeholders** — dynamic content injected via `PromptLoader`

## Related

- [Python-Native Foundation](./python-native-foundation.md)
- [Story Orchestrator](./story-orchestrator.md)
- [Story Planner](./story-planner.md)
- [Prose Quality Passes](./prose-quality-passes.md)
- [PRD: Python Agent Prompt Repair](../planning/fix-python-agent-prompts/prd.md)
- Issue #276 — Design direct-generation prompt templates
- PR #280 — Implementation
