---
name: story-pipeline
description: Story generation pipeline — phases, quality gates, savepoints, wiki lifecycle, and config reference.
version: 1.0.0
---

# Story Pipeline Skill

Reference guide for the full story generation pipeline orchestrated by the `story-orchestrator` agent. Use this skill when implementing, debugging, or extending any part of the pipeline.

## Pipeline Overview

The story generation pipeline transforms a story prompt into a complete novel-length manuscript through nine sequential phases. Each phase produces concrete artifacts, creates savepoints for resume capability, and enforces quality gates where configured.

```
┌─────────┐   ┌─────────┐   ┌──────────┐   ┌───────────┐   ┌────────────┐
│  Init   │──▶│ Outline │──▶│ Approval │──▶│ Wiki Init │──▶│ Characters │
│ (1)     │   │ (2)     │   │ (3)      │   │ (4)       │   │ (5)        │
└─────────┘   └─────────┘   └──────────┘   └───────────┘   └────────────┘
                                                                  │
      ┌───────────────────────────────────────────────────────────┘
      ▼
┌──────────┐   ┌─────────────────┐   ┌────────────────────────┐   ┌──────────┐
│ Settings │──▶│ Wiki Population │──▶│ Per-Chapter Loop (8)   │──▶│ Assembly │
│ (6)      │   │ (7)             │   │ [1..wanted_chapters]   │   │ (9)      │
└──────────┘   └─────────────────┘   └────────────────────────┘   └──────────┘
```

### Per-Chapter Loop Detail

```
┌──────────────┐   ┌─────────────┐   ┌────────────────┐   ┌───────────┐
│ Expand       │──▶│ Scene Gen   │──▶│ Wiki Update    │──▶│ Recap     │
│ Outline (8a) │   │ (8b)        │   │ (8c)           │   │ (8d)      │
└──────────────┘   └─────────────┘   └────────────────┘   └───────────┘
                                                                │
      ┌─────────────────────────────────────────────────────────┘
      ▼
┌───────────┐   ┌──────────────────────────────┐   ┌────────────────────┐
│ Wiki Lint │──▶│ Quality Eval + Revision Loop │──▶│ Chapter Savepoint  │
│ (8e)      │   │ (8f)                         │   │ (8g)               │
└───────────┘   └──────────────────────────────┘   └────────────────────┘
```

---

## Phase Definitions

### Phase 1: Init

| Attribute | Value |
|-----------|-------|
| **Purpose** | Load prompt, read config, initialise story state |
| **Tools** | `prompt-loader`, `story-state`, `savepoint-mgr` |
| **Inputs** | Story prompt file path, `config.md` |
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

### Phase 5: Characters

| Attribute | Value |
|-----------|-------|
| **Purpose** | Generate character sheets for all outline characters |
| **Tools** | `character-mgr`, `story-state`, `savepoint-mgr` |
| **Inputs** | Character list from outline |
| **Outputs** | Character sheet files, references stored in story state |
| **Savepoint** | `characters_complete` |

### Phase 6: Settings

| Attribute | Value |
|-----------|-------|
| **Purpose** | Generate setting sheets for all outline locations |
| **Tools** | `setting-mgr`, `story-state`, `savepoint-mgr` |
| **Inputs** | Location list from outline |
| **Outputs** | Setting sheet files, references stored in story state |
| **Savepoint** | `settings_complete` |

### Phase 7: Wiki Population

| Attribute | Value |
|-----------|-------|
| **Purpose** | Populate wiki with entity pages from outline + character/setting sheets |
| **Tools** | `wiki-update`, `wiki-read` |
| **Subagent** | `wiki-maintainer` |
| **Inputs** | Outline, character sheets, setting sheets |
| **Outputs** | Wiki pages for characters, locations, plot threads, world rules, timeline |
| **Savepoint** | `wiki_populated` |

Entity types created during population: characters, locations, events, factions, items, plot threads, timelines, world rules, themes, relationships.

### Phase 8: Per-Chapter Loop

Executes for each chapter from 1 to `wanted_chapters`.

| Sub-phase | Purpose | Tools / Subagents |
|-----------|---------|-------------------|
| **8a** Expand outline | Break chapter outline into scene-level detail | `outline-generator`, `story-state` |
| **8b** Scene generation | Generate scenes sequentially with wiki context | `chapter-writer` subagent, `wiki-snapshot` |
| **8c** Wiki update | Record new facts, state changes, events | `wiki-maintainer` subagent |
| **8d** Recap | Generate chapter recap | `recap-manager` |
| **8e** Wiki lint | Check chapter consistency against wiki | `wiki-lint` |
| **8f** Quality eval | Critique + revision loop | `critique-runner` |
| **8g** Savepoint | Persist chapter completion | `savepoint-mgr` |

### Phase 9: Assembly

| Attribute | Value |
|-----------|-------|
| **Purpose** | Combine all chapters into final manuscript |
| **Tools** | `story-state`, `savepoint-mgr` |
| **Inputs** | All completed chapters from story state |
| **Outputs** | Final story file in configured output directory |
| **Savepoint** | `story_complete` |

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

Phase 7: wiki-maintainer (initial population)
    └─▶ Creates pages for all entities from outline + character/setting sheets
    └─▶ Generates L1/L2/L3 detail levels per page
    └─▶ Establishes wikilinks between related entities

Phase 8b: wiki-snapshot (pre-scene context)
    └─▶ Assembles token-budgeted context for each scene generation prompt
    └─▶ Uses hybrid retrieval: entity matching → metadata query → semantic search → wikilink traversal

Phase 8c: wiki-maintainer (post-chapter updates)
    └─▶ Extracts new entities, state changes, relationship developments
    └─▶ Updates existing pages, creates new ones
    └─▶ Updates timeline and plot thread progression

Phase 8e: wiki-lint (post-chapter consistency check)
    └─▶ Detects contradictions, timeline issues, character drift
    └─▶ Results feed into quality evaluation (advisory, not blocking)
```

After Phase 7, the wiki is the **authoritative source of truth** for world state. Character sheets and setting sheets become historical inputs — the wiki supersedes them.

---

## Interactive vs Batch Decision Points

| Phase | Interactive | Batch |
|-------|------------|-------|
| Phase 3 (Approval) | Pause — present outline, wait for approval or revision request | Auto-proceed |
| Phase 8f (Quality eval) | May pause to show failing scores and ask whether to continue | Auto-accept best version after max revisions |

All other phases execute identically in both modes.

---

## Savepoint Strategy

### Naming Convention

Format: `{phase_descriptor}` — lowercase, underscore-separated, descriptive.

| Phase | Savepoint Name | Example |
|-------|---------------|---------|
| 1 | `init` | `init` |
| 2 | `outline_complete` | `outline_complete` |
| 5 | `characters_complete` | `characters_complete` |
| 6 | `settings_complete` | `settings_complete` |
| 7 | `wiki_populated` | `wiki_populated` |
| 8 (per chapter) | `chapter_{N}_complete` | `chapter_1_complete`, `chapter_25_complete` |
| 9 | `story_complete` | `story_complete` |

No zero-padding on chapter numbers. The savepoint includes full pipeline state: story state, wiki state, all generated artifacts up to that point.

### What a Savepoint Contains

- Full story state JSON (outline, chapter content, metadata)
- Wiki directory snapshot
- Character and setting sheets
- Generated recaps
- Pipeline position (which phase/step completed)

---

## Config Settings Reference

All settings are read from `config.md` YAML frontmatter under the `generation` key.

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
| `enable_scrubbing` | bool | true | Whether to scrub metacognition artifacts |
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
| `characters_complete` | Phase 6 (Settings) |
| `settings_complete` | Phase 7 (Wiki Population) |
| `wiki_populated` | Phase 8, Chapter 1 |
| `chapter_{N}_complete` | Phase 8, Chapter N+1 (or Phase 9 if N == wanted_chapters) |
| `story_complete` | Pipeline complete — nothing to resume |

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
