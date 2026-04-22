# Story Orchestrator Agent

> The primary pipeline controller for AI-powered long-form story generation — coordinates ten primary phases plus a conditional prose-scrub pass from initial prompt through final manuscript polish.

## Overview

The story orchestrator is the first agent defined in the OpenCode agentic architecture migration. It encodes the full story generation lifecycle as a ten-phase pipeline, plus a conditional Phase 7.5 prose pass, delegating specialised creative tasks to subagents while using deterministic tools for file I/O, state management, and wiki operations.

The orchestrator operates in two modes:

- **Interactive mode** (default): Pauses at approval gates for human review and steering. The user can inspect outlines, character sheets, and settings before generation proceeds.
- **Batch mode** (`--batch`): Auto-proceeds through all approval gates for unattended generation runs.

## Pipeline Phases

The pipeline executes ten primary phases sequentially, with an additional conditional Phase 7.5 prose scrub inside the per-chapter loop. Phase 2.5 inserts a dedicated dramatic arc analysis pass after the outline is finalized and before the human approval gate. Each phase completes fully before the next begins, and key phases create savepoints for resume capability.

```
┌─────────┐   ┌─────────┐   ┌────────────────┐   ┌──────────┐   ┌───────────┐
│  Init   │──▶│ Outline │──▶│ Story Planner  │──▶│ Approval │──▶│ Wiki Init │
│ (1)     │   │ (2)     │   │ (2.5)          │   │ (3)      │   │ (4)       │
└─────────┘   └─────────┘   └────────────────┘   └──────────┘   └───────────┘
                                                                     │
                                                                     ▼
                                                      ┌───────────────────┐
                                                      │ Characters +      │
                                                      │ Settings (5)      │
                                                      └───────────────────┘
                                                                         │
      ┌────────────────────────────────────────────────────────────────┘
      ▼
┌─────────────────┐   ┌────────────────────────┐   ┌──────────┐   ┌────────────┐
│ Wiki Population │──▶│ Per-Chapter Loop (7)   │──▶│ Assembly │──▶│ Final Edit │
│ (6)             │   │ [1..wanted_chapters]   │   │ (8)      │   │ (9)        │
└─────────────────┘   └────────────────────────┘   └──────────┘   └────────────┘
```

| Phase | Name | Purpose | Savepoint |
|-------|------|---------|-----------|
| 1 | Init | Load prompt, read `config.md`, initialise story state | `init` |
| 2 | Outline | Generate story outline; optionally critique and revise | `outline_complete` |
| 2.5 | Narrative Arc Analysis | Dispatch `story-planner` to score the finalised outline's dramatic arc and synthesize an advisory assessment | `arc_analysis_complete` |
| 3 | Approval | Human review gate (interactive) or auto-proceed (batch) | — |
| 4 | Wiki Init | Create wiki directory structure and schema | — |
| 5 | Characters & Settings | Generate character and setting sheets via `character-sheet-generator` | `characters_complete`, `settings_complete` |
| 6 | Wiki Population | Populate wiki with entity pages from outline + sheets via `wiki-maintainer` | `wiki_populated` |
| 7 | Chapter Expansion + Per-Chapter Loop | Dispatch outline expansion once, then run scene gen → wiki update → recap → lint → quality evaluation → handoff generation for each chapter | `chapter_{N}_complete` |
| 7.5 | Prose Scrub | Run `prose-scrubber` for sentence and paragraph-level cleanup when enabled | `chapter_{N}_scrubbed` |
| 8 | Assembly | Combine all chapters into the assembled manuscript | `story_complete` |
| 9 | Final Edit | Run `final-editor` across assembled chapters when enabled | `final_edit_complete` |

### Phase 7 Structure

Phase 7 now has two layers:

- **Phase 7a** runs once before chapter drafting starts. The orchestrator dispatches `chapter-outline-expander`, which expands all chapter outlines in one dedicated pass and manages rolling continuity internally.
- **Per-chapter loop** then runs for each chapter from 1 to `wanted_chapters`.

After the one-time Phase 7a dispatch, each chapter passes through seven core sub-phases, plus the conditional prose scrub:

```
┌─────────────┐   ┌────────────────┐   ┌───────────┐   ┌───────────┐
│ Scene Gen   │──▶│ Wiki Update    │──▶│ Recap     │──▶│ Wiki Lint │
│ (7b)        │   │ (7c)           │   │ (7d)      │   │ (7e)      │
└─────────────┘   └────────────────┘   └───────────┘   └───────────┘
                                                              │
      ┌───────────────────────────────────────────────────────┘
      ▼
┌──────────────────────────────┐   ┌──────────────┐   ┌──────────────┐   ┌───────────────────┐
│ Quality Evaluation (7f)      │──▶│ Handoff      │──▶│ Prose Scrub  │──▶│ Chapter Savepoint │
│ via quality-reviewer         │   │ Gen (7g)     │   │ (7.5)        │   │ (7h)              │
└──────────────────────────────┘   └──────────────┘   └──────────────┘   └───────────────────┘
```

Chapters are generated sequentially because each chapter's wiki updates inform the next chapter's context.

Phase 7a no longer keeps `continuitySummary` inside the orchestrator's working memory. That state now lives inside `chapter-outline-expander`, which can also read the prior chapter's structured handoff artifact from story state.

Phase 7f dispatches the `quality-reviewer` subagent instead of running the critique/revision loop inline. The subagent owns scoring, refinement decisions, feedback generation, and revision for one chapter, then returns a structured result to the orchestrator. When `requires_post_processing` is `true`, the orchestrator re-runs Phases 7c, 7d, and 7e so the wiki, recap, and lint outputs reflect the final accepted chapter text.

Phase 7g runs after the chapter is accepted and any required post-processing is complete. The orchestrator loads `prompts/chapters/generate_handoff.md`, generates one structured JSON handoff artifact inline, and writes it to `story-state` at `chapters.{N}.handoff`. That artifact captures continuity state for the next chapter expansion pass: resolved beats, obligations, active tensions, timeline movement, and character deltas.

Phase 7.5 dispatches `prose-scrubber` only after the chapter has passed the quality gate. The scrubber operates at sentence and paragraph scope, writes the revised chapter text back to story state, and creates a `chapter_{N}_scrubbed` savepoint before the orchestrator records `chapter_{N}_complete`. Because the scrubber is constrained to prose-only edits, the orchestrator does not re-run wiki update, recap generation, or lint after this pass.

## Quality Gates

The orchestrator enforces outline quality directly and delegates chapter quality evaluation to the `quality-reviewer` subagent, which runs the Phase 7f critique/revision loop with `critique-runner` and `scene-writer`. When a quality gate fails after maximum revision attempts, the best-scoring version is accepted and the pipeline continues. The prose-scrub and final-edit passes are enhancement passes, not blocking gates.

| Gate | Config Key | Default Threshold | Max Revisions | Applied In |
|------|-----------|-------------------|---------------|------------|
| Outline quality | `generation.outline_quality` | 87 | `outline_max_revisions` (3) | Phase 2 |
| Chapter quality | `generation.chapter_quality` | 85 | `chapter_max_revisions` (3) | Phase 7f |

Phase 2.5 adds a second review surface before generation starts, but it is advisory rather than blocking. `story-planner` packages critic scores, arc-shape analysis, and a normalized verdict for the Phase 3 approval screen; the user decides whether to proceed or send the outline back through Phase 2.

See [Prose Quality Passes](./prose-quality-passes.md) for the non-gating polish layers that run after the chapter quality gate and after assembly.

## Wiki Lifecycle

The wiki follows a lifecycle synchronised with the pipeline:

| Phase | Wiki Interaction |
|-------|-----------------|
| Phase 4 | `wiki-init` creates directory structure and `_schema.md` |
| Phase 6 | `wiki-maintainer` subagent populates pages for all entities from outline + sheets |
| Phase 7a | `chapter-outline-expander` reads prior handoff state, expands all chapter outlines, and writes `chapters.{N}.expanded_outline` |
| Phase 7b | `wiki-snapshot` assembles token-budgeted context for each scene generation prompt |
| Phase 7c | `wiki-maintainer` subagent extracts and records new facts from the generated chapter |
| Phase 7e | `wiki-lint` checks chapter consistency against the wiki |
| Phase 7g | Orchestrator writes `chapters.{N}.handoff` for downstream continuity planning |
| Phase 7.5 | No wiki mutation; `prose-scrubber` is prose-only and must preserve facts |
| Phase 9 | No wiki mutation; `final-editor` polishes prose after assembly without changing entity state |

After Phase 6, the wiki is the **authoritative source of truth** for world state. Character sheets and setting sheets become historical inputs — the wiki supersedes them.

## Subagents

The orchestrator delegates specialised work to nine subagents:

| Subagent | Purpose | Invoked In | Status |
|----------|---------|------------|--------|
| `outline-planner` | Generate and refine the story outline | Phase 2 | Implemented (PR #64) |
| `story-planner` | Evaluate dramatic arc quality for the finalised outline and return an advisory assessment | Phase 2.5 | Implemented (PR #130) |
| `character-sheet-generator` | Generate and store all character and setting sheets | Phase 5 | Implemented |
| `chapter-outline-expander` | Expand all chapter outlines and manage rolling continuity state | Phase 7a | Implemented (PR #129) |
| `chapter-writer` | Manage per-chapter scene generation pipeline | Phase 7b | Implemented (PR #63) |
| `wiki-maintainer` | Maintain wiki pages — create, update, lint | Phases 6, 7c | Implemented (PR #65) |
| `quality-reviewer` | Run the Phase 7f critique/revision loop for a single chapter | Phase 7f | Implemented (PR #127) |
| `prose-scrubber` | Run the Phase 7.5 sentence/paragraph scrub pass for a single chapter | Phase 7.5 | Implemented (PR #128) |
| `final-editor` | Run the Phase 9 post-assembly voice, pacing, and coherence pass | Phase 9 | Implemented (PR #128) |

### story-planner

The `story-planner` subagent handles Phase 2.5 between outline completion and the human approval gate. It receives the story name and outline-quality threshold from the orchestrator, then:

1. Reads the finalised outline and `story_elements` from story state
2. Extracts the working genre label from `story_elements` for arc interpretation
3. Runs all six `outline_review/` critics through `critique-runner` in `outline` mode
4. Loads and applies three dedicated arc prompts from `prompts/outline_arc/`:
      - `arc_distribution` for chapter dramatic-weight analysis
      - `promise_payoff` for setup/payoff mapping
      - `arc_synthesis` for the final structured report
5. Saves the synthesized report at the `arc_analysis_complete` checkpoint
6. Returns `arc_assessment`, `overall_score`, `critic_scores`, and a normalized `verdict` (`strong`, `minor_concerns`, or `significant_issues`)

The agent is depth-1 by design: it calls tools only and never dispatches nested subagents. Its output is advisory only. The orchestrator surfaces the assessment during Phase 3, but batch mode still proceeds automatically and interactive mode leaves the final decision to the user.

### character-sheet-generator

The `character-sheet-generator` subagent handles Phase 5 — generating all character and setting sheets for the story. It receives the story name, character name list, setting name list, and unified story elements text from the orchestrator, then:

1. Generates a prose/markdown character sheet for each character using `prompt-loader` and `character-mgr`
2. Generates a prose/markdown setting sheet for each setting using `prompt-loader` and `setting-mgr`
3. Writes the processed name lists to story state via `story-state`
4. Creates savepoints (`characters_complete`, `settings_complete`) after each phase
5. Returns only compact name lists to the orchestrator — sheet bodies are not returned

The agent uses five tools: `prompt-loader`, `character-mgr`, `setting-mgr`, `story-state`, and `savepoint-mgr`. Sheet generation is contained entirely within this subagent; the orchestrator receives only a compact summary to keep context lean.

See the [agent definition](../../.opencode/agents/character-sheet-generator.md) for the full workflow, savepoint strategy, and generation prompt references.

### chapter-writer

The `chapter-writer` subagent handles Phase 7b — generating all scenes for a single chapter. It receives a chapter number and story name from the orchestrator, then:

1. Loads the chapter's expanded outline and parses scene definitions via `scene-writer`
2. Assembles token-budgeted context from the wiki via `wiki-snapshot` for each scene
3. Generates scenes sequentially (narrative flow depends on prior scene content)
4. Assembles all scenes into the completed chapter via `scene-writer`

The agent uses three skills:
- **scene-writing** — narrative structure, pacing, transitions, and scene type conventions
- **character-voice** — dialogue patterns, internal thought consistency, voice differentiation across characters
- **context-budgeting** — token budget strategy, three-stage retrieval pipeline reference, composite scoring formula, detail level allocation, and delta caching strategy

Named `chapter-writer` (not `scene-writer`) to avoid collision with the existing `scene-writer` tool. See the [agent definition](../../.opencode/agents/chapter-writer.md) for the full workflow, savepoint strategy, and error handling.

### chapter-outline-expander

The `chapter-outline-expander` subagent handles Phase 7a — the one-time outline expansion pass that runs before chapter drafting begins. It receives the story name, total chapter count, `expand_outline` flag, and optional model override, then:

1. Skips cleanly when outline expansion is disabled in config
2. Loops from chapter 1 to `wanted_chapters`, calling `outline-generator` with `expand-chapter`
3. Threads `continuitySummary` internally instead of keeping it in orchestrator memory
4. Reads `chapters.{N-1}.handoff` from story state when available and prepends that structured continuity state to the next expansion request
5. Writes each expanded outline to `chapters.{N}.expanded_outline` and records expansion progress savepoints

The agent calls tools only and never dispatches subagents, preserving the depth-1 rule. Its main output is a complete set of expanded chapter outlines plus persisted continuity state for downstream chapter generation. See the [feature doc](./chapter-outline-expander.md) and the [agent definition](../../.opencode/agents/chapter-outline-expander.md) for the full contract.

### outline-planner

The `outline-planner` subagent handles Phase 2 — transforming the raw story prompt into a structured, critiqued outline. It receives the story name, prompt text, and config values from the orchestrator, then executes a 5-phase pipeline:

1. **Prompt Analysis** — Calls `outline-generator` with `analyze-prompt` to run the multi-step analysis pipeline: understand prompt, generate 8 analysis chunks (`core_story_foundation`, `character_foundation`, `setting_foundation`, `conflict_stakes`, `plot_structure`, `theme_message`, `tone_style`, `world_rules_logic`), extract story start date, and extract base context
2. **Elements Synthesis** — Calls `outline-generator` with `generate-elements` to combine all 8 chunks into a unified `story_elements` savepoint
3. **Outline Generation** — Either chunked (`expand-chapter` in loops of `outline_chunk_size`) or monolithic (`generate-outline`), controlled by `use_chunked_outline_generation` config
4. **Critique & Refinement** (optional) — When `enable_outline_critique` is enabled, runs `critique-runner` critics against the outline and refines via `outline-generator` until the quality threshold (`outline_quality`, default 87) is met or `outline_critique_iterations` is exhausted
5. **Return** — Reports final outline, critique score, and iteration count to the orchestrator

The agent uses two skills:
- **story-pipeline** — overall pipeline context, phase definitions, and config settings
- **outline-structure** — outline JSON schemas, analysis chunk categories, savepoint naming conventions, quality criteria, and critic types

See the [agent definition](../../.opencode/agents/outline-planner.md) for the full workflow, savepoint strategy, and error handling.

### wiki-maintainer

The `wiki-maintainer` subagent handles Phase 6 (initial wiki population) and Phase 7c (post-chapter incremental updates). It operates in two modes:

- **Mode 1: Initial Population** (Phase 6) — Extracts all known entities from the outline, character sheets, and setting sheets. Creates wiki pages at `planned` confidence with L1/L2/L3 detail summaries and establishes cross-reference wikilinks between related entities.
- **Mode 2: Incremental Update** (Phase 7c) — After each assembled chapter, extracts new entities, state changes, events, aliases, and plot thread progression from the text. Creates or updates wiki pages at `verified` confidence, then runs `wiki-lint` consistency checks for that chapter.

The agent uses five tools: `wiki-read`, `wiki-update`, `wiki-lint`, `wiki-search`, and `story-state`. All wiki mutations are submitted as batch payloads for atomic execution with rollback on failure.

The agent uses two skills:
- **wiki-maintenance** — entity extraction rules, confidence taxonomy, structured output formats, detail level guidelines, and chapter boundary procedures
- **wiki-conventions** — page type schemas, YAML frontmatter specifications, wikilink conventions, and slug naming rules

Named `wiki-maintainer` to reflect its lifecycle responsibility — maintaining wiki state across the full generation pipeline, not just creating pages. Runs on a 7b model (`deepseek-r1-abliterated:7b`) for low overhead. See the [agent definition](../../.opencode/agents/wiki-maintainer.md) and [feature documentation](wiki-maintainer.md) for the full workflow, error handling, and entity type reference.

### quality-reviewer

The `quality-reviewer` subagent handles Phase 7f for one assembled chapter. It receives the story name, chapter number, full chapter text, and the chapter-quality config values from the orchestrator, then:

1. Runs `critique-runner` critics for the current chapter draft and parses the score
2. Checks acceptance against the configured quality threshold and the minimum/maximum revision rules
3. Generates revision feedback and calls `scene-writer` with `operation: revise` when another pass is required
4. Tracks the best score across iterations and saves quality revision checkpoints
5. Returns `accepted_chapter_text`, `best_score`, `revision_count`, and `requires_post_processing` to the orchestrator

The agent calls tools only and never dispatches subagents, preserving the depth-1 nesting rule introduced after the earlier nested-dispatch freeze. The orchestrator keeps ownership of downstream re-processing: when `requires_post_processing` is true, it re-runs the wiki update, recap generation, and wiki lint phases against the final accepted chapter.

See the [agent definition](../../.opencode/agents/quality-reviewer.md) for the full decision matrix, return contract, and savepoint naming.

### prose-scrubber

The `prose-scrubber` subagent handles the conditional Phase 7.5 cleanup for one chapter after the quality gate has accepted the chapter text. It receives the story name, chapter number, and full config, then:

1. Loads the shared `final-edit` skill for scope constraints and revision-budget rules
2. Reads the current chapter object from story state and extracts the active text-bearing field
3. Loads the `final_edit/prose_scrub` prompt and runs sentence/paragraph-level analysis using the `scrub_model` named model role when configured
4. Applies up to five targeted `scene-writer` revision calls for actionable issues such as adverb overuse, filter words, repetitive phrasing, and show-vs-tell drift
5. Writes the revised chapter object back to story state and records a `chapter_{N}_scrubbed` savepoint

The scrubber is tool-only and explicitly constrained to prose scope: no plot changes, no entity-fact changes, and no wholesale rewrites. See [Prose Quality Passes](./prose-quality-passes.md) and the [agent definition](../../.opencode/agents/prose-scrubber.md) for the full workflow.

### final-editor

The `final-editor` subagent handles the conditional Phase 9 manuscript polish after assembly. It receives the story name, the list of assembled chapter numbers, and full config, then:

1. Loads the shared `final-edit` skill for scope constraints, pass types, and revision budgets
2. Reads each chapter from story state and retrieves prior-chapter context via `rag-query`
3. Runs the `final_edit/voice_consistency_pass` prompt to detect voice, pacing, and cross-chapter coherence issues
4. Runs the `final_edit/prose_scrub` prompt for a second sentence-level cleanup pass on the assembled manuscript text
5. Applies targeted `scene-writer` revisions, writes each revised chapter back to story state, and creates `chapter_{N}_final_edited` savepoints plus a final `final_edit_complete` checkpoint

This pass runs after assembly, not instead of Phase 7f. It preserves story events and facts while smoothing chapter-to-chapter style and pacing. See [Prose Quality Passes](./prose-quality-passes.md) and the [agent definition](../../.opencode/agents/final-editor.md) for details.

## Commands

Users invoke the orchestrator through custom commands defined in `.opencode/commands/`. Four commands route directly to the story orchestrator agent:

| Command | Purpose |
|---------|---------|
| `/new-story <prompt-file>` | Initialize a new story and start the full pipeline from Phase 1 |
| `/continue [story-name]` | Resume generation from the most recent savepoint |
| `/regenerate chapter N \| scene C S` | Regenerate a chapter or scene with wiki rollback |
| `/savepoint [name]` | Create a manual savepoint at the current pipeline position |

Three additional informational commands (`/status`, `/settings`, `/wiki`) use the default agent and do not invoke the orchestrator. See [Custom Commands](./custom-commands.md) for full documentation of all seven commands.

## Tools

The orchestrator uses 16 deterministic tools for file I/O, state management, assembly, and wiki operations. See [Tools Reference](../tools.md) for the shared tool architecture and current reference coverage.

| Tool | Purpose |
|------|---------|
| `prompt-loader` | Load and render prompt templates |
| `story-state` | Read/write story state |
| `savepoint-mgr` | Create/restore/list savepoints |
| `character-mgr` | Generate and manage character sheets |
| `setting-mgr` | Generate and manage setting sheets |
| `recap-manager` | Generate and manage chapter recaps |
| `outline-generator` | Generate and expand story outlines |
| `scene-writer` | Generate individual scenes |
| `critique-runner` | Evaluate content quality and produce scores |
| `story-assembler` | Assemble completed chapters into final story markdown |
| `wiki-init` | Initialise wiki directory structure |
| `wiki-read` | Read wiki pages by slug or type |
| `wiki-search` | Semantic search across wiki pages |
| `wiki-snapshot` | Assemble token-budgeted context for generation |
| `wiki-update` | Create or update wiki pages |
| `wiki-lint` | Run consistency checks on wiki vs chapter content |

## Savepoint Strategy

Savepoints capture the full pipeline state at key milestones, enabling resume after interruption. Names use the format `{phase_descriptor}` — lowercase, underscore-separated, no zero-padding on chapter numbers.

A savepoint contains:
- Full story state JSON (outline, chapter content, metadata)
- Wiki directory snapshot
- Character and setting sheets
- Generated recaps
- Chapter handoff artifacts stored under `chapters.{N}.handoff`
- Pipeline position (which phase/step completed)

### Resume Mapping

| Savepoint | Resumes At |
|-----------|-----------|
| `init` | Phase 2 (Outline) |
| `outline_complete` | Phase 3 (Approval) |
| `characters_complete` | Phase 6 (Wiki Population) |
| `settings_complete` | Phase 6 (Wiki Population) |
| `wiki_populated` | Phase 7, Chapter 1 |
| `chapter_{N}_complete` | Phase 7, Chapter N+1 (or Phase 8 if last chapter) |
| `story_complete` | Phase 9 (Final Edit) when enabled; otherwise pipeline complete |
| `final_edit_complete` | Pipeline complete |

## Configuration

All pipeline settings are read from `config.md` YAML frontmatter under the `generation` key. The orchestrator never hardcodes these values.

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `outline_quality` | int | 87 | Minimum critique score to accept outline |
| `chapter_quality` | int | 85 | Minimum critique score to accept chapter |
| `wanted_chapters` | int | 25 | Number of chapters to generate |
| `outline_min_revisions` | int | 0 | Minimum outline revision passes before acceptance |
| `outline_max_revisions` | int | 3 | Maximum outline revision attempts |
| `chapter_min_revisions` | int | 0 | Minimum chapter revision passes before acceptance |
| `chapter_max_revisions` | int | 3 | Maximum chapter revision attempts |
| `enable_outline_critique` | bool | false | Run outline critique loop |
| `outline_critique_iterations` | int | 3 | Critique passes on outline |
| `enable_chapter_revisions` | bool | true | Run chapter revision loop |
| `expand_outline` | bool | true | Expand outline into scene-level detail |
| `scene_generation_pipeline` | bool | true | Use scene-by-scene generation |
| `use_chunked_outline_generation` | bool | true | Generate outline in chunks |
| `outline_chunk_size` | int | 10 | Chapters per outline chunk |
| `enable_scrubbing` | bool | true | Run `prose-scrubber` after Phase 7f |
| `enable_final_edit` | bool | false | Run `final-editor` after assembly |
| `stream` | bool | true | Stream model output during generation |
| `debug` | bool | true | Emit additional pipeline diagnostics |
| `strategy` | string | `outline-chapter` | Story generation strategy identifier |

Named model roles live under `config.models`. `prose-scrubber` reads `scrub_model` when configured; otherwise it falls back to the default model binding.

## Story Pipeline Skill

The `story-pipeline` skill (`.opencode/skills/story-pipeline/SKILL.md`) provides a detailed reference for the pipeline, including:

- ASCII flow diagrams for overall pipeline and per-chapter loop
- Phase definitions with inputs, outputs, tools, and savepoints
- Quality gate logic and revision loop pseudocode
- Wiki update lifecycle details
- Interactive vs batch decision points
- Savepoint strategy and resume instructions
- Config settings reference table
- Error recovery guidelines

The skill is automatically available to the story-orchestrator agent and can be referenced by other agents that need to understand the pipeline sequence.

## Context Budgeting Skill

The `context-budgeting` skill (`.opencode/skills/context-budgeting/SKILL.md`) provides a detailed reference for managing the 65536-token context window, including:

- Token budget allocation table (system overhead, story context, prompt template, input, generation output)
- Five concrete context management rules (wiki-snapshot usage, character loading limits, synopsis preferences, outline scoping, stateless subagent design)
- Three-stage retrieval pipeline reference: hybrid multi-tier retrieval (entity matching → metadata query → semantic search → wikilink traversal), composite scoring formula, detail level selection with priority tiers, and structured context assembly
- Scene-type adaptation rules (dialogue-heavy, action, first-appearance)
- Delta caching strategy for consecutive scenes within a chapter

The skill is automatically available to the `story-orchestrator` and `chapter-writer` agents. It encodes the strategies defined in [ADR 002](../planning/adr/002-context-window-budget-strategy.md) and [ADR 005](../planning/adr/005-hybrid-wiki-context-retrieval-pipeline.md).

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| Tool failure | Retry once; on second failure, halt with diagnostic |
| Subagent failure | Retry delegation once; on second failure, halt |
| Quality gate exhaustion | Accept best-scoring version, log warning, proceed |
| Wiki lint findings | Advisory — logged and included in quality evaluation context |
| Crash recovery | Restore latest savepoint via `savepoint-mgr`; resume from next phase |

## Key Files

- `.opencode/agents/story-orchestrator.md` — Agent definition and phase sequencing
- `.opencode/agents/quality-reviewer.md` — Phase 7f chapter quality-review subagent definition
- `.opencode/agents/prose-scrubber.md` — Phase 7.5 prose scrub subagent definition
- `.opencode/agents/final-editor.md` — Phase 9 manuscript polish subagent definition
- `.opencode/agents/chapter-writer.md` — Phase 7b chapter writer subagent definition
- `.opencode/skills/story-pipeline/SKILL.md` — Pipeline skill reference
- `.opencode/skills/final-edit/SKILL.md` — Shared prose-editing constraints and revision-budget rules
- `.opencode/skills/context-budgeting/SKILL.md` — Context budgeting skill reference
- `prompts/final_edit/prose_scrub.md` — Sentence and paragraph-level scrub analysis prompt
- `prompts/final_edit/voice_consistency_pass.md` — Voice, pacing, and cross-chapter coherence prompt
- `opencode.json` — Agent registration with model binding and skill references

## Related

- [Tools Reference](../tools.md) — Shared tool architecture and reference coverage
- [Prose Quality Passes](./prose-quality-passes.md) — Conditional prose-scrub and final-edit layers, config flags, and scope constraints
- [Architecture Notes](../../.github/notes/architecture.md) — System architecture overview
- [ADR 001: Hybrid Agent-Tool Architecture](../planning/adr/001-hybrid-agent-tool-architecture.md) — Establishes agent-tool separation
- [ADR 004: Progressive Wiki Memory System](../planning/adr/004-progressive-wiki-memory-system.md) — Wiki page format and lifecycle
- [ADR 005: Hybrid Wiki Context Retrieval Pipeline](../planning/adr/005-hybrid-wiki-context-retrieval-pipeline.md) — Three-stage context retrieval used by `wiki-snapshot`
- [Migration Tasks](../planning/opencode-migration/tasks.md) — Task 17 (this feature), plus Tasks 18–20 for subagents
- Issue #20 — Initial implementation
