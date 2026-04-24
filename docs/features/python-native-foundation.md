# Python-Native Foundation

> Agent prompt relocation, Python prompt loading, and typed pipeline handoffs introduced in Issue #158, then extended for orchestrator persistence in Issue #161.

## Overview

Issue #158 implements the first shared infrastructure needed for the Python-native orchestration migration. The change does not alter prompt content or story-generation behaviour. Instead, it moves the existing agent prompts into the main `prompts/` tree, adds a Python loader that returns prompt bodies without YAML frontmatter, and introduces typed dataclasses for phase-to-phase payloads and persisted pipeline state.

This foundation reduces path sprawl, gives later Python orchestration work a stable prompt-loading entry point, and replaces ad hoc phase payloads with explicit Python types that can round-trip through JSON savepoints.

## Agent Prompt Relocation

All eleven agent prompt files now live in `prompts/agents/`. Filenames and Markdown bodies were preserved verbatim during the move so downstream migration tasks can keep using the existing prompt content.

The canonical agent prompt directory is now:

```text
prompts/agents/
```

This directory contains:

- `chapter-outline-expander.md`
- `chapter-writer.md`
- `character-sheet-generator.md`
- `consistency-checker.md`
- `final-editor.md`
- `outline-planner.md`
- `prose-scrubber.md`
- `quality-reviewer.md`
- `story-orchestrator.md`
- `story-planner.md`
- `wiki-maintainer.md`

## Agent Prompt Loader

`src/infrastructure/prompts/agent_prompt_loader.py` adds a small process-local loader for those prompt files.

### Behaviour

- Resolves `prompts/agents/` from the module's `__file__` path, not the current working directory
- Loads `prompts/agents/{name}.md` by file stem
- Strips YAML frontmatter when the file starts with an opening `---` block
- Returns the Markdown body unchanged for files without frontmatter
- Caches loaded prompt bodies for the lifetime of the process
- Raises `ConfigurationError` when the named prompt file does not exist
- Raises `ValueError` when a frontmatter block is opened but never closed

### Example

```python
from infrastructure.prompts.agent_prompt_loader import load_agent_prompt

prompt_text = load_agent_prompt("story-orchestrator")
```

Use `clear_agent_prompt_cache()` in tests or other situations where a fresh on-disk read is required.

## Typed Pipeline Handoffs

`src/application/pipeline/` is now a dedicated package for Python-native pipeline coordination primitives. Its first module, `src/application/pipeline/handoffs.py`, defines five stdlib `@dataclass` payload types.

| Type | Produced By | Consumed By | Purpose |
|------|-------------|-------------|---------|
| `OutlineResult` | Outline phase | Narrative arc analysis, character generation, settings generation | Carries the structured outline plus summary metadata |
| `ChapterDraft` | Chapter loop | Quality review, final edit | Carries one drafted chapter and its savepoint metadata |
| `WikiUpdateBatch` | Wiki maintainer | Wiki storage layer | Carries page-update batches written after chapter generation |
| `ApprovalDecision` | Approval gate | Orchestrator | Carries approve/revise/reject decisions, optional feedback, and batch-mode auto-approval state |
| `PipelineState` | Orchestrator | Savepoint system and later phases | Carries the persisted run state across the full pipeline |

`PipelineState` is the persistence boundary for the new package. It supports `to_dict()` and `from_dict()` so savepoints can store and restore nested dataclass state without custom serializers. `to_json()` emits formatted JSON for debugging or persistence helpers.

Issue #161 extends `PipelineState` with two orchestrator-facing fields used by the headless runner in `src/presentation/orchestrator.py`:

| Field | Type | Purpose |
|------|------|---------|
| `savepoints` | `list[str]` | Ordered list of savepoint labels written during the run |
| `status` | `str` | Lifecycle status for the persisted run; starts as `running`, then becomes `rejected` or `complete` |

Those fields are part of the JSON round-trip contract and are now required for resume behavior.

## Developer Guide

### Key Files

- `prompts/agents/` — canonical agent prompt location
- `src/infrastructure/prompts/agent_prompt_loader.py` — frontmatter-stripping prompt loader with in-memory cache
- `src/application/pipeline/__init__.py` — pipeline package marker
- `src/application/pipeline/handoffs.py` — typed phase payload dataclasses and `PipelineState` persistence helpers
- `tests/unit/test_agent_prompt_loader.py` — loader behaviour and cache coverage
- `tests/unit/test_pipeline_handoffs.py` — dataclass round-trip and JSON serialisation coverage
- `tests/unit/test_prompt_relocation.py` — prompt-tree relocation baseline check updated for `prompts/agents/`

## Testing

Issue #158 added dedicated unit coverage for both new modules:

- `test_agent_prompt_loader.py` verifies frontmatter stripping, verbatim loads, missing-file handling, malformed frontmatter handling, cache hits, and cache clearing
- `test_pipeline_handoffs.py` verifies nested `PipelineState` round-trips, `ApprovalDecision` defaults, JSON serialisation, and package importability
- `test_prompt_relocation.py` now treats the prompt tree as a growing set and asserts a minimum Markdown file count so the additional agent prompts do not break the relocation baseline

## Related

- [Pipeline Primitives](./pipeline-primitives.md)
- [PRD: Python-Native Orchestration and TUI](../planning/python-native-migration/prd.md)
- [Story Orchestrator](./story-orchestrator.md)
- Issue #158 — Agent prompt loader and typed pipeline handoffs
- Issue #161 — Python pipeline orchestrator (headless)
- PR #167 — Python-native migration [1/9]
- PR #171 — Python-native migration [4/9]