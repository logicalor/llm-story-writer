# Tools Reference

> Python-native tool layer, direct CLI entry points, and in-process orchestration surfaces used by the current runtime.

## Overview

The repository no longer uses TypeScript wrappers in `.opencode/tools/`. Task 7 removed the wrapper files, and Issue #164 removed the remaining `.opencode/` tree entirely.

Deterministic operations now live in Python only. They are used in two ways:

| Path | Entry point | Role |
|------|-------------|------|
| In-process | `src/presentation/orchestrator.py`, presentation agents, and application services | Normal runtime path for the Python-native pipeline |
| Ad-hoc CLI | `python -m src.tools.<tool_module> ...` or direct script execution | Manual inspection, repair, and one-off operations |

The `story-writer` console script is separate from the tool CLIs. It dispatches pipeline-level commands from `src/presentation/cli/main.py`; the individual tool modules remain available for focused shell usage.

## Execution Model

The current tool flow stays inside Python.

```text
story-writer / orchestrator / agent
    -> src/tools/<tool>.py or application service
    -> src/infrastructure/* and src/domain/*
    -> stories/<name>/, prompts/, ChromaDB
```

This removes the old subprocess boundary between a TypeScript wrapper and a Python script. Runtime validation, error handling, and savepoint writes now happen inside one language boundary.

The orchestrator also now produces intermediate story artefacts directly in the story directory during the implemented pipeline:

- `stories/<story>/characters/*.json` from the characters phase
- `stories/<story>/settings/*.json` from the settings phase
- `stories/<story>/chapters/chapter_{N}.md` during chapter approval
- `stories/<story>/output/story.md` during final assembly

## Tool Inventory

### Core State And Prompt Tools

| Tool module | Purpose |
|-------------|---------|
| `src/tools/prompt_loader.py` | Load prompt templates and substitute variables |
| `src/tools/story_state.py` | Initialize, read, write, and list story state |
| `src/tools/savepoint_manager.py` | Save, load, inspect, and clear savepoints |
| `src/tools/character_manager.py` | Create and update character sheets |
| `src/tools/setting_manager.py` | Create and update setting sheets |
| `src/tools/recap_manager.py` | Persist chapter recap data |

### Generation And Review Tools

| Tool module | Purpose |
|-------------|---------|
| `src/tools/outline_generator.py` | Generate or refine outlines |
| `src/tools/scene_writer.py` | Generate scenes plus prose-analysis operations such as `scrub-analyze` and `voice-analyze` |
| `src/tools/critique_runner.py` | Run outline or chapter critique flows, including arc-analysis prompt chains |
| `src/tools/story_assembler.py` | Produce chapter handoff and assembly artefacts |

### Wiki And Retrieval Tools

| Tool module | Purpose |
|-------------|---------|
| `src/tools/wiki_init.py` | Initialize wiki structure and seed pages |
| `src/tools/wiki_read.py` | Read wiki pages at requested detail levels |
| `src/tools/wiki_search.py` | Search wiki content |
| `src/tools/wiki_snapshot.py` | Assemble token-budgeted wiki context |
| `src/tools/wiki_extract.py` | Extract candidate wiki facts from text |
| `src/tools/wiki_update.py` | Apply wiki page updates |
| `src/tools/wiki_lint.py` | Validate wiki pages against formatting and consistency rules |
| `src/tools/rag_query.py` | Query ChromaDB collections for story context |

### Shared Internal Helpers

These modules support the public tool CLIs but are not normal top-level user commands.

| Module | Purpose |
|--------|---------|
| `src/tools/_io.py` | Shared filesystem paths and story-name validation |
| `src/tools/_llm.py` | Common LLM-provider bootstrap helpers |
| `src/tools/_wiki.py` | Shared wiki utility logic |
| `src/tools/migrate_state_slim.py` | One-off migration helper retained in Python |

## Story Artefacts

Several runtime artefacts are written by the Python-native orchestrator and then consumed by later phases. These are not separate CLI tools, but they are part of the active tool surface because downstream code relies on their on-disk format.

| Path | Producer | Consumer | Notes |
|------|----------|----------|-------|
| `stories/<story>/characters/<slug>.json` | `src/presentation/orchestrator.py` characters phase | `src/presentation/agents/chapter_writer.py`, character-management workflows | JSON document with `name`, full markdown `sheet`, `chunks`, `summary`, and `updated_at` |
| `stories/<story>/settings/<slug>.json` | `src/presentation/orchestrator.py` settings phase | `src/presentation/agents/chapter_writer.py`, setting-management workflows | Same JSON shape as character sheets |
| `stories/<story>/chapters/chapter_{N}.md` | `src/presentation/orchestrator.py` chapter loop | `src/tools/story_assembler.py`, downstream review flows | Approved chapter manuscript |
| `stories/<story>/output/story.md` | `src/presentation/orchestrator.py` assembly phase | Manual export and downstream editing | Concatenated final manuscript |

Characters and settings files are generated from prompt templates in `prompts/characters/` and `prompts/settings/`. Filenames are slugified from the extracted entity names, and writes are atomic so later phases never read a half-written JSON file.

`ChapterWriterAgent` reads both directories opportunistically. It prefers each sheet's stored `summary`; if that field is empty, it falls back to the first 300 characters of the `sheet` body. Missing directories, malformed JSON files, or individual read failures are skipped instead of aborting chapter generation.

## CLI Entry Points

### Pipeline CLI

`pyproject.toml` now publishes a console script:

```bash
story-writer --help
```

Available subcommands:

| Command | Current behavior |
|---------|------------------|
| `story-writer tui --story <name>` | Lazy-imports `StoryWriterApp` and launches the interactive Textual TUI; if `textual` is missing, exits with an install hint |
| `story-writer run --story <name> [--batch]` | Runs the headless orchestrator via `run_pipeline()` |
| `story-writer resume --story <name> [--savepoint <name>]` | Resumes via `resume_pipeline()` from the persisted pipeline state |

Implementation note: `run` currently always uses `NullApprovalGate`, so it is headless even without `--batch`. The flag remains in the parser for CLI compatibility while the broader TUI work lands.

### Tool CLIs

Individual tools still expose argparse-based interfaces for shell use. Example:

```bash
python -m src.tools.story_state --operation list
python -m src.tools.wiki_search --story test_story --query "chapter summary"
```

The exact arguments differ per tool module. Read the module's `cmd_*` function or argparse setup before documenting or scripting against its JSON output.

## Adding Or Updating A Tool

When you add a new deterministic operation:

1. Put the implementation in `src/tools/` or, if it is orchestration-only, in `src/application/services/`.
2. Keep the shell interface in Python with argparse if ad-hoc execution is useful.
3. Wire the runtime path by importing the Python module or service directly from the orchestrator or presentation agent.
4. Update this document and any affected feature docs. Do not reintroduce a wrapper layer outside Python.

## Related

- [Python-Native Foundation](./features/python-native-foundation.md)
- [Story Orchestrator](./features/story-orchestrator.md)
- [PRD: Python-Native Orchestration and TUI](./planning/python-native-migration/prd.md)
