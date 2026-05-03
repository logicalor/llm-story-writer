# Tools Reference

> Python-native tool layer, direct CLI entry points, and in-process orchestration surfaces used by the current runtime.

## Overview

The repository no longer uses TypeScript wrappers in `.opencode/tools/`. Task 7 removed the wrapper files, and Issue #164 removed the remaining `.opencode/` tree entirely.

Deterministic operations now live in Python only. They are used in two ways:

| Path | Entry point | Role |
|------|-------------|------|
| In-process | `src/presentation/orchestrator.py` and presentation agents | Normal runtime path for the Python-native pipeline |
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

The first in-process pipeline agent is now `StoryFoundationAgent` in `src/presentation/agents/story_foundation.py`. It runs before outline generation and extracts `base_context`, `story_start_date`, and `story_elements` into the persisted `OutlineResult` carried inside `pipeline_state.json`.

Between outline generation and the outline approval gate, `OutlineCriticAgent` in `src/presentation/agents/outline_critic.py` now runs in-process when `generation.enable_outline_critique` is `true`. It reads `PipelineState.outline_result`, runs six `prompts/outline_review/` critics either sequentially or concurrently depending on `generation.enable_concurrent_critics`, then runs the three `prompts/outline_arc/` analytics. It writes `stories/<story>/outline/critic_summary.md`, stores `critic_summary`, `arc_distribution`, and `promise_payoff` on `PipelineState`, and hands those fields forward to `StoryPlannerAgent`.

`StoryMetadataAgent` in `src/presentation/agents/story_metadata.py` now runs at three advisory metadata checkpoints: immediately after outline approval (`metadata-outline`), after the first approved chapter (`metadata-chapter-1`), and after final edit (`metadata-final`). Each run invokes the existing `outline/create_title`, `outline/create_summary`, and `outline/create_tags` prompts, updates `OutlineResult.title` plus `OutlineResult.tags` in `pipeline_state.json` when generation succeeds, and rewrites `stories/<story>/metadata.json` with the current title, back-cover summary, and tag list.

Later in the chapter loop, `RecapWriterAgent` in `src/presentation/agents/recap_writer.py` runs in-process after each approved chapter. It generates recap artefacts directly through `PromptLoader` and the configured `ModelProvider`, then hands the resulting recap dict back to `src/presentation/orchestrator.py` for persistence.

The orchestrator also now produces intermediate story artefacts directly in the story directory during the implemented pipeline:

- `stories/<story>/savepoints/pipeline_state.json` from init onward, including story-foundation fields and later phase handoffs
- `stories/<story>/outline/skeleton.md` plus `stories/<story>/outline/details/chapter_{N}.md` during Phase 3 when `generation.expand_outline` is enabled and the runtime stays on the per-chapter expansion path
- `stories/<story>/outline/chunks/chunk_{start}_{end}.md`, `stories/<story>/outline/continuity/continuity_{start}_{end}.md`, and `stories/<story>/outline/enrichment.md` during Phase 3 when `generation.expand_outline`, `generation.use_chunked_outline_generation`, and `wanted_chapters > outline_chunk_size` select the chunked path
- `stories/<story>/metadata.json` after each successful metadata checkpoint, with the latest generated title, summary, tags, and `updated_at`
- `stories/<story>/characters/*.json` from the characters phase
- `stories/<story>/settings/*.json` from the settings phase
- `stories/<story>/chapters/chapter_{N}.md` during chapter approval
- `stories/<story>/chapters/chapter_{N}_recap.json` after each approved chapter when recap generation returns non-empty events
- `stories/<story>/output/story.md` during final assembly

## Tool Inventory

### Core State And Prompt Tools

| Tool module | Purpose |
|-------------|---------|
| `src/tools/prompt_loader.py` | Load prompt templates and substitute variables |
| `src/tools/story_state.py` | Initialize, read, write, and list story state |
| `src/tools/savepoint_manager.py` | Save, load, inspect, and clear savepoints |
| `src/tools/character_manager.py` | Create and update character sheets; write markdown bodies to sibling `.md` files and store `{"$ref": ...}` pointers in JSON |
| `src/tools/setting_manager.py` | Create and update setting sheets; write markdown bodies to sibling `.md` files and store `{"$ref": ...}` pointers in JSON |
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
| `src/tools/wiki_extract.py` | Run initial wiki population and post-chapter extraction, generate detail levels, and apply batch-ready wiki updates |
| `src/tools/wiki_update.py` | Apply wiki page updates |
| `src/tools/wiki_lint.py` | Validate wiki pages against formatting and consistency rules |
| `src/tools/rag_query.py` | Query ChromaDB collections for story context |
| `src/tools/migrate_inline_markdown.py` | One-shot migration tool that rewrites legacy inline-markdown story JSON into pointer-backed markdown files; supports `--name`, `--all`, and `--dry-run` |

### Shared Internal Helpers

These modules support the public tool CLIs but are not normal top-level user commands.

| Module | Purpose |
|--------|---------|
| `src/tools/_io.py` | Shared filesystem paths and story-name validation |
| `src/tools/_llm.py` | Common LLM-provider bootstrap helpers |
| `src/tools/_persist.py` | Markdown pointer helpers: `persist_markdown` writes markdown to disk and returns a `{"$ref": ...}` pointer; `read_markdown_ref` resolves pointer dicts only and raises `ValueError` for legacy inline strings |
| `src/tools/_wiki.py` | Shared wiki utility logic |
| `src/tools/migrate_state_slim.py` | One-off migration helper retained in Python |

## Story Artefacts

Several runtime artefacts are written by the Python-native orchestrator and then consumed by later phases or manual inspection workflows. These are not separate CLI tools, but they are part of the active tool surface because downstream code or operator workflows rely on their on-disk format.

| Path | Producer | Consumer | Notes |
|------|----------|----------|-------|
| `stories/<story>/savepoints/pipeline_state.json` | `src/presentation/orchestrator.py` across all implemented phases | `resume_pipeline()`, later phases, debugging workflows | JSON snapshot of `PipelineState`, including `OutlineResult` foundation fields, `critic_summary`, `arc_distribution`, `promise_payoff`, `recaps`, `evolved_sheets`, completed phases, and savepoint labels |
| `stories/<story>/outline/skeleton.md` | `src/presentation/agents/outline_planner.py` when `generation.expand_outline` is `true` and the outline fits the per-chapter path | Outline review, resume-safe per-chapter expansion, debugging workflows | Skeleton outline generated from `outline/create_skeleton`; paired with `OutlineResult.chapter_skeletons` |
| `stories/<story>/outline/details/chapter_{N}.md` | `src/presentation/agents/outline_planner.py` when `generation.expand_outline` is `true` and the outline fits the per-chapter path | Chapter drafting, consistency checks, resume-safe outline expansion | One expanded chapter detail block per chapter. Existing files are read back instead of regenerated on resumed runs |
| `stories/<story>/outline/chunks/chunk_{start}_{end}.md` | `src/presentation/agents/outline_planner.py` when chunked outline generation is active | Outline review, debugging workflows, manual continuity inspection | One persisted outline window per chunk from `outline/create_chunk` |
| `stories/<story>/outline/continuity/continuity_{start}_{end}.md` | `src/presentation/agents/outline_planner.py` between adjacent chunk windows | TUI token stream review, debugging workflows | Continuity analysis between the just-finished window and the next one from `outline/analyze_continuity` |
| `stories/<story>/outline/enrichment.md` | `src/presentation/agents/outline_planner.py` after the final chunked window | Manual inspection, downstream enrichment review | Final enrichment suggestions from `outline/analyze_enrichment`; mirrored into `OutlineResult.enrichment_suggestions` |
| `stories/<story>/outline/critic_summary.md` | `src/presentation/agents/outline_critic.py` when `generation.enable_outline_critique` is `true` | Manual inspection, debugging workflows | Concatenated summaries from the six outline-review critics. The separately synthesised arc summary is stored on `PipelineState.critic_summary` |
| `stories/<story>/metadata.json` | `src/presentation/orchestrator.py` after `metadata-outline`, `metadata-chapter-1`, and `metadata-final` | Manual inspection, release metadata export, debugging workflows | JSON document with `title`, `summary`, `tags`, and `updated_at`. The orchestrator also mirrors `title` and `tags` into `PipelineState.outline_result`, but the summary lives on disk only |
| `stories/<story>/characters/<slug>.json` | `src/presentation/orchestrator.py` characters phase | `src/presentation/agents/chapter_writer.py`, `src/presentation/agents/character_evolver.py`, character-management workflows | JSON document with `name`, pointer refs for `sheet`, `chunks`, `abridged`, and `summary`, plus `updated_at`. Bodies live under `stories/<story>/characters/<slug>/` as sibling `.md` files such as `sheet.md`, `summary.md`, `abridged.md`, and `chunks/<key>.md` |
| `stories/<story>/settings/<slug>.json` | `src/presentation/orchestrator.py` settings phase | `src/presentation/agents/chapter_writer.py`, `src/presentation/agents/setting_evolver.py`, setting-management workflows | Same pointer-based shape as character sheets, with markdown bodies under `stories/<story>/settings/<slug>/` |
| `stories/<story>/chapters/chapter_{N}.md` | `src/presentation/orchestrator.py` chapter loop | `src/tools/story_assembler.py`, downstream review flows | Approved chapter manuscript |
| `stories/<story>/chapters/chapter_{N}_recap.json` | `src/presentation/orchestrator.py` after `src/presentation/agents/recap_writer.py` returns a recap result | later chapter-loop continuity context, manual inspection, debugging workflows | JSON document with `events`, `compact`, and `sanitised` fields; the same object is also stored in `PipelineState.recaps[str(N)]` |
| `stories/<story>/output/story.md` | `src/presentation/orchestrator.py` assembly phase | Manual export and downstream editing | Concatenated final manuscript |

Characters and settings files are generated from prompt templates in `prompts/characters/` and `prompts/settings/`. The JSON files now keep only structured metadata plus `{"$ref": ...}` pointers for `sheet`, `chunks`, `summary`, and `abridged`; the markdown bodies live in sibling `.md` files under each entity slug directory. Filenames are slugified from the extracted entity names, and writes are atomic so later phases never read a half-written JSON file.

`ChapterWriterAgent` reads both directories opportunistically. It prefers each sheet's stored `abridged` text, then falls back to `summary`, then falls back to the first 300 characters of the `sheet` body. Missing directories, malformed JSON files, or individual read failures are skipped instead of aborting chapter generation.

After each approved chapter, `CharacterEvolverAgent` and `SettingEvolverAgent` may rewrite the `sheet` field in those same JSON files based on chapter events. The orchestrator records the per-chapter `updated` or `unchanged` status map in `PipelineState.evolved_sheets[str(chapter_number)]`.

`src/tools/wiki_extract.py` now exposes four programmatic entry points used by the runtime. `_list_wiki_entities(story_name, *, model=None)` performs entity extraction plus deduplication only. `_bootstrap_single_wiki_entity(story_name, entity, *, model=None, wiki_dir=None)` generates detail levels and writes one missing wiki page. `bootstrap_wiki_from_story(story_name, *, model=None)` still supports the full one-shot bootstrap for CLI or ad-hoc use by seeding the wiki from the approved outline savepoint plus character and setting JSON sheets, deduplicating extracted entities, skipping already-existing slugs for idempotent upsert behavior, applying the batch through `run_batch()`, and returning `{created, skipped, entity_counts}`. `update_wiki_from_chapter(story_name, chapter_number, chapter_text, *, model=None)` handles the later incremental chapter updates.

`WikiMaintainerAgent` now uses `src/tools/wiki_extract.py` directly for post-chapter updates. The programmatic `update_wiki_from_chapter(story_name, chapter_number, chapter_text, *, model=None)` entry point runs the `wiki/extract_from_chapter` prompt, matches existing entities from the wiki index, generates detail levels for newly created pages, applies the batch through `run_batch()`, and returns both summary counts and the concrete created or updated slug lists. That keeps wiki persistence inside one Python boundary and gives the orchestrator a typed result instead of free-form model text.

## CLI Entry Points

### Pipeline CLI

`pyproject.toml` now publishes a console script:

```bash
story-writer --help
```

Available subcommands:

| Command | Current behavior |
|---------|------------------|
| `story-writer tui --story <name> [--prompt <path>]` | Lazy-imports `StoryWriterApp` and launches the interactive Textual TUI; `--prompt` auto-initialises the story and loads the prompt file. If `textual` is missing, exits with an install hint |
| `story-writer run --story <name> [--prompt <path>] [--batch]` | Runs the headless orchestrator via `run_pipeline()`; `--prompt` auto-initialises the story and loads the prompt file |
| `story-writer resume --story <name> [--prompt <path>] [--savepoint <name>]` | Resumes via `resume_pipeline()` from the latest persisted state. `--prompt` overwrites the existing story prompt. `--savepoint` validates the name exists but does not restore an older snapshot. |

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

1. Put the implementation in `src/tools/`. The `src/application/services/` layer is retired (ADR 008) — do not add new services there.
2. Keep the shell interface in Python with argparse if ad-hoc execution is useful.
3. Wire the runtime path by importing the Python module or service directly from the orchestrator or presentation agent.
4. Update this document and any affected feature docs. Do not reintroduce a wrapper layer outside Python.

## Related

- [Python-Native Foundation](./features/python-native-foundation.md)
- [Story Orchestrator](./features/story-orchestrator.md)
- [PRD: Python-Native Orchestration and TUI](./planning/python-native-migration/prd.md)
