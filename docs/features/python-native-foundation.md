# Python-Native Foundation

> Agent prompt relocation, Python prompt loading, typed pipeline handoffs, CLI packaging, and final OpenCode artefact cleanup across Issues #158, #161, #162, and #164.

## Overview

Issue #158 implements the first shared infrastructure needed for the Python-native orchestration migration. The change does not alter prompt content or story-generation behaviour. Instead, it moves the existing agent prompts into the main `prompts/` tree, adds a Python loader that returns prompt bodies without YAML frontmatter, and introduces typed dataclasses for phase-to-phase payloads and persisted pipeline state.

Issue #161 builds on that base with a headless Python orchestrator and persisted `PipelineState` savepoints. Issue #162 then wires a packaged CLI entry point onto that orchestrator and removes the TypeScript wrapper layer under `.opencode/tools/`. Issue #164 completes that cleanup by deleting the remaining `.opencode/` tree and root Node.js artefacts, while preserving reusable prompt assets under `prompts/agents/` and `prompts/skills/`.

This foundation reduces path sprawl, gives later Python orchestration work a stable prompt-loading entry point, replaces ad hoc phase payloads with explicit Python types that can round-trip through JSON savepoints, and exposes the resulting pipeline through a normal Python console script.

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

Issue #164 extends the prompt relocation surface with two reusable prompt bodies that previously lived under `.opencode/commands/`:

- `prompts/agents/continue.md`
- `prompts/agents/regenerate.md`

The same cleanup also relocates reusable skill reference material from `.opencode/skills/` to `prompts/skills/`.

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

## CLI Entry Points

Issue #162 adds the first packaged Python-native entry point in `pyproject.toml`:

```toml
[project.scripts]
story-writer = "src.presentation.cli.main:main"
```

`src/presentation/cli/argument_parser.py` now builds a parser with three subcommands:

| Subcommand | Handler | Current behavior |
|------------|---------|------------------|
| `tui --story <name>` | `_cmd_tui()` | Lazy-imports `StoryWriterApp` and runs the Textual TUI; if `textual` is missing, exits with a helpful stderr install hint |
| `run --story <name> [--batch]` | `_cmd_run()` | Calls `run_pipeline()` with `NullApprovalGate`, `TokenStreamBus`, and `WikiContextBus` |
| `resume --story <name> [--savepoint <name>]` | `_cmd_resume()` | Calls `resume_pipeline()` with the same Python-native primitives |

Two behavior details matter for follow-on work:

- `run` is currently headless regardless of `--batch`, because `_cmd_run()` always constructs `NullApprovalGate()`.
- `resume --savepoint <name>` passes the name through to the orchestrator for validation only. Resume always continues from the latest `pipeline_state.json` snapshot; the named savepoint is never restored.

## OpenCode Artefact Removal

Issue #162 removes all `.ts` files from `.opencode/tools/`. Issue #164 removes the remaining `.opencode/` tree plus the root Node.js/OpenCode manifests (`opencode.json`, `package.json`, `package-lock.json`, `tsconfig.json`, and `vitest.config.ts`).

The practical effect is simple:

- runtime orchestration no longer shells out through wrapper code
- `src/presentation/orchestrator.py` and related presentation agents call Python services and tool modules directly
- standalone `src/tools/*.py` CLIs remain available for shell use
- reusable prompt content from deleted OpenCode commands and skills now lives under `prompts/agents/` and `prompts/skills/`

## Developer Guide

### Key Files

- `prompts/agents/` — canonical agent prompt location
- `src/infrastructure/prompts/agent_prompt_loader.py` — frontmatter-stripping prompt loader with in-memory cache
- `src/application/pipeline/__init__.py` — pipeline package marker
- `src/application/pipeline/handoffs.py` — typed phase payload dataclasses and `PipelineState` persistence helpers
- `src/presentation/cli/argument_parser.py` — packaged `story-writer` argparse surface
- `src/presentation/cli/main.py` — CLI dispatch into the Python-native orchestrator
- `pyproject.toml` — `story-writer` console script definition
- `tests/unit/test_agent_prompt_loader.py` — loader behaviour and cache coverage
- `tests/unit/test_pipeline_handoffs.py` — dataclass round-trip and JSON serialisation coverage
- `tests/unit/test_prompt_relocation.py` — prompt-tree relocation baseline check updated for `prompts/agents/`
- `tests/unit/test_cli_main.py` — parser and dispatch coverage for the new console entry point

## Testing

Issue #158 added dedicated unit coverage for both new modules:

- `test_agent_prompt_loader.py` verifies frontmatter stripping, verbatim loads, missing-file handling, malformed frontmatter handling, cache hits, and cache clearing
- `test_pipeline_handoffs.py` verifies nested `PipelineState` round-trips, `ApprovalDecision` defaults, JSON serialisation, and package importability
- `test_prompt_relocation.py` now treats the prompt tree as a growing set and asserts a minimum Markdown file count so the additional agent prompts do not break the relocation baseline
- `test_cli_main.py` verifies subcommand parsing for `tui`, `run`, and `resume`, plus dispatch coverage for the packaged CLI entry point

## Related

- [Pipeline Primitives](./pipeline-primitives.md)
- [PRD: Python-Native Orchestration and TUI](../planning/python-native-migration/prd.md)
- [Story Orchestrator](./story-orchestrator.md)
- Issue #158 — Agent prompt loader and typed pipeline handoffs
- Issue #161 — Python pipeline orchestrator (headless)
- Issue #162 — CLI entry points and TypeScript wrapper deletion
- PR #167 — Python-native migration [1/9]
- PR #171 — Python-native migration [4/9]
- PR #172 — Python-native migration [5/9]