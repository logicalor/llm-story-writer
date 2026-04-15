# Task Breakdown: OpenCode Agentic Architecture Migration

> Implements [PRD](./prd.md)

**Date:** 2026-04-12

## Phase 0 — Foundation

### Task 1: Archive Original Codebase

**Type:** infrastructure
**Estimated scope:** small
**Dependencies:** none

**Description:**
Create a `legacy/` directory containing a complete, frozen copy of the current `src/` directory. This serves as a reference during migration — developers can consult it to verify tool behaviour matches the original pipeline. The archive is a plain directory copy (not a git submodule), committed to the repo. The current `src/` remains in place during migration and is restructured incrementally.

Also update `.github/notes/repo.md` with the correct OWNER/REPO values parsed from the git remote.

**Acceptance Criteria:**

- [ ] `legacy/src/` exists and contains a complete copy of the current `src/` directory
- [ ] `legacy/README.md` explains the archive purpose and its relationship to the active codebase
- [ ] `.github/notes/repo.md` has correct OWNER=logicalor, REPO=llm-story-writer
- [ ] Original `src/` is unchanged

**Key Files:**

- `legacy/` — new directory (complete archive)
- `legacy/README.md` — archive documentation
- `.github/notes/repo.md` — repository identity fix

---

### Task 2: Initialize OpenCode Project Structure

**Type:** infrastructure
**Estimated scope:** small
**Dependencies:** none

**Description:**
Create the OpenCode project scaffolding: `opencode.json` configuration file, `.opencode/` directory structure (`agents/`, `tools/`, `skills/`, `commands/`, `plugins/`), and a minimal AGENTS.md. The `opencode.json` should configure the local LLM provider (Ollama), set default model, and define baseline permissions. No agents or tools yet — just the skeleton.

**Acceptance Criteria:**

- [ ] `opencode.json` exists with Ollama provider configured, default model set to `huihui_ai/magistral-abliterated:24b`
- [ ] `.opencode/agents/`, `.opencode/tools/`, `.opencode/skills/`, `.opencode/commands/`, `.opencode/plugins/` directories exist
- [ ] `AGENTS.md` exists with project-level instructions for all agents
- [ ] OpenCode can start and present the TUI with the configured model
- [ ] `.gitignore` updated for `.opencode/` runtime artefacts if needed

**Key Files:**

- `opencode.json` — main configuration
- `AGENTS.md` — top-level agent instructions
- `.opencode/` — directory structure

---

### Task 3: Relocate Prompt Templates to Shared Location

**Type:** infrastructure
**Estimated scope:** small
**Dependencies:** Task 1

**Description:**
Move the 131 prompt templates from `src/application/strategies/outline_chapter/prompts/` to a top-level `prompts/` directory. This decouples the templates from the Python strategy module structure and makes them accessible to both the legacy code (via symlink or path config) and the new OpenCode tools. Preserve the existing subdirectory structure (chapters/, characters/, multistep/, outline/, recap/, scenes/, settings/, story_state/). Also relocate the 3 root-level prompts (extract_base_context.md, extract_chapter_events.md, extract_story_start_date.md).

**Acceptance Criteria:**

- [x] `prompts/` directory exists at project root with all 131 templates in their subdirectories
- [x] No prompt templates remain in `src/application/strategies/outline_chapter/prompts/` (removed; all path references updated)
- [x] Legacy code can still load prompts (path references updated in PromptLoader, container, strategy_factory)
- [x] Template content is byte-identical to the originals

**Completed:** PR #29 (issue #5)

**Key Files:**

- `prompts/` — top-level prompt directory
- `prompts/chapters/`, `prompts/characters/`, etc. — template subdirectories
- `src/infrastructure/prompts/prompt_loader.py` — default path updated to `prompts`
- `src/infrastructure/container.py` — DI container path updated
- `src/application/strategies/strategy_factory.py` — factory fallback updated
- `src/application/strategies/outline_chapter/strategy.py` — `get_prompt_directory()` returns `"prompts"`

---

## Phase 1 — Core Tools (Python Layer)

### Task 4: Build prompt-loader Tool

**Type:** full-stack (TypeScript wrapper + Python logic)
**Estimated scope:** medium
**Dependencies:** Task 2, Task 3

**Description:**
Create the first custom tool: `prompt-loader`. This tool loads a prompt template by ID (e.g., `chapters/create_content`), substitutes variables, and returns the rendered prompt text. The TypeScript tool definition in `.opencode/tools/prompt-loader.ts` validates inputs and calls a Python script `src/tools/prompt_loader.py` that reuses the existing `PromptLoader` class logic. This is the foundational tool — most other tools depend on it.

**Acceptance Criteria:**

- [ ] `.opencode/tools/prompt-loader.ts` exists with proper tool definition (description, Zod schema, execute function)
- [ ] `src/tools/prompt_loader.py` exists, accepts `--prompt-id` and `--variables` (JSON) arguments, prints rendered prompt to stdout
- [ ] Loading `chapters/create_content` with `{chapter_num: 1}` returns correctly rendered text
- [ ] Missing prompt ID returns a clear error message
- [ ] Invalid variables are handled gracefully
- [ ] Tool is visible in OpenCode's tool list

**Key Files:**

- `.opencode/tools/prompt-loader.ts` — TypeScript tool definition
- `src/tools/prompt_loader.py` — Python implementation
- `src/tools/__init__.py` — package init

---

### Task 5: Build story-state Tool

**Type:** full-stack
**Estimated scope:** medium
**Dependencies:** Task 2

**Description:**
Create the `story-state` tool for reading and writing story state JSON files. Operations: `init` (create new story directory structure), `read` (load state.json or a specific field), `write` (update state.json fields), `list` (list available stories). The tool manages the `stories/<story-name>/` directory structure including `state.json`, and subdirectories for chapters, characters, settings, and savepoints. The state format preserves the `StoryContext`, `CharacterState`, and `PlotThread` dataclass structures from the current `story_state_manager.py`.

**Acceptance Criteria:**

- [ ] `.opencode/tools/story-state.ts` exists with tool definition
- [ ] `src/tools/story_state.py` exists with `init`, `read`, `write`, `list` operations
- [ ] `init` creates correct directory structure under `stories/<name>/`
- [ ] `read` returns full state or specific nested fields
- [ ] `write` updates specific fields without clobbering others (merge semantics)
- [ ] State JSON schema matches current `StoryContext`/`CharacterState`/`PlotThread` structures
- [ ] Concurrent write safety (file locking or atomic write)

**Key Files:**

- `.opencode/tools/story-state.ts` — TypeScript tool definition
- `src/tools/story_state.py` — Python implementation
- `src/domain/entities/story.py` — existing entities (referenced, not modified)

---

### Task 6: Build savepoint-mgr Tool

**Type:** full-stack
**Estimated scope:** medium
**Dependencies:** Task 5

**Description:**
Create the `savepoint-mgr` tool wrapping the existing `SavepointManager` and `FilesystemSavepointRepository`. Operations: `save` (save a named step), `load` (load a step), `has` (check if step exists), `list` (list all steps for a story), `clear` (clear all savepoints). This preserves the current savepoint file format and directory structure so that stories started with the legacy pipeline can be resumed with the new system.

**Acceptance Criteria:**

- [ ] `.opencode/tools/savepoint-mgr.ts` exists with tool definition
- [ ] `src/tools/savepoint_manager.py` exists wrapping existing `SavepointManager`
- [ ] Save/load/has/list/clear operations work correctly
- [ ] Savepoint files written by the legacy system can be read by the new tool
- [ ] Savepoint files written by the new tool can be read by the legacy system
- [ ] Step names support hierarchical paths (e.g., `chapter_1/scene_2`)

**Key Files:**

- `.opencode/tools/savepoint-mgr.ts` — TypeScript tool definition
- `src/tools/savepoint_manager.py` — Python implementation
- `src/infrastructure/savepoints/savepoint_decorator.py` — existing logic (reused)
- `src/infrastructure/storage/savepoint_repository.py` — existing repo (reused)

---

### Task 7: Build character-mgr Tool

**Type:** full-stack
**Estimated scope:** medium
**Dependencies:** Task 4, Task 5

**Description:**
Create the `character-mgr` tool wrapping existing `CharacterManager` logic. Operations: `extract-names` (extract character names from story elements), `generate-sheet` (generate a full character sheet for a named character), `update-sheet` (update after chapter events), `load-sheet` (load existing sheet), `list` (list all character sheets for a story), `generate-abridged` (create a context-efficient summary). The tool reads/writes character sheet files in `stories/<name>/characters/`.

The Python implementation extracts the core logic from `CharacterManager` but replaces the `ModelProvider` dependency with direct Ollama HTTP calls (keeping it self-contained) or accepts pre-generated content from the agent.

**Acceptance Criteria:**

- [ ] `.opencode/tools/character-mgr.ts` exists with tool definition
- [ ] `src/tools/character_manager.py` exists with all operations
- [ ] Character sheets are written as individual JSON files in `stories/<name>/characters/<char-name>.json`
- [ ] `generate-sheet` uses the chunked approach (background, personality, motivations, etc.) from current templates
- [ ] `load-sheet` returns the full sheet or abridged version
- [ ] `update-sheet` merges new information without losing existing data
- [ ] Token-aware: abridged sheets are limited to a configurable token budget

**Key Files:**

- `.opencode/tools/character-mgr.ts` — TypeScript tool definition
- `src/tools/character_manager.py` — Python implementation
- `prompts/characters/` — character prompt templates
- `src/application/strategies/outline_chapter/character_manager.py` — legacy logic (reference)

---

### Task 8: Build setting-mgr Tool

**Type:** full-stack
**Estimated scope:** medium
**Dependencies:** Task 4, Task 5

**Description:**
Create the `setting-mgr` tool, mirroring the character-mgr pattern for settings/locations. Operations: `extract-names`, `generate-sheet`, `update-sheet`, `load-sheet`, `list`, `generate-abridged`. Writes to `stories/<name>/settings/`.

**Acceptance Criteria:**

- [ ] `.opencode/tools/setting-mgr.ts` exists with tool definition
- [ ] `src/tools/setting_manager.py` exists with all operations
- [ ] Setting sheets are written as individual JSON files in `stories/<name>/settings/<setting-name>.json`
- [ ] Generation uses the chunked approach from current templates
- [ ] Token-aware abridged loading works correctly

**Key Files:**

- `.opencode/tools/setting-mgr.ts` — TypeScript tool definition
- `src/tools/setting_manager.py` — Python implementation
- `prompts/settings/` — setting prompt templates
- `src/application/strategies/outline_chapter/setting_manager.py` — legacy logic (reference)

---

### Task 9: Build recap-manager Tool

**Type:** full-stack
**Estimated scope:** medium
**Dependencies:** Task 4, Task 6

**Description:**
Create the `recap-manager` tool wrapping `RecapManager` logic. Operations: `generate` (generate recap from chapter content), `sanitize` (run multi-stage sanitizer), `load` (load existing recap), `compact` (create progressively compacted recap for context efficiency). The multi-stage recap sanitizer is a proven piece of the current pipeline and must be preserved.

**Acceptance Criteria:**

- [ ] `.opencode/tools/recap-manager.ts` exists with tool definition
- [ ] `src/tools/recap_manager.py` exists with all operations
- [ ] Multi-stage recap sanitization pipeline preserved from current implementation
- [ ] Recaps are stored as savepoint steps (backward-compatible with legacy format)
- [ ] Progressive compaction produces summaries within configurable token limits

**Key Files:**

- `.opencode/tools/recap-manager.ts` — TypeScript tool definition
- `src/tools/recap_manager.py` — Python implementation
- `prompts/recap/` — recap prompt templates
- `src/application/strategies/outline_chapter/recap_manager.py` — legacy logic (reference)

---

### Task 10: Build outline-generator Tool

**Type:** full-stack
**Estimated scope:** large
**Dependencies:** Task 4, Task 5, Task 7, Task 8

**Description:**
Create the `outline-generator` tool wrapping `OutlineGenerator` logic. This is the most complex tool because the outline generation pipeline has multiple sub-steps: understand prompt → generate story analysis chunks (core foundation, character foundation, setting foundation, conflict/stakes, plot structure, theme/message, tone/style, world rules) → extract story start date → extract base context → generate story elements → generate initial outline → generate chapter list → (optional) critique and refine.

Operations: `analyze-prompt` (run multi-step prompt analysis), `generate-elements` (generate story elements), `generate-outline` (create full outline), `expand-chapter` (expand outline for a single chapter), `refine` (apply critique feedback to outline). Each operation reads/writes savepoints so the process can be resumed.

**Acceptance Criteria:**

- [ ] `.opencode/tools/outline-generator.ts` exists with tool definition
- [ ] `src/tools/outline_generator.py` exists with all operations
- [ ] Story analysis chunks are generated and saved individually (for selective context loading)
- [ ] The outline is generated using the multistep conversation approach from current implementation
- [ ] Chunked outline generation (configurable via `outline_chunk_size`) is supported
- [ ] Each sub-step creates a savepoint for resumability
- [ ] Output format matches current `Outline` entity structure

**Key Files:**

- `.opencode/tools/outline-generator.ts` — TypeScript tool definition
- `src/tools/outline_generator.py` — Python implementation
- `prompts/outline/` — outline prompt templates
- `prompts/multistep/outline/` — multistep outline templates
- `src/application/strategies/outline_chapter/outline_generator.py` — legacy logic (reference)

---

### Task 11: Build scene-writer Tool

**Type:** full-stack
**Estimated scope:** large
**Dependencies:** Task 4, Task 5, Task 7, Task 8, Task 9

**Description:**
Create the `scene-writer` tool wrapping `SceneGenerator` logic. Operations: `parse-definitions` (extract scene definitions from chapter outline), `generate` (write a single scene with full context: chapter outline, character sheets, setting sheets, previous recap, synopsis), `revise` (apply revision feedback), `assemble-chapter` (combine scenes into chapter content).

This tool implements the context-budgeting strategy: for each scene, it selectively loads only the relevant character sheets, setting sheets, and recaps that fit within the 65536-token budget.

**Acceptance Criteria:**

- [ ] `.opencode/tools/scene-writer.ts` exists with tool definition
- [ ] `src/tools/scene_writer.py` exists with all operations
- [ ] Context assembly respects the 65536-token budget (measured by token counting, not character counting)
- [ ] Scene definitions are parsed from chapter outlines using current JSON schema
- [ ] Generated scenes are saved individually as savepoints
- [ ] Chapter assembly concatenates scenes with appropriate transitions
- [ ] Revision takes existing scene + feedback and produces improved version

**Key Files:**

- `.opencode/tools/scene-writer.ts` — TypeScript tool definition
- `src/tools/scene_writer.py` — Python implementation
- `prompts/scenes/` — scene prompt templates
- `src/application/strategies/outline_chapter/scene_generator.py` — legacy logic (reference)

---

### Task 12: Build critique-runner Tool

**Type:** full-stack
**Estimated scope:** medium
**Dependencies:** Task 4, Task 6

**Description:**
Create the `critique-runner` tool wrapping `CritiqueService` logic. Operations: `run-critics` (run all 6 critic types against content), `parse-scores` (extract structured scores from critic responses), `should-refine` (determine if content meets quality threshold), `generate-feedback` (synthesize actionable feedback from critic scores). The 6 critic types (audiobook-producer, book-club-moderator, commercial-fiction-editor, literary-fiction-reviewer, publishing-acquisitions-editor, subject-expert) are preserved.

**Acceptance Criteria:**

- [x] `.opencode/tools/critique-runner.ts` exists with tool definition
- [x] `src/tools/critique_runner.py` exists with all operations
- [x] All 6 critic types run and return structured scores
- [x] Quality threshold comparison uses configurable `outline_quality` / `chapter_quality` from config.md
- [x] Critique results are saved as savepoints per iteration
- [x] `should-refine` correctly calculates average scores and determines if refinement needed

**Key Files:**

- `.opencode/tools/critique-runner.ts` — TypeScript tool definition
- `src/tools/critique_runner.py` — Python implementation
- `src/application/services/critique_service.py` — legacy logic (reference)
- `src/application/services/critique_parser.py` — legacy parser (reused)

---

## Phase 2 — Agent Layer

### Task 13: Build Wiki Tools (wiki-init, wiki-read, wiki-search)

**Type:** full-stack (TypeScript wrappers + Python logic)
**Estimated scope:** medium
**Dependencies:** Task 5

**Description:**
Create the foundational wiki tools that manage the wiki file structure and provide read/search access:

**`wiki-init`**: Initialize the wiki directory structure for a new story. Creates `wiki/` with subdirectories (characters/, locations/, events/, factions/, items/, plot-threads/, world-rules/, themes/, relationships/, timeline/, chapters/), plus `_schema.md` (page type definitions, frontmatter conventions, naming rules), `index.md` (empty catalog), `log.md` (empty operations log), and `contradictions.md`. The schema defines ~12 page types with YAML frontmatter fields, [[wikilink]] conventions, and the confidence taxonomy (verified/planned/speculative).

**`wiki-read`**: Read one or more wiki pages by slug, type, or glob pattern. Supports reading at different detail levels: `headline` (1-line from index.md, ~30 tokens), `brief` (3-sentence summary + frontmatter, ~150 tokens), `full` (entire page, ~500 tokens). Returns structured JSON with frontmatter parsed. Also supports `match-entities` mode: given a text string, deterministically matches entity names and aliases (from wiki frontmatter `aliases` field) against the wiki index and returns the matched page slugs.

**`wiki-search`**: Semantic search across wiki content via ChromaDB. Wiki pages are embedded when created/updated (reuses the per-story ChromaDB collection from `rag-query`). Supports two modes: `semantic` (embed query text, return nearest neighbors) and `metadata` (ChromaDB where-filter on YAML frontmatter fields — e.g., `type=plot_thread AND status=active`). Returns ranked results with page slugs, match scores, and brief excerpts.

**Acceptance Criteria:**

- [ ] `.opencode/tools/wiki-init.ts`, `.opencode/tools/wiki-read.ts`, `.opencode/tools/wiki-search.ts` exist
- [ ] `src/tools/wiki_init.py`, `src/tools/wiki_read.py`, `src/tools/wiki_search.py` exist
- [ ] `wiki-init` creates correct directory tree under `stories/<name>/wiki/`
- [ ] `_schema.md` defines all ~12 page types with frontmatter field specs (including `aliases` field for entity matching)
- [ ] `wiki-read` parses YAML frontmatter and returns structured output
- [ ] `wiki-read` supports headline/brief/full detail levels
- [ ] `wiki-read` `match-entities` mode matches entity names and aliases against index
- [ ] `wiki-search` `semantic` mode queries ChromaDB and returns ranked page matches
- [ ] `wiki-search` `metadata` mode supports where-filter on frontmatter fields
- [ ] All tools handle empty wiki gracefully (no errors on fresh stories)

**Key Files:**

- `.opencode/tools/wiki-init.ts`, `wiki-read.ts`, `wiki-search.ts` — TypeScript tool definitions
- `src/tools/wiki_init.py`, `wiki_read.py`, `wiki_search.py` — Python implementations
- `src/tools/wiki_schema_template.md` — Default `_schema.md` template

---

### Task 14: Build wiki-snapshot Tool

**Type:** full-stack
**Estimated scope:** large
**Dependencies:** Task 13, Task 19

**Description:**
Create the `wiki-snapshot` tool — the critical pre-generation context assembler. This tool implements the three-stage hybrid retrieval and context assembly pipeline described in [ADR 005](../adr/005-hybrid-wiki-context-retrieval-pipeline.md) and the [retrieval/synthesis research report](../../.github/research/wiki-context-search-synthesis-2026-04-12.md).

Given a scene specification (chapter number, scene number, scene outline text, list of character names and location names from the scene definition), the tool:

**Stage 1 — Hybrid Multi-Tier Retrieval:**
1. **T1 — Entity Matching (deterministic):** Parse the scene outline for entity names using `wiki-read match-entities` against the wiki index name list + aliases. Matched pages are always included (priority: HIGHEST).
2. **T2 — Metadata-Filtered Structured Query:** Use `wiki-search metadata` to find category-relevant but unnamed pages — e.g., `type=plot_thread AND status=active`, `type=world_rule AND tags OVERLAP scene_tags` (priority: HIGH).
3. **T3 — Semantic Vector Search:** Use `wiki-search semantic` to embed the scene outline and find thematically related pages not caught by T1/T2 (priority: SUPPLEMENTARY).
4. **T4 — Wikilink Graph Traversal:** From T1/T2/T3 results, parse [[wikilinks]] in retrieved pages and follow 1-2 hops to discover related entities. Cap at 5 additional entities to prevent context flooding (priority: MEDIUM).
5. **Merge & Deduplicate:** Combine all results via Reciprocal Rank Fusion (RRF), deduplicate by page slug.
6. **Relevance Scoring:** Score each page using a composite formula: `0.40 × entity_match + 0.20 × wikilink_proximity + 0.20 × semantic_similarity + 0.10 × recency + 0.10 × type_priority`. Drop pages scoring below 0.15.

**Stage 2 — Detail Level Selection & Token Budgeting:**
1. Sort pages by relevance score.
2. Assign detail levels top-down: protected tier (POV character, primary location) always L3; top pages → L3; middle → L2; low → L1.
3. Apply scene-type adaptation: dialogue-heavy → more character budget; action → more location/rules budget; first-appearance → always L3 for new entities.
4. Enforce total ~15K token budget by demoting lower-priority pages L3→L2→L1 until sum fits. Never drop a page entirely — minimum L1 (headline).

**Stage 3 — Structured Context Assembly:**
1. Load each page at its assigned detail level (using the pre-computed L1/L2/L3 content from wiki page frontmatter).
2. Assemble into a fixed-structure markdown document with sections: Characters (POV full, scene characters brief, background headline), Location (full), Active Plot Threads (brief), World Rules (brief), Recent Events (last 3 timeline entries), Relationships (between scene characters).
3. **Optional LLM synthesis pass:** For complex scenes (>5 characters or >3 active plot threads), run the 7b model to condense and connect the assembled content. The synthesis prompt instructs: restructure and condense only, never add information not in source pages.

**Delta Caching:**
The tool maintains a scene-level cache to avoid redundant retrieval between consecutive scenes:
1. Parse new scene outline for entity names and compare to the previous scene's entity set.
2. For kept entities: check page version counters — if unchanged, reuse cached content; if bumped (wiki-update ran), re-fetch.
3. For new entities: full retrieval + detail level assignment.
4. For removed entities: drop from cache.
5. Always refresh: recent timeline (new events from prior scene).
6. Chapter boundaries invalidate the entire scene cache.

**Acceptance Criteria:**

- [ ] `.opencode/tools/wiki-snapshot.ts` exists with tool definition
- [ ] `src/tools/wiki_snapshot.py` exists with full three-stage pipeline
- [ ] T1 entity matching correctly identifies entities by name and alias
- [ ] T2 metadata filtering retrieves active plot threads and applicable world rules
- [ ] T3 semantic search finds thematically related pages not caught by T1/T2
- [ ] T4 wikilink traversal discovers related entities (capped at 5 additional)
- [ ] RRF fusion correctly merges results from all tiers
- [ ] Composite relevance scoring matches the documented formula
- [ ] Pages scoring below 0.15 are excluded
- [ ] Detail level selection respects protected tier (POV character, primary location always L3)
- [ ] Token budget is enforced (measured by tiktoken, not character count)
- [ ] Graceful degradation: if budget exceeded, demotes pages L3→L2→L1 (never drops entirely)
- [ ] Assembled markdown has correct section structure (Characters, Location, Plot Threads, World Rules, Recent Events, Relationships)
- [ ] Optional LLM synthesis pass triggers for scenes with >5 characters or >3 plot threads
- [ ] Delta caching reuses unchanged entity content between consecutive scenes
- [ ] Chapter boundaries correctly invalidate the scene cache
- [ ] Cache hit rate exceeds 60% for consecutive scenes in the same chapter
- [ ] Missing pages are skipped with warnings (not errors)
- [ ] Snapshot for a scene with 3 characters, 1 location, 2 plot threads fits within 15K tokens

**Key Files:**

- `.opencode/tools/wiki-snapshot.ts` — TypeScript tool definition
- `src/tools/wiki_snapshot.py` — Python implementation (three-stage pipeline, delta caching, relevance scoring)

---

### Task 15: Build wiki-update Tool

**Type:** full-stack
**Estimated scope:** large
**Dependencies:** Task 13

**Description:**
Create the `wiki-update` tool that processes generated scene text and updates wiki pages. Given the generated scene content and the scene's metadata (chapter, scene number), the tool:

1. Accepts a structured update payload (produced by the wiki-maintainer agent) containing: new entities to create, existing entities to update, new events to record, state changes to apply, relationship changes
2. Creates new wiki pages with proper YAML frontmatter, body text, and [[wikilinks]]
3. Updates existing pages: merges new information into relevant sections, updates `last_updated`, adds arc progression entries, updates status fields
4. Appends new events to `timeline/main-timeline.md`
5. Updates `wiki/index.md` with new page entries (1-line summaries)
6. Appends an operation record to `wiki/log.md`
7. Re-embeds changed pages into ChromaDB
8. **Pre-computes hierarchical detail levels:** For each created/updated page, generates L1 (headline, ~30 tokens), L2 (brief, ~150 tokens), and L3 (full, ~500 tokens) content and stores them in the page's YAML frontmatter under `detail_levels:`. These pre-computed levels are used by `wiki-snapshot` for adaptive token budgeting.
9. Increments the page's `version` counter (used by wiki-snapshot's delta caching to detect stale cache entries)

The tool does NOT do entity extraction itself — that's the wiki-maintainer agent's job. This tool is a structured CRUD layer.

**Acceptance Criteria:**

- [ ] `.opencode/tools/wiki-update.ts` exists with tool definition
- [ ] `src/tools/wiki_update.py` exists with all CRUD operations
- [ ] New pages are created with correct frontmatter (type, name, slug, confidence, first_appearance, etc.)
- [ ] Existing pages are updated with merge semantics (no data loss)
- [ ] `index.md` is updated atomically with new entries
- [ ] `log.md` is appended with timestamped operation records
- [ ] Timeline is extended with new events in chronological order
- [ ] Changed pages are re-embedded into ChromaDB
- [ ] Pre-computed detail levels (L1 headline, L2 brief, L3 full) are stored in page frontmatter
- [ ] Page `version` counter is incremented on every update
- [ ] Rollback: if any update fails, previously-applied updates in the batch are not left in inconsistent state

**Key Files:**

- `.opencode/tools/wiki-update.ts` — TypeScript tool definition
- `src/tools/wiki_update.py` — Python implementation (CRUD, index management, ChromaDB re-embedding)

---

### Task 16: Build wiki-lint Tool

**Type:** full-stack
**Estimated scope:** medium
**Dependencies:** Task 13

**Description:**
Create the `wiki-lint` tool that runs consistency checks across the wiki. Operations:

- `check-chapter` (run after each chapter): Detect contradictions between wiki state and the chapter content using the ConStory-Bench error taxonomy (timeline & plot logic, characterization, world-building, factual consistency, narrative & style)
- `check-full` (run periodically): Full lint pass checking for orphan pages (referenced but don't exist), stale claims (not updated in 5+ chapters), missing cross-references, timeline ordering violations, confidence downgrades (verified claims contradicted by later content)
- `check-entity <slug>` (run on demand): Check a single entity page for internal consistency and cross-reference validity

Returns a structured report with severity levels (error/warning/info) and suggested fixes.

**Acceptance Criteria:**

- [ ] `.opencode/tools/wiki-lint.ts` exists with tool definition
- [ ] `src/tools/wiki_lint.py` exists with all check operations
- [ ] `check-chapter` detects contradictions between wiki state and chapter content
- [ ] `check-full` identifies orphan pages, stale claims, missing cross-refs, timeline violations
- [ ] Lint report includes severity, error type (ConStory-Bench category), affected pages, and suggested fix
- [ ] `contradictions.md` is updated with newly-detected contradictions and their resolution status
- [ ] Lint is fast enough to run after every chapter without noticeable delay

**Key Files:**

- `.opencode/tools/wiki-lint.ts` — TypeScript tool definition
- `src/tools/wiki_lint.py` — Python implementation (consistency checks, ConStory-Bench taxonomy)

---

## Phase 3 — Agent Layer

### Task 17: Build Story Orchestrator Agent

**Type:** full-stack (agent definition + skill)
**Estimated scope:** large
**Dependencies:** Tasks 4-16

**Description:**
Define the primary `story-orchestrator` agent in `.opencode/agents/story-orchestrator.md`. This agent coordinates the full story generation pipeline by invoking subagents in the correct order. Its system prompt encodes the pipeline phases:

1. Prompt analysis → outline generation (delegate to outline-planner)
2. Outline approval (interactive) or auto-approve (batch)
3. Wiki initialization for the story (via `wiki-init` tool)
4. Character sheet generation (delegate to character-manager)
5. Setting sheet generation
6. Initial wiki population from outline, character sheets, and settings (delegate to wiki-maintainer)
7. Per-chapter loop: chapter outline → wiki snapshot → scene generation → wiki update (delegate to wiki-maintainer) → chapter assembly → wiki lint → quality evaluation → (optional) revision
8. Story assembly and final output

Create the `story-pipeline` skill with detailed instructions for pipeline ordering, quality gates, and decision points — including the wiki update cycle.

**Acceptance Criteria:**

- [x] `.opencode/agents/story-orchestrator.md` exists with complete agent definition
- [x] Agent correctly sequences pipeline phases via subagent delegation
- [x] Agent invokes `wiki-init` during story initialization
- [x] Agent invokes wiki-maintainer after each scene and at chapter boundaries
- [x] In interactive mode, agent pauses for human approval at outline stage
- [x] In batch mode, agent auto-proceeds through all phases
- [x] `.opencode/skills/story-pipeline/SKILL.md` exists with pipeline instructions (including wiki cycle)
- [x] Agent respects generation settings from config.md (quality thresholds, revision counts, etc.)
- [x] Agent creates and manages savepoints at each major phase transition

**Completed:** PR #62 (issue #20)

**Key Files:**

- `.opencode/agents/story-orchestrator.md` — agent definition
- `.opencode/skills/story-pipeline/SKILL.md` — pipeline skill
- `opencode.json` — agent registration

---

### Task 18: Build Outline Planner Subagent

**Type:** full-stack (agent definition + skill)
**Estimated scope:** medium
**Dependencies:** Task 10, Task 12

**Description:**
Define the `outline-planner` subagent. This agent is invoked by the orchestrator and uses the `outline-generator` and `critique-runner` tools to generate and iteratively refine the story outline. It implements the multi-step outline generation pipeline: analyze prompt → generate story analysis chunks → generate elements → create outline → (optional) chunked generation → critique → refine loop.

Create the `outline-structure` skill with outline format specifications.

**Acceptance Criteria:**

- [x] `.opencode/agents/outline-planner.md` exists with agent definition
- [x] Agent uses `outline-generator` and `critique-runner` tools correctly
- [x] Optional critique loop runs up to `outline_critique_iterations` times
- [x] `.opencode/skills/outline-structure/SKILL.md` exists
- [x] Agent returns completed outline to the orchestrator
- [x] All intermediate steps are saved as savepoints

**Key Files:**

- `.opencode/agents/outline-planner.md` — agent definition
- `.opencode/skills/outline-structure/SKILL.md` — outline skill
- `opencode.json` — agent registration

---

### Task 19: Build Scene Writer Subagent

**Type:** full-stack (agent definition + skill)
**Estimated scope:** medium
**Dependencies:** Task 11, Task 7, Task 8, Task 9, Task 14

**Description:**
Define the `scene-writer` subagent. This agent is invoked per-chapter by the orchestrator. It receives a chapter number and uses the `scene-writer`, `character-mgr`, `setting-mgr`, `recap-manager`, and `wiki-snapshot` tools to generate all scenes for that chapter. It uses the wiki snapshot (rather than raw character/setting sheet loading) as the primary context source for each scene — the snapshot provides pre-synthesized, token-budgeted context including characters, locations, plot threads, world rules, and timeline events.

Create the `scene-writing` and `character-voice` skills.

**Acceptance Criteria:**

- [ ] `.opencode/agents/scene-writer.md` exists with agent definition
- [ ] Agent calls `wiki-snapshot` before each scene to assemble pre-generation context
- [ ] Agent loads relevant context within token budget before generating each scene
- [ ] Agent generates scenes sequentially (maintaining narrative flow)
- [ ] `.opencode/skills/scene-writing/SKILL.md` exists
- [ ] `.opencode/skills/character-voice/SKILL.md` exists
- [ ] Agent returns assembled chapter content to orchestrator

**Key Files:**

- `.opencode/agents/scene-writer.md` — agent definition
- `.opencode/skills/scene-writing/SKILL.md` — scene writing conventions
- `.opencode/skills/character-voice/SKILL.md` — character consistency rules
- `opencode.json` — agent registration

---

### Task 20: Build Wiki Maintainer Subagent

**Type:** full-stack (agent definition + skill)
**Estimated scope:** large
**Dependencies:** Task 15, Task 16

**Description:**
Define the `wiki-maintainer` subagent. This agent is invoked by the orchestrator after each scene (and at chapter boundaries) to extract entities, events, and state changes from generated content and update the wiki. It uses a smaller/faster model (e.g. deepseek-r1-abliterated:7b) to keep overhead low.

The agent's workflow per scene:
1. Read the generated scene text
2. Read the current wiki state (relevant pages via `wiki-read`)
3. Extract: new entities (characters, locations, items mentioned for the first time), state changes (character movements, emotional shifts, relationship changes), new events, revealed information
4. Identify aliases for each entity (common references, titles, nicknames used in the text) and include them in the entity's `aliases` frontmatter field
5. Produce a structured update payload (JSON) specifying creates, updates, timeline entries
6. Call `wiki-update` with the payload (which auto-generates pre-computed L1/L2/L3 detail levels and increments version counters)
7. At chapter boundaries: call `wiki-lint check-chapter` and log results

Create the `wiki-maintenance` skill with extraction rules, confidence scoring guidelines, and the entity extraction prompt templates.

**Acceptance Criteria:**

- [x] `.opencode/agents/wiki-maintainer.md` exists with agent definition
- [x] Agent extracts new entities and state changes from scene text
- [x] Agent identifies entity aliases (titles, nicknames, common references) from scene text
- [x] Agent produces structured update payloads consumed by `wiki-update`
- [x] Agent uses `wiki-lint` at chapter boundaries
- [x] Agent assigns correct `confidence` levels (verified for explicit statements, speculative for implied)
- [x] Agent tracks provenance (source chapter/scene for every fact)
- [x] `.opencode/skills/wiki-maintenance/SKILL.md` exists with extraction rules and confidence taxonomy
- [x] Agent can run on a 7b model without tool-use failures
- [x] Agent handles initial wiki population from outline (creating planned/speculative entries)

**Key Files:**

- `.opencode/agents/wiki-maintainer.md` — agent definition
- `.opencode/skills/wiki-maintenance/SKILL.md` — wiki maintenance skill (extraction rules, confidence scoring)
- `opencode.json` — agent registration (configured with smaller model)

---

### Task 21: Build Custom Commands

**Type:** full-stack
**Estimated scope:** medium
**Dependencies:** Task 17

**Description:**
Create OpenCode custom commands that serve as the user interface:
- `/new-story <prompt-file>` — Initialize new story (including wiki), start orchestrator
- `/continue [story-name]` — Resume from last savepoint
- `/regenerate chapter <N>` — Regenerate a specific chapter
- `/regenerate scene <chapter> <scene>` — Regenerate a specific scene
- `/savepoint [name]` — Create a manual savepoint
- `/status` — Show generation progress (chapters completed, current phase, wiki stats)
- `/settings [key] [value]` — View or modify generation settings
- `/wiki [story-name]` — Show wiki summary (page counts by type, last update, lint status)

**Acceptance Criteria:**

- [ ] All commands defined in `.opencode/commands/`
- [ ] `/new-story` validates prompt file exists, initializes wiki, and starts orchestrator
- [ ] `/continue` lists available stories if no name given, resumes correct story
- [ ] `/regenerate` correctly identifies chapter/scene and triggers regeneration (including wiki rollback)
- [ ] `/status` reads story state and displays human-readable progress
- [ ] `/settings` reads config.md and displays/modifies settings
- [ ] `/wiki` displays wiki page counts, last update timestamp, and recent lint results

**Key Files:**

- `.opencode/commands/new-story.md` — new story command
- `.opencode/commands/continue.md` — continue command
- `.opencode/commands/regenerate.md` — regenerate command
- `.opencode/commands/savepoint.md` — savepoint command
- `.opencode/commands/status.md` — status command
- `.opencode/commands/settings.md` — settings command
- `.opencode/commands/wiki.md` — wiki status command

---

## Phase 4 — Integration & Polish

### Task 22: Build Compaction Plugin

**Type:** full-stack
**Estimated scope:** medium
**Dependencies:** Task 5, Task 17

**Description:**
Create an OpenCode plugin that hooks into `experimental.session.compacting` to inject critical story state into the compaction summary. When context is being compacted, the plugin reads the current story state JSON and wiki state and injects: current chapter/scene being written, active character names (from wiki index), active plot threads (from wiki), current story direction, and the last 2 chapter synopses (from wiki chapter pages). This ensures the agent retains narrative continuity after compaction.

**Acceptance Criteria:**

- [ ] `.opencode/plugins/story-compaction.ts` exists
- [ ] Plugin hooks into `experimental.session.compacting`
- [ ] Injected state includes: current chapter, active characters, plot threads, story direction (sourced from wiki)
- [ ] Injected state fits within ~4000 tokens (measured)
- [ ] Agent behaviour is coherent after compaction (manual verification)

**Key Files:**

- `.opencode/plugins/story-compaction.ts` — compaction plugin
- `opencode.json` — plugin registration

---

### Task 23: Build Context Budgeting and Wiki Convention Skills

**Type:** skill
**Estimated scope:** medium
**Dependencies:** Task 14, Task 19, Task 20

**Description:**
Create three skills:

**`context-budgeting`**: Instructs agents on managing the 65536-token context window. Rules include: use `wiki-snapshot` for scene context instead of raw file loading, never load more than 3 character wiki pages simultaneously (use brief level), always use wiki chapter synopses instead of full chapter text, load only the current chapter outline (not the full outline), prefer wiki queries over holding state in conversation. Includes the token budget table and relevance scoring formula from the [retrieval/synthesis research report](../../.github/research/wiki-context-search-synthesis-2026-04-12.md). Documents the three-stage retrieval pipeline (hybrid search → detail level selection → structured assembly), the composite scoring formula (0.40 entity_match + 0.20 wikilink + 0.20 semantic + 0.10 recency + 0.10 type_priority), and the delta caching strategy for consecutive scenes.

**`wiki-conventions`**: Defines wiki page type schemas, YAML frontmatter field specifications for all ~12 page types, [[wikilink]] conventions, naming rules (slugification), and cross-reference patterns. This skill is loaded by the wiki-maintainer agent.

**`wiki-maintenance`**: (Created alongside Task 20 but refined here.) Update workflows, lint procedures, contradiction handling, confidence scoring rules, entity extraction guidelines. Includes the ConStory-Bench error taxonomy for lint operations.

**Acceptance Criteria:**

- [ ] `.opencode/skills/context-budgeting/SKILL.md` exists with concrete token budgets per context category
- [ ] `.opencode/skills/wiki-conventions/SKILL.md` exists with all page type schemas and frontmatter specs
- [ ] `.opencode/skills/wiki-maintenance/SKILL.md` exists with extraction rules, confidence taxonomy, lint procedures
- [ ] Skills are referenced by the appropriate agents (wiki-maintainer, scene-writer, orchestrator)
- [ ] Context budgeting rules are practical and testable (not vague guidelines)
- [ ] Wiki conventions include example pages for at least 3 page types

**Key Files:**

- `.opencode/skills/context-budgeting/SKILL.md` — context budgeting skill
- `.opencode/skills/wiki-conventions/SKILL.md` — wiki conventions skill
- `.opencode/skills/wiki-maintenance/SKILL.md` — wiki maintenance skill

---

### Task 24: Replace PostgreSQL RAG with ChromaDB

**Type:** full-stack
**Estimated scope:** medium
**Dependencies:** Task 5

**Description:**
Replace the PostgreSQL/pgvector RAG system with a ChromaDB-based local solution. Create a `rag-query` tool that queries a per-story ChromaDB collection. The collection is populated automatically as content is generated (outline, chapters, character sheets, setting sheets, and wiki pages are embedded when saved). Use the existing Ollama embedding model (nomic-embed-text) for embeddings. Wiki pages are embedded by the `wiki-update` tool (Task 15) using this same ChromaDB infrastructure.

Remove dependencies: `psycopg2`, `pgvector`, `docker-compose.yml` (PostgreSQL), `init.sql`.

**Acceptance Criteria:**

- [ ] `.opencode/tools/rag-query.ts` exists with tool definition
- [ ] `src/tools/rag_query.py` exists with `index` and `query` operations
- [ ] Content is automatically indexed when saved by other tools
- [ ] Wiki pages are indexed into the same per-story collection
- [ ] Query returns relevant chunks with similarity scores
- [ ] ChromaDB collection is stored per-story in `.chromadb/stories/<name>/`
- [ ] PostgreSQL/pgvector dependencies removed from requirements.txt
- [ ] docker-compose.yml and init.sql removed or archived

**Key Files:**

- `.opencode/tools/rag-query.ts` — TypeScript tool definition
- `src/tools/rag_query.py` — Python implementation
- `requirements.txt` — dependency cleanup
- `requirements-rag.txt` — updated RAG dependencies

---

### Task 25: End-to-End Integration Test (with Wiki)

**Type:** testing
**Estimated scope:** large
**Dependencies:** Tasks 17-24

**Description:**
Create an end-to-end integration test that generates a short story (3 chapters, 2 scenes each) using the full OpenCode agent pipeline including the wiki memory system. The test uses one of the existing example prompts (`ExamplePrompts/ShortDebuggingStory/Prompt.txt`) and verifies that:

1. Story state is correctly initialized and maintained
2. Wiki is initialized with correct structure
3. Outline is generated with all required elements
4. Character and setting sheets are created
5. Wiki is populated from outline (planned/speculative entries)
6. All scenes and chapters are generated
7. Wiki is updated after each scene (new entities, state changes, events)
8. Wiki lint runs after each chapter with no errors
9. Wiki snapshots are assembled and used for scene context
10. Savepoints are created at each phase
11. Final output includes Markdown and JSON forms
12. All operations stay within the 65536-token context budget

The test can be run in headless/SDK mode.

**Acceptance Criteria:**

- [ ] Test script exists and runs end-to-end
- [ ] Output story has 3 chapters with 2+ scenes each
- [ ] Character sheets exist for all extracted characters
- [ ] Setting sheets exist for all extracted settings
- [ ] Wiki exists with pages for characters, locations, events, plot threads
- [ ] Wiki index.md lists all created pages with summaries
- [ ] Wiki log.md records all operations
- [ ] Wiki lint produces no errors on the final state
- [ ] Savepoints exist for all major pipeline phases
- [ ] Story Markdown output is properly formatted
- [ ] No individual tool call exceeds 65536 tokens of context
- [ ] Test documents any manual verification steps needed

**Key Files:**

- `tests/integration/test_e2e_opencode.py` — integration test
- `ExamplePrompts/ShortDebuggingStory/Prompt.txt` — test input

---

### Task 26: Clean Up Legacy Dependencies

**Type:** infrastructure
**Estimated scope:** small
**Dependencies:** Task 25

**Description:**
After successful E2E testing, clean up dependencies no longer needed:
- Remove `dependency-injector` from requirements.txt
- Remove LangChain dependencies (`langchain`, `langchain-core`, etc.)
- Remove `psycopg2` / pgvector dependencies
- Update README.md with new setup instructions (OpenCode installation, Ollama setup, wiki system overview)
- Update config.md documentation section to reflect new architecture
- Mark legacy code as archived in documentation

**Acceptance Criteria:**

- [ ] `requirements.txt` contains only actively-used dependencies
- [ ] `requirements-rag.txt` updated for ChromaDB-only RAG
- [ ] README.md documents the OpenCode-based workflow including wiki memory system
- [ ] README.md includes quickstart: install OpenCode, configure Ollama, run `/new-story`
- [ ] No import errors when running the new tool suite
- [ ] Legacy `src/infrastructure/container.py` is only in `legacy/`

**Key Files:**

- `requirements.txt` — dependency cleanup
- `requirements-rag.txt` — RAG dependency update
- `README.md` — documentation update
- `config.md` — documentation update

---

## Task Dependency Graph

```
Task 1 (Archive) ─────┐
                       ├──→ Task 3 (Relocate Prompts)
Task 2 (OpenCode Init) ┤
                       ├──→ Task 4 (prompt-loader) ──┬──→ Task 7 (character-mgr) ──┐
                       │                              ├──→ Task 8 (setting-mgr)  ───┤
                       │                              ├──→ Task 9 (recap-manager) ──┤
                       │                              ├──→ Task 10 (outline-gen) ───┤
                       │                              └──→ Task 12 (critique)    ───┤
                       │                                                            │
                       ├──→ Task 5 (story-state) ──┬──→ Task 6 (savepoint-mgr) ─────┤
                       │                           ├──→ Task 13 (wiki tools) ───────┤
                       │                           └──→ Task 24 (ChromaDB RAG) ─────┤
                       │                                                            │
                       └──→ Task 11 (scene-writer) ←── Tasks 7,8,9 ────────────────┤
                                                                                    │
                                                    ┌── Task 13 ──→ Task 14 (wiki-snapshot) ←── Task 24
                                                    │           └──→ Task 15 (wiki-update)
                                                    │           └──→ Task 16 (wiki-lint)
                                                    │                                   │
                                                    ▼                                   ▼
                    Task 17 (Orchestrator) ←── Tasks 4-16 ────────────┐
                    Task 18 (Outline Planner) ←── Tasks 10,12 ────────┤
                    Task 19 (Scene Writer Agent) ←── Tasks 7-9,11,14 ─┤
                    Task 20 (Wiki Maintainer) ←── Tasks 15,16 ─────────┤
                    Task 21 (Commands) ←── Task 17 ────────────────────┤
                    Task 22 (Compaction Plugin) ←── Tasks 5,17 ────────┤
                    Task 23 (Skills: context/wiki) ←── Tasks 14,19,20 ─┤
                                                                       │
                    Task 24 (ChromaDB RAG) ←── Task 5 ─────────────────┤
                                                                       ▼
                    Task 25 (E2E Test) ←── Tasks 17-24
                                                  │
                                                  ▼
                    Task 26 (Cleanup) ←── Task 25
```

## Summary

| Phase | Tasks | Scope |
|-------|-------|-------|
| Phase 0 — Foundation | Tasks 1-3 | 3 small |
| Phase 1 — Core Tools | Tasks 4-12 | 9 tasks (2 large, 7 medium) |
| Phase 2 — Wiki Tools | Tasks 13-16 | 4 tasks (2 large, 2 medium) |
| Phase 3 — Agent Layer | Tasks 17-21 | 5 tasks (2 large, 3 medium) |
| Phase 4 — Integration | Tasks 22-26 | 5 tasks (1 large, 2 medium, 1 small, 1 small) |
| **Total** | **26 tasks** | **~7 large, ~14 medium, ~5 small** |
