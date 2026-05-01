---
date: "2026-05-01"
issue: 276
pr: 280
category: agent
targets:
  - ".opencode/agents/coder.md"
  - ".github/notes/gotchas.md"
severity: minor
---

## Prompt Template Refactoring Leaves Dead Code and Loses Runtime Guards

### Finding

During issue #276 (PR #280), the Coder replaced manual `load_agent_prompt()` calls with `PromptLoader` in five agent files (`outline_planner.py`, `story_planner.py`, `chapter_writer.py`, `final_editor.py`, `consistency_checker.py`). The synthesis review (all three models) found:

1. **Dead code:** Each file still contained `_get_system_prompt()` and `self._system_prompt` that were never called after the refactor. The old `load_agent_prompt` import was retained with `# noqa: F401`.
2. **Cache loss:** `PromptLoader` was instantiated fresh on every `run()` call inside loops, defeating the instance-level prompt cache.
3. **Lost truncation guard:** The consistency checker's `chapter_content[:4000]` truncation was dropped when content moved from user message into the system prompt template, risking context-window overflow for local models.

### Observation

These are all variants of the same pattern: when replacing an old pattern with a new one, the Coder focused on the new code path and did not systematically verify:
- Old methods are still called (they weren't)
- New instances should be cached (they weren't)
- Runtime guards on data size should be preserved (they weren't)

The `coder.md` Rule 7 already instructs sweeping for dead code, but the specific case of "pattern replacement produces orphaned methods/fields/imports" is not explicitly called out.

### Suggested Improvement

Add a targeted sub-bullet to `coder.md` Rule 7:

> **When replacing an implementation pattern** (e.g., manual loading → loader utility, string formatting → template, inline → helper) — verify that the old pattern's methods, cached fields, and imports are removed. Do not leave 'fallback' methods that are never called or '# noqa' imports that serve no purpose.

Also add a note about preserving runtime guards:

> **When moving data into a new field or message** (e.g., from user message to system prompt via template) — preserve any existing truncation, clamping, or length guards that protected downstream consumers in the old location.

And tighten `prompts/chapter_review/consistency_check_direct.md` output format: remove the fenced JSON example block (lines 50–61) since the prompt already says "no markdown fences" — the example contradicts the instruction.

### Action Taken

Applied:
- Added "pattern replacement" sub-bullet to `coder.md` Rule 7
- Added "preserve runtime guards" sub-bullet to `coder.md` Rule 7
- Removed fenced JSON example from `consistency_check_direct.md`
- Updated gotcha #039 source line to include issue #276
