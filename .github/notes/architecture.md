# Architecture Notes

## Current Architecture (Pre-Migration)

**Stack:** Python 3.x, clean architecture, dependency-injector, OpenAI-compatible API (local LLM), PostgreSQL/pgvector (RAG)

**Codebase size:** 72 Python files, ~18k LoC, 132 prompt templates (Markdown)

### Layer Structure

- `src/presentation/cli/` — CLI entry point, argument parsing
- `src/application/services/` — Services: story generation, outline, chapter, critique, RAG, etc.
- `src/application/strategies/` — Strategy pattern: outline-chapter (primary), stream-of-consciousness
- `src/application/interfaces/` — Abstractions: ModelProvider, StorageProvider, StoryStrategy
- `src/domain/entities/` — Story, Chapter, Scene, Outline, StoryInfo
- `src/domain/value_objects/` — GenerationSettings, ModelConfig
- `src/domain/repositories/` — SavepointRepository, StoryRepository
- `src/infrastructure/providers/` — OpenAI-compatible, LM Studio, LangChain, llama.cpp providers
- `src/infrastructure/prompts/` — PromptLoader, PromptHandler, PromptWrapper
- `src/infrastructure/savepoints/` — SavepointManager, SavepointDecorator
- `src/infrastructure/storage/` — FileStorage, PgVectorStore, SavepointRepository impl
- `src/infrastructure/container.py` — DI container (dependency-injector)
- `src/config/` — ConfigLoader (reads config.md YAML frontmatter)

### Pipeline Flow (outline-chapter strategy)

1. Read prompt file → load config.md
2. **Outline phase:**
   - Understand prompt (multistep conversation)
   - Generate story analysis chunks (8 categories: core foundation, character foundation, setting foundation, conflict/stakes, plot structure, theme/message, tone/style, world rules)
   - Extract story start date
   - Extract base context
   - Generate story elements
   - Generate initial outline (optional: chunked, `outline_chunk_size` chapters at a time)
   - Generate chapter list
   - (Optional) Critique loop: 6 critic types evaluate outline, refine if below quality threshold
3. **Character/Setting phase:**
   - Extract character names from story elements
   - Generate chunked character sheets (7 chunks: background, personality, motivations, relationships, skills, growth arc, current state)
   - Extract setting names
   - Generate chunked setting sheets
4. **Chapter generation loop (per chapter):**
   - Generate chapter outline expansion
   - Generate chapter synopsis
   - Load previous chapter recap (from savepoint)
   - Parse scene definitions from chapter outline
   - Per-scene: load relevant character/setting sheets → generate scene content
   - Assemble scenes into chapter
   - Generate chapter recap
   - Multi-stage recap sanitization
   - (Optional) Quality evaluation + revision loop
   - Update story state (character arcs, plot threads)
   - Save savepoints
5. **Assembly:** Combine all chapters into story Markdown + JSON

### Model Configuration (from config.md)

The system uses named model roles, each mapping to a model string:
- initial_outline_writer, chapter_outline_writer, chapter_stage{1-4}_writer
- chapter_revision_writer, revision_model, eval_model
- info_model, scrub_model, checker_model, translator_model
- sanity_model (small, fast — DeepSeek R1 7b)
- logical_model (Qwen 2.5 Coder 7b — JSON extraction)
- scene_writer, creative_model

### Prompt Template Categories (132 total)

Prompt templates are **Markdown files** stored in the top-level `prompts/` directory (relocated from `src/application/strategies/outline_chapter/prompts/` in issue #5). The subdirectory structure is preserved. Note: `src/infrastructure/prompts/` contains only the Python prompt-loading infrastructure (PromptLoader, PromptHandler, PromptWrapper), not the templates themselves.

| Category | Count | Purpose |
|----------|-------|---------|
| chapters/ | 16 | Chapter outline, content, synopsis, titles |
| characters/ | 15 | Character extraction, sheet generation (7 chunks), updates |
| multistep/ | 38 | Multi-turn conversation for outline + chapter enrichment |
| outline/ | 11 | Outline generation, expansion, validation |
| outline_review/ | 6 | Outline critique and quality review |
| recap/ | 8 | Chapter recap generation, sanitization |
| scenes/ | 9 | Scene parsing, generation, revision |
| settings/ | 13 | Setting extraction, sheet generation |
| story_state/ | 6 | Story state tracking, progression |
| _unused/ | 7 | Deprecated templates |
| root-level | 3 | Base context extraction, story start date, chapter events |

## Tools

Twelve tools implemented following the hybrid pattern from [ADR 001](docs/planning/adr/001-hybrid-agent-tool-architecture.md):

| Tool | Wrapper | Script | Infrastructure |
|------|---------|--------|---------------|
| `prompt-loader` | `.opencode/tools/prompt-loader.ts` | `src/tools/prompt_loader.py` | `PromptLoader` — template loading + variable substitution |
| `story-state` | `.opencode/tools/story-state.ts` | `src/tools/story_state.py` | Direct filesystem — atomic writes with `fcntl` locking |
| `savepoint-mgr` | `.opencode/tools/savepoint-mgr.ts` | `src/tools/savepoint_manager.py` | `FilesystemSavepointRepository` — checkpoint save/load/list/clear |
| `character-mgr` | `.opencode/tools/character-mgr.ts` | `src/tools/character_manager.py` | Direct filesystem — character sheet JSON I/O with deep-merge updates |
| `setting-mgr` | `.opencode/tools/setting-mgr.ts` | `src/tools/setting_manager.py` | Direct filesystem — setting sheet JSON I/O with deep-merge updates |
| `recap-manager` | `.opencode/tools/recap-manager.ts` | `src/tools/recap_manager.py` | `_llm.py` + `FilesystemSavepointRepository` — 5-stage recap pipeline with LLM |
| `outline-generator` | `.opencode/tools/outline-generator.ts` | `src/tools/outline_generator.py` | `_llm.py` + `FilesystemSavepointRepository` + `PromptLoader` — multi-step outline pipeline with conversation history |
| `scene-writer` | `.opencode/tools/scene-writer.ts` | `src/tools/scene_writer.py` | `_llm.py` + `FilesystemSavepointRepository` + `PromptLoader` — per-scene generation, revision, and chapter assembly |
| `critique-runner` | `.opencode/tools/critique-runner.ts` | `src/tools/critique_runner.py` | `_llm.py` + `CritiqueParser` — 6-critic evaluation with scoring and threshold logic |
| `wiki-init` | `.opencode/tools/wiki-init.ts` | `src/tools/wiki_init.py` | `_wiki.py` — idempotent wiki directory + schema creation |
| `wiki-read` | `.opencode/tools/wiki-read.ts` | `src/tools/wiki_read.py` | `_wiki.py` — page reading with detail levels, entity matching |
| `wiki-search` | `.opencode/tools/wiki-search.ts` | `src/tools/wiki_search.py` | ChromaDB `PersistentClient` — semantic + metadata search over `wiki-<name>` collections |

Pattern: `.opencode/tools/*.ts` (Zod schema + execFileSync) → `src/tools/*.py` (argparse + domain logic) → `src/infrastructure/` or `src/domain/`.

See [Tools Reference](docs/tools.md) for full documentation.

## Planned Architecture (Post-Migration)

See [PRD](docs/planning/opencode-migration/prd.md) and ADRs:
- [ADR 001](docs/planning/adr/001-hybrid-agent-tool-architecture.md) — Hybrid agent-tool architecture
- [ADR 002](docs/planning/adr/002-context-window-budget-strategy.md) — Context window budget strategy
- [ADR 003](docs/planning/adr/003-chromadb-replaces-pgvector.md) — ChromaDB replaces pgvector
- [ADR 004](docs/planning/adr/004-progressive-wiki-memory-system.md) — Progressive wiki memory system
- [ADR 005](docs/planning/adr/005-hybrid-wiki-context-retrieval-pipeline.md) — Hybrid wiki context retrieval pipeline

### Wiki Context Retrieval Pipeline (ADR 005)

The wiki-snapshot tool uses a three-stage pipeline to assemble scene context:
1. **Hybrid retrieval** — 4 tiers: deterministic entity matching (primary signal) → metadata-filtered query → semantic vector search → wikilink graph traversal (1-2 hops). Merged via RRF.
2. **Detail level selection** — Pre-computed L1/L2/L3 summaries per page. Token budget (~15K) enforced by demoting lower-priority pages L3→L2→L1. POV character + primary location are protected (always L3).
3. **Structured assembly** — Deterministic template assembly (default) or optional LLM synthesis pass for complex scenes. Fixed markdown structure: Characters → Location → Plot Threads → World Rules → Recent Events → Relationships.

Delta caching between consecutive scenes targets >60% cache hit rate. Relevance scoring: 0.40 entity_match + 0.20 wikilink + 0.20 semantic + 0.10 recency + 0.10 type_priority.
