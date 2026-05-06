== REVIEW PACKAGE ==

=== BRANCH ===
feat/issue-274-story-creator-manual

=== COMMIT LOG ===
b3a027a docs: comprehensive story creator manual (#274)

=== CHANGED FILES ===
docs/manual.md

=== DIFF ===
diff --git a/docs/manual.md b/docs/manual.md
index c6053c4..b965c59 100644
--- a/docs/manual.md
+++ b/docs/manual.md
@@ -1,6 +1,6 @@
 # AI Story Writer — Comprehensive Manual
 
-**Version:** 1.0
+**Version:** 1.1
 **Last Updated:** April 2026
 **Stack:** Python 3.10+ · Textual · ChromaDB · OpenAI-compatible local LLM (LM Studio default)
 
@@ -9,17 +9,24 @@
 ## Table of Contents
 
 1. [System Overview](#1-system-overview)
-2. [Architecture](#2-architecture)
-3. [Installation & Setup](#3-installation--setup)
-4. [Configuration](#4-configuration)
-5. [Usage](#5-usage)
-6. [Project Structure](#6-project-structure)
-7. [Wiki Memory System](#7-wiki-memory-system)
-8. [Agents & Tools](#8-agents--tools)
-9. [Strategies](#9-strategies)
-10. [Testing](#10-testing)
-11. [Development](#11-development)
-12. [Troubleshooting](#12-troubleshooting)
+2. [Quick Start](#2-quick-start)
+3. [Creating Your First Story](#3-creating-your-first-story)
+4. [Understanding the Pipeline Phases](#4-understanding-the-pipeline-phases)
+5. [Architecture](#5-architecture)
+6. [Installation & Setup](#6-installation--setup)
+7. [Configuration](#7-configuration)
+8. [Configuration Cookbook](#8-configuration-cookbook)
+9. [Usage](#9-usage)
+10. [Project Structure](#10-project-structure)
+11. [Wiki Memory System](#11-wiki-memory-system)
+12. [Agents & Tools](#12-agents--tools)
+13. [Strategies](#13-strategies)
+14. [Working with Savepoints](#14-working-with-savepoints)
+15. [Troubleshooting](#15-troubleshooting)
+16. [Prompt Writing Tips](#16-prompt-writing-tips)
+17. [Testing](#17-testing)
+18. [Development](#18-development)
+19. [Quick Reference](#19-quick-reference)
 
 ---
 
@@ -37,9 +44,530 @@ AI Story Writer is an AI-powered long-form story generation system. It produces
 
 ---
 
-## 2. Architecture
+## 2. Quick Start
 
-### 2.1 Python-Native Pipeline Architecture
+### 2.1 Prerequisites Checklist
+
+Before starting, ensure you have:
+
+- [ ] **Python 3.10+** installed (`python --version`)
+- [ ] **Git** installed
+- [ ] A local **OpenAI-compatible LLM server** running:
+  - **LM Studio** (default): server running on `http://127.0.0.1:1234/v1` with a model loaded
+  - **Ollama**: `ollama serve` running with a model pulled (e.g., `ollama pull llama3:70b`)
+  - **llama.cpp** or **vLLM**: any server exposing the OpenAI chat completions endpoint
+- [ ] A text prompt file with your story idea (any `.txt` or `.md` file)
+- [ ] ~2 GB free disk space for models, stories, and ChromaDB indexes
+
+### 2.2 One-Command Startup
+
+After installation (see [Installation & Setup](#6-installation--setup)):
+
+```bash
+# 1. Initialize the story directory
+python -m src.tools.story_state --operation init --name test_story
+
+# 2. Write your prompt into story state
+cat > /tmp/prompt.txt << 'EOF'
+A space-opera epic about a rogue archaeologist who discovers
+an ancient AI buried beneath the ice of Europa. The story should
+blend hard sci-fi with mythic undertones, exploring themes of
+identity, sacrifice, and what it means to be alive.
+EOF
+python -c "import json,sys; print(json.dumps(sys.stdin.read()))" < /tmp/prompt.txt | \
+  python -m src.tools.story_state --operation write --name test_story \
+  --field story_prompt --value -
+
+# 3. Launch the interactive TUI
+story-writer tui --story test_story
+```
+
+### 2.3 Expected First-Run Output
+
+When you launch the TUI, you will see:
+
+1. **Left panel** — Phase tracker showing pipeline progress:
+   ```
+   Phases
+   > outline
+   - chapters
+   - wiki
+   - final-edit
+   - assembly
+   ```
+2. **Center panel** — Streaming LLM output showing outline generation in real time
+3. **Right panel** — Hidden by default; press `Ctrl+W` to toggle the wiki context panel
+4. **Footer** — An input box appears when the outline approval gate opens:
+   ```
+   Approval required. Type: approve / reject / revise <feedback>
+   ```
+
+If running headless:
+
+```bash
+story-writer run --story test_story
+```
+
+You will see a headless notice, then streaming progress in the terminal, ending with:
+
+```
+Pipeline complete: status=complete
+```
+
+### 2.4 Approximate Runtime for a Full Novel
+
+Runtimes depend heavily on model speed, context length, and revision settings.
+
+| Target | Chapters | Model Size | Approximate Time |
+|--------|----------|-----------|------------------|
+| Short story | 5–10 | 7B–13B | 30 min – 2 hours |
+| Novella | 15–20 | 13B–30B | 2 – 6 hours |
+| Full novel | 25–40 | 30B–70B | 6 – 24 hours |
+| Epic / series | 50+ | 70B+ | 1 – 3 days |
+
+Factors that increase runtime:
+- **Revisions enabled** (`enable_chapter_revisions: true`) — can double chapter time
+- **Outline critique** (`enable_outline_critique: true`) — adds 10–30 min
+- **Final edit pass** (`enable_final_edit: true`) — adds 10–20 min
+- **Streaming disabled** — harder to judge progress, same total time
+- **Slower endpoints** (Ollama on CPU vs LM Studio on GPU)
+
+Use `story-writer resume --story <name>` to continue after any interruption without losing progress.
+
+---
+
+## 3. Creating Your First Story
+
+This walkthrough takes you from a blank page to a finished manuscript.
+
+### Step 1: Write a Prompt File
+
+Create a plain-text file describing your story. The more detail you provide, the better the output. Save it anywhere (e.g., `~/prompts/my-story.txt`):
+
+```text
+Title: The Silence Between Stars
+Genre: Hard science fiction with mythic undertones
+Tone: Somber, contemplative, slowly escalating tension
+Target audience: Adult readers who enjoy Le Guin and Reynolds
+
+Premise:
+Dr. Yuki Tanaka-Oduya is a xenogeologist stationed on Europa's
+subsurface research base. When her seismic probes detect a
+regular, artificial signal from the moon's iron core, she
+must decide whether to report it to Earth — knowing that
+confirmation will trigger a corporate land-rush that will
+destroy the pristine environment she has spent her career
+studying.
+
+Key themes:
+- The conflict between scientific preservation and human expansion
+- What "ownership" means when you are not the first intelligent species
+- Sacrifice for a principle that no one else values
+
+Setting constraints:
+- No faster-than-light travel; Earth is a 30-minute light-delay
+- The base has only six permanent staff
+- Europa's ocean is genuinely hostile; suits fail, ice quakes happen
+- The alien artefact is ancient, damaged, and not hostile — but not helpful either
+
+Character notes:
+- Yuki: 48, Nigerian-Japanese, widowed, dry sense of humour, drinks too much coffee
+- Commander Voss: by-the-book, secretly terrified of being forgotten
+- Dr. Okonkwo: junior geologist, optimistic, represents the future Yuki is protecting
+
+Desired length: ~25 chapters, ~80,000 words total
+```
+
+**Tip:** Include genre, tone, target audience, core conflict, setting rules, and character sketches. The system uses every paragraph.
+
+### Step 2: Configure `config.yml`
+
+The project ships with a working `config.yml`. For a first run, you only need to verify two things:
+
+```yaml
+# config.yml — minimal required settings for first run
+
+models:
+  # Point to whatever model you have loaded in your local server
+  initial_outline_writer: "openai-compat://llama3:70b"
+  chapter_stage1_writer: "openai-compat://llama3:70b"
+  info_model: "openai-compat://llama3:70b"
+  embedding_model: "openai-compat://nomic-embed-text"
+
+generation:
+  wanted_chapters: 25
+  enable_chapter_revisions: true
+  stream: true
+  debug: true
+
+infrastructure:
+  model_api_base: "http://127.0.0.1:1234/v1"
+  embedding_model: "openai-compat://nomic-embed-text"
+  vector_dimensions: 1536
+```
+
+**What you must change:**
+- `models.*` entries — match the model loaded in your inference server
+- `infrastructure.model_api_base` — match your server's URL
+
+**What you can leave alone for now:**
+- Quality thresholds, revision counts, and strategy settings (defaults are sensible)
+- Output and savepoint directories (default to project-relative paths)
+
+### Step 3: Initialize the Story and Load the Prompt
+
+Create the story directory and write your prompt into `state.json`:
+
+```bash
+# Initialize the story directory
+python -m src.tools.story_state --operation init --name my-first-story
+
+# Load your prompt file into story state
+python -c "import json,sys; print(json.dumps(sys.stdin.read()))" < ~/prompts/my-story.txt | \
+  python -m src.tools.story_state --operation write --name my-first-story \
+  --field story_prompt --value -
+```
+
+**Alternative:** You can also edit `stories/my-first-story/state.json` directly and add a `story_prompt` field containing your prompt text.
+
+### Step 4: Launch TUI or Run Headless
+
+**Interactive mode (recommended for first stories):**
+
+```bash
+story-writer tui --story my-first-story
+```
+
+This opens the Textual interface where you can approve or reject each major phase.
+
+**Headless mode (good for overnight runs):**
+
+```bash
+story-writer run --story my-first-story --batch
+```
+
+`run` always uses `NullApprovalGate` internally, so it behaves headlessly even when `--batch` is omitted. The flag is reserved for future interactive surfaces.
+
+### Step 5: Approve, Reject, or Revise the Outline
+
+When the outline finishes generating, the TUI pauses and asks for approval:
+
+```
+Approval required. Type: approve / reject / revise <feedback>
+```
+
+- **`approve`** — Accept the outline and continue to character generation
+- **`reject`** — Halt the pipeline cleanly. You can resume later or restart with a different prompt
+- **`revise <feedback>`** — Reject the outline, send your feedback back to the outline planner, and trigger a revision pass. Example:
+  ```
+  revise The pacing is too fast in the middle act. Add a chapter where Yuki discovers the corporate spy before the climax.
+  ```
+
+**How the gate works:**
+- The outline quality threshold (`outline_quality`, default 87) is evaluated before the gate opens
+- If the outline scores below the threshold, the system may auto-revise up to `outline_max_revisions` times before asking you
+- Your `revise` feedback is injected directly into the next outline generation prompt
+- Rejecting does not delete savepoints; you can resume or inspect the generated outline at any time
+
+### Step 6: Monitor Chapter Generation
+
+After the outline is approved, the pipeline enters the **Chapter Loop**:
+
+1. **Phase tracker** (left panel) highlights `chapters`
+2. **Streaming output** (center panel) shows each scene being generated in real time
+3. **Wiki panel** (right panel, `Ctrl+W`) shows wiki pages being created or updated after each approved chapter
+
+Per-chapter approval:
+- Each chapter also triggers an approval gate before it is written to disk
+- `approve` — saves the chapter to `stories/<name>/chapters/chapter_{N}.md` and updates the wiki
+- `revise <feedback>` — regenerates the chapter with your notes
+- `reject` — halts the pipeline after the current chapter
+
+**What to watch for:**
+- **Inconsistencies** in character names or setting details → use `revise` with specific corrections
+- **Repetitive phrasing** → note it in feedback; the system will vary sentence structure
+- **Pacing issues** → request more or fewer scenes per chapter
+
+### Step 7: Review and Export the Final Manuscript
+
+When the last chapter is approved, the pipeline proceeds to:
+
+1. **Final Edit** (if enabled) — a polish pass over all approved chapters
+2. **Assembly** — combines all chapters into a single manuscript
+
+Final files are written to:
+
+```
+stories/my-first-story/
+├── output/
+│   ├── story.md           # Assembled manuscript (all chapters)
+│   └── story_edited.md    # Final-edit manuscript (if final edit was enabled)
+```
+
+You can also manually assemble at any time:
+
+```bash
+python -m src.tools.story_assembler assemble --story-name my-first-story
+```
+
+### Expected File Tree After Completion
+
+```
+stories/my-first-story/
+├── state.json                    # Pipeline state and metadata
+├── outline.json                  # Approved outline
+├── chapters/
+│   ├── chapter_1.md
+│   ├── chapter_2.md
+│   ├── chapter_3.md
+│   └── ...                       # One file per approved chapter
+├── output/
+│   ├── story.md                  # Final assembled manuscript
+│   └── story_edited.md           # Post-final-edit manuscript (optional)
+├── characters/
+│   ├── yuki-tanaka-oduya.json    # Character sheet (name, sheet, chunks, summary, updated_at)
+│   ├── commander-voss.json
+│   └── ...
+├── settings/
+│   ├── europa-research-base.json # Setting sheet (same JSON schema as characters)
+│   └── ...
+├── savepoints/
+│   ├── pipeline_state.json       # Resume state (single JSON file)
+│   ├── outline_complete          # Milestone marker
+│   ├── arc_analysis_complete     # Milestone marker
+│   ├── chapter_1_complete        # Chapter content savepoint
+│   ├── chapter_2_complete
+│   └── ...                       # Additional per-step savepoints
+└── wiki/
+    ├── _schema.md                # Wiki schema and conventions
+    ├── characters/
+    ├── locations/
+    ├── events/
+    ├── factions/
+    ├── items/
+    ├── plot-threads/
+    ├── world-rules/
+    ├── themes/
+    ├── relationships/
+    ├── timeline/
+    ├── chapters/
+    └── contradictions/
+```
+
+**Key points about the file tree:**
+- `state.json` is the source of truth for story metadata and progress
+- `savepoints/pipeline_state.json` is the resume checkpoint (single JSON file)
+- Individual step savepoints (e.g., `outline_complete`, `chapter_3_complete`) are separate files in the same directory
+- The `wiki/` directory is fully Obsidian-compatible — open it in Obsidian to browse linked pages
+
+---
+
+## 4. Understanding the Pipeline Phases
+
+The story generation pipeline is divided into nine primary phases. Each phase writes a savepoint on completion, so you can resume after any interruption.
+
+### ASCII Flow Diagram
+
+```
+┌─────────┐     ┌──────────┐     ┌─────────────────┐
+│  Init   │────▶│ Outline  │────▶│ Outline Approval│
+│ (setup) │     │(generate)│     │   (user gate)   │
+└─────────┘     └──────────┘     └─────────────────┘
+                                        │
+                    ┌───────────────────┘
+                    ▼
+           ┌─────────────────┐
+           │ Narrative Arc   │
+           │   Analysis      │
+           └─────────────────┘
+                    │
+    ┌───────────────┼───────────────┐
+    ▼               ▼               ▼
+┌─────────┐   ┌──────────┐   ┌───────────┐
+│Characters│   │ Settings │   │ Wiki Init │
+│(sheets)  │   │ (sheets) │   │(idempotent)│
+└─────────┘   └──────────┘   └───────────┘
+    │               │               │
+    └───────────────┴───────────────┘
+                    │
+                    ▼
+         ┌──────────────────┐
+         │   Chapter Loop   │
+         │ (generate → gate │
+         │  → approve → wiki│
+         │  → repeat)       │
+         └──────────────────┘
+                    │
+                    ▼
+         ┌──────────────────┐     ┌──────────┐
+         │   Final Edit     │────▶│ Assembly │
+         │ (conditional)    │     │ (manuscript)
+         └──────────────────┘     └──────────┘
+```
+
+### Phase 1: Init
+
+**What the system does:**
+- Validates the story name and creates the story directory structure if missing
+- Loads `config.yml` and resolves model endpoints
+- Initializes the `PipelineState` object
+- Writes the first savepoint (`init`)
+
+**Artefacts produced:**
+- `stories/<name>/savepoints/init`
+- `stories/<name>/savepoints/pipeline_state.json` (initial snapshot)
+
+**User action needed:** None
+
+**Approximate duration:** < 1 second
+
+### Phase 2: Outline
+
+**What the system does:**
+- Loads your story prompt from `state.json`
+- Delegates to the `outline-planner` agent
+- Generates a detailed chapter-by-chapter outline
+- Optionally runs critique and refinement loops (if `enable_outline_critique: true`)
+- Persists the approved outline to savepoints
+
+**Artefacts produced:**
+- `stories/<name>/savepoints/outline_complete`
+- `stories/<name>/outline.json` (structured outline data)
+
+**User action needed:**
+- Approve, reject, or revise via the approval gate (TUI) or auto-approve (headless)
+
+**Approximate duration:** 5–20 minutes (longer with critique loops)
+
+### Phase 2.5: Narrative Arc Analysis
+
+**What the system does:**
+- Loads the approved outline
+- Delegates to the `story-planner` agent
+- Streams one advisory arc assessment (promise/payoff, tension curve, pacing)
+- Persists `state.arc_result` and writes `arc_analysis_complete`
+- On agent error, emits a skip message and continues (non-blocking)
+
+**Artefacts produced:**
+- `stories/<name>/savepoints/arc_analysis_complete`
+- `stories/<name>/savepoints/arc_assessment` (detailed analysis text)
+
+**User action needed:** None (advisory only)
+
+**Approximate duration:** 2–5 minutes
+
+### Phase 3: Characters
+
+**What the system does:**
+- Extracts character names from the approved outline
+- Generates one JSON sheet per character via the `character_manager`
+- Each sheet contains: `name`, `sheet` (full text), `chunks` (segmented details), `summary`, `updated_at`
+- If name extraction returns invalid JSON, the phase degrades gracefully and the pipeline continues
+
+**Artefacts produced:**
+- `stories/<name>/savepoints/characters_complete`
+- `stories/<name>/characters/<slug>.json` (one per character)
+
+**User action needed:** None
+
+**Approximate duration:** 2–10 minutes (scales with character count)
+
+### Phase 4: Settings
+
+**What the system does:**
+- Extracts setting/location names from the outline
+- Generates one JSON sheet per setting
+- Same JSON schema as characters: `name`, `sheet`, `chunks`, `summary`, `updated_at`
+
+**Artefacts produced:**
+- `stories/<name>/savepoints/settings_complete`
+- `stories/<name>/settings/<slug>.json` (one per setting)
+
+**User action needed:** None
+
+**Approximate duration:** 2–5 minutes
+
+### Phase 5: Wiki Initialization
+
+**What the system does:**
+- Idempotently ensures the `stories/<name>/wiki/` directory structure exists
+- Creates subdirectories, index, log, and schema template if missing
+- Safe to rerun on resume; skips creation if wiki already present
+
+**Artefacts produced:**
+- `stories/<name>/wiki/_schema.md`
+- `stories/<name>/wiki/characters/`
+- `stories/<name>/wiki/locations/`
+- `stories/<name>/wiki/events/`
+- And other wiki subdirectories
+
+**User action needed:** None
+
+**Approximate duration:** < 1 second
+
+### Phase 6: Chapter Loop
+
+**What the system does:**
+- For each chapter (1 to `wanted_chapters`):
+  1. Loads abridged character and setting sheet context
+  2. Generates chapter text via the `chapter-writer` agent
+  3. Presents the chapter for approval (gate)
+  4. On approval, writes `stories/<name>/chapters/chapter_{N}.md`
+  5. Calls `wiki_maintainer` to extract structured data and persist wiki pages
+  6. Runs `consistency_checker` (streams findings but does not block persistence)
+  7. Saves a chapter-level savepoint (`chapter_{N}_complete`)
+
+**Artefacts produced:**
+- `stories/<name>/chapters/chapter_1.md` through `chapter_{N}.md`
+- `stories/<name>/savepoints/chapter_1_complete` through `chapter_{N}_complete`
+- Updated wiki pages under `stories/<name>/wiki/`
+
+**User action needed:**
+- Per-chapter approval gate in TUI mode
+- None in headless mode (auto-approves all chapters)
+
+**Approximate duration:** 5–20 minutes per chapter (depending on model speed, scene count, and revisions)
+
+### Phase 7: Final Edit (conditional)
+
+**What the system does:**
+- Enabled unless `generation.enable_final_edit` is explicitly set to `false`
+- Loads `prompts/agents/final-editor.md`
+- Streams one editing pass per approved chapter (voice consistency, pacing, prose polish)
+- Falls back to original chapter content if the model returns empty output
+- Writes the edited manuscript to `stories/<name>/output/story_edited.md`
+- Persists `final_edit_complete`
+
+**Artefacts produced:**
+- `stories/<name>/output/story_edited.md`
+- `stories/<name>/savepoints/final_edit_complete`
+
+**User action needed:** None
+
+**Approximate duration:** 10–20 minutes total (scales with chapter count)
+
+### Phase 8: Assembly
+
+**What the system does:**
+- Assembles the final manuscript from the current `state.approved_chapters`
+- Writes `stories/<name>/output/story.md`
+- Raises `StoryGenerationError` if no approved chapter content is found
+- Persists the `story_complete` milestone
+
+**Artefacts produced:**
+- `stories/<name>/output/story.md`
+- `stories/<name>/savepoints/story_complete`
+- Updated `stories/<name>/savepoints/pipeline_state.json` with `status: complete`
+
+**User action needed:** None
+
+**Approximate duration:** < 1 second
+
+---
+
+## 5. Architecture
+
+### 5.1 Python-Native Pipeline Architecture
 
 The system uses a **Python-native prompt-and-tool architecture** during active runtime. Prompt-defined pipeline phases live under `prompts/agents/`, and Python orchestration code loads those prompts directly (see [ADR 007](planning/adr/007-python-native-orchestration.md)):
 
@@ -52,7 +580,7 @@ The system uses a **Python-native prompt-and-tool architecture** during active r
 
 **Key principle:** Prompt-defined phases make decisions; tools execute operations. Runtime orchestration never directly manipulates story files, wiki pages, or savepoints without going through the relevant Python tool or service boundary.
 
-### 2.2 Clean Architecture Layers (Python Domain)
+### 5.2 Clean Architecture Layers (Python Domain)
 
 ```
 src/domain/          → Entities, value objects (core business rules, no dependencies)
@@ -64,10 +592,10 @@ src/tools/           → Python tool implementations and ad-hoc CLIs
 
 Each layer depends only on inner layers. `src/domain/` has zero external dependencies.
 
-### 2.3 Data Flow
+### 5.3 Data Flow
 
 ```
-User prompt (.txt)
+User prompt (loaded from state.json)
     ↓
 story-writer CLI / orchestrator
     ↓
@@ -90,16 +618,16 @@ stories/<name>/  (chapters, wiki, savepoints)
 
 ---
 
-## 3. Installation & Setup
+## 6. Installation & Setup
 
-### 3.1 Prerequisites
+### 6.1 Prerequisites
 
 | Requirement | Version | Notes |
 |-------------|---------|-------|
 | Python | 3.10+ | Required by `pyproject.toml` |
 | OpenAI-compatible LLM server | any | LM Studio (default), Ollama, llama.cpp, vLLM, etc. |
 
-### 3.2 Installation Steps
+### 6.2 Installation Steps
 
 ```bash
 # 1. Clone the repository
@@ -115,13 +643,13 @@ pip install -r requirements.txt
 pip install -e .
 
 # 4. Copy and configure
-cp config.example.sh config.sh
-# Edit config.sh with your model paths and API endpoints
+#    The project reads config.yml in the repo root
+#    Edit models and model_api_base to match your inference server
 ```
 
-### 3.3 Model Configuration
+### 6.3 Model Configuration
 
-Models are configured in `config.md` under the `models:` YAML block. The system uses OpenAI-compatible endpoints:
+Models are configured in `config.yml` under the `models:` YAML block. The system uses OpenAI-compatible endpoints:
 
 ```yaml
 models:
@@ -133,7 +661,7 @@ models:
 
 The `openai-compat://` prefix routes to the configured OpenAI-compatible API. Override `model_api_base` in `infrastructure:` to change the endpoint (default: `http://127.0.0.1:1234/v1`).
 
-### 3.4 Opencode Agent Runtime Setup
+### 6.4 Opencode Agent Runtime Setup
 
 The Python story-generation runtime above is separate from the Opencode agent runtime used for the Copilot-to-Opencode migration work. That migration config lives in the repository root `opencode.json`, where the default model is now `openrouter/moonshotai/kimi-k2.6` and the OpenRouter provider registry includes Kimi K2.6, Qwen3.6 Plus, and GLM 5.1.
 
@@ -141,11 +669,11 @@ Developer-local credentials and user-level MCP servers are not committed to the
 
 ---
 
-## 4. Configuration
+## 7. Configuration
 
-All configuration lives in `config.md` (YAML frontmatter at the top of the file). No environment variables or secrets are required — all providers use local inference.
+All configuration lives in `config.yml` in the repository root. No secrets are required — all providers use local inference. Optional environment variables include `LLM_API_BASE` and `STORIES_DIR`.
 
-### 4.1 Generation Settings
+### 7.1 Generation Settings
 
 | Setting | Default | Description |
 |---------|---------|-------------|
@@ -155,7 +683,7 @@ All configuration lives in `config.md` (YAML frontmatter at the top of the file)
 | `outline_max_revisions` | 3 | Max outline revision passes |
 | `chapter_max_revisions` | 3 | Max chapter revision passes |
 | `enable_chapter_revisions` | true | Enable chapter revision loop |
-| `enable_final_edit` | false | Run final polish pass |
+| `enable_final_edit` | true* | Run final polish pass |
 | `enable_scrubbing` | true | Remove redundant/phrases |
 | `strategy` | "outline-chapter" | Writing strategy |
 | `use_chunked_outline_generation` | true | Generate outline in chunks |
@@ -163,7 +691,9 @@ All configuration lives in `config.md` (YAML frontmatter at the top of the file)
 | `stream` | true | Stream LLM output |
 | `debug` | true | Enable debug logging |
 
-### 4.2 Infrastructure Settings
+\* `enable_final_edit` defaults to `true` in the orchestrator. It is only disabled if you explicitly set `generation.enable_final_edit: false` in `config.yml`.
+
+### 7.2 Infrastructure Settings
 
 | Setting | Default | Description |
 |---------|---------|-------------|
@@ -176,7 +706,7 @@ All configuration lives in `config.md` (YAML frontmatter at the top of the file)
 | `similarity_threshold` | 0.7 | ChromaDB similarity threshold |
 | `max_context_chunks` | 20 | Max RAG chunks per scene |
 
-### 4.3 Model Role Assignments
+### 7.3 Model Role Assignments
 
 Each phase of the pipeline uses a specific model:
 
@@ -193,9 +723,114 @@ Each phase of the pipeline uses a specific model:
 
 ---
 
-## 5. Usage
+## 8. Configuration Cookbook
+
+These presets are starting points. Copy the relevant block into your `config.yml` under the `generation:` key.
+
+### 8.1 Fast Prototype Preset
+
+For quickly testing a concept or iterating on a short story (~5 chapters, low quality, fast turnaround):
+
+```yaml
+generation:
+  wanted_chapters: 5
+  outline_min_revisions: 0
+  outline_max_revisions: 1
+  chapter_min_revisions: 0
+  chapter_max_revisions: 1
+  enable_chapter_revisions: false
+  enable_outline_critique: false
+  enable_final_edit: false
+  enable_scrubbing: false
+  use_chunked_outline_generation: false
+  stream: true
+  debug: true
+```
+
+| Setting | Value | Why |
+|---------|-------|-----|
+| `wanted_chapters` | 5 | Short test run |
+| `enable_chapter_revisions` | false | Skip revision loops |
+| `enable_outline_critique` | false | Skip critique phase |
+| `enable_final_edit` | false | Skip polish pass |
+| `use_chunked_outline_generation` | false | Faster single-pass outline |
+
+### 8.2 High Quality Novel Preset
+
+For a polished, full-length novel (~25 chapters, revisions, critique):
+
+```yaml
+generation:
+  wanted_chapters: 25
+  outline_min_revisions: 2
+  outline_max_revisions: 5
+  chapter_min_revisions: 1
+  chapter_max_revisions: 3
+  enable_chapter_revisions: true
+  enable_outline_critique: true
+  outline_critique_iterations: 5
+  enable_final_edit: true
+  enable_scrubbing: true
+  use_chunked_outline_generation: true
+  outline_chunk_size: 10
+  stream: true
+  debug: false
+```
+
+| Setting | Value | Why |
+|---------|-------|-----|
+| `outline_max_revisions` | 5 | More chances to refine outline |
+| `chapter_max_revisions` | 3 | Per-chapter quality loop |
+| `enable_outline_critique` | true | Iterative outline refinement |
+| `enable_final_edit` | true | Post-generation polish pass |
+| `debug` | false | Cleaner output |
+
+### 8.3 Short Story Preset
+
+For a contained short story (~10 chapters, no revisions, fast):
+
+```yaml
+generation:
+  wanted_chapters: 10
+  outline_min_revisions: 0
+  outline_max_revisions: 2
+  chapter_min_revisions: 0
+  chapter_max_revisions: 0
+  enable_chapter_revisions: false
+  enable_outline_critique: false
+  enable_final_edit: false
+  enable_scrubbing: true
+  use_chunked_outline_generation: false
+  stream: true
+  debug: true
+```
+
+| Setting | Value | Why |
+|---------|-------|-----|
+| `wanted_chapters` | 10 | Novella length |
+| `chapter_max_revisions` | 0 | No per-chapter revision loop |
+| `enable_scrubbing` | true | Still clean up redundant prose |
+
+### 8.4 Settings Change Summary Table
+
+| Setting | Fast Prototype | High Quality Novel | Short Story |
+|---------|---------------|-------------------|-------------|
+| `wanted_chapters` | 5 | 25 | 10 |
+| `outline_min_revisions` | 0 | 2 | 0 |
+| `outline_max_revisions` | 1 | 5 | 2 |
+| `chapter_min_revisions` | 0 | 1 | 0 |
+| `chapter_max_revisions` | 1 | 3 | 0 |
+| `enable_chapter_revisions` | false | true | false |
+| `enable_outline_critique` | false | true | false |
+| `enable_final_edit` | false | true | false |
+| `enable_scrubbing` | false | true | true |
+| `use_chunked_outline_generation` | false | true | false |
+
+---
+
+## 9. Usage
 
-### 5.1 Python CLI
+### 9.1 Python CLI
 
 ```bash
 story-writer --help
@@ -209,7 +844,7 @@ Available subcommands:
 | `story-writer run --story <name> [--batch]` | Run the headless Python-native pipeline |
 | `story-writer resume --story <name> [--savepoint <name>]` | Resume from the latest persisted pipeline state. `--savepoint` validates the name exists but does not restore an older snapshot. |
 
-`run` currently uses `NullApprovalGate` internally, so it behaves headlessly even when `--batch` is omitted. When you omit `--batch`, the CLI prints a headless notice before starting the run. The flag remains for forward compatibility with later interactive surfaces.
+`run` always uses `NullApprovalGate` internally, so it behaves headlessly even when `--batch` is omitted. When you omit `--batch`, the CLI prints a headless notice before starting the run. The flag remains for forward compatibility with later interactive surfaces.
 
 #### Textual TUI
 
@@ -234,7 +869,7 @@ Keybindings:
 
 See [Textual TUI](./features/textual-tui.md) for the thread model, approval-gate bridge, and test coverage.
 
-### 5.2 Prompt Asset Locations
+### 9.2 Prompt Asset Locations
 
 Issue #164 removed the remaining OpenCode runtime artefacts from the repository. Reusable prompt content that still matters to the Python-native pipeline now lives in these locations:
 
@@ -242,7 +877,7 @@ Issue #164 removed the remaining OpenCode runtime artefacts from the repository.
 - `prompts/agents/regenerate.md`
 - `prompts/skills/` — relocated skill reference material used by prompt-defined phases
 
-### 5.3 Story Generation Pipeline
+### 9.3 Story Generation Pipeline
 
 The current Python-native orchestrator slice runs through these phases:
 
@@ -300,18 +935,20 @@ Phase 7: Final Edit (conditional)
 Phase 8: Assembly
   → Assemble final manuscript from the current `state.approved_chapters`
   → Write `stories/<name>/output/story.md`
+  → Raises `StoryGenerationError` if no approved chapter content is found
 ```
 
 Current implementation note: the PRD's initial wiki population pass, chapter-outline-expander, quality-reviewer, and prose-scrubber are not yet wired into `src/presentation/orchestrator.py`. Wiki directory initialization is now handled idempotently before the chapter loop.
 
 ---
 
-## 6. Project Structure
+## 10. Project Structure
 
 ```
 llm-story-writer/
-├── config.md                  # All configuration (YAML frontmatter)
-├── config.example.sh          # Shell env config template
+├── config.yml                  # All configuration (YAML)
+├── config-guide.md             # Configuration reference and examples
+├── config.example.sh           # Shell env config template
 │
 ├── src/                       # Python domain logic
 │   ├── domain/
@@ -371,6 +1008,7 @@ llm-story-writer/
 │       ├── characters/       # Character JSON sheets
 │       ├── settings/         # Setting JSON sheets
 │       ├── savepoints/       # Savepoint files
+│       │   └── pipeline_state.json  # Resume checkpoint
 │       └── wiki/             # Progressive wiki
 │           ├── _schema.md
 │           ├── characters/
@@ -400,18 +1038,18 @@ llm-story-writer/
 
 ---
 
-## 7. Wiki Memory System
+## 11. Wiki Memory System
 
 The **progressive wiki memory system** ([ADR 004](planning/adr/004-progressive-wiki-memory-system.md)) maintains structured story knowledge as interlinked markdown pages with YAML frontmatter.
 
-### 7.1 Design Goals
+### 11.1 Design Goals
 
 - Eliminate knowledge re-derivation (agents receive authoritative world state)
 - Proactive contradiction detection before errors propagate
 - Token-efficient context budgeting via hierarchical detail levels
 - Human-readable, git-versionable, Obsidian-compatible
 
-### 7.2 Page Types
+### 11.2 Page Types
 
 | Type | Description |
 |------|-------------|
@@ -428,7 +1066,7 @@ The **progressive wiki memory system** ([ADR 004](planning/adr/004-progressive-w
 | `chapter` | Chapter synopsis and metadata |
 | `contradictions` | Log of detected contradictions |
 
-### 7.3 Confidence Taxonomy
+### 11.3 Confidence Taxonomy
 
 Every wiki fact carries a confidence level:
 
@@ -438,7 +1076,7 @@ Every wiki fact carries a confidence level:
 | `planned` | Outlined but not yet written |
 | `speculative` | Inferred or implied by the agent |
 
-### 7.4 Detail Levels
+### 11.4 Detail Levels
 
 Wiki pages support three hierarchical summary levels:
 
@@ -448,14 +1086,14 @@ Wiki pages support three hierarchical summary levels:
 | `L2` | ~150 tokens | Brief summary for scene pre-generation context |
 | `L3` | ~500 tokens | Full description for complex scene decisions |
 
-### 7.5 Wiki Update Lifecycle
+### 11.5 Wiki Update Lifecycle
 
 1. **Initial population** (before chapter generation): `wiki-extract` reads the outline plus character and setting sheets, creates the first wiki page set, and writes retrieval-ready L1/L2/L3 detail levels
 2. **Post-chapter persistence** (after each accepted chapter): `wiki-maintainer` calls `update_wiki_from_chapter()`, the `wiki/extract_from_chapter` prompt returns structured JSON, and `run_batch()` persists new pages, state changes, aliases, and timeline events under `stories/<name>/wiki/`
 3. **Chapter-level lint** (after each chapter): `wiki-lint` checks consistency against the ConStory-Bench error taxonomy
 4. **Pre-generation snapshot** (before each scene): `wiki-snapshot` assembles a token-budgeted world state snapshot from the current wiki
 
-### 7.6 Wikilink Syntax
+### 11.6 Wikilink Syntax
 
 Wiki pages cross-reference each other using `[[wikilink]]` syntax:
 
@@ -467,9 +1105,9 @@ Wiki pages cross-reference each other using `[[wikilink]]` syntax:
 
 ---
 
-## 8. Agents & Tools
+## 12. Agents & Tools
 
-### 8.1 Agents
+### 12.1 Agents
 
 Agent system prompts now live in `prompts/agents/` as Markdown files. `src/infrastructure/prompts/agent_prompt_loader.py` reads those prompt bodies directly and strips YAML frontmatter before returning the reusable instruction text.
 
@@ -482,7 +1120,7 @@ Agent system prompts now live in `prompts/agents/` as Markdown files. `src/infra
 
 **Orchestrator Pipeline Phases:** Init → Outline → Approval → Narrative Arc → Characters → Settings → Wiki Init → Chapter Loop → Final Edit → Assembly
 
-### 8.2 Tools
+### 12.2 Tools
 
 Tools are Python modules under `src/tools/`. The runtime imports them directly or calls the same Python services in-process; there is no TypeScript wrapper layer anymore.
 
@@ -521,7 +1159,7 @@ Tools are Python modules under `src/tools/`. The runtime imports them directly o
 |------|---------|
 | `critique_runner.py` | Run quality critique on outline or chapter |
 
-### 8.3 Tool Architecture
+### 12.3 Tool Architecture
 
 ```
 Agent call
@@ -540,11 +1178,11 @@ Result returned to agent
 
 ---
 
-## 9. Strategies
+## 13. Strategies
 
 The system supports pluggable story writing strategies via the strategy pattern.
 
-### 9.1 Outline-Chapter Strategy (default)
+### 13.1 Outline-Chapter Strategy (default)
 
 ```
 1. Extract story elements and context from prompt
@@ -553,31 +1191,364 @@ The system supports pluggable story writing strategies via the strategy pattern.
 4. Generate metadata (title, summary, tags)
 ```
 
-**Config:** `strategy: "outline-chapter"` in `config.md`
+**Config:** `strategy: "outline-chapter"` in `config.yml`
 
 **Prompts:** `prompts/chapters/`, `prompts/outline/`
 
-### 9.2 Stream-of-Consciousness Strategy
+### 13.2 Stream-of-Consciousness Strategy
 
 Generates stories in a flowing, associative narrative style without a formal outline.
 
-**Config:** `strategy: "stream-of-consciousness"` in `config.md`
+**Config:** `strategy: "stream-of-consciousness"` in `config.yml`
 
 **Prompts:** `prompts/stream_of_consciousness/`
 
-### 9.3 Adding a Custom Strategy
+### 13.3 Adding a Custom Strategy
 
 1. Create `src/application/strategies/<my_strategy>/`
 2. Implement the strategy class inheriting from `StoryStrategy`
 3. Add prompts under `prompts/<my_strategy>/`
 4. Register in `strategy_factory.py`
-5. Set `strategy: "my_strategy"` in `config.md`
+5. Set `strategy: "my_strategy"` in `config.yml`
 
 ---
 
-## 10. Testing
+## 14. Working with Savepoints
+
+### 14.1 Why Savepoints Exist
+
+Story generation can take hours or days. Savepoints let you:
+
+- **Pause and resume** without losing progress
+- **Retry a phase** after making a config or prompt change
+- **Inspect intermediate output** (e.g., read the outline savepoint without running the full pipeline)
+- **Debug** by loading a specific savepoint and examining its data
+
+### 14.2 Savepoint File Structure
+
+The pipeline resume state is stored as a single JSON file:
+
+```
+stories/<name>/savepoints/pipeline_state.json
+```
+
+This file contains the full `PipelineState` object (completed phases, approved chapters, current phase, etc.).
 
-### 10.1 Test Structure
+Individual phase outputs are also stored as separate savepoint files in the same directory:
+
+```
+stories/<name>/savepoints/
+├── pipeline_state.json       # Resume checkpoint (single JSON file)
+├── outline_complete          # Milestone: outline finished
+├── arc_analysis_complete     # Milestone: arc analysis finished
+├── chapter_1_complete        # Chapter 1 content
+├── chapter_2_complete        # Chapter 2 content
+└── ...
+```
+
+### 14.3 How to Resume After Interruption
+
+If the TUI is closed, the machine reboots, or the pipeline crashes:
+
+```bash
+# Resume in the TUI
+story-writer tui --story <name> --resume
+
+# Resume headlessly
+story-writer resume --story <name>
+```
+
+Resume always continues from the latest `pipeline_state.json` snapshot. The `--savepoint` argument only validates that the story reached at least the named phase; it does not restore an older snapshot.
+
+```bash
+# Validate that the story reached chapter-3 before resuming
+story-writer resume --story <name> --savepoint chapter-3
+```
+
+### 14.4 How to Check Savepoint Status
+
+List savepoint names (fast, no data loaded):
+
+```bash
+python -m src.tools.savepoint_manager --operation list --name <story>
+```
+
+List savepoints with full data (can be large):
+
+```bash
+python -m src.tools.savepoint_manager --operation list-full --name <story>
+```
+
+Determine the next phase to run:
+
+```bash
+python -m src.tools.savepoint_manager --operation next-phase --name <story>
+```
+
+Example output:
+
+```json
+{
+  "last_completed": "chapter_5_complete",
+  "next_phase": "Phase 7 — chapter 6",
+  "last_canonical": "wiki_populated",
+  "last_chapter_complete": 5,
+  "missing_below_top": [],
+  "all_savepoints": ["init", "outline_complete", "wiki_populated", "chapter_1_complete", "chapter_2_complete", "chapter_3_complete", "chapter_4_complete", "chapter_5_complete"]
+}
+```
+
+### 14.5 Common Resume Scenarios
+
+**Scenario A: Power loss during chapter 12**
+
+```bash
+# Check status
+python -m src.tools.savepoint_manager --operation next-phase --name my-story
+# → "Phase 7 — chapter 12"
+
+# Resume in TUI
+story-writer tui --story my-story --resume
+```
+
+**Scenario B: Want to restart from outline after changing the prompt**
+
+```bash
+# Clear savepoints (destructive)
+python -m src.tools.savepoint_manager --operation clear --name my-story
+
+# Or selectively remove phases and edit state.json to remove completed phases
+# Then re-run
+story-writer tui --story my-story
+```
+
+**Scenario C: Resume says "complete" but you want to add more chapters**
+
+1. Edit `config.yml` to increase `wanted_chapters`
+2. Edit `stories/<name>/state.json` to remove `assembly` and `complete` from completed phases
+3. Delete `stories/<name>/savepoints/story_complete`
+4. Resume:
+   ```bash
+   story-writer tui --story my-story --resume
+   ```
+
+**Scenario D: Resuming on a different machine**
+
+1. Copy the entire `stories/<name>/` directory to the new machine
+2. Ensure the new machine has the same `config.yml` (or equivalent)
+3. Run `story-writer resume --story <name>`
+
+---
+
+## 15. Troubleshooting
+
+### LLM endpoint not responding
+
+```bash
+# Verify your inference server is running (LM Studio, Ollama, or similar)
+#   LM Studio: check the Developer tab shows "Server running"
+#   Ollama:    ollama list
+
+# Test API endpoint (defaults to LM Studio; adjust if using a different server)
+curl http://127.0.0.1:1234/v1/models
+```
+
+### ChromaDB search returning no results
+
+- Verify `.chromadb/` directory exists and is writable
+- Check `embedding_model` is loaded in your inference server (e.g. LM Studio: load `nomic-embed-text`; Ollama: `ollama pull nomic-embed-text`)
+- Verify `similarity_threshold` in `config.yml` is not set too high (try 0.5)
+
+### Story generation producing inconsistent output
+
+- Enable `enable_chapter_revisions: true` in `config.yml`
+- Use the wiki tool CLIs or the Textual wiki panel to inspect wiki state
+- Use `story-writer resume --story <name>` from the last savepoint rather than restarting
+
+### Savepoint validation failing
+
+- Check `savepoint_dir` in `config.yml` points to the correct path
+- Check `stories/<name>/savepoints/pipeline_state.json` exists for resume
+- Use `python -m src.tools.savepoint_manager --operation list --name <story>` to see savepoint names without loading full payloads
+- Use `python -m src.tools.savepoint_manager --operation list-full --name <story>` only when you need the stored data itself
+
+### Context window overflow
+
+- Reduce `max_context_chunks` in `config.yml`
+- Lower `outline_chunk_size` if using chunked outline generation
+- Enable `use_chunked_outline_generation: true` to reduce prompt sizes
+
+### "The outline looks wrong"
+
+**Symptoms:** Outline skips chapters, characters act out of character, pacing is uneven.
+
+**Fix:**
+1. In the TUI, type `revise <specific feedback>` at the outline approval gate
+2. Example: `revise Chapter 5 needs a slower build-up. Add a scene where Elena discovers the letter before the confrontation.`
+3. The outline planner will regenerate the outline with your feedback injected
+4. If the revised outline is still wrong, repeat up to `outline_max_revisions` times
+5. If it never improves, reject the outline, edit your prompt file to add more constraints, clear savepoints, and restart
+
+### "A chapter feels off"
+
+**Symptoms:** Dialogue is wooden, a character knows something they shouldn't, the scene skips an important beat.
+
+**Fix:**
+1. At the chapter approval gate, type `revise <feedback>`
+2. Example: `revise Dr. Okonkwo should not know about the signal yet. Remove his line about the anomaly.`
+3. The chapter writer will regenerate with your feedback
+4. If the chapter is fundamentally broken, you can also `reject` to halt and investigate the outline or wiki state
+
+### "Generation stopped mid-chapter"
+
+**Symptoms:** Power outage, LM Studio crashed, or you pressed `Ctrl+C`.
+
+**Fix:**
+```bash
+story-writer resume --story <name>
+```
+The pipeline resumes from the last completed phase savepoint. If chapter 7 was halfway through, it restarts chapter 7 from the beginning (chapter generation is atomic per chapter, not per scene).
+
+### "Output is repetitive"
+
+**Symptoms:** Same sentence structure, repeated phrases, characters echoing each other.
+
+**Fix:**
+1. Increase model temperature (add `?temperature=0.8` to the model URI in `config.yml`)
+2. Enable `enable_scrubbing: true` to remove redundant phrases
+3. Enable `enable_chapter_revisions: true` and provide feedback like `revise Vary sentence openings; avoid starting three consecutive paragraphs with "She"`
+
+### "Context window overflow"
+
+**Symptoms:** LLM server returns 413 or truncation errors; output cuts off mid-sentence.
+
+**Fix:**
+1. Reduce `max_context_chunks` (try 10 instead of 20)
+2. Reduce `outline_chunk_size` (try 5 instead of 10)
+3. Enable `use_chunked_outline_generation: true` if not already enabled
+4. If using a model with a small context window (e.g., 4K), consider switching to a model with at least 8K context
+
+---
+
+## 16. Prompt Writing Tips
+
+### What Makes a Good Story Prompt
+
+The prompt is the single most important input. A strong prompt includes:
+
+1. **Premise** — What happens? Who is involved? What is at stake?
+2. **Genre and tone** — Fantasy? Hard sci-fi? Noir? Whimsical? Grim?
+3. **Target audience** — Middle grade, young adult, adult literary
+4. **Setting rules** — Magic system constraints, tech level, social structure
+5. **Character sketches** — Name, age, background, motivation, flaw
+6. **Themes** — What questions should the story explore?
+7. **Length constraints** — Chapter count, approximate word count
+
+### Genre Guidance
+
+| Genre | What to specify |
+|-------|-----------------|
+| **Fantasy** | Magic system rules, power ceiling, cultural inspirations, magic cost |
+| **Sci-fi** | Tech level, FTL rules (or lack thereof), alien biology, societal structure |
+| **Mystery** | Crime type, detective style (amateur vs professional), red herring policy, tone (cozy vs hardboiled) |
+| **Romance** | Relationship arc (enemies-to-lovers, second chance), heat level, obstacles |
+| **Horror** | Type of fear (cosmic, body, psychological), gore level, hope vs despair balance |
+| **Historical** | Era, historical figures (real or fictional), anachronism tolerance |
+
+### Length Recommendations
+
+| Output target | Prompt length | Detail needed |
+|---------------|---------------|---------------|
+| Short story (5–10 chapters) | 200–500 words | Core conflict + 1–2 characters |
+| Novella (15–20 chapters) | 500–1,000 words | Full premise + 3–4 characters + setting rules |
+| Novel (25–40 chapters) | 1,000–2,000 words | Detailed premise + full cast + setting + themes + pacing notes |
+
+A longer, more detailed prompt consistently produces better outlines and fewer revision cycles.
+
+### Example Prompts
+
+#### Fantasy: The Last Glasswright
+
+```text
+Title: The Last Glasswright
+Genre: High fantasy with artificer/magical-craftsmanship focus
+Tone: Warm, melancholic, slowly building to epic
+Target audience: Adult readers who enjoy Rothfuss and McKillip
+
+Premise:
+In the city of Verral, where magic is woven into glass,
+Aelind the glasswright is the last living practitioner of
+a lost technique: singing the glass awake. When a corrupt
+guildmaster begins melting down ancestral stained-glass
+windows to fuel a war machine, Aelind must choose between
+hiding her gift or using it to forge a weapon that could
+save her city — and destroy her soul.
+
+Setting rules:
+- Magic requires breath, blood, or tears; glass "remembers" the emotion used to shape it
+- The guild controls all legal magic; unsanctioned crafters are exiled
+- Verral is built on the ruins of a glass dragon's corpse; the bones are still warm
+- No gods intervene directly; only relics and memory-magic work
+
+Characters:
+- Aelind: 34, shy, has a stutter that disappears when she sings to glass, grieving her mentor
+- Guildmaster Sorn: 60s, genuinely believes the war is necessary, sees Aelind as a resource
+- Kael: street thief who steals a piece of Aelind's glass and accidentally bonds with it
+
+Themes:
+- The cost of preservation vs the cost of action
+- Art as resistance
+- What we owe to the dead
+
+Desired length: ~25 chapters, ~90,000 words
+```
+
+#### Sci-Fi: The Silence Between Stars
+
+See [Section 3, Step 1](#step-1-write-a-prompt-file) for a complete sci-fi example.
+
+#### Mystery: The Haymarket Cipher
+
+```text
+Title: The Haymarket Cipher
+Genre: Historical mystery (Chicago, 1886)
+Tone: Tense, atmospheric, morally ambiguous
+Target audience: Adult readers who enjoy C.J. Tudor and The Alienist
+
+Premise:
+Clara Doherty is a typesetter at a German-language anarchist
+newspaper in Chicago. When a bomb kills seven policemen at
+the Haymarket rally, the police round up her entire print
+shop. Clara knows one of her coworkers is guilty — but she
+also knows the police are fabricating evidence to crush the
+labour movement. She has three days before the trial to find
+the real bomber without revealing that she, too, was at the
+rally.
+
+Setting rules:
+- 1886 Chicago: soot, ice, gaslight, immigrant neighbourhoods
+- The anarchist movement is real and varied; not all characters agree
+- Clara is fictional but interacts with real historical figures (August Spies, Albert Parsons)
+- No anachronistic technology; fingerprinting is brand-new and distrusted
+
+Characters:
+- Clara Doherty: 28, Irish-American, widow of a union organiser, can read five languages
+- Inspector Bonfield: violent, politically motivated, genuinely believes anarchists are a threat
+- Johann Most: real historical figure, editor, charismatic, possibly manipulative
+
+Themes:
+- Justice vs peace
+- The individual vs the collective
+- Who gets to tell the story of a tragedy
+
+Desired length: ~20 chapters, ~70,000 words
+```
+
+---
+
+## 17. Testing
+
+### 17.1 Test Structure
 
 ```
 tests/
@@ -590,7 +1561,7 @@ tests/
   └── test_wiki_read_integration.py
 ```
 
-### 10.2 Running Tests
+### 17.2 Running Tests
 
 ```bash
 # Unit tests only (default discovery target)
@@ -612,7 +1583,7 @@ pytest tests/unit/test_prompt_loader.py -v
 pytest --cov=src tests/unit tests/integration
 ```
 
-### 10.3 Integration Test Setup
+### 17.3 Integration Test Setup
 
 Integration tests exercise the full pipeline against a live OpenAI-compatible LLM endpoint. Most integration files use `LLM_API_BASE` and default to `http://127.0.0.1:1234/v1`. The headless batch E2E test currently probes LM Studio directly at that same local address and skips when it is unavailable. The `slow` marker identifies integration coverage that may take multiple minutes.
 
@@ -620,9 +1591,9 @@ See [docs/testing/integration-tests.md](testing/integration-tests.md) for detail
 
 ---
 
-## 11. Development
+## 18. Development
 
-### 11.1 Code Style
+### 18.1 Code Style
 
 | Language | Tool | Config |
 |----------|------|--------|
@@ -632,7 +1603,7 @@ See [docs/testing/integration-tests.md](testing/integration-tests.md) for detail
 
 **Naming:** `snake_case` for Python.
 
-### 11.2 Commands
+### 18.2 Commands
 
 ```bash
 # Lint and auto-fix
@@ -648,7 +1619,7 @@ mypy src/
 ruff check --fix . && ruff format . && mypy src/
 ```
 
-### 11.3 Feature-Based Workflow
+### 18.3 Feature-Based Workflow
 
 1. **Implement the feature** — write production code
 2. **Lint and type check** — fix all errors
@@ -656,7 +1627,7 @@ ruff check --fix . && ruff format . && mypy src/
 4. **Confirm tests pass** — before committing
 5. **Refactor only after tests pass**
 
-### 11.4 Architecture Decision Records
+### 18.4 Architecture Decision Records
 
 Significant architectural decisions are documented in `docs/planning/adr/`:
 
@@ -671,65 +1642,43 @@ Significant architectural decisions are documented in `docs/planning/adr/`:
 
 ---
 
-## 12. Troubleshooting
-
-### LLM endpoint not responding
+## 19. Quick Reference
 
 ```bash
-# Verify your inference server is running (LM Studio, Ollama, or similar)
-#   LM Studio: check the Developer tab shows "Server running"
-#   Ollama:    ollama list
-
-# Test API endpoint (defaults to LM Studio; adjust if using a different server)
-curl http://127.0.0.1:1234/v1/models
-```
-
-### ChromaDB search returning no results
-
-- Verify `.chromadb/` directory exists and is writable
-- Check `embedding_model` is loaded in your inference server (e.g. LM Studio: load `nomic-embed-text`; Ollama: `ollama pull nomic-embed-text`)
-- Verify `similarity_threshold` in `config.md` is not set too high (try 0.5)
-
-### Story generation producing inconsistent output
+# Start your local LLM server (e.g. LM Studio, or `ollama serve`)
 
-- Enable `enable_chapter_revisions: true` in `config.md`
-- Use the wiki tool CLIs or the Textual wiki panel to inspect wiki state
-- Use `story-writer resume --story <name>` from the last savepoint rather than restarting
+# Initialize a new story
+python -m src.tools.story_state --operation init --name test_story
 
-### Savepoint validation failing
+# Write the prompt into story state (JSON-encode the text first)
+printf '%s' "Your story prompt here" | python -c "import json,sys; print(json.dumps(sys.stdin.read()))" | \
+  python -m src.tools.story_state --operation write --name test_story \
+  --field story_prompt --value -
 
-- Check `savepoint_dir` in `config.md` points to the correct path
-- Check both `stories/<name>/savepoints/**/*.json` and `stories/<name>/savepoints/**/*.md` for the expected step
-- Use `python3 src/tools/savepoint_manager.py --operation list --name <story>` to see savepoint names without loading full payloads
-- Use `python3 src/tools/savepoint_manager.py --operation list-full --name <story>` only when you need the stored data itself
-
-### Context window overflow
+# Run Textual TUI
+story-writer tui --story test_story
 
-- Reduce `max_context_chunks` in `config.md`
-- Lower `outline_chunk_size` if using chunked outline generation
-- Enable `use_chunked_outline_generation: true` to reduce prompt sizes
+# Resume in TUI
+story-writer tui --story test_story --resume
 
----
+# Run headless pipeline
+story-writer run --story test_story --batch
 
-## Quick Reference
+# Resume headlessly
+story-writer resume --story story-name
 
-```bash
-# Start your local LLM server (e.g. LM Studio, or `ollama serve`)
+# Check savepoint status
+python -m src.tools.savepoint_manager --operation list --name story-name
+python -m src.tools.savepoint_manager --operation next-phase --name story-name
 
-# Run Textual TUI
-story-writer tui --story test_story
+# Assemble manuscript manually
+python -m src.tools.story_assembler assemble --story-name story-name
 
 # Lint + format + type check
 ruff check --fix . && ruff format . && mypy src/
 
 # Run tests
 pytest tests/unit/ -v
-
-# Run headless pipeline
-story-writer run --story test_story --batch
-
-# Continue from savepoint
-story-writer resume --story story-name
 ```
 
 ---

=== FILE CONTENTS ===
--- docs/manual.md ---
# AI Story Writer — Comprehensive Manual

**Version:** 1.1
**Last Updated:** April 2026
**Stack:** Python 3.10+ · Textual · ChromaDB · OpenAI-compatible local LLM (LM Studio default)

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
15. [Troubleshooting](#15-troubleshooting)
16. [Prompt Writing Tips](#16-prompt-writing-tips)
17. [Testing](#17-testing)
18. [Development](#18-development)
19. [Quick Reference](#19-quick-reference)

---

## 1. System Overview

AI Story Writer is an AI-powered long-form story generation system. It produces coherent, multi-chapter novels (typically 25+ chapters) using local LLM inference, with a progressive wiki memory system that maintains consistency across the narrative.

**Core capabilities:**
- Generate full-length novels from prompt files
- Progressive wiki memory for consistency tracking
- Per-story semantic search via ChromaDB
- Multiple writing strategies (outline-then-chapter vs stream-of-consciousness)
- Savepoint/resume system for long generation runs
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
story-writer run --story test_story
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

# Load your prompt file into story state
python -c "import json,sys; print(json.dumps(sys.stdin.read()))" < ~/prompts/my-story.txt | \
  python -m src.tools.story_state --operation write --name my-first-story \
  --field story_prompt --value -
```

**Alternative:** You can also edit `stories/my-first-story/state.json` directly and add a `story_prompt` field containing your prompt text.

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
- If the outline scores below the threshold, the system may auto-revise up to `outline_max_revisions` times before asking you
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
├── state.json                    # Pipeline state and metadata
├── outline.json                  # Approved outline
├── chapters/
│   ├── chapter_1.md
│   ├── chapter_2.md
│   ├── chapter_3.md
│   └── ...                       # One file per approved chapter
├── output/
│   ├── story.md                  # Final assembled manuscript
│   └── story_edited.md           # Post-final-edit manuscript (optional)
├── characters/
│   ├── yuki-tanaka-oduya.json    # Character sheet (name, sheet, chunks, summary, updated_at)
│   ├── commander-voss.json
│   └── ...
├── settings/
│   ├── europa-research-base.json # Setting sheet (same JSON schema as characters)
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
- `savepoints/pipeline_state.json` is the resume checkpoint (single JSON file)
- Individual step savepoints (e.g., `outline_complete`, `chapter_3_complete`) are separate files in the same directory
- The `wiki/` directory is fully Obsidian-compatible — open it in Obsidian to browse linked pages

---

## 4. Understanding the Pipeline Phases

The story generation pipeline is divided into nine primary phases. Each phase writes a savepoint on completion, so you can resume after any interruption.

### ASCII Flow Diagram

```
┌─────────┐     ┌──────────┐     ┌─────────────────┐
│  Init   │────▶│ Outline  │────▶│ Outline Approval│
│ (setup) │     │(generate)│     │   (user gate)   │
└─────────┘     └──────────┘     └─────────────────┘
                                        │
                    ┌───────────────────┘
                    ▼
           ┌─────────────────┐
           │ Narrative Arc   │
           │   Analysis      │
           └─────────────────┘
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
┌─────────┐   ┌──────────┐   ┌───────────┐
│Characters│   │ Settings │   │ Wiki Init │
│(sheets)  │   │ (sheets) │   │(idempotent)│
└─────────┘   └──────────┘   └───────────┘
    │               │               │
    └───────────────┴───────────────┘
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
         │ (conditional)    │     │ (manuscript)
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

### Phase 2: Outline

**What the system does:**
- Loads your story prompt from `state.json`
- Delegates to the `outline-planner` agent
- Generates a detailed chapter-by-chapter outline
- Optionally runs critique and refinement loops (if `enable_outline_critique: true`)
- Persists the approved outline to savepoints

**Artefacts produced:**
- `stories/<name>/savepoints/outline_complete`
- `stories/<name>/outline.json` (structured outline data)

**User action needed:**
- Approve, reject, or revise via the approval gate (TUI) or auto-approve (headless)

**Approximate duration:** 5–20 minutes (longer with critique loops)

### Phase 2.5: Narrative Arc Analysis

**What the system does:**
- Loads the approved outline
- Delegates to the `story-planner` agent
- Streams one advisory arc assessment (promise/payoff, tension curve, pacing)
- Persists `state.arc_result` and writes `arc_analysis_complete`
- On agent error, emits a skip message and continues (non-blocking)

**Artefacts produced:**
- `stories/<name>/savepoints/arc_analysis_complete`
- `stories/<name>/savepoints/arc_assessment` (detailed analysis text)

**User action needed:** None (advisory only)

**Approximate duration:** 2–5 minutes

### Phase 3: Characters

**What the system does:**
- Extracts character names from the approved outline
- Generates one JSON sheet per character via the `character_manager`
- Each sheet contains: `name`, `sheet` (full text), `chunks` (segmented details), `summary`, `updated_at`
- If name extraction returns invalid JSON, the phase degrades gracefully and the pipeline continues

**Artefacts produced:**
- `stories/<name>/savepoints/characters_complete`
- `stories/<name>/characters/<slug>.json` (one per character)

**User action needed:** None

**Approximate duration:** 2–10 minutes (scales with character count)

### Phase 4: Settings

**What the system does:**
- Extracts setting/location names from the outline
- Generates one JSON sheet per setting
- Same JSON schema as characters: `name`, `sheet`, `chunks`, `summary`, `updated_at`

**Artefacts produced:**
- `stories/<name>/savepoints/settings_complete`
- `stories/<name>/settings/<slug>.json` (one per setting)

**User action needed:** None

**Approximate duration:** 2–5 minutes

### Phase 5: Wiki Initialization

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

### Phase 6: Chapter Loop

**What the system does:**
- For each chapter (1 to `wanted_chapters`):
  1. Loads abridged character and setting sheet context
  2. Generates chapter text via the `chapter-writer` agent
  3. Presents the chapter for approval (gate)
  4. On approval, writes `stories/<name>/chapters/chapter_{N}.md`
  5. Calls `wiki_maintainer` to extract structured data and persist wiki pages
  6. Runs `consistency_checker` (streams findings but does not block persistence)
  7. Saves a chapter-level savepoint (`chapter_{N}_complete`)

**Artefacts produced:**
- `stories/<name>/chapters/chapter_1.md` through `chapter_{N}.md`
- `stories/<name>/savepoints/chapter_1_complete` through `chapter_{N}_complete`
- Updated wiki pages under `stories/<name>/wiki/`

**User action needed:**
- Per-chapter approval gate in TUI mode
- None in headless mode (auto-approves all chapters)

**Approximate duration:** 5–20 minutes per chapter (depending on model speed, scene count, and revisions)

### Phase 7: Final Edit (conditional)

**What the system does:**
- Enabled unless `generation.enable_final_edit` is explicitly set to `false`
- Loads `prompts/agents/final-editor.md`
- Streams one editing pass per approved chapter (voice consistency, pacing, prose polish)
- Falls back to original chapter content if the model returns empty output
- Writes the edited manuscript to `stories/<name>/output/story_edited.md`
- Persists `final_edit_complete`

**Artefacts produced:**
- `stories/<name>/output/story_edited.md`
- `stories/<name>/savepoints/final_edit_complete`

**User action needed:** None

**Approximate duration:** 10–20 minutes total (scales with chapter count)

### Phase 8: Assembly

**What the system does:**
- Assembles the final manuscript from the current `state.approved_chapters`
- Writes `stories/<name>/output/story.md`
- Raises `StoryGenerationError` if no approved chapter content is found
- Persists the `story_complete` milestone

**Artefacts produced:**
- `stories/<name>/output/story.md`
- `stories/<name>/savepoints/story_complete`
- Updated `stories/<name>/savepoints/pipeline_state.json` with `status: complete`

**User action needed:** None

**Approximate duration:** < 1 second

---

## 5. Architecture

### 5.1 Python-Native Pipeline Architecture

The system uses a **Python-native prompt-and-tool architecture** during active runtime. Prompt-defined pipeline phases live under `prompts/agents/`, and Python orchestration code loads those prompts directly (see [ADR 007](planning/adr/007-python-native-orchestration.md)):

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
│  Domain layer (entities, services, strategies) │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│  Infrastructure (OpenAI-compatible LLM, ChromaDB, disk) │
└─────────────────────────────────────────────┘
    ↓
stories/<name>/  (chapters, wiki, savepoints)
```

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
git clone https://github.com/logicalor/llm-story-writer.git
cd AIStoryWriter

# 2. Start your local LLM server and load models
#    e.g. LM Studio (default: http://127.0.0.1:1234/v1) — load model via the UI
#    or:  ollama serve && ollama pull <model-name>

# 3. Install Python dependencies and the console script
pip install -r requirements.txt
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

### 6.4 Opencode Agent Runtime Setup

The Python story-generation runtime above is separate from the Opencode agent runtime used for the Copilot-to-Opencode migration work. That migration config lives in the repository root `opencode.json`, where the default model is now `openrouter/moonshotai/kimi-k2.6` and the OpenRouter provider registry includes Kimi K2.6, Qwen3.6 Plus, and GLM 5.1.

Developer-local credentials and user-level MCP servers are not committed to the repository. Configure `OPENROUTER_API_KEY`, Tavily, and Context7 in your personal Opencode config instead. See [Opencode Runtime Configuration](./features/opencode-runtime.md) for the exact setup and confirmed model IDs.

---

## 7. Configuration

All configuration lives in `config.yml` in the repository root. No secrets are required — all providers use local inference. Optional environment variables include `LLM_API_BASE` and `STORIES_DIR`.

### 7.1 Generation Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `wanted_chapters` | 25 | Target chapter count |
| `outline_quality` | 87 | Quality threshold for outline (0–100) |
| `chapter_quality` | 85 | Quality threshold for chapters |
| `outline_max_revisions` | 3 | Max outline revision passes |
| `chapter_max_revisions` | 3 | Max chapter revision passes |
| `enable_chapter_revisions` | true | Enable chapter revision loop |
| `enable_final_edit` | true* | Run final polish pass |
| `enable_scrubbing` | true | Remove redundant/phrases |
| `strategy` | "outline-chapter" | Writing strategy |
| `use_chunked_outline_generation` | true | Generate outline in chunks |
| `outline_chunk_size` | 10 | Chapters per outline chunk |
| `stream` | true | Stream LLM output |
| `debug` | true | Enable debug logging |

\* `enable_final_edit` defaults to `true` in the orchestrator. It is only disabled if you explicitly set `generation.enable_final_edit: false` in `config.yml`.

### 7.2 Infrastructure Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `output_dir` | — | Where to write final story files |
| `savepoint_dir` | — | Where to store savepoints |
| `model_api_base` | `http://127.0.0.1:1234/v1` | LLM API endpoint |
| `context_length` | 16384 | Context window size |
| `embedding_model` | `nomic-embed-text` | Embedding model for ChromaDB |
| `vector_dimensions` | 1536 | Embedding vector dimensions |
| `similarity_threshold` | 0.7 | ChromaDB similarity threshold |
| `max_context_chunks` | 20 | Max RAG chunks per scene |

### 7.3 Model Role Assignments

Each phase of the pipeline uses a specific model:

| Phase | Model Role |
|-------|-----------|
| Initial outline writing | `initial_outline_writer` |
| Chapter outline | `chapter_outline_writer` |
| Chapter content (stage 1–4) | `chapter_stage1_writer` … `chapter_stage4_writer` |
| Chapter revision | `chapter_revision_writer` |
| Critique/eval | `eval_model`, `revision_model` |
| Info extraction | `info_model` |
| Wiki maintenance | `info_model` (separate agent) |
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
  outline_chunk_size: 10
  stream: true
  debug: false
```

| Setting | Value | Why |
|---------|-------|-----|
| `outline_max_revisions` | 5 | More chances to refine outline |
| `chapter_max_revisions` | 3 | Per-chapter quality loop |
| `enable_outline_critique` | true | Iterative outline refinement |
| `enable_final_edit` | true | Post-generation polish pass |
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
  enable_scrubbing: true
  use_chunked_outline_generation: false
  stream: true
  debug: true
```

| Setting | Value | Why |
|---------|-------|-----|
| `wanted_chapters` | 10 | Novella length |
| `chapter_max_revisions` | 0 | No per-chapter revision loop |
| `enable_scrubbing` | true | Still clean up redundant prose |

### 8.4 Settings Change Summary Table

| Setting | Fast Prototype | High Quality Novel | Short Story |
|---------|---------------|-------------------|-------------|
| `wanted_chapters` | 5 | 25 | 10 |
| `outline_min_revisions` | 0 | 2 | 0 |
| `outline_max_revisions` | 1 | 5 | 2 |
| `chapter_min_revisions` | 0 | 1 | 0 |
| `chapter_max_revisions` | 1 | 3 | 0 |
| `enable_chapter_revisions` | false | true | false |
| `enable_outline_critique` | false | true | false |
| `enable_final_edit` | false | true | false |
| `enable_scrubbing` | false | true | true |
| `use_chunked_outline_generation` | false | true | false |

---

## 9. Usage

### 9.1 Python CLI

```bash
story-writer --help
```

Available subcommands:

| Command | Description |
|---------|-------------|
| `story-writer tui --story <name> [--resume] [--savepoint <name>]` | Launch the interactive Textual TUI for a fresh run or resume an existing run |
| `story-writer run --story <name> [--batch]` | Run the headless Python-native pipeline |
| `story-writer resume --story <name> [--savepoint <name>]` | Resume from the latest persisted pipeline state. `--savepoint` validates the name exists but does not restore an older snapshot. |

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

Issue #164 removed the remaining OpenCode runtime artefacts from the repository. Reusable prompt content that still matters to the Python-native pipeline now lives in these locations:

- `prompts/agents/continue.md`
- `prompts/agents/regenerate.md`
- `prompts/skills/` — relocated skill reference material used by prompt-defined phases

### 9.3 Story Generation Pipeline

The current Python-native orchestrator slice runs through these phases:

```
Phase 1: Init
  → Load prompt, parse config, init story state, create savepoint

Phase 2: Outline
  → Delegate to outline-planner subagent
  → Stream outline generation
  → Persist `OutlineResult`

Phase 2 Gate: Outline Approval
  → Wait for injected approval gate
  → Reject halts cleanly; revise reruns outline with feedback

Phase 2.5: Narrative Arc Analysis
  → Delegate to story-planner subagent
  → Load `prompts/agents/story-planner.md`
  → Stream one advisory arc assessment from approved outline content
  → Persist `state.arc_result` and write `arc_analysis_complete`
  → On agent error, emit skip message and continue

Phase 3: Characters
  → Extract character names from outline
  → Orchestrator helper functions generate markdown sheets via prompts/characters and prompts/settings
  → Write per-entity JSON sheets to `stories/<name>/characters/`
  → If name extraction returns invalid JSON, phase degrades gracefully and pipeline continues

Phase 4: Settings
  → Extract setting names from outline
  → Generate one JSON sheet per extracted setting
  → Write per-entity JSON sheets to `stories/<name>/settings/`

Phase 5: Wiki Initialization
  → Idempotently ensure `stories/<name>/wiki/` directory structure exists
  → Creates subdirectories, index, log, and schema template if missing
  → Safe to rerun on resume; skips creation if wiki already present

Phase 6: Chapter Loop
  → Per chapter: chapter-writer loads abridged character/setting sheet context, then generates chapter text
  → Wait for chapter approval gate; revise reruns chapter with feedback
  → After chapter approval, orchestrator writes stories/<name>/chapters/chapter_{N}.md
  → wiki-maintainer calls `update_wiki_from_chapter()` to extract structured JSON, persist wiki pages through `run_batch()`, and emit created/updated page events
  → consistency-checker streams findings but does not block persistence

Phase 7: Final Edit (conditional)
  → Enabled unless `generation.enable_final_edit` is explicitly `false`
  → final-editor loads `prompts/agents/final-editor.md`
  → Stream one editing pass per approved chapter
  → Fall back to original chapter content if the model returns empty output
  → Write `stories/<name>/output/story_edited.md`
  → Persist `final_edit_complete`

Phase 8: Assembly
  → Assemble final manuscript from the current `state.approved_chapters`
  → Write `stories/<name>/output/story.md`
  → Raises `StoryGenerationError` if no approved chapter content is found
```

Current implementation note: the PRD's initial wiki population pass, chapter-outline-expander, quality-reviewer, and prose-scrubber are not yet wired into `src/presentation/orchestrator.py`. Wiki directory initialization is now handled idempotently before the chapter loop.

---

## 10. Project Structure

```
llm-story-writer/
├── config.yml                  # All configuration (YAML)
├── config-guide.md             # Configuration reference and examples
├── config.example.sh           # Shell env config template
│
├── src/                       # Python domain logic
│   ├── domain/
│   │   ├── entities/         # Story, Chapter, Character, Scene entities
│   │   ├── value_objects/    # ModelConfig, GenerationSettings
│   │   ├── repositories/     # Repository interfaces
│   │   └── exceptions.py     # Domain exceptions
│   ├── application/
│   │   ├── services/         # Application services
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
│       ├── wiki_*.py         # Wiki operations
│       ├── savepoint_manager.py
│       ├── character_manager.py
│       ├── scene_writer.py
│       └── ...
│
├── prompts/                  # 132+ prompt templates
│   ├── agents/               # Prompt-defined pipeline phase instructions
│   │   ├── story-orchestrator.md
│   │   ├── outline-planner.md
│   │   ├── continue.md
│   │   ├── regenerate.md
│   │   └── ...
│   ├── skills/               # Reusable skill reference material
│   │   ├── story-pipeline/
│   │   ├── wiki-conventions/
│   │   ├── wiki-maintenance/
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
│   ├── README.md
│   ├── tools.md            # Tools reference
│   ├── features/
│   ├── planning/
│   │   ├── adr/           # Architecture decision records
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

1. **Initial population** (before chapter generation): `wiki-extract` reads the outline plus character and setting sheets, creates the first wiki page set, and writes retrieval-ready L1/L2/L3 detail levels
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

Agent system prompts now live in `prompts/agents/` as Markdown files. `src/infrastructure/prompts/agent_prompt_loader.py` reads those prompt bodies directly and strips YAML frontmatter before returning the reusable instruction text.

| Agent | Role |
|-------|------|
| `story-orchestrator` | Primary pipeline controller; drives the full generation lifecycle |
| `outline-planner` | Generates and refines the story outline |
| `chapter-writer` | Writes individual chapter content |
| `wiki-maintainer` | Persists wiki page updates after each accepted chapter and reports changed page slugs |

**Orchestrator Pipeline Phases:** Init → Outline → Approval → Narrative Arc → Characters → Settings → Wiki Init → Chapter Loop → Final Edit → Assembly

### 12.2 Tools

Tools are Python modules under `src/tools/`. The runtime imports them directly or calls the same Python services in-process; there is no TypeScript wrapper layer anymore.

#### Core Tools

| Tool | Purpose |
|------|---------|
| `prompt_loader.py` | Load and render prompt templates with variable substitution |
| `story_state.py` | Initialize and update story state JSON |
| `savepoint_manager.py` | Create, inspect, and load savepoints (`list` = names only, `list-full` = full payloads) |
| `character_manager.py` | Extract and manage character sheets |
| `setting_manager.py` | Extract and manage setting sheets |
| `recap_manager.py` | Generate and manage chapter recaps |

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

#### RAG Tools

| Tool | Purpose |
|------|---------|
| `rag_query.py` | Query ChromaDB for relevant story content chunks |

#### Critique Tools

| Tool | Purpose |
|------|---------|
| `critique_runner.py` | Run quality critique on outline or chapter |

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
4. Generate metadata (title, summary, tags)
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

This file contains the full `PipelineState` object (completed phases, approved chapters, current phase, etc.).

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

## 15. Troubleshooting

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
- Lower `outline_chunk_size` if using chunked outline generation
- Enable `use_chunked_outline_generation: true` to reduce prompt sizes

### "The outline looks wrong"

**Symptoms:** Outline skips chapters, characters act out of character, pacing is uneven.

**Fix:**
1. In the TUI, type `revise <specific feedback>` at the outline approval gate
2. Example: `revise Chapter 5 needs a slower build-up. Add a scene where Elena discovers the letter before the confrontation.`
3. The outline planner will regenerate the outline with your feedback injected
4. If the revised outline is still wrong, repeat up to `outline_max_revisions` times
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
The pipeline resumes from the last completed phase savepoint. If chapter 7 was halfway through, it restarts chapter 7 from the beginning (chapter generation is atomic per chapter, not per scene).

### "Output is repetitive"

**Symptoms:** Same sentence structure, repeated phrases, characters echoing each other.

**Fix:**
1. Increase model temperature (add `?temperature=0.8` to the model URI in `config.yml`)
2. Enable `enable_scrubbing: true` to remove redundant phrases
3. Enable `enable_chapter_revisions: true` and provide feedback like `revise Vary sentence openings; avoid starting three consecutive paragraphs with "She"`

### "Context window overflow"

**Symptoms:** LLM server returns 413 or truncation errors; output cuts off mid-sentence.

**Fix:**
1. Reduce `max_context_chunks` (try 10 instead of 20)
2. Reduce `outline_chunk_size` (try 5 instead of 10)
3. Enable `use_chunked_outline_generation: true` if not already enabled
4. If using a model with a small context window (e.g., 4K), consider switching to a model with at least 8K context

---

## 16. Prompt Writing Tips

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

## 17. Testing

### 17.1 Test Structure

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

### 17.2 Running Tests

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

### 17.3 Integration Test Setup

Integration tests exercise the full pipeline against a live OpenAI-compatible LLM endpoint. Most integration files use `LLM_API_BASE` and default to `http://127.0.0.1:1234/v1`. The headless batch E2E test currently probes LM Studio directly at that same local address and skips when it is unavailable. The `slow` marker identifies integration coverage that may take multiple minutes.

See [docs/testing/integration-tests.md](testing/integration-tests.md) for detailed setup instructions.

---

## 18. Development

### 18.1 Code Style

| Language | Tool | Config |
|----------|------|--------|
| Python | ruff | `pyproject.toml` |

**Import ordering:** stdlib → third-party → local, alphabetised within groups.

**Naming:** `snake_case` for Python.

### 18.2 Commands

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

### 18.3 Feature-Based Workflow

1. **Implement the feature** — write production code
2. **Lint and type check** — fix all errors
3. **Write tests** — verify correctness
4. **Confirm tests pass** — before committing
5. **Refactor only after tests pass**

### 18.4 Architecture Decision Records

Significant architectural decisions are documented in `docs/planning/adr/`:

| ADR | Subject |
|-----|---------|
| 001 | Hybrid agent-tool architecture |
| 002 | Context window budget strategy |
| 003 | ChromaDB replaces PGvector |
| 004 | Progressive wiki memory system |
| 005 | Hybrid wiki context retrieval pipeline |
| 006 | OpenAI-compatible provider |

---

## 19. Quick Reference

```bash
# Start your local LLM server (e.g. LM Studio, or `ollama serve`)

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

# Lint + format + type check
ruff check --fix . && ruff format . && mypy src/

# Run tests
pytest tests/unit/ -v
```

---

*For architecture details, see [docs/planning/adr/](planning/adr/). For tools reference, see [docs/tools.md](tools.md). For feature documentation, see [docs/features/](features/).*

== END REVIEW PACKAGE ==
