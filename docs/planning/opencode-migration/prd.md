# PRD: OpenCode Agentic Architecture Migration

> Migrate the AI Story Writer from a monolithic Python/LangChain pipeline to a hybrid agent-orchestrated architecture running inside OpenCode, preserving existing domain logic as callable tools while enabling interactive co-creation and context-aware generation within a 65536-token window.

**Date:** 2026-04-12
**Author:** Planner agent
**Status:** Draft

## Problem Statement

The current AI Story Writer (~18k LoC Python, 72 files, 131 prompt templates) is a monolithic pipeline application built with clean architecture patterns. While functional, it suffers from several architectural limitations:

1. **No interactive feedback loop.** The pipeline runs end-to-end without human-in-the-loop guidance. A user cannot steer the story mid-generation, reject a chapter direction, or adjust tone without restarting.

2. **Rigid orchestration.** The generation pipeline is hard-coded: outline → character sheets → setting sheets → chapter generation (with recap → synopsis → scene decomposition → scene writing per chapter). Adding a new step or reordering requires code changes across multiple service classes.

3. **Context management is implicit.** The application loads and passes context through method parameters, with no central mechanism for deciding what fits within the model's context window. The current `context_length: 16384` configuration is a blunt limit; the application doesn't actively manage token budgets.

4. **Provider coupling.** Despite the `ModelProvider` interface, the strategy layer is tightly coupled to Ollama-specific behaviors (streaming, seed handling, thinking tags). Moving to a different orchestration layer requires re-implementing these concerns.

The user wants to adopt the OpenCode agentic infrastructure to gain interactive orchestration, natural-language reconfiguration, and agent-driven coordination — while keeping the proven domain logic (prompt templates, state management, character/setting/recap managers) intact. **Local LLM usage is the primary deployment target; cost is not a factor but context window size (65536 tokens) is the binding constraint.**

## Goals

1. **Archive the current codebase** as a referenceable baseline — no code is deleted, all history and logic can be consulted during and after migration
2. **Preserve all 131 prompt templates** verbatim — they are proven creative assets
3. **Wrap existing Python domain logic** as OpenCode custom tools — character management, setting management, recap/synopsis generation, scene generation, story state management
4. **Build an OpenCode agent hierarchy** that replaces the hard-coded pipeline with flexible, inspectable orchestration
5. **Implement context-window-aware state management** that operates within a 65536-token budget, using file-based state + selective loading rather than holding everything in conversation
6. **Enable interactive co-creation mode** where a human can guide story direction at key decision points (outline approval, chapter-by-chapter steering, character development choices)
7. **Support batch/automated mode** where the full pipeline runs end-to-end without human intervention, matching current behaviour
8. **Replace PostgreSQL/pgvector RAG with a lightweight local alternative** (ChromaDB or file-based retrieval) since the deployment target is fully local
9. **Build a progressive wiki-based memory system** following the Karpathy LLM Wiki pattern — a structured, LLM-maintained knowledge base of characters, locations, events, factions, plot threads, timelines, and world rules that grows incrementally as the story is written, providing pre-synthesized context for each scene and enabling consistency enforcement across the full novel

## Non-Goals

- **Cloud deployment** — this is a local-first, single-user application using local LLMs
- **Multi-user collaboration** — single writer, single model host
- **Rewriting prompt templates** — templates are preserved as-is; only the loading/rendering mechanism changes
- **New creative features beyond the wiki** — story features beyond the wiki memory system come later
- **Supporting the stream-of-consciousness strategy** — focus on the outline-chapter strategy which is the primary and actively-used pipeline
- **Preserving the dependency-injector container** — OpenCode's tool/agent system replaces DI
- **LangChain retention** — LangChain provider is deprecated in favour of OpenCode's native LLM integration

## User Stories

### Story Writer (Primary User)

- As a story writer, I want to start a new story with a prompt file and have the agent guide me through outline generation, so that I can review and approve the outline before chapter writing begins
- As a story writer, I want to continue a previously-started story from where I left off, using savepoints, so that I don't lose work
- As a story writer, I want to override generation settings mid-run (e.g., change quality threshold, skip critique), so that I can adapt the process to what I'm seeing
- As a story writer, I want to run the full pipeline without interaction, so that I can generate a complete novel overnight
- As a story writer, I want to see what the agent is doing at each step (which tool it's calling, what state it's reading/writing), so that I can trust and debug the process
- As a story writer, I want to regenerate a single chapter or scene without restarting the whole story, so that I can iterate on specific sections

### Developer (Maintainer)

- As a developer, I want to add a new pipeline step by creating a prompt template and a tool wrapper, without modifying orchestration code, so that the system is extensible
- As a developer, I want to reference the original codebase when debugging the new tools, so that I can verify behaviour matches
- As a developer, I want each tool to be independently testable with mock inputs, so that I can validate changes in isolation

## Proposed Solution

### Architecture Overview

A **hybrid architecture** where OpenCode agents handle orchestration, coordination, and human interaction, while Python scripts (wrapped as OpenCode custom tools) handle deterministic domain logic.

```
┌──────────────────────────────────────────────────────────────┐
│                    OpenCode Interface                         │
│  Commands: /new-story /continue /regenerate /savepoint       │
│  Modes: interactive (TUI) │ batch (SDK/headless)             │
└──────────────┬───────────────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────────────┐
│          Story Orchestrator (Primary Agent)                    │
│  Model: local LLM (e.g. magistral-abliterated:24b)           │
│  Role: coordinate pipeline phases, manage human dialogue      │
│  Context budget: 65536 tokens                                 │
└──┬────────┬────────┬────────┬────────┬────────┬─────────────┘
   │        │        │        │        │        │
   ▼        ▼        ▼        ▼        ▼        ▼
┌───────┐┌───────┐┌───────┐┌───────┐┌─────────┐┌──────────┐
│Outline││Char   ││Scene  ││State  ││Critique ││Wiki      │
│Planner││Mgr    ││Writer ││Mgr    ││Agent    ││Maintainer│
│Agent  ││Agent  ││Agent  ││Agent  ││         ││Agent     │
└──┬────┘└──┬────┘└──┬────┘└──┬────┘└──┬──────┘└──┬───────┘
   │        │        │        │        │          │
   ▼        ▼        ▼        ▼        ▼          ▼
┌──────────────────────────────────────────────────────────────┐
│                 Custom Tools (.opencode/tools/)               │
│                                                               │
│  ┌───────────────┐ ┌───────────────┐ ┌─────────────────────┐ │
│  │prompt-loader   │ │story-state    │ │outline-generator    │ │
│  │Load+render     │ │Read/write JSON│ │Invoke Python outline│ │
│  │templates from  │ │savepoint files│ │generation logic     │ │
│  │prompts/ dir    │ │               │ │                     │ │
│  └───────────────┘ └───────────────┘ └─────────────────────┘ │
│  ┌───────────────┐ ┌───────────────┐ ┌─────────────────────┐ │
│  │character-mgr   │ │scene-writer   │ │recap-manager        │ │
│  │Generate/update │ │Generate scenes│ │Generate/sanitize    │ │
│  │character sheets│ │from outlines  │ │chapter recaps       │ │
│  └───────────────┘ └───────────────┘ └─────────────────────┘ │
│  ┌───────────────┐ ┌───────────────┐ ┌─────────────────────┐ │
│  │setting-mgr     │ │content-chunker│ │savepoint-mgr        │ │
│  │Generate/update │ │Split content  │ │Save/load/list       │ │
│  │setting sheets  │ │for RAG/context│ │checkpoint state     │ │
│  └───────────────┘ └───────────────┘ └─────────────────────┘ │
│  ┌───────────────┐ ┌───────────────┐ ┌─────────────────────┐ │
│  │critique-runner │ │rag-query      │ │wiki-snapshot         │ │
│  │Run critic      │ │Query ChromaDB │ │Assemble pre-gen      │ │
│  │pipeline        │ │for context    │ │context from wiki     │ │
│  └───────────────┘ └───────────────┘ └─────────────────────┘ │
│  ┌───────────────┐ ┌───────────────┐ ┌─────────────────────┐ │
│  │wiki-init       │ │wiki-update    │ │wiki-lint             │ │
│  │Initialize wiki │ │Update pages   │ │Consistency checks    │ │
│  │structure       │ │post-generation│ │& contradiction detect│ │
│  └───────────────┘ └───────────────┘ └─────────────────────┘ │
│  ┌───────────────┐ ┌───────────────┐                         │
│  │wiki-read       │ │wiki-search    │                         │
│  │Read wiki page  │ │Search wiki    │                         │
│  │by slug/type    │ │via ChromaDB   │                         │
│  └───────────────┘ └───────────────┘                         │
└──────────────────────┬───────────────────────────────────────┘
                       │ subprocess / import
                       ▼
┌──────────────────────────────────────────────────────────────┐
│        Python Domain Logic (src/, preserved and refactored)   │
│  Prompt templates:  131 .md files (unchanged)                 │
│  Domain entities:   Story, Chapter, Scene, Outline            │
│  State management:  StoryStateManager, CharacterState, etc.   │
│  Content chunking:  retired with inactive services            │
│  Critique parser:   src/tools/critique_parser.py              │
│  Savepoint system:  SavepointManager, FilesystemRepository    │
│  Recap sanitizer:   RecapManager (multi-stage)                │
└──────────────────────────────────────────────────────────────┘

Skills (.opencode/skills/):
  story-pipeline/     — Pipeline phase ordering, quality gates
  scene-writing/      — Scene generation conventions, pacing
  character-voice/    — Character consistency rules
  outline-structure/  — Outline format, chapter structure
  context-budgeting/  — Token budget management for 65536 window
  wiki-conventions/   — Wiki page types, frontmatter schemas, naming rules
  wiki-maintenance/   — Update workflows, lint procedures, confidence scoring

Config:
  opencode.json       — Agent definitions, tool permissions, MCP servers
  config.md           — Story generation settings (preserved, read by tools)
```

### Context Window Strategy (65536 tokens)

The 65536-token window is managed through a **selective loading** pattern:

1. **Agent system prompts**: ~2000 tokens (fixed overhead)
2. **Tool descriptions**: ~3000 tokens (fixed overhead)
3. **Available creative budget**: ~60000 tokens per agent turn

For each pipeline step, only the required context is loaded:
- **Outline generation**: prompt + story analysis chunks (~15k tokens)
- **Chapter generation**: chapter outline + character sheets + recaps + previous synopsis (~20-30k tokens)
- **Scene generation**: wiki snapshot (characters, locations, plot threads, world rules, timeline) + scene definition + previous scene recap (~15-20k tokens)

The Python tools handle context assembly — they read the full state from files and the wiki, select relevant context, and return a curated context window to the agent. The agent never needs to hold the entire story state in context.

### Wiki Context Retrieval and Synthesis Pipeline

Scene generation context is assembled by the `wiki-snapshot` tool via a three-stage pipeline (see [ADR 005](../adr/005-hybrid-wiki-context-retrieval-pipeline.md) and [retrieval/synthesis research](../../.github/research/wiki-context-search-synthesis-2026-04-12.md)):

**Stage 1 — Hybrid Multi-Tier Retrieval:** Four retrieval tiers run in sequence and merge results via Reciprocal Rank Fusion (RRF):
  - T1: Deterministic entity matching — parse scene outline for entity names against the wiki index + alias list. These are always included.
  - T2: Metadata-filtered structured query — ChromaDB where-filter on YAML frontmatter (e.g., `type=plot_thread AND status=active`).
  - T3: Semantic vector search — embed scene outline, query ChromaDB for nearest neighbors.
  - T4: Wikilink graph traversal — follow [[wikilinks]] 1-2 hops from T1/T2/T3 results (max 5 additional entities).

**Stage 2 — Detail Level Selection & Token Budgeting:** Each retrieved page is assigned a detail level (L1 headline ~30 tokens, L2 brief ~150 tokens, L3 full ~500 tokens) based on relevance score, running token count, and scene type. Protected tier (POV character, primary location) is always L3. When budget is exceeded, lower-priority pages demote L3→L2→L1. Total budget: ~15K tokens.

**Stage 3 — Structured Context Assembly:** Default is deterministic template assembly (fixed markdown structure with sections for characters, location, plot threads, world rules, timeline, relationships). An optional lightweight LLM synthesis pass (7b model) condenses and connects content for complex scenes (>5 characters or >3 active plot threads) — the synthesis LLM may only restructure, never invent facts.

A **delta caching** layer avoids redundant retrieval between consecutive scenes: entity sets are diffed, unchanged pages reuse cached content, only new/updated entities are re-retrieved. Chapter boundaries invalidate the scene-level cache.

### Wiki Memory System

A progressive, LLM-maintained wiki (structured markdown pages with YAML frontmatter) grows alongside the story, following the [Karpathy LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). Three layers:

1. **Raw sources** (immutable): manuscript chapters, the original prompt, the outline
2. **Wiki** (LLM-maintained): structured pages for characters, locations, events, factions, items, plot threads, timelines, world rules, chapter synopses, themes, relationships
3. **Schema** (`_schema.md`): defines page types, frontmatter conventions, cross-reference rules, update lifecycle

The wiki replaces implicit state tracking with explicit, pre-synthesized knowledge. Before each scene, a `wiki-snapshot` tool assembles a "world state snapshot" containing the current status of relevant characters, locations, active plot threads, applicable world rules, and recent timeline events. This snapshot is injected into the generation prompt as authoritative constraints.

A dedicated **wiki-maintainer agent** (separate from the creative generator, can use a smaller/faster model) runs after each scene to extract entities, events, and state changes from the generated text and update wiki pages. The wiki-maintainer also pre-computes **hierarchical detail levels** (L1 headline, L2 brief, L3 full) for each page when it is created or updated — these are stored in the page frontmatter and used by the retrieval pipeline for adaptive token budgeting. Chapter-level lint runs after each chapter to detect contradictions using the ConStory-Bench error taxonomy. Every wiki fact carries a `confidence` field (verified/planned/speculative) and provenance tracking (source chapter/scene).

Each wiki page includes an `aliases` field in its frontmatter for fuzzy entity matching (e.g., `aliases: ["the old king", "King Aldric", "Father"]`), enabling the deterministic entity matcher to catch common references beyond exact name matches.

See [ADR 004](../adr/004-progressive-wiki-memory-system.md), [ADR 005](../adr/005-hybrid-wiki-context-retrieval-pipeline.md), and [research reports](../../.github/research/story-wiki-memory-system-2026-04-12.md) for full architectural analysis.

### Backend

**Agents** (defined in `opencode.json` or `.opencode/agents/`):
- `story-orchestrator` — Primary agent. Reads the pipeline skill, coordinates generation phases, handles human interaction
- `outline-planner` — Subagent. Generates and refines outlines using the outline tools
- `character-manager` — Subagent. Creates and updates character sheets
- `scene-writer` — Subagent. Generates individual scenes with full context loading via wiki snapshots
- `state-manager` — Subagent. Handles savepoint operations, state queries
- `critique-agent` — Subagent. Runs the multi-critic evaluation pipeline
- `wiki-maintainer` — Subagent. Extracts entities/events/state changes from generated content, updates wiki pages, runs consistency lint. Uses a smaller/faster model (e.g. deepseek-r1-abliterated:7b)

**Custom Tools** (TypeScript wrappers in `.opencode/tools/` calling Python scripts):
- `prompt-loader` — Load and render a prompt template by ID with variable substitution
- `story-state` — CRUD operations on the story state JSON (read/write/query)
- `savepoint-mgr` — Save/load/list/restore savepoints
- `character-mgr` — Generate/update/query character sheets
- `setting-mgr` — Generate/update/query setting sheets
- `outline-generator` — Run outline generation steps (extract context, story elements, generate/refine outline)
- `scene-writer` — Generate a scene given context inputs
- `recap-manager` — Generate/sanitize chapter recaps
- `content-chunker` — Split content into chunks for context loading
- `critique-runner` — Run the multi-critic pipeline and return scores
- `rag-query` — Query the local ChromaDB for relevant story context
- `wiki-init` — Initialize wiki structure for a new story (directories, schema, index, log)
- `wiki-snapshot` — Assemble pre-generation context from wiki (characters, locations, plot threads, world rules, timeline for a given scene)
- `wiki-update` — Extract entities/events/state changes from generated text; create/update wiki pages
- `wiki-lint` — Run consistency checks (contradictions, orphan pages, stale claims, timeline conflicts)
- `wiki-read` — Read wiki page(s) by slug or type filter
- `wiki-search` — Semantic search across wiki content via ChromaDB

**Skills** (`.opencode/skills/`):
- `story-pipeline` — Pipeline step ordering, quality gates, when to invoke critique
- `scene-writing` — Scene generation conventions, structural rules
- `character-voice` — Character consistency and voice maintenance rules
- `outline-structure` — Outline format spec, chapter/scene breakdown rules
- `context-budgeting` — Rules for what to load into context at each step, token limits

### Frontend

No traditional frontend. The **OpenCode TUI** is the interface. Custom **commands** provide the entry points:
- `/new-story <prompt-file>` — Start a new story
- `/continue [story-name]` — Continue from last savepoint
- `/regenerate chapter <N>` — Regenerate a specific chapter
- `/regenerate scene <chapter> <scene>` — Regenerate a specific scene
- `/savepoint [name]` — Create a named savepoint
- `/status` — Show current generation progress and state
- `/settings` — Show/modify generation settings

### Database

- **Remove PostgreSQL/pgvector dependency.** Replace with ChromaDB (already used in the agent system's knowledge base) or pure file-based retrieval
- **Story state**: JSON files on disk (preserved from current savepoint system)
- **RAG index**: ChromaDB collection per story, populated as content is generated

### File System Layout (Post-Migration)

```
llm-story-writer/
├── .opencode/
│   ├── agents/          # Agent definitions (Markdown with YAML frontmatter)
│   ├── tools/           # Custom tools (TypeScript, call Python)
│   ├── skills/          # Skills (Markdown instructions)
│   ├── commands/        # Custom commands
│   └── plugins/         # Compaction hooks
├── opencode.json        # Main OpenCode configuration
├── config.md            # Story generation config (preserved)
├── src/                 # Refactored Python domain logic (tools call into this)
│   ├── domain/          # Entities, value objects (preserved)
│   ├── tools/           # Python tool implementations (new)
│   │   ├── prompt_loader.py
│   │   ├── story_state.py
│   │   ├── character_manager.py
│   │   ├── setting_manager.py
│   │   ├── scene_writer.py
│   │   ├── outline_generator.py
│   │   ├── recap_manager.py
│   │   ├── critique_runner.py
│   │   └── savepoint_manager.py
│   └── prompts/         # All 131 prompt templates (preserved in place)
├── stories/             # Story output and state (runtime)
│   ├── <story-name>/
│   │   ├── state.json
│   │   ├── outline.md
│   │   ├── chapters/
│   │   ├── characters/
│   │   ├── settings/
│   │   ├── savepoints/
│   │   └── wiki/            # Progressive wiki memory (LLM-maintained)
│   │       ├── _schema.md       # Page type definitions, conventions
│   │       ├── index.md         # Content catalog (1-line per page)
│   │       ├── log.md           # Chronological operations log
│   │       ├── contradictions.md # Logged contradictions & resolutions
│   │       ├── characters/      # Character pages (YAML frontmatter + markdown)
│   │       ├── locations/       # Location/setting pages
│   │       ├── events/          # Plot-significant events
│   │       ├── factions/        # Organizations & groups
│   │       ├── items/           # Significant objects
│   │       ├── plot-threads/    # Active/resolved storylines
│   │       ├── world-rules/     # Magic systems, physics, social norms
│   │       ├── themes/          # Recurring motifs
│   │       ├── relationships/   # Character relationship evolution
│   │       ├── timeline/        # Chronological event indices
│   │       └── chapters/        # Per-chapter synopsis digests
│   └── ...
└── .chromadb/           # Local RAG index (includes wiki content)
```

## Acceptance Criteria

- [x] Temporary migration archive was removed after cleanup issue #107
- [ ] All 131 prompt templates are preserved and loadable via the `prompt-loader` tool
- [ ] A new story can be generated end-to-end via `/new-story` command in OpenCode TUI
- [ ] A story can be generated in batch mode via `opencode serve` + SDK without human interaction
- [ ] A user can interactively approve/reject the outline before chapter generation begins
- [ ] Savepoints work: a story can be stopped and resumed from the last checkpoint
- [ ] Each pipeline step operates within a 65536-token context budget (verified by logging)
- [ ] Character sheets, setting sheets, and recaps are generated and persisted as files
- [ ] The critique pipeline runs and returns quality scores
- [ ] Story output (Markdown + JSON) matches the format of the current pipeline
- [ ] PostgreSQL/pgvector is no longer required — all storage is file-based + ChromaDB
- [ ] Each custom tool is independently invocable and testable
- [ ] Generation settings from `config.md` are respected by all tools
- [ ] Wiki is initialized when a new story starts (`wiki-init`)
- [ ] Wiki pages are created/updated after each scene by the wiki-maintainer agent
- [ ] Pre-generation wiki snapshots are assembled and injected into scene prompts
- [ ] Chapter-level lint detects contradictions using ConStory-Bench error taxonomy
- [ ] Every wiki fact carries a `confidence` field and provenance (source chapter/scene)
- [ ] Wiki pages use YAML frontmatter with structured fields and markdown body with [[wikilinks]]
- [ ] Wiki-snapshot uses multi-tier hybrid retrieval (entity matching + metadata filter + semantic search + wikilink traversal)
- [ ] Wiki-snapshot assembles context within a ~15K token budget using adaptive detail levels (L1/L2/L3)
- [ ] Wiki pages include pre-computed detail levels (headline, brief, full) generated by the wiki-maintainer
- [ ] Wiki pages include an `aliases` field for fuzzy deterministic entity matching
- [ ] Delta caching reuses unchanged entity context between consecutive scenes (>60% cache hit rate target)
- [ ] Relevance scoring combines entity match, wikilink proximity, semantic similarity, recency, and page type priority

## Open Questions

1. **OpenCode version pinning** — Which version of OpenCode should be targeted? The project is evolving rapidly; the `experimental.session.compacting` hook may change.
2. **Local LLM for agent orchestration** — The orchestrator agent needs to reliably invoke tools in sequence. Does the local model (magistral-abliterated:24b) handle tool-use reliably, or should a different model be used for orchestration vs. creative writing?
3. **Compaction hook complexity** — How much story state can be preserved through compaction? Needs empirical testing during prototype phase.
4. **ChromaDB vs. file-based retrieval** — For a single local story with manageable context, is ChromaDB worth the dependency, or is keyword/file-based retrieval sufficient?
5. **Parallel scene generation** — Can multiple subagent instances run in parallel for scenes within a chapter, or must they be sequential to maintain narrative flow?
6. **Wiki entry extraction quality** — NER on fictional text (fantasy names, invented locations) is harder than factual text. Can the local 7b model reliably extract entities and state changes, or does the wiki-maintainer need the 24b model?
7. **Wiki maintenance token overhead** — Each scene generates 5-15 wiki page updates, each requiring an LLM call. For a 100-scene novel this means ~1000+ maintenance calls. Is the overhead acceptable, and should maintenance be batched (per-chapter rather than per-scene)?
8. **Outline divergence handling** — When generated content diverges from the outline, should the wiki capture what was actually written (ground truth) or what was planned (outline)? What triggers a human review?
9. **Schema evolution** — The wiki schema must evolve as the story develops (e.g., a twist introduces a magic system). How are new page types added mid-story?
10. **Relevance score weight tuning** — The proposed composite relevance weights (entity_match 0.40, wikilink 0.20, semantic 0.20, recency 0.10, type_priority 0.10) are reasoned from first principles but not empirically validated for narrative retrieval. These need tuning against actual generated stories.
11. **nomic-embed-text on fiction domain** — No specific benchmarks exist for nomic-embed-text on fictional/narrative content. Embedding quality for fantasy names, invented locations, and genre-specific terminology may differ from general benchmarks.
12. **Wikilink graph density** — For heavily interlinked wikis, 1-hop traversal from 3-4 entities could return dozens of related pages. The max-5 cap is a conservative guard; optimal bounds depend on actual wiki graph topology.
13. **7b model synthesis quality** — All context synthesis research (CASC, Oreo, RECOMP) benchmarks larger models. Whether the local 7b model can produce adequate synthesis quality for the optional synthesis pass is unvalidated — deterministic assembly is the default for this reason.

## Related

- [Research report: OpenCode architecture](../../.github/research/opencode-agentic-infrastructure-2026-04-12.md) — Multi-model synthesis on OpenCode capabilities
- [Research report: Wiki memory system](../../.github/research/story-wiki-memory-system-2026-04-12.md) — Multi-model synthesis on progressive wiki for story generation
- [ADR 001: Hybrid agent-tool architecture](../adr/001-hybrid-agent-tool-architecture.md)
- [ADR 002: Context window budget strategy](../adr/002-context-window-budget-strategy.md)
- [ADR 003: ChromaDB replaces pgvector](../adr/003-chromadb-replaces-pgvector.md)
- [ADR 004: Progressive wiki memory system](../adr/004-progressive-wiki-memory-system.md)
- [ADR 005: Hybrid wiki context retrieval pipeline](../adr/005-hybrid-wiki-context-retrieval-pipeline.md)
- [Research report: Wiki context retrieval and synthesis](../../.github/research/wiki-context-search-synthesis-2026-04-12.md) — Multi-model synthesis on search/synthesis pipeline for wiki context
- [Karpathy LLM Wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — Foundational pattern
- [Current config](../../config.md) — Active generation settings
- `src/application/strategies/outline_chapter/` — Current pipeline implementation
- `prompts/` — 131 prompt templates (9 categories), relocated to top-level in issue #5
