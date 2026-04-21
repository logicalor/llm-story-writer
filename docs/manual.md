# AI Story Writer — Comprehensive Manual

**Version:** 1.0
**Last Updated:** April 2026
**Stack:** Python 3.x · TypeScript · OpenCode · ChromaDB · OpenAI-compatible local LLM (LM Studio default)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Installation & Setup](#3-installation--setup)
4. [Configuration](#4-configuration)
5. [Usage](#5-usage)
6. [Project Structure](#6-project-structure)
7. [Wiki Memory System](#7-wiki-memory-system)
8. [Agents & Tools](#8-agents--tools)
9. [Strategies](#9-strategies)
10. [Testing](#10-testing)
11. [Development](#11-development)
12. [Troubleshooting](#12-troubleshooting)

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

## 2. Architecture

### 2.1 Hybrid Agent-Tool Architecture

The system uses a **hybrid agent-tool architecture** (per [ADR 001](planning/adr/001-hybrid-agent-tool-architecture.md)):

| Component | Technology | Role |
|-----------|------------|------|
| **Agents** | OpenCode | Orchestration, creative decisions, human interaction |
| **Tools** | TypeScript wrappers + Python scripts | Deterministic domain operations |
| **Wiki** | Markdown + YAML frontmatter | Structured story knowledge base |
| **Vector index** | ChromaDB | Semantic search over story content and wiki |

**Key principle:** Agents make decisions; tools execute operations. Agents never directly manipulate story files, wiki pages, or savepoints — they delegate to tools.

### 2.2 Clean Architecture Layers (Python Domain)

```
src/domain/          → Entities, value objects (core business rules, no dependencies)
src/application/     → Services, strategies (use cases, depends on domain)
src/infrastructure/  → Providers, storage (external adapters: OpenAI-compatible LLM, ChromaDB, disk I/O)
src/presentation/   → CLI interfaces
src/tools/          → Python tool implementations (called by TypeScript wrappers)
```

Each layer depends only on inner layers. `src/domain/` has zero external dependencies.

### 2.3 Data Flow

```
User prompt (.txt)
    ↓
story-orchestrator (OpenCode agent)
    ↓
┌─────────────────────────────────────────────┐
│  Tools (TypeScript wrappers → Python scripts) │
│  prompt-loader · story-state · wiki-*        │
│  savepoint-mgr · character-mgr · etc.        │
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

## 3. Installation & Setup

### 3.1 Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.8+ | |
| OpenCode | latest | CLI tool for agent orchestration |
| OpenAI-compatible LLM server | any | LM Studio (default), Ollama, llama.cpp, vLLM, etc. |

### 3.2 Installation Steps

```bash
# 1. Clone the repository
git clone https://github.com/datacrystals/AIStoryWriter.git
cd AIStoryWriter

# 2. Install OpenCode (follow platform-specific instructions)
opencode --version

# 3. Start your local LLM server and load models
#    e.g. LM Studio (default: http://127.0.0.1:1234/v1) — load model via the UI
#    or:  ollama serve && ollama pull <model-name>

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Copy and configure
cp config.example.sh config.sh
# Edit config.sh with your model paths and API endpoints
```

### 3.3 Model Configuration

Models are configured in `config.md` under the `models:` YAML block. The system uses OpenAI-compatible endpoints:

```yaml
models:
  initial_outline_writer: "openai-compat://huihui_ai/magistral-abliterated:24b"
  chapter_stage1_writer: "openai-compat://huihui_ai/magistral-abliterated:24b"
  info_model: "openai-compat://huihui_ai/magistral-abliterated:24b"
  embedding_model: "openai-compat://nomic-embed-text"
```

The `openai-compat://` prefix routes to the configured OpenAI-compatible API. Override `model_api_base` in `infrastructure:` to change the endpoint (default: `http://127.0.0.1:1234/v1`).

---

## 4. Configuration

All configuration lives in `config.md` (YAML frontmatter at the top of the file). No environment variables or secrets are required — all providers use local inference.

### 4.1 Generation Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `wanted_chapters` | 25 | Target chapter count |
| `outline_quality` | 87 | Quality threshold for outline (0–100) |
| `chapter_quality` | 85 | Quality threshold for chapters |
| `outline_max_revisions` | 3 | Max outline revision passes |
| `chapter_max_revisions` | 3 | Max chapter revision passes |
| `enable_chapter_revisions` | true | Enable chapter revision loop |
| `enable_final_edit` | false | Run final polish pass |
| `enable_scrubbing` | true | Remove redundant/phrases |
| `strategy` | "outline-chapter" | Writing strategy |
| `use_chunked_outline_generation` | true | Generate outline in chunks |
| `outline_chunk_size` | 10 | Chapters per outline chunk |
| `stream` | true | Stream LLM output |
| `debug` | true | Enable debug logging |

### 4.2 Infrastructure Settings

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

### 4.3 Model Role Assignments

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

## 5. Usage

### 5.1 Interactive Mode (OpenCode TUI)

```bash
opencode
```

Available slash commands in the TUI:

| Command | Description |
|---------|-------------|
| `/new-story prompts/YourPrompt.txt` | Initialize and start a new story |
| `/continue [story-name]` | Resume from last savepoint |
| `/status` | Show generation progress |
| `/savepoint [name]` | Create a named savepoint |
| `/wiki [query]` | Search the story wiki |
| `/settings` | Show current configuration |
| `/regenerate [chapter]` | Regenerate a specific chapter |

### 5.2 Batch Mode

```bash
opencode --batch
```

Auto-proceeds through all approval gates without pausing for human review.

### 5.3 Story Generation Pipeline

The full pipeline runs through these phases:

```
Phase 1: Init
  → Load prompt, parse config, init story state, create savepoint

Phase 2: Outline
  → Delegate to outline-planner subagent
  → Chunked or monolithic outline generation
  → Critique/refinement loop (if enabled)

Phase 3: Approval (interactive gate)
  → User reviews outline summary
  → User may request revisions → return to Phase 2

Phase 4: Wiki Init
  → Create wiki directory structure
  → Initialize schema and page templates

Phase 5: Characters & Settings
  → Extract characters and locations from outline
  → Delegate to character-sheet-generator subagent
  → Generate character sheets and setting sheets

Phase 6: Wiki Population
  → Delegate to wiki-maintainer subagent
  → Populate wiki entity pages from outline + sheets

Phase 7: Chapter Generation
  → For each chapter:
      → Load previous chapter recap
      → Assemble context via wiki-snapshot
      → Generate chapter content via chapter-writer subagent
      → Update wiki (post-chapter)
      → Create savepoint
  → Chapter revision loop (if enabled)

Phase 8: Assembly
  → Final edit pass (if enabled)
  → Scrubbing (if enabled)
  → Assemble final manuscript
```

---

## 6. Project Structure

```
llm-story-writer/
├── config.md                  # All configuration (YAML frontmatter)
├── config.example.sh          # Shell env config template
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
│   ├── presentation/         # CLI interfaces
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
├── .opencode/                # OpenCode agentic system
│   ├── agents/
│   │   ├── story-orchestrator.md
│   │   ├── outline-planner.md
│   │   ├── chapter-writer.md
│   │   └── wiki-maintainer.md
│   ├── tools/                # TypeScript tool wrappers
│   │   ├── prompt-loader.ts
│   │   ├── story-state.ts
│   │   ├── wiki-*.ts
│   │   ├── savepoint-mgr.ts
│   │   ├── _run.ts           # Shared Python tool runner
│   │   └── ...
│   ├── skills/               # Reusable skill definitions
│   │   ├── story-pipeline/
│   │   ├── wiki-conventions/
│   │   ├── context-budgeting/
│   │   └── ...
│   └── commands/             # TUI slash commands
│       ├── new-story.md
│       ├── continue.md
│       ├── status.md
│       └── ...
│
├── prompts/                  # 132+ prompt templates
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
│       ├── characters/       # Character JSON sheets
│       ├── settings/         # Setting JSON sheets
│       ├── savepoints/       # Savepoint files
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

## 7. Wiki Memory System

The **progressive wiki memory system** ([ADR 004](planning/adr/004-progressive-wiki-memory-system.md)) maintains structured story knowledge as interlinked markdown pages with YAML frontmatter.

### 7.1 Design Goals

- Eliminate knowledge re-derivation (agents receive authoritative world state)
- Proactive contradiction detection before errors propagate
- Token-efficient context budgeting via hierarchical detail levels
- Human-readable, git-versionable, Obsidian-compatible

### 7.2 Page Types

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

### 7.3 Confidence Taxonomy

Every wiki fact carries a confidence level:

| Level | Meaning |
|-------|---------|
| `verified` | Explicitly stated in the manuscript |
| `planned` | Outlined but not yet written |
| `speculative` | Inferred or implied by the agent |

### 7.4 Detail Levels

Wiki pages support three hierarchical summary levels:

| Level | Size | Use Case |
|-------|------|----------|
| `L1` | ~30 tokens | One-line headline for rapid context assembly |
| `L2` | ~150 tokens | Brief summary for scene pre-generation context |
| `L3` | ~500 tokens | Full description for complex scene decisions |

### 7.5 Wiki Update Lifecycle

1. **Scene-level update** (after each scene): `wiki-maintainer` agent extracts entities, state changes, and relationships
2. **Chapter-level lint** (after each chapter): Consistency check against the ConStory-Bench error taxonomy
3. **Pre-generation snapshot** (before each scene): `wiki-snapshot` tool assembles a token-budgeted world state snapshot

### 7.6 Wikilink Syntax

Wiki pages cross-reference each other using `[[wikilink]]` syntax:

```
[[character:herald]]     → links to the herald character page
[[location:citadel]]     → links to the citadel location page
[[event:the-siege]]      → links to the siege event page
```

---

## 8. Agents & Tools

### 8.1 Agents

Agents are defined in `.opencode/agents/` as markdown files with OpenCode skill syntax.

| Agent | Role |
|-------|------|
| `story-orchestrator` | Primary pipeline controller; drives the full generation lifecycle |
| `outline-planner` | Generates and refines the story outline |
| `chapter-writer` | Writes individual chapter content |
| `wiki-maintainer` | Updates wiki pages after each scene/chapter |

**Orchestrator Pipeline Phases:** Init → Outline → Approval → Wiki Init → Characters → Settings → Chapter Generation → Final Polish

### 8.2 Tools

Tools are TypeScript wrappers (`.opencode/tools/*.ts`) that call Python scripts (`src/tools/*.py`) via subprocess. Each tool handles a specific deterministic operation.

#### Core Tools

| Tool | Purpose |
|------|---------|
| `prompt-loader` | Load and render prompt templates with variable substitution |
| `story-state` | Initialize and update story state JSON |
| `savepoint-mgr` | Create, inspect, and restore savepoints (`list` = names only, `list-full` = full payloads) |
| `character-mgr` | Extract and manage character sheets |
| `setting-mgr` | Extract and manage setting sheets |
| `recap-manager` | Generate and manage chapter recaps |

#### Wiki Tools

| Tool | Purpose |
|------|---------|
| `wiki-init` | Initialize wiki directory structure and schema |
| `wiki-update` | Update wiki pages after scene/chapter |
| `wiki-read` | Read wiki pages at specified detail levels |
| `wiki-search` | Semantic search over wiki pages (ChromaDB) |
| `wiki-snapshot` | Assemble token-budgeted world state snapshot |
| `wiki-lint` | Consistency check against error taxonomy |
| `wiki-lint` | Check wiki page format compliance |

#### RAG Tools

| Tool | Purpose |
|------|---------|
| `rag-query` | Query ChromaDB for relevant story content chunks |

#### Critique Tools

| Tool | Purpose |
|------|---------|
| `critique-runner` | Run quality critique on outline or chapter |

### 8.3 Tool Architecture

```
Agent call
    ↓
TypeScript wrapper (.opencode/tools/<tool>.ts)
  — Zod schema for argument validation
  — execFileSync to invoke Python script
    ↓
Python script (src/tools/<tool_name>.py)
  — argparse for argument parsing
  — Domain logic via src/infrastructure/ classes
  — stdout for result, stderr for errors
    ↓
Result returned to agent
```

---

## 9. Strategies

The system supports pluggable story writing strategies via the strategy pattern.

### 9.1 Outline-Chapter Strategy (default)

```
1. Extract story elements and context from prompt
2. Generate detailed chapter-by-chapter outline
3. Write each chapter based on its outline entry
4. Generate metadata (title, summary, tags)
```

**Config:** `strategy: "outline-chapter"` in `config.md`

**Prompts:** `prompts/chapters/`, `prompts/outline/`

### 9.2 Stream-of-Consciousness Strategy

Generates stories in a flowing, associative narrative style without a formal outline.

**Config:** `strategy: "stream-of-consciousness"` in `config.md`

**Prompts:** `prompts/stream_of_consciousness/`

### 9.3 Adding a Custom Strategy

1. Create `src/application/strategies/<my_strategy>/`
2. Implement the strategy class inheriting from `StoryStrategy`
3. Add prompts under `prompts/<my_strategy>/`
4. Register in `strategy_factory.py`
5. Set `strategy: "my_strategy"` in `config.md`

---

## 10. Testing

### 10.1 Test Structure

```
tests/
├── unit/                    # Unit tests (fast, no LLM required)
│   └── test_<module>.py
└── integration/             # Integration tests (live LLM required)
    └── test_e2e_*.py
```

### 10.2 Running Tests

```bash
# Unit tests only (default, fast)
pytest tests/unit/ -v

# All tests including integration (requires live LLM)
pytest tests/ -v

# Single test file
pytest tests/unit/test_prompt_loader.py -v

# With coverage
pytest --cov=src tests/unit tests/integration
```

### 10.3 Integration Test Setup

Integration tests exercise the full pipeline against a live OpenAI-compatible LLM endpoint. Set `LLM_API_BASE` to override the default (`http://127.0.0.1:1234/v1`). A full integration run typically takes 30–90 minutes.

See [docs/testing/integration-tests.md](testing/integration-tests.md) for detailed setup instructions.

---

## 11. Development

### 11.1 Code Style

| Language | Tool | Config |
|----------|------|--------|
| Python | ruff | `pyproject.toml` |
| TypeScript | ESLint | `tsconfig.json` |

**Import ordering:** stdlib → third-party → local, alphabetised within groups.

**Naming:** `snake_case` for Python, `camelCase` for TypeScript.

### 11.2 Commands

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

### 11.3 Feature-Based Workflow

1. **Implement the feature** — write production code
2. **Lint and type check** — fix all errors
3. **Write tests** — verify correctness
4. **Confirm tests pass** — before committing
5. **Refactor only after tests pass**

### 11.4 Architecture Decision Records

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

## 12. Troubleshooting

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
- Verify `similarity_threshold` in `config.md` is not set too high (try 0.5)

### Story generation producing inconsistent output

- Enable `enable_chapter_revisions: true` in `config.md`
- Run `/wiki` command to inspect wiki state
- Use `/continue` from the last savepoint rather than restarting

### Savepoint restore failing

- Check `savepoint_dir` in `config.md` points to the correct path
- Check both `stories/<name>/savepoints/**/*.json` and `stories/<name>/savepoints/**/*.md` for the expected step
- Use `python3 src/tools/savepoint_manager.py --operation list --name <story>` to see savepoint names without loading full payloads
- Use `python3 src/tools/savepoint_manager.py --operation list-full --name <story>` only when you need the stored data itself

### Context window overflow

- Reduce `max_context_chunks` in `config.md`
- Lower `outline_chunk_size` if using chunked outline generation
- Enable `use_chunked_outline_generation: true` to reduce prompt sizes

---

## Quick Reference

```bash
# Start your local LLM server (e.g. LM Studio, or `ollama serve`)

# Run OpenCode TUI
opencode

# Lint + format + type check
ruff check --fix . && ruff format . && mypy src/

# Run tests
pytest tests/unit/ -v

# Create a new story
/new-story prompts/YourPrompt.txt

# Continue from savepoint
/continue story-name

# Check status
/status
```

---

*For architecture details, see [docs/planning/adr/](planning/adr/). For tools reference, see [docs/tools.md](tools.md). For feature documentation, see [docs/features/](features/).*
