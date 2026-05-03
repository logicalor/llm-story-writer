# AI Story Writer — Comprehensive Manual

**Version:** 1.2
**Last Updated:** April 2026
**Stack:** Python 3.10+ · Textual TUI · ChromaDB · OpenAI-compatible local LLM (LM Studio default)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Quick Start](#2-quick-start)
3. [Creating Your First Story](#3-creating-your-first-story)
4. [Understanding the Pipeline Phases](#4-understanding-the-pipeline-phases)
5. [Architecture](#5-architecture)
6. [Installation & Setup](#6-installation--setup)
7. [Configuration](#7-configuration)
8. [Configuration Cookbook](#8-configuration-cookbook)
9. [Usage](#9-usage)
10. [Project Structure](#10-project-structure)
11. [Wiki Memory System](#11-wiki-memory-system)
12. [Agents & Tools](#12-agents--tools)
13. [Strategies](#13-strategies)
14. [Working with Savepoints](#14-working-with-savepoints)
15. [General Operation](#15-general-operation)
16. [Troubleshooting](#16-troubleshooting)
17. [Prompt Writing Tips](#17-prompt-writing-tips)
18. [Testing](#18-testing)
19. [Development](#19-development)
20. [Quick Reference](#20-quick-reference)

---

## 1. System Overview

AI Story Writer is an AI-powered long-form story generation system. It produces coherent, multi-chapter novels (typically 25+ chapters) using local LLM inference, with a progressive wiki memory system that maintains consistency across the narrative.

**Core capabilities:**
- Generate full-length novels from prompt files
- Progressive wiki memory for consistency tracking
- Per-story semantic search via ChromaDB
- Multiple writing strategies (`outline-chapter` vs `stream-of-consciousness`)
- Savepoint/resume system for long generation runs
- Scene-by-scene generation pipeline with configurable scene counts
- Local-only inference (LM Studio, Ollama, llama.cpp — any OpenAI-compatible server)

---

## 2. Quick Start

### 2.1 Prerequisites Checklist

Before starting, ensure you have:

- [ ] **Python 3.10+** installed (`python --version`)
- [ ] **Git** installed
- [ ] A local **OpenAI-compatible LLM server** running:
  - **LM Studio** (default): server running on `http://127.0.0.1:1234/v1` with a model loaded
  - **Ollama**: `ollama serve` running with a model pulled (e.g., `ollama pull llama3:70b`)
  - **llama.cpp** or **vLLM**: any server exposing the OpenAI chat completions endpoint
- [ ] A text prompt file with your story idea (any `.txt` or `.md` file)
- [ ] ~2 GB free disk space for models, stories, and ChromaDB indexes

### 2.2 One-Command Startup

After installation (see [Installation & Setup](#6-installation--setup)):

**With a prompt file (recommended):**

```bash
story-writer tui --story test_story --prompt /tmp/prompt.txt
```

This single command initialises the story directory, writes the prompt into state, and launches the TUI.

**Manual multi-step (equivalent):**

```bash
# 1. Initialize the story directory
python -m src.tools.story_state --operation init --name test_story

# 2. Write your prompt into story state
cat > /tmp/prompt.txt << 'EOF'
A space-opera epic about a rogue archaeologist who discovers
an ancient AI buried beneath the ice of Europa. The story should
blend hard sci-fi with mythic undertones, exploring themes of
identity, sacrifice, and what it means to be alive.
EOF
python -c "import json,sys; print(json.dumps(sys.stdin.read()))" < /tmp/prompt.txt | \
  python -m src.tools.story_state --operation write --name test_story \
  --field story_prompt --value -

# 3. Launch the interactive TUI
story-writer tui --story test_story
```

### 2.3 Expected First-Run Output

When you launch the TUI, you will see:

1. **Left panel** — Phase tracker showing pipeline progress:
   ```
   Phases
   > outline
   - chapters
   - wiki
   - final-edit
   - assembly
   ```
2. **Center panel** — Streaming LLM output showing outline generation in real time
3. **Right panel** — Hidden by default; press `Ctrl+W` to toggle the wiki context panel
4. **Footer** — An input box appears when the outline approval gate opens:
   ```
   Approval required. Type: approve / reject / revise <feedback>
   ```

If running headless:

```bash
story-writer run --story test_story --batch
```

You will see a headless notice, then streaming progress in the terminal, ending with:

```
Pipeline complete: status=complete
```

### 2.4 Approximate Runtime for a Full Novel

Runtimes depend heavily on model speed, context length, and revision settings.

| Target | Chapters | Model Size | Approximate Time |
|--------|----------|-----------|------------------|
| Short story | 5–10 | 7B–13B | 30 min – 2 hours |
| Novella | 15–20 | 13B–30B | 2 – 6 hours |
| Full novel | 25–40 | 30B–70B | 6 – 24 hours |
| Epic / series | 50+ | 70B+ | 1 – 3 days |

Factors that increase runtime:
- **Revisions enabled** (`enable_chapter_revisions: true`) — can double chapter time
- **Outline critique** (`enable_outline_critique: true`) — adds 10–30 min
- **Final edit pass** (`enable_final_edit: true`) — adds 10–20 min
- **Streaming disabled** — harder to judge progress, same total time
- **Slower endpoints** (Ollama on CPU vs LM Studio on GPU)

Use `story-writer resume --story <name>` to continue after any interruption without losing progress.

---

## 3. Creating Your First Story

This walkthrough takes you from a blank page to a finished manuscript.

### Step 1: Write a Prompt File

Create a plain-text file describing your story. The more detail you provide, the better the output. Save it anywhere (e.g., `~/prompts/my-story.txt`):

```text
Title: The Silence Between Stars
Genre: Hard science fiction with mythic undertones
Tone: Somber, contemplative, slowly escalating tension
Target audience: Adult readers who enjoy Le Guin and Reynolds

Premise:
Dr. Yuki Tanaka-Oduya is a xenogeologist stationed on Europa's
subsurface research base. When her seismic probes detect a
regular, artificial signal from the moon's iron core, she
must decide whether to report it to Earth — knowing that
confirmation will trigger a corporate land-rush that will
destroy the pristine environment she has spent her career
studying.

Key themes:
- The conflict between scientific preservation and human expansion
- What "ownership" means when you are not the first intelligent species
- Sacrifice for a principle that no one else values

Setting constraints:
- No faster-than-light travel; Earth is a 30-minute light-delay
- The base has only six permanent staff
- Europa's ocean is genuinely hostile; suits fail, ice quakes happen
- The alien artefact is ancient, damaged, and not hostile — but not helpful either

Character notes:
- Yuki: 48, Nigerian-Japanese, widowed, dry sense of humour, drinks too much coffee
- Commander Voss: by-the-book, secretly terrified of being forgotten
- Dr. Okonkwo: junior geologist, optimistic, represents the future Yuki is protecting

Desired length: ~25 chapters, ~80,000 words total
```

**Tip:** Include genre, tone, target audience, core conflict, setting rules, and character sketches. The system uses every paragraph.

### Step 2: Configure `config.yml`

The project ships with a working `config.yml`. For a first run, you only need to verify two things:

```yaml
# config.yml — minimal required settings for first run

models:
  # Point to whatever model you have loaded in your local server
  initial_outline_writer: "openai-compat://llama3:70b"
  chapter_stage1_writer: "openai-compat://llama3:70b"
  info_model: "openai-compat://llama3:70b"
  embedding_model: "openai-compat://nomic-embed-text"

generation:
  wanted_chapters: 25
  enable_chapter_revisions: true
  stream: true
  debug: true

infrastructure:
  model_api_base: "http://127.0.0.1:1234/v1"
  embedding_model: "openai-compat://nomic-embed-text"
  vector_dimensions: 1536
```

**What you must change:**
- `models.*` entries — match the model loaded in your inference server
- `infrastructure.model_api_base` — match your server's URL

**What you can leave alone for now:**
- Quality thresholds, revision counts, and strategy settings (defaults are sensible)
- Output and savepoint directories (default to project-relative paths)

### Step 3: Initialize the Story and Load the Prompt

Create the story directory and write your prompt into `state.json`:

```bash
# Initialize the story directory
python -m src.tools.story_state --operation init --name my-first-story
```

Load the prompt with `--prompt` so the runtime writes the pointer form directly: `state.json` stores `{"$ref": "prompt.md"}` and the prompt body lives in `stories/<story>/prompt.md`.

**Alternative — use `--prompt` (simpler):**

Both `tui` and `run` accept a `--prompt <path>` argument that automatically initialises the story (if it does not exist) and loads the prompt file into state:

```bash
# Interactive mode with prompt file
story-writer tui --story my-first-story --prompt ~/prompts/my-story.txt

# Headless mode with prompt file
story-writer run --story my-first-story --prompt ~/prompts/my-story.txt --batch
```

You can also use `--prompt` with `resume` to overwrite the existing prompt before continuing:

```bash
story-writer resume --story my-first-story --prompt ~/prompts/revised-prompt.txt
```

If you already have stories created before the markdown-pointer migration, run the one-shot migrator before resuming generation:

```bash
python3 src/tools/migrate_inline_markdown.py --name my-first-story
```

**Alternative:** You can edit `stories/my-first-story/prompt.md` directly, or edit `stories/my-first-story/state.json` and set `story_prompt` to `{"$ref": "prompt.md"}`.

### Step 4: Launch TUI or Run Headless

**Interactive mode (recommended for first stories):**

```bash
story-writer tui --story my-first-story
```

This opens the Textual interface where you can approve or reject each major phase.

**Headless mode (good for overnight runs):**

```bash
story-writer run --story my-first-story --batch
```

`run` always uses `NullApprovalGate` internally, so it behaves headlessly even when `--batch` is omitted. The flag is reserved for future interactive surfaces.

### Step 5: Approve, Reject, or Revise the Outline

When the outline finishes generating, the TUI pauses and asks for approval:

```
Approval required. Type: approve / reject / revise <feedback>
```

- **`approve`** — Accept the outline and continue to character generation
- **`reject`** — Halt the pipeline cleanly. You can resume later or restart with a different prompt
- **`revise <feedback>`** — Reject the outline, send your feedback back to the outline planner, and trigger a revision pass. Example:
  ```
  revise The pacing is too fast in the middle act. Add a chapter where Yuki discovers the corporate spy before the climax.
  ```

**How the gate works:**
- The outline quality threshold (`outline_quality`, default 87) is evaluated before the gate opens
- If `enable_outline_critique` is `true`, the orchestrator runs `OutlineCriticAgent` before the gate opens and persists its findings into `pipeline_state.json`
- Your `revise` feedback is injected directly into the next outline generation prompt
- Rejecting does not delete savepoints; you can resume or inspect the generated outline at any time

### Step 6: Monitor Chapter Generation

After the outline is approved, the pipeline enters the **Chapter Loop**:

1. **Phase tracker** (left panel) highlights `chapters`
2. **Streaming output** (center panel) shows each scene being generated in real time
3. **Wiki panel** (right panel, `Ctrl+W`) shows wiki pages being created or updated after each approved chapter

Per-chapter approval:
- Each chapter also triggers an approval gate before it is written to disk
- `approve` — saves the chapter to `stories/<name>/chapters/chapter_{N}.md` and updates the wiki
- `revise <feedback>` — regenerates the chapter with your notes
- `reject` — halts the pipeline after the current chapter

**What to watch for:**
- **Inconsistencies** in character names or setting details → use `revise` with specific corrections
- **Repetitive phrasing** → note it in feedback; the system will vary sentence structure
- **Pacing issues** → request more or fewer scenes per chapter

### Step 7: Review and Export the Final Manuscript

When the last chapter is approved, the pipeline proceeds to:

1. **Final Edit** (if enabled) — a polish pass over all approved chapters
2. **Assembly** — combines all chapters into a single manuscript

Final files are written to:

```
stories/my-first-story/
├── output/
│   ├── story.md           # Assembled manuscript (all chapters)
│   └── story_edited.md    # Final-edit manuscript (if final edit was enabled)
```

You can also manually assemble at any time:

```bash
python -m src.tools.story_assembler assemble --story-name my-first-story
```

### Expected File Tree After Completion

```
stories/my-first-story/
├── prompt.md                    # Story prompt markdown body
├── state.json                    # Pipeline state and metadata
├── outline.json                  # Approved outline
├── chapters/
│   ├── chapter_1.md
│   ├── chapter_1_recap.json      # Pointer map for recap markdown
│   ├── chapter_1/
│   │   ├── recap_events.md
│   │   ├── recap_compact.md
│   │   └── recap_sanitised.md
│   ├── chapter_2.md
│   ├── chapter_3.md
│   └── ...                       # One file per approved chapter
├── output/
│   ├── story.md                  # Final assembled manuscript
│   └── story_edited.md           # Post-final-edit manuscript (optional)
├── characters/
│   ├── yuki-tanaka-oduya.json    # Character sheet metadata + {"$ref": ...} pointers
│   ├── yuki-tanaka-oduya/
│   │   ├── sheet.md              # Full markdown body
│   │   ├── summary.md            # Summary markdown body
│   │   ├── abridged.md           # Prompt-safe markdown body
│   │   └── chunks/
│   │       └── ...               # One markdown file per character chunk
│   ├── commander-voss.json
│   └── ...
├── settings/
│   ├── europa-research-base.json # Setting sheet metadata + {"$ref": ...} pointers
│   ├── europa-research-base/
│   │   ├── sheet.md
│   │   ├── summary.md
│   │   ├── abridged.md
│   │   └── chunks/
│   │       └── ...               # One markdown file per setting chunk
│   └── ...
├── savepoints/
│   ├── pipeline_state.json       # Resume state (single JSON file)
│   ├── outline_complete          # Milestone marker
│   ├── arc_analysis_complete     # Milestone marker
│   ├── chapter_1_complete        # Chapter content savepoint
│   ├── chapter_2_complete
│   └── ...                       # Additional per-step savepoints
└── wiki/
    ├── _schema.md                # Wiki schema and conventions
    ├── characters/
    ├── locations/
    ├── events/
    ├── factions/
    ├── items/
    ├── plot-threads/
    ├── world-rules/
    ├── themes/
    ├── relationships/
    ├── timeline/
    ├── chapters/
    └── contradictions/
```

**Key points about the file tree:**
- `state.json` is the source of truth for story metadata and progress
- `state.json.story_prompt` now points to `prompt.md` instead of embedding the full prompt body
- `savepoints/pipeline_state.json` is the resume checkpoint (single JSON file) and now stores pointer refs for recap markdown, chapter outline summaries, and structured `enrichment_suggestions`
- Individual step savepoints (e.g., `outline_complete`, `chapter_3_complete`) are separate files in the same directory
- The `wiki/` directory is fully Obsidian-compatible — open it in Obsidian to browse linked pages

---

## 4. Understanding the Pipeline Phases

The story generation pipeline is divided into primary phases. Each phase writes a savepoint on completion, so you can resume after any interruption.

The current restored pipeline runs in this order:

```text
Init -> Story Foundation -> Outline -> [Outline Critique] -> Narrative Arc Analysis -> Characters & Settings -> Wiki Initialization -> Wiki Bootstrap -> Chapter Loop -> Final Edit -> Assembly
```

- **Foundation** extracts the story's base context, story start date, and story elements from the prompt before outline generation begins. Those fields seed `OutlineResult` and survive savepoints and resume.
- **Outline Structure** turns the prompt plus foundation context into the chapter-by-chapter outline, using either direct, expanded, or chunked outline generation depending on the active settings. The approved outline becomes the structural source for downstream character, setting, wiki, and chapter work.
- **Outline Critique** runs the outline review loop when `enable_outline_critique` is enabled. The outline phase now checkpoints the draft and critique sub-steps separately, so resume can return to the approval gate or skip critique when those artefacts are already persisted.
- **Chapter Loop (Recap -> Chapter Write)** carries forward recap context from the prior approved chapter, writes the next chapter from the outline plus accumulated story state, then updates wiki pages, sheets, metadata, and the new recap for the following chapter. Drafting, consistency, wiki update, sheet evolution, recap, and Chapter 1 metadata refresh are now resumable as separate chapter-local ledger items.
- **Final Edit** performs the last prose-polish pass across approved chapters, optionally running scrub and voice-consistency diagnostics before editing. Each edited chapter is now checkpointed independently before assembly writes the final manuscript.

In addition to the primary phases, the orchestrator now runs three advisory metadata checkpoints that never block progress:

| Checkpoint | Trigger | Inputs | Output |
|------------|---------|--------|--------|
| `metadata-outline` | Immediately after outline approval | Outline text only | First pass for story title, back-cover summary, and tags; on success writes `stories/<name>/metadata.json` and updates `OutlineResult.title` plus `OutlineResult.tags` |
| `metadata-chapter-1` | After Chapter 1 is approved inside the chapter loop | Outline text + approved Chapter 1 prose | Refreshes `metadata.json` with stronger title and summary candidates based on real prose |
| `metadata-final` | After final edit finishes | Outline text + edited Chapter 1 prose | Writes the final canonical metadata payload used at the end of the run |

### ASCII Flow Diagram

```
┌─────────┐     ┌──────────────────┐     ┌──────────┐
│  Init   │────▶│ Story Foundation │────▶│ Outline  │
│ (setup) │     │ (prompt context) │     │ + gate   │
└─────────┘     └──────────────────┘     └──────────┘
                      │
                      ▼
                 ┌─────────────────┐
                 │ Narrative Arc   │
                 │   Analysis      │
                 └─────────────────┘
                      │
          ┌─────────────────────────────┼─────────────────────────────┐
          ▼                             ▼                             ▼
      ┌────────────┐                ┌──────────┐                  ┌───────────┐
      │ Characters │                │ Settings │                  │ Wiki Init │
      │  (sheets)  │                │ (sheets) │                  │           │
      └────────────┘                └──────────┘                  └───────────┘
          │                             │                             │
          └─────────────────────────────┴─────────────────────────────┘
                      │
                      ▼
                 ┌──────────────────┐
                 │   Chapter Loop   │
                 │ (generate → gate │
                 │  → approve → wiki│
                 │  → repeat)       │
                 └──────────────────┘
                      │
                      ▼
                 ┌──────────────────┐     ┌──────────┐
                 │   Final Edit     │────▶│ Assembly │
                 │ (conditional)    │     │          │
                 └──────────────────┘     └──────────┘
```

### Phase 1: Init

**What the system does:**
- Validates the story name and creates the story directory structure if missing
- Loads `config.yml` and resolves model endpoints
- Initializes the `PipelineState` object
- Writes the first savepoint (`init`)

**Artefacts produced:**
- `stories/<name>/savepoints/init`
- `stories/<name>/savepoints/pipeline_state.json` (initial snapshot)

**User action needed:** None

**Approximate duration:** < 1 second

### Phase 2: Story Foundation

**What the system does:**
- Loads your story prompt from `state.json`
- Runs `StoryFoundationAgent` before outline generation
- Extracts three early context fields used by later phases: `base_context`, `story_start_date`, and `story_elements`
- Seeds `PipelineState.outline_result` with those fields so later phases can preserve them across savepoints and resume

**Artefacts produced:**
- `stories/<name>/savepoints/pipeline_state.json` with `outline_result.base_context`, `outline_result.story_start_date`, and `outline_result.story_elements`
- `stories/<name>/savepoints/story_foundation_complete`

**User action needed:** None

**Approximate duration:** 1–3 minutes

### Phase 3: Outline

**What the system does:**
- Delegates to the `outline-planner` agent
- Generates a detailed chapter-by-chapter outline
- Optionally runs `OutlineCriticAgent` before the approval gate (if `enable_outline_critique: true`)
- Writes the in-progress outline to `pipeline_state.json` before opening the approval gate
- When outline critique is enabled, runs six outline critics plus three arc analytics and persists the critic artefacts before the gate opens
- Waits for outline approval or revision feedback before marking the phase complete
- After approval, runs the advisory `metadata-outline` checkpoint to generate the first title, summary, and tag set from outline text alone

**Resume behavior:**
- `outline/draft` lets resume reuse the saved outline instead of regenerating it before the approval gate
- `outline/critique` lets resume skip the critic pass when the reviewed outline is already persisted
- Legacy savepoints with `outline` already in `completed_phases` still bypass the whole section cleanly

**Artefacts produced:**
- `stories/<name>/savepoints/outline`
- `stories/<name>/savepoints/pipeline_state.json` with the latest `OutlineResult`
- `stories/<name>/outline/critic_summary.md` when outline critique is enabled
- `stories/<name>/savepoints/pipeline_state.json` with `critic_summary`, `arc_distribution`, and `promise_payoff` when outline critique is enabled
- `stories/<name>/metadata.json` with the current generated title, summary, tags, and `updated_at` when metadata generation succeeds

**User action needed:**
- Approve, reject, or revise via the approval gate (TUI) or auto-approve (headless)

**Approximate duration:** 5–20 minutes (longer with critique loops)

### Phase 4: Narrative Arc Analysis

**What the system does:**
- Loads the approved outline
- Delegates to the `story-planner` agent
- Builds the assessment prompt from the approved outline plus the persisted `critic_summary`, `arc_distribution`, and `promise_payoff` fields when outline critique ran
- Streams one advisory arc assessment (promise/payoff, tension curve, pacing)
- Persists `state.arc_result` and writes `arc_analysis_complete`
- On agent error, emits a skip message and continues (non-blocking)

**Artefacts produced:**
- `stories/<name>/savepoints/arc_analysis_complete`
- `stories/<name>/savepoints/pipeline_state.json` with `arc_result`

**User action needed:** None (advisory only)

**Approximate duration:** 2–5 minutes

### Phase 5: Characters & Settings

**What the system does:**
- Extracts character names from the approved outline and generates one JSON sheet per character
- Extracts setting/location names from the approved outline and generates one JSON sheet per setting
- Caches extracted names to `stories/<name>/characters/_names.json` and `stories/<name>/settings/_names.json` before the per-entity loop continues
- Uses the work-item ledger inside `pipeline_state.json` to checkpoint each base sheet, each chunk, each abridged write, and each summary write
- Uses orchestrator helpers rather than standalone character or setting presentation agents
- If name extraction returns invalid JSON, the phase degrades gracefully and the pipeline continues

**Resume behavior:**
- Already-cached name lists are loaded from `_names.json` instead of being re-extracted
- Completed character and setting JSON files are read back from disk
- Resume continues from the next missing chunk or summary step instead of restarting the whole phase

**Artefacts produced:**
- `stories/<name>/savepoints/characters`
- `stories/<name>/savepoints/settings`
- `stories/<name>/characters/_names.json`
- `stories/<name>/characters/<slug>.json` (one per character)
- `stories/<name>/settings/_names.json`
- `stories/<name>/settings/<slug>.json` (one per setting)

**User action needed:** None

**Approximate duration:** 2–10 minutes (scales with entity count)

### Phase 6: Wiki Initialization

**What the system does:**
- Idempotently ensures the `stories/<name>/wiki/` directory structure exists
- Creates subdirectories, index, log, and schema template if missing
- Safe to rerun on resume; skips creation if wiki already present

**Artefacts produced:**
- `stories/<name>/wiki/_schema.md`
- `stories/<name>/wiki/characters/`
- `stories/<name>/wiki/locations/`
- `stories/<name>/wiki/events/`
- And other wiki subdirectories

**User action needed:** None

**Approximate duration:** < 1 second

### Phase 7: Wiki Bootstrap

Runs immediately after wiki initialization and before the chapter loop.

What this phase does:
- Calls `_list_wiki_entities()` in `src/tools/wiki_extract.py` to extract and deduplicate entities from the approved outline plus character and setting JSON sheets
- Drives `_bootstrap_single_wiki_entity()` in a per-entity loop so each created wiki page has its own ledger item
- Skips already-completed work items and already-existing wiki slugs for idempotent reruns
- Leaves `bootstrap_wiki_from_story()` available for direct CLI or ad-hoc one-shot bootstrap usage
- Continues the pipeline even if bootstrap fails; the exception is logged but the chapter loop still runs

**Savepoint:** `wiki_populated`

**Resume behavior:**
- Completed wiki pages are tracked as `wiki-bootstrap/<slug>` ledger items and skipped individually on resume
- A partial bootstrap resumes from the next missing entity instead of redoing the full batch
- If bootstrap produces zero pages or raises, the phase is not marked complete, so the next run retries it

### Phase 8: Chapter Loop

**What the system does:**
- For each chapter (1 to `wanted_chapters`):
  1. **Scene Generation (7b)** — Loads abridged character and setting sheet context; prefers the chapter's detailed outline block when available; forwards the prior chapter recap from `state.recaps[str(N-1)]` (preferring `compact`, then `sanitised`, then `events`); and generates chapter text via the `chapter-writer` agent. If `scene_generation_pipeline: true`, the agent expands the chapter into `stories/<name>/chapters/chapter_<N>_scenes.json`, then drafts scenes sequentially with position-aware prompts for first, middle, and final scenes. Each completed scene is written to `stories/<name>/chapters/chapter_<N>/scene_<M>.md` before the corresponding work item is marked done. Otherwise, the full chapter is generated in one LLM call. Once the draft is approved, `stories/<name>/chapters/chapter_<N>.md` is written before `chapter-<N>/draft` is recorded.
  2. **Approval Gate** — Presents the chapter for user approval (interactive mode only)
  3. **Consistency Check (7e)** — Runs `consistency_checker`; findings stream to the token bus but do not block chapter persistence
  4. **Chapter Persistence** — Appends the approved draft to `state.approved_chapters` and writes `stories/<name>/chapters/chapter_<N>.md`
  5. **Wiki Update (7c)** — Calls `WikiMaintainerAgent` to extract structured data and persist wiki pages; failures are logged and do not block the loop
  6. **Sheet Evolution** — Calls `CharacterEvolverAgent` and `SettingEvolverAgent` after the wiki step. Each agent runs `extract_from_chapter` → `analyze_changes` → `update` over the existing sheet files, rewrites `sheet` when a change is needed, and records per-entity `updated` or `unchanged` results in `state.evolved_sheets[str(N)]`.
  7. **Recap Generation (7d)** — Calls `RecapWriterAgent` after sheet evolution. The default path runs six LLM stages (`extract_chapter_events` → `recap/assign_event_timing` → `recap/enrich_event_details` → `recap/format_json` → `recap/compact_events` → optional `recap/sanitize`). When `use_multi_stage_recap_sanitizer: false`, the agent takes the short path (`extract_chapter_events` → `recap/format_json`). On success, the orchestrator writes the recap bodies to `stories/<name>/chapters/chapter_<N>/recap_events.md`, `recap_compact.md`, and `recap_sanitised.md`, then stores `{"$ref": ...}` pointers for those files in both `state.recaps[str(N)]` and `chapter_<N>_recap.json`. Recap failures are advisory and do not block later chapters.
  8. **Metadata Refresh (`metadata-chapter-1`)** — Immediately after Chapter 1 is approved, the orchestrator re-runs `StoryMetadataAgent` with the approved Chapter 1 prose. This refresh is advisory, updates `OutlineResult.title` plus `OutlineResult.tags` on success, and rewrites `stories/<name>/metadata.json`.
  9. **Savepoint (7h)** — Saves a chapter-level savepoint (`chapter-{N}`); after the last chapter, the orchestrator also marks `chapter-loop`

**Resume behavior:**
- If an approved draft already exists in `state.approved_chapters` from a legacy savepoint, resume backfills `chapter-<N>/draft` and continues with the next missing post-processing item
- If scene decomposition already completed, resume reloads `chapter_<N>_scenes.json` instead of regenerating the scene list
- If one or more scenes already completed, resume reloads `chapter_<N>/scene_<M>.md` files and continues from the first missing scene
- If the chapter draft already completed, resume independently skips completed consistency, wiki update, sheet evolution, recap, and Chapter 1 metadata sub-steps
- Direct whole-chapter fallback still behaves as a single-shot draft; granular resume here applies only to the scene pipeline path

> **Future work (not yet wired):** Phase 7a (chapter-outline-expander), Phase 7f (quality-reviewer / critique-revision loop), Phase 7.5 (prose-scrubber), Phase 7g (handoff artifact generation).

**Artefacts produced:**
- `stories/<name>/chapters/chapter_<N>_scenes.json` when scene generation pipeline is enabled
- `stories/<name>/chapters/chapter_<N>/scene_<M>.md` for each completed scene when scene generation pipeline is enabled
- `stories/<name>/chapters/chapter_1.md` through `chapter_{N}.md`
- `stories/<name>/chapters/chapter_1_recap.json` through `chapter_{N}_recap.json`, each storing `events`, `compact`, and `sanitised` as `{"$ref": ...}` pointers
- `stories/<name>/chapters/chapter_<N>/recap_events.md`, `recap_compact.md`, and `recap_sanitised.md`
- `stories/<name>/savepoints/chapter-1` through `chapter-{N}` plus `chapter-loop`
- Updated wiki pages under `stories/<name>/wiki/`

**User action needed:**
- Per-chapter approval gate in TUI mode
- None in headless mode (auto-approves all chapters)

**Approximate duration:** 5–20 minutes per chapter (depending on model speed, scene count, and revisions)

### Phase 9: Final Edit (conditional)

**What the system does:**
- Enabled unless `generation.enable_final_edit` is explicitly set to `false` in `config.yml`
- Loads `prompts/final_edit/edit_chapter_direct.md` via `PromptLoader`
- Streams one editing pass per approved chapter (voice consistency, pacing, prose polish)
- Writes each edited chapter to `stories/<name>/chapters/chapter_<N>_edited.md` before recording `final-edit/chapter:<N>`
- Falls back to original chapter content if the model returns empty output
- Writes the edited manuscript to `stories/<name>/output/story_edited.md`
- Runs the advisory `metadata-final` checkpoint after editing completes, using the edited Chapter 1 prose when available to produce the final title, summary, and tag set in `stories/<name>/metadata.json`
- Persists `final_edit_complete`

**Resume behavior:**
- Resume reloads `chapter_<N>_edited.md` for any chapter whose `final-edit/chapter:<N>` ledger item is already complete
- A partial final-edit pass resumes from the first unedited chapter instead of restarting the whole polish phase

**Artefacts produced:**
- `stories/<name>/output/story_edited.md`
- `stories/<name>/savepoints/final_edit_complete`

**User action needed:** None

**Approximate duration:** 10–20 minutes total (scales with chapter count)

### Phase 10: Assembly

**What the system does:**
- Assembles the final manuscript from the current `state.approved_chapters`
- Writes `stories/<name>/output/story.md`
- Raises `StoryGenerationError` if no approved chapter content is found
- Marks the run complete in `pipeline_state.json`

**Artefacts produced:**
- `stories/<name>/output/story.md`
- `stories/<name>/savepoints/assembly`
- Updated `stories/<name>/savepoints/pipeline_state.json` with `status: complete`

**User action needed:** None

**Approximate duration:** < 1 second

---

## 5. Architecture

### 5.1 Python-Native Pipeline Architecture

The system uses a **Python-native prompt-and-tool architecture** during active runtime. Python-native agents load direct-generation prompts from `prompts/outline/`, `prompts/chapters/`, `prompts/final_edit/`, and `prompts/chapter_review/` via `PromptLoader`. The files under `prompts/agents/` are workflow specifications for OpenCode and Copilot agent runtimes, not direct LLM prompts (see [ADR 007](planning/adr/007-python-native-orchestration.md)):

| Component | Technology | Role |
|-----------|------------|------|
| **Pipeline phases** | Python presentation layer + `prompts/agents/` | Orchestration, creative decisions, human interaction |
| **Tools** | Python modules and scripts | Deterministic domain operations |
| **Wiki** | Markdown + YAML frontmatter | Structured story knowledge base |
| **Vector index** | ChromaDB | Semantic search over story content and wiki |

**Key principle:** Prompt-defined phases make decisions; tools execute operations. Runtime orchestration never directly manipulates story files, wiki pages, or savepoints without going through the relevant Python tool or service boundary.

### 5.2 Clean Architecture Layers (Python Domain)

```
src/domain/          → Entities, value objects (core business rules, no dependencies)
src/application/     → Strategies (use cases, depends on domain); services/ layer retired per ADR 008
src/infrastructure/  → Providers, storage (external adapters: OpenAI-compatible LLM, ChromaDB, disk I/O)
src/presentation/    → CLI entry points and pipeline orchestration
src/tools/           → Python tool implementations and ad-hoc CLIs
```

Each layer depends only on inner layers. `src/domain/` has zero external dependencies.

### 5.3 Data Flow

```
User prompt (loaded from state.json)
    ↓
story-writer CLI / orchestrator
    ↓
┌─────────────────────────────────────────────┐
│  Python tools and services                    │
│  prompt_loader · story_state · wiki_*         │
│  savepoint_manager · character_manager · etc. │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│  Domain layer (entities, services, strategies)│
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│  Infrastructure (OpenAI-compatible LLM,       │
│  ChromaDB, disk)                              │
└─────────────────────────────────────────────┘
    ↓
stories/<name>/  (chapters, wiki, savepoints)
```

### 5.4 Prompt Architecture

The project maintains two distinct categories of prompt files. Confusing them caused bugs #276 and #277, so the distinction is enforced here.

**1. Agent workflow prompts** (`prompts/agents/*.md`)
These are OpenCode/Copilot runtime specifications. They describe agent behaviour, tool usage, and workflow steps. They are **NOT** loaded as LLM system prompts by the Python-native runtime.

**2. Direct generation prompts** (`prompts/outline/`, `prompts/chapters/`, `prompts/final_edit/`, `prompts/chapter_review/`, etc.)
These are LLM system/user prompts loaded by `PromptLoader` at runtime by Python-native agents. They contain instructions, templates, and variable placeholders for direct LLM invocation.

**Migration reference:** The following agents were migrated from workflow prompts to direct-generation prompts in issue #277:

| Agent | Old Workflow Prompt (DO NOT USE) | New Direct-Generation Prompt |
|---|---|---|
| `OutlinePlannerAgent` | `prompts/agents/outline-planner.md` | `prompts/outline/create_direct.md` when `expand_outline=false`; otherwise `prompts/outline/create_skeleton.md`, `prompts/outline/expand_chapter_detail.md`, and `prompts/outline/strip_elements.md`; when `use_chunked_outline_generation=true` and `wanted_chapters > outline_chunk_size`, switch to `prompts/outline/create_chunk.md`, `prompts/outline/analyze_continuity.md`, and `prompts/outline/analyze_enrichment.md` |
| `StoryPlannerAgent` | `prompts/agents/story-planner.md` | `prompts/outline/arc_assessment_direct.md` |
| `ChapterWriterAgent` | `prompts/agents/chapter-writer.md` | `prompts/chapters/write_chapter_direct.md` |
| `FinalEditorAgent` | `prompts/agents/final-editor.md` | `prompts/final_edit/edit_chapter_direct.md` |
| `ConsistencyCheckerAgent` | `prompts/agents/consistency-checker.md` | `prompts/chapter_review/consistency_check_direct.md` |

**Rule:** Python agents must **NEVER** load `prompts/agents/*.md` as system prompts. Use `PromptLoader.load_prompt('path/to/direct_prompt', variables={...})` instead.

---

## 6. Installation & Setup

### 6.1 Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.10+ | Required by `pyproject.toml` |
| OpenAI-compatible LLM server | any | LM Studio (default), Ollama, llama.cpp, vLLM, etc. |

### 6.2 Installation Steps

```bash
# 1. Clone the repository
git clone https://github.com/datacrystals/AIStoryWriter.git
cd AIStoryWriter

# 2. Start your local LLM server and load models
#    e.g. LM Studio (default: http://127.0.0.1:1234/v1) — load model via the UI
#    or:  ollama serve && ollama pull <model-name>

# 3. Install Python dependencies and the console script
pip install -e .

# 4. Copy and configure
#    The project reads config.yml in the repo root
#    Edit models and model_api_base to match your inference server
```

### 6.3 Model Configuration

Models are configured in `config.yml` under the `models:` YAML block. The system uses OpenAI-compatible endpoints:

```yaml
models:
  initial_outline_writer: "openai-compat://gemma-4-26b-a4b-it-heretic-guff"
  chapter_stage1_writer: "openai-compat://gemma-4-26b-a4b-it-heretic-guff"
  info_model: "openai-compat://gemma-4-26b-a4b-it-heretic-guff"
  embedding_model: "openai-compat://nomic-embed-text"
```

The `openai-compat://` prefix routes to the configured OpenAI-compatible API. Override `model_api_base` in `infrastructure:` to change the endpoint (default: `http://127.0.0.1:1234/v1`).

### 6.4 Opencode Agent Runtime Setup (Development Only)

The Python story-generation runtime above is separate from the Opencode agent runtime used for development and migration work (e.g., Copilot-to-Opencode migration). That development runtime config lives in the repository root `opencode.json`, where the default model is `openrouter/moonshotai/kimi-k2.6` and the OpenRouter provider registry includes Kimi K2.6, Qwen3.6 Plus, and GLM 5.1.

Developer-local credentials and user-level MCP servers are not committed to the repository. Configure `OPENROUTER_API_KEY`, Tavily, and Context7 in your personal Opencode config (`~/.config/opencode/opencode.json`) instead. See [Opencode Runtime Configuration](./features/opencode-runtime.md) for the exact setup and confirmed model IDs.

**Do not confuse the two runtimes:**
- **Story generation runtime** — Python-native, uses `config.yml`, runs via `story-writer` CLI
- **Development agent runtime** — Opencode, uses `opencode.json`, runs via `opencode run @agent-name`

---

## 7. Configuration

All configuration lives in `config.yml` in the repository root. No secrets are required — all providers use local inference. Optional environment variables include `LLM_API_BASE` and `STORIES_DIR`.

### 7.1 Generation Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `wanted_chapters` | 40 | Target chapter count |
| `outline_quality` | 87 | Quality threshold for outline (0–100) |
| `chapter_quality` | 85 | Quality threshold for chapters |
| `outline_min_revisions` | 2 | Lower bound retained in outline revision settings |
| `outline_max_revisions` | 3 | Max outline revision passes |
| `chapter_max_revisions` | 3 | Max chapter revision passes |
| `enable_outline_critique` | true | Run `OutlineCriticAgent` between outline generation and the outline approval gate |
| `enable_concurrent_critics` | false | Run the six outline-review critics concurrently instead of sequentially |
| `outline_critique_iterations` | 3 | Stored and validated critique-loop setting; current implementation still runs one critic pass per generated outline |
| `enable_chapter_revisions` | true | Enable chapter revision loop |
| `enable_final_edit` | false | Run final polish pass |
| `enable_scrubbing` | true | When final edit runs, gather prose-scrub and voice-consistency diagnostics before chapter polish |
| `strategy` | "outline-chapter" | Writing strategy |
| `use_chunked_outline_generation` | false | Allow the chunked outline branch when `expand_outline=true` and `wanted_chapters > outline_chunk_size` |
| `outline_chunk_size` | 4 | Chapters per chunk window before the chunked branch activates |
| `expand_outline` | true | Select outline mode: when `false`, use one `create_direct` call; when `true`, use per-chapter expansion by default and switch to chunked windows only if `use_chunked_outline_generation=true` and the outline exceeds one chunk |
| `scene_generation_pipeline` | true | Use scene-by-scene generation |
| `scenes_per_chapter_min` | 8 | Minimum scenes per chapter (when scene expansion is enabled) |
| `scenes_per_chapter_max` | 16 | Maximum scenes per chapter (when scene expansion is enabled) |
| `scene_expansion_enabled` | true | Enable scene expansion in Phase 7a (when wired) |
| `stream` | true | Stream LLM output |
| `debug` | true | Enable debug logging |
| `log_prompt_inputs` | false | Log full prompt inputs to console |
| `use_improved_recap_sanitizer` | true | In the multi-stage recap path, run the final `recap/sanitize` prompt and store its output in `sanitised`; when `false`, `sanitised` falls back to `compact` |
| `use_multi_stage_recap_sanitizer` | true | Run the six-stage recap pipeline after each approved chapter; when `false`, use the short extract-plus-format recap path |

### 7.2 Infrastructure Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `output_dir` | — | Where to write final story files |
| `savepoint_dir` | — | Where to store savepoints |
| `logs_dir` | "Logs" | Where to write log files |
| `model_api_base` | `http://127.0.0.1:1234/v1` | LLM API endpoint |
| `context_length` | 16384 | Context window size |
| `embedding_model` | `nomic-embed-text` | Embedding model for ChromaDB |
| `vector_dimensions` | 1536 | Embedding vector dimensions |
| `similarity_threshold` | 0.7 | ChromaDB similarity threshold |
| `max_context_chunks` | 20 | Max RAG chunks per scene |
| `max_chunk_size` | 1000 | Max chunk size in characters |
| `overlap_size` | 200 | Overlap between chunks in characters |

### 7.3 Model Role Assignments

Each phase of the pipeline uses a specific model:

| Phase | Model Role |
|-------|-----------|
| Initial outline writing | `initial_outline_writer` |
| Chapter outline | `chapter_outline_writer` |
| Chapter content (stage 1–4) | `chapter_stage1_writer` … `chapter_stage4_writer` |
| Chapter revision | `chapter_revision_writer` |
| Scene writing | `scene_writer` |
| Creative generation | `creative_model` |
| Critique/eval | `eval_model`, `revision_model` |
| Info extraction | `info_model` |
| Wiki maintenance | `info_model` (separate agent) |
| Scrubbing | `scrub_model` |
| Sanity checking | `sanity_model` |
| Logical operations | `logical_model` |
| Translation | `translator_model` |
| Embedding | `embedding_model` |

---

## 8. Configuration Cookbook

These presets are starting points. Copy the relevant block into your `config.yml` under the `generation:` key.

### 8.1 Fast Prototype Preset

For quickly testing a concept or iterating on a short story (~5 chapters, low quality, fast turnaround):

```yaml
generation:
  wanted_chapters: 5
  outline_min_revisions: 0
  outline_max_revisions: 1
  chapter_min_revisions: 0
  chapter_max_revisions: 1
  enable_chapter_revisions: false
  enable_outline_critique: false
  enable_final_edit: false
  enable_scrubbing: false
  use_chunked_outline_generation: false
  stream: true
  debug: true
```

| Setting | Value | Why |
|---------|-------|-----|
| `wanted_chapters` | 5 | Short test run |
| `outline_min_revisions` | 0 | Do not force manual outline revision rounds |
| `outline_max_revisions` | 1 | Keep outline retries bounded when you choose to revise |
| `enable_chapter_revisions` | false | Skip revision loops |
| `enable_outline_critique` | false | Skip critique phase |
| `enable_final_edit` | false | Skip polish pass |
| `use_chunked_outline_generation` | false | Faster single-pass outline |

### 8.2 High Quality Novel Preset

For a polished, full-length novel (~25 chapters, revisions, critique):

```yaml
generation:
  wanted_chapters: 25
  outline_min_revisions: 2
  outline_max_revisions: 5
  chapter_min_revisions: 1
  chapter_max_revisions: 3
  enable_chapter_revisions: true
  enable_outline_critique: true
  outline_critique_iterations: 5
  enable_final_edit: true
  enable_scrubbing: true
  use_chunked_outline_generation: true
  outline_chunk_size: 4
  stream: true
  debug: false
```

| Setting | Value | Why |
|---------|-------|-----|
| `outline_max_revisions` | 5 | More chances to refine outline |
| `enable_concurrent_critics` | false | Keep critic output deterministic and easier to inspect |
| `outline_critique_iterations` | 5 | Preserve a higher critique-loop ceiling for future iteration-aware flows |
| `chapter_max_revisions` | 3 | Per-chapter quality loop |
| `enable_outline_critique` | true | Iterative outline refinement |
| `enable_final_edit` | true | Post-generation polish pass |
| `enable_scrubbing` | true | Feed prose and voice diagnostics into final edit |
| `outline_chunk_size` | 4 | Keep each outline window small while preserving between-window continuity checks |
| `debug` | false | Cleaner output |

### 8.3 Short Story Preset

For a contained short story (~10 chapters, no revisions, fast):

```yaml
generation:
  wanted_chapters: 10
  outline_min_revisions: 0
  outline_max_revisions: 2
  chapter_min_revisions: 0
  chapter_max_revisions: 0
  enable_chapter_revisions: false
  enable_outline_critique: false
  enable_final_edit: false
  enable_scrubbing: false
  use_chunked_outline_generation: false
  stream: true
  debug: true
```

| Setting | Value | Why |
|---------|-------|-----|
| `wanted_chapters` | 10 | Novella length |
| `chapter_max_revisions` | 0 | No per-chapter revision loop |
| `enable_scrubbing` | false | Skip final-edit diagnostics because final edit is disabled |

### 8.4 Settings Change Summary Table

| Setting | Fast Prototype | High Quality Novel | Short Story |
|---------|---------------|-------------------|-------------|
| `wanted_chapters` | 5 | 25 | 10 |
| `outline_min_revisions` | 0 | 2 | 0 |
| `outline_max_revisions` | 1 | 5 | 2 |
| `outline_critique_iterations` | 3 | 5 | 3 |
| `chapter_min_revisions` | 0 | 1 | 0 |
| `chapter_max_revisions` | 1 | 3 | 0 |
| `enable_chapter_revisions` | false | true | false |
| `enable_outline_critique` | false | true | false |
| `enable_concurrent_critics` | false | false | false |
| `enable_final_edit` | false | true | false |
| `enable_scrubbing` | false | true | false |
| `use_chunked_outline_generation` | false | true | false |
| `outline_chunk_size` | — | 4 | — |

---

## 9. Usage

### 9.1 Python CLI

```bash
story-writer --help
```

Available subcommands:

| Command | Description |
|---------|-------------|
| `story-writer tui --story <name> [--prompt <path>] [--resume] [--savepoint <name>]` | Launch the interactive Textual TUI. `--prompt` auto-initialises the story and writes the prompt file to state. |
| `story-writer run --story <name> [--prompt <path>] [--batch]` | Run the headless Python-native pipeline. `--prompt` auto-initialises the story and writes the prompt file to state. |
| `story-writer resume --story <name> [--prompt <path>] [--savepoint <name>]` | Resume from the latest persisted pipeline state. `--prompt` overwrites the existing story prompt. `--savepoint` validates the name exists but does not restore an older snapshot. |

`run` always uses `NullApprovalGate` internally, so it behaves headlessly even when `--batch` is omitted. When you omit `--batch`, the CLI prints a headless notice before starting the run. The flag remains for forward compatibility with later interactive surfaces.

#### Textual TUI

Use the TUI when you want live pipeline visibility and interactive approval gates:

```bash
story-writer tui --story test_story
story-writer tui --story test_story --resume
story-writer tui --story test_story --resume --savepoint chapter-3
```

Use `--resume` to continue from saved pipeline state inside the TUI. Add `--savepoint <name>` to validate that the story reached at least that phase. Resume always continues from the latest `pipeline_state.json` snapshot regardless of the named savepoint provided.

The screen shows a left-side phase tracker, a central streaming output log, and a toggleable wiki-context panel on the right. Approval requests appear in the footer input widget. Type `approve`, `reject`, or `revise <feedback>` to answer the gate.

Savepoints are written automatically at phase boundaries. The TUI no longer exposes a manual savepoint keybinding.

Keybindings:

- `Ctrl+W` — toggle wiki panel
- `Ctrl+C` — cancel workers, preserve the savepoint from the last completed phase, and print the resume command

See [Textual TUI](./features/textual-tui.md) for the thread model, approval-gate bridge, and test coverage.

### 9.2 Prompt Asset Locations

Reusable prompt content used by the Python-native pipeline lives in these locations:

- `prompts/agents/` — OpenCode/Copilot workflow specifications. **NOT for Python-native LLM loading.**
- `prompts/outline/` — Outline and arc assessment direct-generation prompts
- `prompts/chapters/` — Chapter writing and scene direct-generation prompts
- `prompts/final_edit/` — Final editing direct-generation prompts
- `prompts/chapter_review/` — Consistency checking and review direct-generation prompts
- `prompts/skills/` — Reusable skill reference material
- `prompts/characters/` — Character sheet direct-generation prompts
- `prompts/settings/` — Setting/location direct-generation prompts
- `prompts/scenes/` — Scene generation direct-generation prompts
- `prompts/wiki/` — Wiki extraction and maintenance direct-generation prompts

### 9.3 Story Generation Pipeline

The current Python-native orchestrator slice runs through these phases:

```
Phase 1: Init
  → Load prompt, parse config, init story state, create savepoint

Phase 2: Story Foundation
  → Run `StoryFoundationAgent`
  → Extract `base_context`, `story_start_date`, and `story_elements`
  → Seed `OutlineResult` before outline generation

Phase 3: Outline
  → Delegate to outline-planner subagent
  → When `expand_outline=false`, fall back to one `create_direct` outline call using the same foundation context
  → When `expand_outline=true` and chunking is off or the outline fits inside one chunk, run `create_skeleton` → per-chapter `expand_chapter_detail` → `strip_elements`
  → Persist `stories/<name>/outline/skeleton.md` and `stories/<name>/outline/details/chapter_{N}.md` for the per-chapter path
  → When `expand_outline=true`, `use_chunked_outline_generation=true`, and `wanted_chapters > outline_chunk_size`, split the outline into chapter windows and run `create_chunk` for each window
  → Between chunk windows, run `analyze_continuity`, write `stories/<name>/outline/continuity/continuity_{start}_{end}.md`, and surface the findings on the token bus
  → After the last chunk, run `analyze_enrichment`, write `stories/<name>/outline/enrichment.md`, and store the result in `OutlineResult.enrichment_suggestions`
  → Persist chunk files under `stories/<name>/outline/chunks/chunk_{start}_{end}.md` when the chunked path is active, then wait on approval gate
  → When `enable_outline_critique=true`, run `OutlineCriticAgent` before the approval gate and persist `critic_summary.md` plus critique fields in `PipelineState`
  → After approval, run `metadata-outline` to write the first generated `stories/<name>/metadata.json`

Phase 4: Narrative Arc Analysis
  → Delegate to story-planner subagent
  → Build the assessment prompt from the approved outline plus `critic_summary`, `arc_distribution`, and `promise_payoff` when outline critique ran
  → Stream one advisory arc assessment from approved outline content
  → Persist `state.arc_result` and write `arc_analysis_complete`
  → On agent error, emit skip message and continue

Phase 5: Characters & Settings
  → Extract character and setting names from outline
  → Generate one JSON sheet per entity, then enrich it with `summary`, `abridged`, and per-aspect `chunks`
  → Write per-entity JSON sheets to `stories/<name>/characters/` and `settings/`
  → If name extraction returns invalid JSON, phase degrades gracefully

Phase 6: Wiki Initialization
  → Idempotently ensure `stories/<name>/wiki/` directory structure exists
  → Creates subdirectories, index, log, and schema template if missing
  → Safe to rerun on resume; skips creation if wiki already present

Phase 7: Wiki Bootstrap
  → Call `bootstrap_wiki_from_story()` after wiki init and before chapter generation
  → Seed wiki pages from the outline savepoint plus character and setting sheets
  → Skip existing slugs so resume and rerun stay idempotent
  → Mark `wiki_populated` even if bootstrap raises, then continue pipeline

Phase 8: Chapter Loop
  → Generate approved chapters one at a time, then run wiki maintenance, sheet evolution, recap generation, and consistency checks
  → After Chapter 1 approval, run `metadata-chapter-1` to refresh `stories/<name>/metadata.json`

Phase 9: Final Edit
  → Conditionally edit approved chapters before assembly
  → Then run `metadata-final` to produce final title, summary, and tags from edited Chapter 1 prose

Phase 10: Assembly
  → Write the final manuscript and mark the run complete
```

Current implementation note: the PRD's chapter-outline-expander, quality-reviewer, and prose-scrubber are not yet wired into `src/presentation/orchestrator.py`. Wiki directory initialization and the initial wiki bootstrap now run before the chapter loop.

---

## 10. Project Structure

```
llm-story-writer/
├── config.yml                  # All configuration (YAML)
├── config.example.sh           # Shell env config template
│
├── src/                       # Python domain logic
│   ├── domain/
│   │   ├── entities/         # Story, Chapter, Character, Scene entities
│   │   ├── value_objects/    # ModelConfig, GenerationSettings
│   │   ├── repositories/     # Repository interfaces
│   │   └── exceptions.py     # Domain exceptions
│   ├── application/
│   │   ├── interfaces/       # Abstract interfaces
│   │   └── strategies/       # Writing strategies
│   │       ├── outline_chapter/
│   │       └── stream_of_consciousness/
│   ├── infrastructure/
│   │   ├── providers/        # OpenAI-compatible LLM providers (LM Studio, Ollama, llama.cpp)
│   │   ├── storage/          # File-based story storage
│   │   ├── prompts/          # PromptLoader class
│   │   ├── savepoints/       # SavepointManager
│   │   └── logging/          # Logging configuration
│   ├── presentation/         # CLI interfaces and orchestrator
│   ├── config/               # Config management
│   └── tools/                # Python tool implementations
│       ├── prompt_loader.py
│       ├── story_state.py
│       ├── story_assembler.py
│       ├── wiki_*.py         # Wiki operations
│       ├── savepoint_manager.py
│       ├── character_manager.py
│       ├── setting_manager.py
│       ├── scene_writer.py
│       ├── critique_runner.py
│       ├── recap_manager.py
│       ├── rag_query.py
│       └── ...
│
├── prompts/                  # 100+ prompt templates
│   ├── agents/               # Prompt-defined pipeline phase instructions
│   │   ├── story-orchestrator.md
│   │   ├── outline-planner.md
│   │   ├── chapter-writer.md
│   │   ├── wiki-maintainer.md
│   │   ├── final-editor.md
│   │   ├── quality-reviewer.md
│   │   ├── consistency-checker.md
│   │   ├── prose-scrubber.md
│   │   ├── continue.md
│   │   ├── regenerate.md
│   │   └── ...
│   ├── skills/               # Reusable skill reference material
│   │   ├── story-pipeline/
│   │   ├── wiki-conventions/
│   │   ├── wiki-maintenance/
│   │   ├── outline-structure/
│   │   ├── narrative-arc/
│   │   └── ...
│   ├── chapters/             # Chapter generation prompts
│   ├── characters/          # Character sheet prompts
│   ├── outline/              # Outline generation prompts
│   ├── scenes/              # Scene generation prompts
│   ├── settings/            # Setting/location prompts
│   ├── recap/               # Recap generation prompts
│   └── ...
│
├── stories/                  # Per-story storage
│   └── <story-name>/
│       ├── state.json        # Story state
│       ├── outline.json      # Story outline
│       ├── chapters/         # Generated chapter files
│       ├── output/           # Final assembled manuscript output
│       ├── characters/       # Character JSON sheets
│       ├── settings/         # Setting JSON sheets
│       ├── savepoints/       # Savepoint files
│       │   └── pipeline_state.json  # Resume checkpoint
│       └── wiki/             # Progressive wiki
│           ├── _schema.md
│           ├── characters/
│           ├── locations/
│           ├── events/
│           └── ...
│
├── .chromadb/               # ChromaDB vector storage (per-story)
│
├── tests/
│   ├── unit/               # Unit tests (pytest)
│   └── integration/        # Integration tests (live LLM)
│
├── docs/
│   ├── manual.md            # This file
│   ├── README.md
│   ├── tools.md            # Tools reference
│   ├── features/            # Feature documentation
│   ├── planning/
│   │   ├── adr/            # Architecture decision records
│   │   └── opencode-migration/
│   └── testing/
│
└── configs/                # Generation config presets
    ├── fast-prototype.sh
    └── high-quality.sh
```

---

## 11. Wiki Memory System

The **progressive wiki memory system** ([ADR 004](planning/adr/004-progressive-wiki-memory-system.md)) maintains structured story knowledge as interlinked markdown pages with YAML frontmatter.

### 11.1 Design Goals

- Eliminate knowledge re-derivation (agents receive authoritative world state)
- Proactive contradiction detection before errors propagate
- Token-efficient context budgeting via hierarchical detail levels
- Human-readable, git-versionable, Obsidian-compatible

### 11.2 Page Types

| Type | Description |
|------|-------------|
| `character` | Named characters with traits, arcs, relationships |
| `location` | Geographic locations with descriptions |
| `event` | Plot events, their chapter, impact, and consequences |
| `faction` | Organizations, groups, political entities |
| `item` | Significant objects, artifacts, magical items |
| `plot-thread` | Ongoing narrative threads |
| `world-rule` | Magic systems, physics, social rules |
| `theme` | Thematic elements |
| `relationship` | Character-to-character relationships |
| `timeline` | Chronological ordering of events |
| `chapter` | Chapter synopsis and metadata |
| `contradictions` | Log of detected contradictions |

### 11.3 Confidence Taxonomy

Every wiki fact carries a confidence level:

| Level | Meaning |
|-------|---------|
| `verified` | Explicitly stated in the manuscript |
| `planned` | Outlined but not yet written |
| `speculative` | Inferred or implied by the agent |

### 11.4 Detail Levels

Wiki pages support three hierarchical summary levels:

| Level | Size | Use Case |
|-------|------|----------|
| `L1` | ~30 tokens | One-line headline for rapid context assembly |
| `L2` | ~150 tokens | Brief summary for scene pre-generation context |
| `L3` | ~500 tokens | Full description for complex scene decisions |

### 11.5 Wiki Update Lifecycle

1. **Initial bootstrap** (Phase 7, before Chapter 1): `bootstrap_wiki_from_story()` reads the approved outline savepoint plus character and setting sheets, creates the first wiki page set, and writes retrieval-ready L1/L2/L3 detail levels
2. **Post-chapter persistence** (after each accepted chapter): `wiki-maintainer` calls `update_wiki_from_chapter()`, the `wiki/extract_from_chapter` prompt returns structured JSON, and `run_batch()` persists new pages, state changes, aliases, and timeline events under `stories/<name>/wiki/`
3. **Chapter-level lint** (after each chapter): `wiki-lint` checks consistency against the ConStory-Bench error taxonomy
4. **Pre-generation snapshot** (before each scene): `wiki-snapshot` assembles a token-budgeted world state snapshot from the current wiki

### 11.6 Wikilink Syntax

Wiki pages cross-reference each other using `[[wikilink]]` syntax:

```
[[character:herald]]     → links to the herald character page
[[location:citadel]]     → links to the citadel location page
[[event:the-siege]]      → links to the siege event page
```

---

## 12. Agents & Tools

### 12.1 Agents

Agent workflow specifications for OpenCode and Copilot runtimes live in `prompts/agents/` as Markdown files. These are agent runtime instructions, not direct LLM prompts. See [Prompt Architecture](#54-prompt-architecture) for the full distinction between workflow prompts and direct-generation prompts.

Python-native agents in `src/presentation/agents/` load direct-generation prompts via `PromptLoader` from `src/infrastructure/prompts/prompt_loader.py`. `PromptLoader` supports variable substitution and caches loaded bodies for the process lifetime.

The orchestrator may dispatch exactly these subagents for creative work:

| Agent | Role | Invoked In |
|-------|------|------------|
| `story-orchestrator` | Primary pipeline controller; drives the full generation lifecycle | — |
| `story-foundation` | Extracts `base_context`, `story_start_date`, and `story_elements` before outline generation | Phase 2 |
| `outline-planner` | Generates and refines the story outline | Phase 3 |
| `story-metadata` | Generates advisory title, summary, and tags after outline approval, after Chapter 1, and after final edit | `metadata-outline`, `metadata-chapter-1`, `metadata-final` |
| `story-planner` | Evaluates dramatic arc quality (promise/payoff, tension, pacing) | Phase 4 |
| `chapter-outline-expander` | Expands all chapter outlines with scene-level detail and continuity threading | Phase 7a ⏳ |
| `chapter-writer` | Writes individual chapter content | Phase 7b |
| `wiki-maintainer` | Persists wiki page updates after each accepted chapter | Phase 7c |
| `consistency-checker` | Runs three-layer consistency analysis (wiki-lint + semantic + RAG) | Phase 7e |
| `quality-reviewer` | Runs critique/revision loop for a single chapter | Phase 7f ⏳ |
| `prose-scrubber` | Sentence/paragraph-level prose cleanup | Phase 7.5 ⏳ |
| `final-editor` | Post-assembly voice, pacing, and coherence pass | Phase 9 |

**Orchestrator Pipeline Phases:** Init → Story Foundation → Outline → `metadata-outline` → Narrative Arc → Characters & Settings → Wiki Init → Chapter Loop (+ `metadata-chapter-1` after the first approved chapter) → Final Edit → `metadata-final` → Assembly

### 12.2 Tools

Tools are Python modules under `src/tools/`. The runtime imports them directly or calls the same Python services in-process; there is no TypeScript wrapper layer anymore.

#### Core Tools

| Tool | Purpose |
|------|---------|
| `prompt_loader.py` | Load and render prompt templates with variable substitution |
| `story_state.py` | Initialize and update story state JSON (`--operation init/read/write/list`) |
| `story_assembler.py` | Assemble approved chapters into a single manuscript |
| `savepoint_manager.py` | Create, inspect, and load savepoints (`list`, `list-full`, `next-phase`, `clear`) |
| `character_manager.py` | Extract and manage character sheets |
| `setting_manager.py` | Extract and manage setting sheets |
| `recap_manager.py` | Generate and manage chapter recaps |
| `scene_writer.py` | Generate scene-level content |
| `critique_runner.py` | Run quality critique on outline or chapter |
| `critique_parser.py` | Parse critique output into structured scores and feedback |
| `rag_query.py` | Query ChromaDB for relevant story content chunks |
| `outline_generator.py` | Generate and expand story outlines |

#### Wiki Tools

| Tool | Purpose |
|------|---------|
| `wiki_init.py` | Initialize wiki directory structure and schema |
| `wiki_update.py` | Apply wiki page, alias, and timeline updates |
| `wiki_read.py` | Read wiki pages at specified detail levels |
| `wiki_search.py` | Semantic search over wiki pages (ChromaDB) |
| `wiki_snapshot.py` | Assemble token-budgeted world state snapshot |
| `wiki_extract.py` | Run initial-populate and post-chapter extraction flows, generate detail levels, and persist batch-ready wiki payloads |
| `wiki_lint.py` | Check wiki page format and consistency compliance |

#### Shared Modules

| Module | Purpose |
|--------|---------|
| `_io.py` | Shared I/O helpers for tools |
| `_llm.py` | Shared LLM provider helpers for tools |
| `_wiki.py` / `_wiki_api.py` | Internal wiki data structures and API helpers |

### 12.3 Tool Architecture

```
Agent call
    ↓
Python tool or service
  — argparse for shell usage where needed
  — direct import for runtime orchestration
    ↓
Python script (src/tools/<tool_name>.py)
  — argparse for argument parsing
  — Domain logic via src/infrastructure/ classes
  — stdout for CLI result, stderr for errors
    ↓
Result returned to agent
```

---

## 13. Strategies

The system supports pluggable story writing strategies via the strategy pattern.

### 13.1 Outline-Chapter Strategy (default)

```
1. Extract story elements and context from prompt
2. Generate detailed chapter-by-chapter outline
3. Write each chapter based on its outline entry
4. Generate and refresh metadata (title, summary, tags) after outline approval, after Chapter 1, and after final edit
```

**Config:** `strategy: "outline-chapter"` in `config.yml`

**Prompts:** `prompts/chapters/`, `prompts/outline/`

### 13.2 Stream-of-Consciousness Strategy

Generates stories in a flowing, associative narrative style without a formal outline.

**Config:** `strategy: "stream-of-consciousness"` in `config.yml`

**Prompts:** `prompts/stream_of_consciousness/`

### 13.3 Adding a Custom Strategy

1. Create `src/application/strategies/<my_strategy>/`
2. Implement the strategy class inheriting from `StoryStrategy`
3. Add prompts under `prompts/<my_strategy>/`
4. Register in `strategy_factory.py`
5. Set `strategy: "my_strategy"` in `config.yml`

---

## 14. Working with Savepoints

### 14.1 Why Savepoints Exist

Story generation can take hours or days. Savepoints let you:

- **Pause and resume** without losing progress
- **Retry a phase** after making a config or prompt change
- **Inspect intermediate output** (e.g., read the outline savepoint without running the full pipeline)
- **Debug** by loading a specific savepoint and examining its data

### 14.2 Savepoint File Structure

The pipeline resume state is stored as a single JSON file:

```
stories/<name>/savepoints/pipeline_state.json
```

This file contains the full `PipelineState` object (completed phases, approved chapters, current phase, `completed_work_items`, and related phase data).

Granular resume inside converted phases works by combining that ledger state with the persisted artefacts those work items point to. Current ADR 010 coverage writes these additional files during a run:

```
stories/<name>/chapters/chapter_<N>.md
stories/<name>/characters/_names.json
stories/<name>/settings/_names.json
stories/<name>/chapters/chapter_<N>_scenes.json
stories/<name>/chapters/chapter_<N>/scene_<M>.md
stories/<name>/chapters/chapter_<N>_edited.md
```

On resume, the orchestrator reloads those files only when the matching work-item IDs already appear in `PipelineState.completed_work_items`.

Individual phase outputs are also stored as separate savepoint files in the same directory:

```
stories/<name>/savepoints/
├── pipeline_state.json       # Resume checkpoint (single JSON file)
├── outline_complete          # Milestone: outline finished
├── arc_analysis_complete     # Milestone: arc analysis finished
├── chapter_1_complete        # Chapter 1 content
├── chapter_2_complete        # Chapter 2 content
└── ...
```

### 14.3 How to Resume After Interruption

If the TUI is closed, the machine reboots, or the pipeline crashes:

```bash
# Resume in the TUI
story-writer tui --story <name> --resume

# Resume headlessly
story-writer resume --story <name>
```

Resume always continues from the latest `pipeline_state.json` snapshot. The `--savepoint` argument only validates that the story reached at least the named phase; it does not restore an older snapshot.

When the savepoint contains ledger data, the TUI backfills completed phase-end events and shows `Resuming at: next step after <last_done>` for each partially completed phase. Legacy savepoints with an empty `completed_work_items` dict do not show that banner.

```bash
# Validate that the story reached chapter-3 before resuming
story-writer resume --story <name> --savepoint chapter-3
```

### 14.4 How to Check Savepoint Status

List savepoint names (fast, no data loaded):

```bash
python -m src.tools.savepoint_manager --operation list --name <story>
```

List savepoints with full data (can be large):

```bash
python -m src.tools.savepoint_manager --operation list-full --name <story>
```

Determine the next phase to run:

```bash
python -m src.tools.savepoint_manager --operation next-phase --name <story>
```

Example output:

```json
{
  "last_completed": "chapter_5_complete",
  "next_phase": "Phase 7 — chapter 6",
  "last_canonical": "wiki_populated",
  "last_chapter_complete": 5,
  "missing_below_top": [],
  "all_savepoints": ["init", "outline_complete", "wiki_populated", "chapter_1_complete", "chapter_2_complete", "chapter_3_complete", "chapter_4_complete", "chapter_5_complete"]
}
```

### 14.5 Common Resume Scenarios

**Scenario A: Power loss during chapter 12**

```bash
# Check status
python -m src.tools.savepoint_manager --operation next-phase --name my-story
# → "Phase 7 — chapter 12"

# Resume in TUI
story-writer tui --story my-story --resume
```

If the interruption happened during scene drafting, resume reloads the completed `chapter_12/scene_<M>.md` files and continues from the first missing scene rather than restarting Chapter 12 from scene 1.

**Scenario B: Want to restart from outline after changing the prompt**

```bash
# Clear savepoints (destructive)
python -m src.tools.savepoint_manager --operation clear --name my-story

# Or selectively remove phases and edit state.json to remove completed phases
# Then re-run
story-writer tui --story my-story
```

**Scenario C: Resume says "complete" but you want to add more chapters**

1. Edit `config.yml` to increase `wanted_chapters`
2. Edit `stories/<name>/state.json` to remove `assembly` and `complete` from completed phases
3. Delete `stories/<name>/savepoints/story_complete`
4. Resume:
   ```bash
   story-writer tui --story my-story --resume
   ```

**Scenario D: Resuming on a different machine**

1. Copy the entire `stories/<name>/` directory to the new machine
2. Ensure the new machine has the same `config.yml` (or equivalent)
3. Run `story-writer resume --story <name>`

---

## 15. General Operation

This section covers day-to-day workflows after you are familiar with the basics.

### 15.1 Inspecting Story State

Use `story_state` to read or modify story metadata without running the full pipeline:

```bash
# Read the entire state file
python -m src.tools.story_state --operation read --name my-story

# Read a specific field (dot notation)
python -m src.tools.story_state --operation read --name my-story --field generation.wanted_chapters

# Update a field
python -m src.tools.story_state --operation write --name my-story \
  --field generation.wanted_chapters --value 30

# List all stories
python -m src.tools.story_state --operation list
```

### 15.2 Browsing the Wiki

The wiki is a collection of Markdown files with YAML frontmatter. You can browse it with any text editor or with Obsidian:

```bash
# Open the wiki directory in your file manager
open stories/my-story/wiki/
```

Common wiki operations:

```bash
# Search wiki pages
python -m src.tools.wiki_search --story my-story --query "ancient AI"

# Read a page at a specific detail level
python -m src.tools.wiki_read --story my-story --page character:yuki-tanaka-oduya --level L2

# Assemble a token-budgeted snapshot for a scene
python -m src.tools.wiki_snapshot --story my-story --budget 2000
```

### 15.3 Manual Manuscript Assembly

If you want to assemble chapters without running the full pipeline (e.g., after manually editing chapter files):

```bash
python -m src.tools.story_assembler assemble --story-name my-story
```

This reads all `chapter_*.md` files in `stories/my-story/chapters/` and writes `stories/my-story/output/story.md`.

### 15.4 Changing Configuration Mid-Story

You can edit `config.yml` at any time, but only some changes take effect on resume:

| Change | Effect on Resume |
|--------|-----------------|
| `wanted_chapters` | Increases/decreases target; resume continues from last chapter |
| `model_api_base` | Takes effect immediately (next LLM call) |
| `enable_chapter_revisions` | Takes effect for next chapter |
| `chapter_quality` / `outline_quality` | Takes effect for next quality gate |
| `scene_generation_pipeline` | Takes effect for next chapter |

Changes to already-completed phases (e.g., outline chunk size) have no retroactive effect.

### 15.5 Cleaning Up Old Stories

```bash
# Remove a story and all its data (destructive)
rm -rf stories/old-story
rm -rf .chromadb/old-story

# Or selectively clear savepoints to restart while keeping chapters
python -m src.tools.savepoint_manager --operation clear --name old-story
```

### 15.6 Switching Between TUI and Headless

You can start a story in the TUI, approve the outline, then switch to headless for overnight chapter generation:

```bash
# 1. Run in TUI, approve the outline, then press Ctrl+C after character/settings finish
story-writer tui --story my-story

# 2. Resume headlessly
story-writer resume --story my-story
```

Conversely, you can run headlessly and then switch to TUI for manual review:

```bash
# 1. Run headlessly until completion
story-writer run --story my-story --batch

# 2. Later, launch TUI to review (the story is already complete)
story-writer tui --story my-story
```

### 15.7 Working with Character and Setting Sheets

Character and setting sheets are split across pointer JSON plus sibling markdown files. Edit the markdown bodies directly when you want to change sheet content:

```bash
# Edit a character sheet body
vim stories/my-story/characters/yuki-tanaka-oduya/sheet.md

# Edit a setting sheet body
vim stories/my-story/settings/europa-research-base/sheet.md
```

Each entity still has a companion JSON file, but markdown-bearing fields now store `{"$ref": ...}` pointers to sibling `.md` files:

```json
{
  "name": "Yuki Tanaka-Oduya",
  "sheet": {"$ref": "characters/yuki-tanaka-oduya/sheet.md"},
  "chunks": {
    "backstory": {"$ref": "characters/yuki-tanaka-oduya/chunks/backstory.md"},
    "personality": {"$ref": "characters/yuki-tanaka-oduya/chunks/personality.md"},
    "motivation": {"$ref": "characters/yuki-tanaka-oduya/chunks/motivation.md"},
    "relationships": {"$ref": "characters/yuki-tanaka-oduya/chunks/relationships.md"},
    "skills": {"$ref": "characters/yuki-tanaka-oduya/chunks/skills.md"},
    "arc": {"$ref": "characters/yuki-tanaka-oduya/chunks/arc.md"},
    "current_state": {"$ref": "characters/yuki-tanaka-oduya/chunks/current_state.md"}
  },
  "abridged": {"$ref": "characters/yuki-tanaka-oduya/abridged.md"},
  "summary": {"$ref": "characters/yuki-tanaka-oduya/summary.md"},
  "updated_at": "2026-04-30T12:00:00Z"
}
```

Setting sheets use the same top-level pointer shape but different chunk keys: `physical_description`, `atmosphere_mood`, `function_purpose`, `history_background`, `connections_relationships`, and `rules_constraints`.

After manual edits, the next chapter generation will pick up the updated sheets automatically. Runtime reads now expect pointer objects for markdown-backed fields, and new writes always persist markdown into sibling `.md` files. If an older story still has inline markdown in JSON, run `python3 src/tools/migrate_inline_markdown.py --name <story>` before continuing. Chapter prompts prefer `abridged`, then `summary`, then the first 300 characters of `sheet` when building character and setting context.

### 15.8 Common Daily Workflows

**Morning start:**
```bash
# Check which stories exist and their status
python -m src.tools.story_state --operation list
python -m src.tools.savepoint_manager --operation next-phase --name my-story

# Resume generation
story-writer resume --story my-story
```

**Reviewing last night's output:**
```bash
# Read the latest chapter
cat stories/my-story/chapters/chapter_12.md

# Check wiki updates
ls stories/my-story/wiki/events/

# Search for a character mention
python -m src.tools.wiki_search --story my-story --query "commander voss"
```

**Iterating on a prompt:**
```bash
# Rewrite prompt.md and refresh the state.json pointer automatically
story-writer resume --story my-story --prompt ~/new-prompt.txt

# Clear savepoints to restart from outline
python -m src.tools.savepoint_manager --operation clear --name my-story
story-writer tui --story my-story
```

---

## 16. Troubleshooting

### LLM endpoint not responding

```bash
# Verify your inference server is running (LM Studio, Ollama, or similar)
#   LM Studio: check the Developer tab shows "Server running"
#   Ollama:    ollama list

# Test API endpoint (defaults to LM Studio; adjust if using a different server)
curl http://127.0.0.1:1234/v1/models
```

### ChromaDB search returning no results

- Verify `.chromadb/` directory exists and is writable
- Check `embedding_model` is loaded in your inference server (e.g. LM Studio: load `nomic-embed-text`; Ollama: `ollama pull nomic-embed-text`)
- Verify `similarity_threshold` in `config.yml` is not set too high (try 0.5)

### Story generation producing inconsistent output

- Enable `enable_chapter_revisions: true` in `config.yml`
- Use the wiki tool CLIs or the Textual wiki panel to inspect wiki state
- Use `story-writer resume --story <name>` from the last savepoint rather than restarting

### Savepoint validation failing

- Check `savepoint_dir` in `config.yml` points to the correct path
- Check `stories/<name>/savepoints/pipeline_state.json` exists for resume
- Use `python -m src.tools.savepoint_manager --operation list --name <story>` to see savepoint names without loading full payloads
- Use `python -m src.tools.savepoint_manager --operation list-full --name <story>` only when you need the stored data itself

### Context window overflow

- Reduce `max_context_chunks` in `config.yml`
- Lower `outline_chunk_size` if `wanted_chapters` exceeds the current chunk window
- Enable `use_chunked_outline_generation: true` to reduce prompt sizes for long outlines; short outlines still stay on the per-chapter expansion path
- Reduce `scenes_per_chapter_max` if using the scene generation pipeline

### "The outline looks wrong"

**Symptoms:** Outline skips chapters, characters act out of character, pacing is uneven.

**Fix:**
1. In the TUI, type `revise <specific feedback>` at the outline approval gate
2. Example: `revise Chapter 5 needs a slower build-up. Add a scene where Elena discovers the letter before the confrontation.`
3. The outline planner will regenerate the outline with your feedback injected
4. If the revised outline is still wrong, repeat the approval-gate revision flow with tighter feedback or disable outline critique to inspect the raw outline first
5. If it never improves, reject the outline, edit your prompt file to add more constraints, clear savepoints, and restart

### "A chapter feels off"

**Symptoms:** Dialogue is wooden, a character knows something they shouldn't, the scene skips an important beat.

**Fix:**
1. At the chapter approval gate, type `revise <feedback>`
2. Example: `revise Dr. Okonkwo should not know about the signal yet. Remove his line about the anomaly.`
3. The chapter writer will regenerate with your feedback
4. If the chapter is fundamentally broken, you can also `reject` to halt and investigate the outline or wiki state

### "Generation stopped mid-chapter"

**Symptoms:** Power outage, LM Studio crashed, or you pressed `Ctrl+C`.

**Fix:**
```bash
story-writer resume --story <name>
```
The pipeline resumes from the latest `pipeline_state.json` snapshot. For converted ledger-backed loops, resume is finer-grained than the phase boundary: character and setting generation continue from the next missing work item, and scene-based chapter drafting continues from the next missing scene. Phases that are still single-shot continue to restart at the phase boundary.

### "Output is repetitive"

**Symptoms:** Same sentence structure, repeated phrases, characters echoing each other.

**Fix:**
1. Increase model temperature (add `?temperature=0.8` to the model URI in `config.yml`)
2. Enable both `enable_final_edit: true` and `enable_scrubbing: true` to feed prose and voice diagnostics into the final chapter polish pass
3. Enable `enable_chapter_revisions: true` and provide feedback like `revise Vary sentence openings; avoid starting three consecutive paragraphs with "She"`

### Scene generation pipeline issues

**Symptoms:** Chapters are too short, scenes feel disconnected, or scene count is wrong.

**Fix:**
1. Adjust `scenes_per_chapter_min` and `scenes_per_chapter_max` in `config.yml`
2. Ensure `scene_expansion_enabled: true` if you want scene-level expansion
3. Set `scene_generation_pipeline: true` to enable the per-scene generation path
4. If scenes are too fragmented, increase `scenes_per_chapter_min` and reduce `scenes_per_chapter_max` to a narrow range

---

## 17. Prompt Writing Tips

### What Makes a Good Story Prompt

The prompt is the single most important input. A strong prompt includes:

1. **Premise** — What happens? Who is involved? What is at stake?
2. **Genre and tone** — Fantasy? Hard sci-fi? Noir? Whimsical? Grim?
3. **Target audience** — Middle grade, young adult, adult literary
4. **Setting rules** — Magic system constraints, tech level, social structure
5. **Character sketches** — Name, age, background, motivation, flaw
6. **Themes** — What questions should the story explore?
7. **Length constraints** — Chapter count, approximate word count

### Genre Guidance

| Genre | What to specify |
|-------|-----------------|
| **Fantasy** | Magic system rules, power ceiling, cultural inspirations, magic cost |
| **Sci-fi** | Tech level, FTL rules (or lack thereof), alien biology, societal structure |
| **Mystery** | Crime type, detective style (amateur vs professional), red herring policy, tone (cozy vs hardboiled) |
| **Romance** | Relationship arc (enemies-to-lovers, second chance), heat level, obstacles |
| **Horror** | Type of fear (cosmic, body, psychological), gore level, hope vs despair balance |
| **Historical** | Era, historical figures (real or fictional), anachronism tolerance |

### Length Recommendations

| Output target | Prompt length | Detail needed |
|---------------|---------------|---------------|
| Short story (5–10 chapters) | 200–500 words | Core conflict + 1–2 characters |
| Novella (15–20 chapters) | 500–1,000 words | Full premise + 3–4 characters + setting rules |
| Novel (25–40 chapters) | 1,000–2,000 words | Detailed premise + full cast + setting + themes + pacing notes |

A longer, more detailed prompt consistently produces better outlines and fewer revision cycles.

### Example Prompts

#### Fantasy: The Last Glasswright

```text
Title: The Last Glasswright
Genre: High fantasy with artificer/magical-craftsmanship focus
Tone: Warm, melancholic, slowly building to epic
Target audience: Adult readers who enjoy Rothfuss and McKillip

Premise:
In the city of Verral, where magic is woven into glass,
Aelind the glasswright is the last living practitioner of
a lost technique: singing the glass awake. When a corrupt
guildmaster begins melting down ancestral stained-glass
windows to fuel a war machine, Aelind must choose between
hiding her gift or using it to forge a weapon that could
save her city — and destroy her soul.

Setting rules:
- Magic requires breath, blood, or tears; glass "remembers" the emotion used to shape it
- The guild controls all legal magic; unsanctioned crafters are exiled
- Verral is built on the ruins of a glass dragon's corpse; the bones are still warm
- No gods intervene directly; only relics and memory-magic work

Characters:
- Aelind: 34, shy, has a stutter that disappears when she sings to glass, grieving her mentor
- Guildmaster Sorn: 60s, genuinely believes the war is necessary, sees Aelind as a resource
- Kael: street thief who steals a piece of Aelind's glass and accidentally bonds with it

Themes:
- The cost of preservation vs the cost of action
- Art as resistance
- What we owe to the dead

Desired length: ~25 chapters, ~90,000 words
```

#### Sci-Fi: The Silence Between Stars

See [Section 3, Step 1](#step-1-write-a-prompt-file) for a complete sci-fi example.

#### Mystery: The Haymarket Cipher

```text
Title: The Haymarket Cipher
Genre: Historical mystery (Chicago, 1886)
Tone: Tense, atmospheric, morally ambiguous
Target audience: Adult readers who enjoy C.J. Tudor and The Alienist

Premise:
Clara Doherty is a typesetter at a German-language anarchist
newspaper in Chicago. When a bomb kills seven policemen at
the Haymarket rally, the police round up her entire print
shop. Clara knows one of her coworkers is guilty — but she
also knows the police are fabricating evidence to crush the
labour movement. She has three days before the trial to find
the real bomber without revealing that she, too, was at the
rally.

Setting rules:
- 1886 Chicago: soot, ice, gaslight, immigrant neighbourhoods
- The anarchist movement is real and varied; not all characters agree
- Clara is fictional but interacts with real historical figures (August Spies, Albert Parsons)
- No anachronistic technology; fingerprinting is brand-new and distrusted

Characters:
- Clara Doherty: 28, Irish-American, widow of a union organiser, can read five languages
- Inspector Bonfield: violent, politically motivated, genuinely believes anarchists are a threat
- Johann Most: real historical figure, editor, charismatic, possibly manipulative

Themes:
- Justice vs peace
- The individual vs the collective
- Who gets to tell the story of a tragedy

Desired length: ~20 chapters, ~70,000 words
```

---

## 18. Testing

### 18.1 Test Structure

```
tests/
├── unit/                    # Unit tests (fast, no LLM required)
│   └── test_<module>.py
└── integration/             # Integration tests (live LLM required)
  ├── test_end_to_end_headless.py
  ├── test_openai_async_provider_live.py
  ├── test_outline_generator_expand_to_scenes.py
  └── test_wiki_read_integration.py
```

### 18.2 Running Tests

```bash
# Unit tests only (default discovery target)
pytest

# Integration tests (requires live LLM endpoint)
pytest tests/integration/ -v -m integration

# Slow integration tests only
pytest tests/integration/ -v -m slow

# Headless batch E2E test
pytest tests/integration/test_end_to_end_headless.py -v -m "integration and slow"

# Single test file
pytest tests/unit/test_prompt_loader.py -v

# With coverage
pytest --cov=src tests/unit tests/integration
```

### 18.3 Integration Test Setup

Integration tests exercise the full pipeline against a live OpenAI-compatible LLM endpoint. Most integration files use `LLM_API_BASE` and default to `http://127.0.0.1:1234/v1`. The headless batch E2E test currently probes LM Studio directly at that same local address and skips when it is unavailable. The `slow` marker identifies integration coverage that may take multiple minutes.

See [docs/testing/integration-tests.md](testing/integration-tests.md) for detailed setup instructions.

---

## 19. Development

### 19.1 Code Style

| Language | Tool | Config |
|----------|------|--------|
| Python | ruff | `pyproject.toml` |

**Import ordering:** stdlib → third-party → local, alphabetised within groups.

**Naming:** `snake_case` for Python.

### 19.2 Commands

```bash
# Lint and auto-fix
ruff check --fix .

# Format
ruff format .

# Type check
mypy src/

# Full check (lint + format + type check)
ruff check --fix . && ruff format . && mypy src/
```

### 19.3 Feature-Based Workflow

1. **Implement the feature** — write production code
2. **Lint and type check** — fix all errors
3. **Write tests** — verify correctness
4. **Confirm tests pass** — before committing
5. **Refactor only after tests pass**

### 19.4 Architecture Decision Records

Significant architectural decisions are documented in `docs/planning/adr/`:

| ADR | Subject |
|-----|---------|
| 001 | Hybrid agent-tool architecture |
| 002 | Context window budget strategy |
| 003 | ChromaDB replaces PGvector |
| 004 | Progressive wiki memory system |
| 005 | Hybrid wiki context retrieval pipeline |
| 006 | OpenAI-compatible provider |
| 007 | Python-native orchestration |
| 008 | Retire application services layer |
| 009 | Opencode as primary agent runtime |

---

## 20. Quick Reference

```bash
# Start your local LLM server (e.g. LM Studio, or `ollama serve`)

# Quick one-command start with prompt file
story-writer tui --story test_story --prompt prompts/sample-story.md
story-writer run --story test_story --prompt prompts/sample-story.md --batch

# Or do it manually step-by-step:

# Quick one-command start with prompt file
story-writer tui --story test_story --prompt prompts/sample-story.md
story-writer run --story test_story --prompt prompts/sample-story.md --batch

# Or do it manually step-by-step:

# Initialize a new story
python -m src.tools.story_state --operation init --name test_story

# Write the prompt into story state (JSON-encode the text first)
printf '%s' "Your story prompt here" | python -c "import json,sys; print(json.dumps(sys.stdin.read()))" | \
  python -m src.tools.story_state --operation write --name test_story \
  --field story_prompt --value -

# Run Textual TUI
story-writer tui --story test_story

# Resume in TUI
story-writer tui --story test_story --resume

# Run headless pipeline
story-writer run --story test_story --batch

# Resume headlessly
story-writer resume --story story-name

# Check savepoint status
python -m src.tools.savepoint_manager --operation list --name story-name
python -m src.tools.savepoint_manager --operation next-phase --name story-name

# Assemble manuscript manually
python -m src.tools.story_assembler assemble --story-name story-name

# Search the wiki
python -m src.tools.wiki_search --story story-name --query "ancient AI"

# Read a wiki page
python -m src.tools.wiki_read --story story-name --page character:yuki --level L2

# Lint + format + type check
ruff check --fix . && ruff format . && mypy src/

# Run tests
pytest tests/unit/ -v
```

---

*For architecture details, see [docs/planning/adr/](planning/adr/). For tools reference, see [docs/tools.md](tools.md). For feature documentation, see [docs/features/](features/).*
