---
name: story-pipeline
description: Story generation pipeline — phases, quality gates, savepoints, wiki lifecycle, and config reference.
version: 1.0.0
---

# Story Pipeline Skill

Reference guide for the full story generation pipeline orchestrated by the `story-orchestrator` agent. Use this skill when implementing, debugging, or extending any part of the pipeline.

## Pipeline Overview

The story generation pipeline transforms a story prompt into a complete novel-length manuscript through nine primary phases plus the conditional Phase 7.5 prose scrub pass. Each phase produces concrete artifacts, creates savepoints for resume capability, and enforces quality gates where configured.

```
┌─────────┐   ┌─────────┐   ┌──────────┐   ┌───────────┐   ┌───────────────────┐
│  Init   │──▶│ Outline │──▶│ Approval │──▶│ Wiki Init │──▶│ Characters +      │
│ (1)     │   │ (2)     │   │ (3)      │   │ (4)       │   │ Settings (5)      │
└─────────┘   └─────────┘   └──────────┘   └───────────┘   └───────────────────┘
                                                 │
    ┌────────────────────────────────────────────────────────────────┘
    ▼
┌─────────────────┐   ┌────────────────────────┐   ┌──────────┐   ┌────────────┐
│ Wiki Population │──▶│ Per-Chapter Loop (7)   │──▶│ Assembly │──▶│ Final Edit │
│ (6)             │   │ [1..wanted_chapters]   │   │ (8)      │   │ (9)        │
└─────────────────┘   └────────────────────────┘   └──────────┘   └────────────┘
```

### Per-Chapter Loop Detail

```
┌──────────────┐   ┌─────────────┐   ┌────────────────┐   ┌───────────┐
│ Expand       │──▶│ Scene Gen   │──▶│ Wiki Update    │──▶│ Recap     │
│ Outline (7a) │   │ (7b)        │   │ (7c)           │   │ (7d)      │
└──────────────┘   └─────────────┘   └────────────────┘   └───────────┘
                                                                │
      ┌─────────────────────────────────────────────────────────┘
      ▼
┌───────────────┐   ┌──────────────────────────────┐   ┌──────────────┐   ┌────────────────────┐
│ Consistency   │──▶│ Quality Eval + Revision Loop │──▶│ Prose Scrub  │──▶│ Chapter Savepoint  │
│ Check (7e)    │   │ (7f)                         │   │ (7.5)        │   │ (7g)               │
└───────────────┘   └──────────────────────────────┘   └──────────────┘   └────────────────────┘
```

---

## Phase Definitions

### Phase 1: Init

| Attribute | Value |
|-----------|-------|
| **Purpose** | Load prompt, read config, initialise story state |
| **Tools** | `prompt-loader`, `story-state`, `savepoint-mgr` |
| **Inputs** | Story prompt file path, `config.yml` |
| **Outputs** | Initialised story state with config values |
| **Savepoint** | `init` |

### Phase 2: Outline

| Attribute | Value |
|-----------|-------|
| **Purpose** | Generate full story outline; optionally critique and revise |
| **Tools** | `outline-generator`, `critique-runner`, `story-state`, `savepoint-mgr` |
| **Subagent** | `outline-planner` |
| **Inputs** | Story prompt, config (chunked generation settings) |
| **Outputs** | Finalised outline stored in story state |
| **Savepoint** | `outline_complete` |

Key behaviours:
- If `use_chunked_outline_generation` is true, generate in batches of `outline_chunk_size` chapters
- If `enable_outline_critique` is true, run critique loop up to `outline_critique_iterations` passes
- Revise up to `outline_max_revisions` times if score < `outline_quality`

### Phase 2.5: Narrative Arc Analysis

| Attribute | Value |
|-----------|-------|
| **Purpose** | Evaluate dramatic arc quality of the finalised outline before human review |
| **Subagent** | `story-planner` |
| **Inputs** | Finalised outline and story elements from story state |
| **Outputs** | Structured arc assessment stored in story state (`arc_assessment` field) |
| **Savepoint** | `arc_analysis_complete` |

Key behaviours:
- Advisory only — verdict never blocks the pipeline
- Runs 6 outline critics via `critique-runner` plus two arc-specific prompt analyses
- Arc assessment is presented alongside the outline at Phase 3 approval

### Phase 3: Approval

| Attribute | Value |
|-----------|-------|
| **Purpose** | Human review gate for the outline |
| **Tools** | None (agent interaction) |
| **Inputs** | Finalised outline |
| **Outputs** | Approval signal or revision feedback |
| **Savepoint** | None (outline re-enters Phase 2 if rejected) |

- **Interactive mode:** Pause and present outline for review. User may approve or request changes.
- **Batch mode:** Auto-proceed without pausing.

### Phase 4: Wiki Init

| Attribute | Value |
|-----------|-------|
| **Purpose** | Create wiki directory structure and schema |
| **Tools** | `wiki-init` |
| **Inputs** | Story name from story state |
| **Outputs** | Empty wiki with `_schema.md` and directory structure |
| **Savepoint** | None (lightweight, no state to preserve) |

### Phase 5: Characters & Settings

| Attribute | Value |
|-----------|-------|
| **Purpose** | Generate character and setting sheets for all entities in the outline |
| **Subagent** | `character-sheet-generator` |
| **Inputs** | Character list, setting list, and unified story elements from story state |
| **Outputs** | Character sheet files, setting sheet files, references stored in story state |
| **Savepoints** | `characters_complete`, `settings_complete` |

### Phase 6: Wiki Population

| Attribute | Value |
|-----------|-------|
| **Purpose** | Populate wiki with entity pages from outline + character/setting sheets |
| **Tools** | `wiki-update`, `wiki-read` |
| **Subagent** | `wiki-maintainer` |
| **Inputs** | Outline, character sheets, setting sheets |
| **Outputs** | Wiki pages for characters, locations, plot threads, world rules, timeline |
| **Savepoint** | `wiki_populated` |

Entity types created during population: characters, locations, events, factions, items, plot threads, timelines, world rules, themes, relationships.

### Phase 7: Chapter Expansion + Per-Chapter Loop

Phase 7 begins with a single delegated outline-expansion pass, then executes the remaining sub-phases per chapter from 1 to `wanted_chapters`.

| Sub-phase | Purpose | Tools / Subagents |
|-----------|---------|-------------------|
| **7a** Expand outline | Delegate full chapter-outline expansion loop and continuitySummary threading | `chapter-outline-expander` subagent |
| **7b** Scene generation | `scene_generation_pipeline: true`: generate scenes sequentially with wiki context; `scene_generation_pipeline: false`: generate full chapter in one LLM call | `chapter-writer` + `wiki-snapshot` (`scene_generation_pipeline: true`); `scene-writer` (`generate-chapter`) (`scene_generation_pipeline: false`) |
| **7c** Wiki update | Record new facts, state changes, events | `wiki-maintainer` subagent |
| **7d** Recap | Generate chapter recap | `recap-manager` |
| **7e** Consistency check | Check chapter consistency with three-layer analysis | `consistency-checker` subagent (three-layer: wiki-lint + semantic + RAG) |
| **7f** Quality eval | Critique + revision loop | `critique-runner` |
| **7g** Handoff artifact | Generate structured per-chapter continuity handoff in story state | `story-assembler` |
| **7.5** Prose scrub | Sentence and paragraph-level prose cleanup | `prose-scrubber` subagent |
| **7h** Savepoint | Persist chapter completion | `savepoint-mgr` |

### Phase 8: Assembly

| Attribute | Value |
|-----------|-------|
| **Purpose** | Combine all chapters into final manuscript |
| **Tools** | `story-state`, `savepoint-mgr` |
| **Inputs** | All completed chapters from story state |
| **Outputs** | Final story file in configured output directory |
| **Savepoint** | `story_complete` |

### Phase 9: Final Edit

| Attribute | Value |
|-----------|-------|
| **Purpose** | Run post-assembly chapter-by-chapter prose polish for voice, pacing, and cross-chapter coherence |
| **Subagent** | `final-editor` |
| **Inputs** | Assembled chapter numbers, chapter text in story state, config |
| **Outputs** | Revised chapter text entries and final edit summary |
| **Savepoint** | `final_edit_complete` |

---

## Subagents

The pipeline uses ten subagents for specialised creative work. The `story-orchestrator` dispatches these by name via OpenCode delegation.

| Subagent | Purpose | Invoked In |
|----------|---------|------------|
| `outline-planner` | Generate and refine the story outline | Phase 2 |
| `story-planner` | Evaluate dramatic arc quality for the finalised outline — narrative arc analysis gate | Phase 2.5 |
| `character-sheet-generator` | Generate and store all character and setting sheets | Phase 5 |
| `chapter-outline-expander` | Expands all chapter outlines (Phase 7a); manages continuitySummary threading | Phase 7a |
| `chapter-writer` | Manage per-chapter scene generation pipeline | Phase 7b |
| `wiki-maintainer` | Maintain the wiki knowledge base — create, update, lint pages | Phases 6, 7c |
| `consistency-checker` | Run the Phase 7e three-layer consistency analysis (wiki-lint + semantic + RAG) | Phase 7e |
| `quality-reviewer` | Run the Phase 7f critique/revision loop for a single chapter | Phase 7f |
| `prose-scrubber` | Run the Phase 7.5 sentence/paragraph scrub pass for a single chapter | Phase 7.5 |
| `final-editor` | Run the Phase 9 post-assembly voice, pacing, and coherence pass | Phase 9 |

**These are the only ten subagents the orchestrator may dispatch: `outline-planner`, `story-planner`, `character-sheet-generator`, `chapter-outline-expander`, `chapter-writer`, `wiki-maintainer`, `consistency-checker`, `quality-reviewer`, `prose-scrubber`, and `final-editor`.** Do not dispatch built-in or external agents for any reason outside the pipeline phases above.

---

## Savepoint Ownership

**The orchestrator owns the savepoint lifecycle. Subagents must never call `savepoint-mgr` directly, with the documented exceptions below.**

- Savepoints are checkpoints created by `story-orchestrator` at the boundary of each phase — not by subagents during their internal work.
- When a subagent completes its delegated work, it writes results to `story-state` (or produces handoff artifacts) and returns to the orchestrator. The orchestrator then creates the savepoint after confirming results are stored.
- **Why this matters:** If a subagent creates its own savepoint and the orchestrator also creates one at the same step name, the orchestrator's write silently overwrites the subagent's richer payload (`savepoint-mgr` overwrites existing entries by default). A pipeline resumed from that savepoint recovers a degraded snapshot.
- **Correct pattern:** `story-orchestrator` Phase 2.5 creates `arc_analysis_complete` with the full arc payload after `story-planner` returns. `story-planner` writes only to `story-state` — it never calls `savepoint-mgr`.

### Documented exceptions

The following subagents own specific savepoints because they perform per-entity work in a loop and the orchestrator has no equivalent re-entry point:

| Subagent | Owned savepoints | Rationale |
|----------|-------------------|-----------|
| `character-sheet-generator` | `characters_complete`, `settings_complete` | Subagent loops over the full character/setting list and is the only context that knows when the loop has finished. The orchestrator must NOT also create these. |
| `chapter-outline-expander` | `outlines_expanded` (auto-written by `outline-generator expand-chapter` on the final chapter) | Subagent owns the full Phase 7a per-chapter expand loop and is the only context that knows when every chapter has been expanded. The orchestrator must NOT also create `outlines_expanded`. |

When adding a new exception: document it in this table, ensure the orchestrator does NOT create the same savepoint, and add the savepoint to the canonical phase order in `src/tools/savepoint_manager.py`'s `CANONICAL_PHASES` list.

---

## Quality Gates

### Thresholds

| Gate | Config Key | Default | Max Revisions Key | Default |
|------|-----------|---------|-------------------|---------|
| Outline quality | `generation.outline_quality` | 87 | `generation.outline_max_revisions` | 3 |
| Chapter quality | `generation.chapter_quality` | 85 | `generation.chapter_max_revisions` | 3 |

### Critique Iterations

| Setting | Config Key | Default |
|---------|-----------|---------|
| Outline critique enabled | `generation.enable_outline_critique` | false |
| Outline critique iterations | `generation.outline_critique_iterations` | 3 |
| Chapter revisions enabled | `generation.enable_chapter_revisions` | true |

### Revision Loop Logic

```
score = critique_runner(content)
revision_count = 0

while score < threshold AND revision_count < max_revisions:
    content = revise(content, critique_feedback)
    score = critique_runner(content)
    revision_count += 1

accept(content)  # best available version
```

If max revisions are exhausted without meeting the threshold, accept the best scoring version and log a warning. Never block the pipeline indefinitely.

---

## Wiki Update Cycle

The wiki follows a lifecycle synchronized with the pipeline phases:

```
Phase 4: wiki-init
    └─▶ Creates directory structure, _schema.md

Phase 6: wiki-maintainer (initial population)
    └─▶ Creates pages for all entities from outline + character/setting sheets
    └─▶ Generates L1/L2/L3 detail levels per page
    └─▶ Establishes wikilinks between related entities

Phase 7b: wiki-snapshot (pre-scene context)
    └─▶ Assembles token-budgeted context for each scene generation prompt
    └─▶ Uses hybrid retrieval: entity matching → metadata query → semantic search → wikilink traversal

Phase 7c: wiki-maintainer (post-chapter updates)
    └─▶ Extracts new entities, state changes, relationship developments
    └─▶ Updates existing pages, creates new ones
    └─▶ Updates timeline and plot thread progression

Phase 7e: consistency-checker (post-chapter consistency check)
    └─▶ Runs three-layer analysis: wiki-lint, semantic wiki search, and cross-chapter RAG review
    └─▶ Results feed into quality evaluation (advisory, not blocking)
```

After Phase 6, the wiki is the **authoritative source of truth** for world state. Character sheets and setting sheets become historical inputs — the wiki supersedes them.

---

## Interactive vs Batch Decision Points

| Phase | Interactive | Batch |
|-------|------------|-------|
| Phase 3 (Approval) | Pause — present outline, wait for approval or revision request | Auto-proceed |
| Phase 7f (Quality eval) | May pause to show failing scores and ask whether to continue | Auto-accept best version after max revisions |

All other phases execute identically in both modes.

---

## Savepoint Strategy

### Naming Convention

Format: `{phase_descriptor}` — lowercase, underscore-separated, descriptive.

| Phase | Savepoint Name | Example |
|-------|---------------|---------|
| 1 | `init` | `init` |
| 2 | `outline_complete` | `outline_complete` |
| 5 | `characters_complete`, `settings_complete` | `characters_complete` |
| 6 | `wiki_populated` | `wiki_populated` |
| 7 (per chapter) | `chapter_{N}_complete` | `chapter_1_complete`, `chapter_25_complete` |
| 8 | `story_complete` | `story_complete` |
| 9 | `final_edit_complete` | `final_edit_complete` |

No zero-padding on chapter numbers. The savepoint includes full pipeline state: story state, wiki state, all generated artifacts up to that point.

### What a Savepoint Contains

- Full story state JSON (outline, chapter content, metadata)
- Wiki directory snapshot
- Character and setting sheets
- Generated recaps
- Pipeline position (which phase/step completed)

---

## Config Settings Reference

All settings are read from `config.yml` under the `generation` key.

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `outline_quality` | int | 87 | Minimum critique score to accept outline |
| `chapter_quality` | int | 85 | Minimum critique score to accept chapter |
| `wanted_chapters` | int | 25 | Number of chapters to generate |
| `outline_min_revisions` | int | 0 | Minimum outline revision passes |
| `outline_max_revisions` | int | 3 | Maximum outline revision attempts |
| `chapter_min_revisions` | int | 0 | Minimum chapter revision passes |
| `chapter_max_revisions` | int | 3 | Maximum chapter revision attempts |
| `enable_outline_critique` | bool | false | Whether to run outline critique loop |
| `outline_critique_iterations` | int | 3 | Number of critique passes on outline |
| `enable_chapter_revisions` | bool | true | Whether to run chapter revision loop |
| `expand_outline` | bool | true | Whether to expand outline into scene-level detail |
| `scene_generation_pipeline` | bool | true | Whether to use scene-by-scene generation |
| `use_chunked_outline_generation` | bool | true | Whether to generate outline in chunks |
| `outline_chunk_size` | int | 10 | Number of chapters per outline chunk |
| `enable_final_edit` | bool | false | Whether to run a final editing pass |
| `enable_scrubbing` | bool | true | Whether to run the Phase 7.5 prose-scrubber pass (adverbs, filter words, repetition, show-vs-tell) |
| `stream` | bool | true | Whether to stream LLM output |
| `debug` | bool | true | Whether to enable debug logging |
| `strategy` | string | "outline-chapter" | Generation strategy identifier |

---

## Resume from Savepoint

To resume a story generation run after interruption:

1. List available savepoints: `savepoint-mgr` (operation: `list`)
2. Identify the latest savepoint (or a specific one to resume from)
3. Load: `savepoint-mgr` (operation: `load`, step: `<savepoint-name>`)
4. The story-orchestrator reads the restored story state to determine the last completed phase
5. Execution resumes from the **next** phase after the savepoint

**Resume mapping:**

| Savepoint | Resumes At |
|-----------|-----------|
| `init` | Phase 2 (Outline) |
| `outline_complete` | Phase 3 (Approval) |
| `characters_complete` | Phase 5 (Characters & Settings, settings portion) |
| `settings_complete` | Phase 6 (Wiki Population) |
| `wiki_populated` | Phase 7, Chapter 1 |
| `chapter_{N}_complete` | Phase 7, Chapter N+1 (or Phase 8 if N == wanted_chapters) |
| `story_complete` | Phase 9 (Final Edit) when `enable_final_edit: true`; otherwise pipeline complete |
| `final_edit_complete` | Pipeline complete — final edit already applied |

---

## Error Recovery Guidelines

### Tool Failures

- Retry the tool call once with the same arguments
- If the retry fails, log full error context (tool name, arguments, error message, phase, step)
- Halt the pipeline — do not skip phases or produce partial output silently

### Subagent Failures

- Retry the delegation once
- If the subagent produces invalid output on retry, halt with diagnostics
- Never substitute orchestrator-generated content for subagent output — the subagent exists because the task requires specialised handling

### Quality Gate Exhaustion

- Accept the best-scoring version produced during the revision loop
- Log a warning: include the target threshold, best achieved score, and number of attempts
- Proceed to the next phase — do not loop indefinitely

### Wiki Lint Findings

- Wiki lint results are **advisory**, not blocking
- Log findings and include them as additional context for the quality evaluation critique
- Critical contradictions should be flagged prominently but still do not halt the pipeline
- The wiki-maintainer can be re-invoked to attempt corrections if contradictions are severe

### Crash Recovery

- On any unhandled error, the latest savepoint preserves all prior work
- Resume instructions are in the "Resume from Savepoint" section above
- If the crash occurred mid-phase (between savepoints), the current phase's partial work is lost and must be regenerated from the last savepoint
