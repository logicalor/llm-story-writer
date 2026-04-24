# Tools Reference

> Custom tools and plugins in the hybrid agent-tool architecture — TypeScript wrappers calling Python domain logic via subprocess, and lifecycle plugins hooking into OpenCode events.

## Overview

Tools follow the pattern established in [ADR 001](./planning/adr/001-hybrid-agent-tool-architecture.md): OpenCode agents handle orchestration and creative decisions; tools handle deterministic operations with single correct outputs for given inputs.

The active tool layer no longer uses the legacy `dependency-injector` container or the removed LangChain provider. OpenCode loads each TypeScript wrapper directly, and the Python runtime dependencies are intentionally narrow so the active stack reflects only code that still executes.

Each tool consists of two layers:

| Layer | Location | Language | Responsibility |
|-------|----------|----------|----------------|
| **Wrapper** | `.opencode/tools/<tool-name>.ts` | TypeScript | Argument parsing (Zod schema), OpenCode integration, subprocess invocation |
| **Script** | `src/tools/<tool_name>.py` | Python | Domain logic, reuses classes from `src/infrastructure/` and `src/domain/` |

The TypeScript wrapper calls the Python script via `execFileSync`, passing arguments as an array. The Python script writes its result to stdout and errors to stderr, using conventional exit codes (0 = success, 1 = domain error, 2 = argument error).

```
┌──────────────────────┐     subprocess      ┌─────────────────────┐
│  .opencode/tools/    │ ──────────────────▶  │  src/tools/         │
│  prompt-loader.ts    │     execFileSync     │  prompt_loader.py   │
│  (Zod schema, I/O)   │ ◀──────────────────  │  (argparse, logic)  │
└──────────────────────┘     stdout/stderr    └─────────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────────┐
                                              │  src/infrastructure/ │
                                              │  (PromptLoader, etc) │
                                              └─────────────────────┘
```

---

## prompt-loader

Loads a prompt template by ID and substitutes variables, returning the rendered prompt text.

**Source files:**
- `.opencode/tools/prompt-loader.ts` — TypeScript wrapper
- `src/tools/prompt_loader.py` — Python CLI script
- `src/infrastructure/prompts/prompt_loader.py` — Underlying `PromptLoader` class

### Purpose

Prompt templates are Markdown files in the `prompts/` directory (132 templates across 11 categories). This tool provides deterministic template loading and variable substitution so agents can retrieve rendered prompts without managing file paths or parsing logic.

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `promptId` | string | Yes | Template ID matching the file path under `prompts/` without `.md` extension |
| `variables` | `Record<string, string>` | No | Key-value pairs substituted into `{{key}}` and `{key}` placeholders |

### CLI Interface (Python script)

```bash
python3 src/tools/prompt_loader.py --prompt-id <id> [--variables '<json>']
```

**Examples:**

```bash
# Load a chapter content prompt with variables
python3 src/tools/prompt_loader.py \
  --prompt-id chapters/create_content \
  --variables '{"chapter_num": "1"}'

# Load a root-level prompt without variables
python3 src/tools/prompt_loader.py --prompt-id extract_base_context
```

### Prompt ID Format

The prompt ID maps directly to the file path under `prompts/`, minus the `.md` extension:

| Prompt ID | File Path |
|-----------|-----------|
| `chapters/create_content` | `prompts/chapters/create_content.md` |
| `extract_base_context` | `prompts/extract_base_context.md` |
| `recap/generate` | `prompts/recap/generate.md` |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success — rendered prompt printed to stdout |
| 1 | Domain error — prompt not found, invalid JSON in `--variables` |
| 2 | Argument error — missing required `--prompt-id` flag |

### Variable Substitution

The underlying `PromptLoader` supports two placeholder formats:
- `{{variable_name}}` — double-brace format
- `{variable_name}` — single-brace format

Both are replaced with the string value from the variables dictionary.

---

## story-state

Manages story state on disk — initialises story directory structures, reads/writes state fields with deep-merge semantics, and lists available stories.

**Source files:**
- `.opencode/tools/story-state.ts` — TypeScript wrapper
- `src/tools/story_state.py` — Python CLI script

### Purpose

Each story is stored as a directory under `stories/<name>/` containing a `state.json` file and subdirectories for chapters, characters, settings, and savepoints. This tool provides atomic, locked access to the state file so agents can safely initialise, inspect, and update story state without race conditions or data loss.

The state JSON schema matches the legacy `StoryContext`, `CharacterState`, `PlotThread`, and `ChapterState` structures:

```json
{
  "story_context": {
    "story_direction": "",
    "tone_style": "",
    "target_audience": "",
    "story_pacing": "medium",
    "current_themes": [],
    "world_rules": [],
    "genre_conventions": [],
    "current_tension": 1,
    "story_goals": [],
    "completed_arcs": []
  },
  "characters": {},
  "plot_threads": {},
  "chapters": {}
}
```

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `operation` | `"init" \| "read" \| "write" \| "list"` | Yes | Operation to perform |
| `name` | string | For `init`, `read`, `write` | Story name (maps to directory under `stories/`) |
| `field` | string | For `write`; optional for `read` | Dot-notation path into the state JSON (e.g., `story_context.tone_style`) |
| `value` | string | For `write` | JSON-encoded value to set at the target field |

### CLI Interface (Python script)

```bash
python3 src/tools/story_state.py --operation <op> [--name <name>] [--field <path>] [--value '<json>']
```

**Examples:**

```bash
# Initialise a new story
python3 src/tools/story_state.py --operation init --name my-story

# Read full state
python3 src/tools/story_state.py --operation read --name my-story

# Read a nested field
python3 src/tools/story_state.py --operation read --name my-story --field story_context.current_tension

# Write a field (deep-merges dicts, replaces scalars)
python3 src/tools/story_state.py --operation write --name my-story \
  --field story_context --value '{"tone_style": "noir", "current_tension": 7}'

# List all stories
python3 src/tools/story_state.py --operation list
```

### Operations

| Operation | Effect | Output |
|-----------|--------|--------|
| `init` | Creates `stories/<name>/` with subdirectories (`chapters/`, `characters/`, `settings/`, `savepoints/`) and an empty `state.json` | `{"status": "created", "story": "<name>"}` |
| `read` | Reads full state or a nested field via `--field` dot-notation | JSON state object or field value |
| `write` | Deep-merges a JSON value into the field at `--field`; sibling fields are preserved | `{"status": "updated", "field": "<path>"}` |
| `list` | Scans `stories/` for directories containing `state.json` | JSON array of story names |

### Deep Merge Semantics

The `write` operation uses deep merge when both the existing value and the new value are dictionaries. This means writing to `story_context` with `{"tone_style": "noir"}` updates only `tone_style` — all sibling fields (`story_direction`, `current_themes`, etc.) remain unchanged.

For non-dict values (scalars, arrays), the new value replaces the old one entirely.

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success — result printed to stdout as JSON |
| 1 | Domain error — story already exists (init), story/field not found (read/write), invalid JSON in `--value` |
| 2 | Argument error — missing required flag for the chosen operation |

### Security

- **Path traversal prevention** — story names are validated with `Path.is_relative_to()` to ensure they cannot escape the `stories/` directory (e.g., `../../etc/passwd` is rejected)
- **Atomic writes** — state is written to a temporary file then moved into place with `os.replace()`, preventing partial writes on crash
- **File locking** — `fcntl.flock(LOCK_EX)` prevents concurrent writes from corrupting state
- **Shell injection prevention** — the TypeScript wrapper uses `execFileSync` with an argument array, never shell interpolation
- **Test isolation** — the `STORIES_DIR` environment variable overrides the default stories directory, ensuring tests never touch production data

---

## savepoint-mgr

Manages story savepoints — save, load, check, list names, list full data, and clear checkpoint data used to resume story generation from intermediate steps.

**Source files:**
- `.opencode/tools/savepoint-mgr.ts` — TypeScript wrapper
- `.opencode/tools/_run.ts` — Shared Python subprocess runner with a 5-minute timeout
- `src/tools/savepoint_manager.py` — Python CLI script
- `src/infrastructure/storage/savepoint_repository.py` — Underlying `FilesystemSavepointRepository` class

### Purpose

During story generation, intermediate results (outlines, character sheets, chapter recaps, etc.) are saved as savepoints under `stories/<name>/savepoints/`. This tool provides CLI access to the `FilesystemSavepointRepository` so agents can checkpoint and resume multi-step generation pipelines without re-running expensive LLM calls.

Savepoints support **hierarchical step names** (e.g., `chapter_1/scene_2`) for organising checkpoints by phase and sub-step.

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `operation` | `"save" \| "load" \| "has" \| "list" \| "list-full" \| "clear"` | Yes | Operation to perform. Use `list` for names only; use `list-full` only when the savepoint payloads are actually needed |
| `name` | string | Yes | Story name (maps to directory under `stories/`) |
| `step` | string | For `save`, `load`, `has` | Step name, supports hierarchical paths like `chapter_1/scene_2` |
| `data` | string | For `save` | Data to save. Valid JSON is parsed and stored as structured data; non-JSON input is stored as raw text |

### CLI Interface (Python script)

```bash
python3 src/tools/savepoint_manager.py --operation <op> --name <name> [--step <step>] [--data '<json>']
```

**Examples:**

```bash
# Save a chapter outline checkpoint
python3 src/tools/savepoint_manager.py --operation save --name my-story \
  --step chapter_1/outline --data '{"title": "The Beginning", "scenes": 3}'

# Load a savepoint
python3 src/tools/savepoint_manager.py --operation load --name my-story \
  --step chapter_1/outline

# Check if a savepoint exists
python3 src/tools/savepoint_manager.py --operation has --name my-story \
  --step chapter_1/outline

# List all savepoints for a story
python3 src/tools/savepoint_manager.py --operation list --name my-story

# List all savepoints with full payloads (can be large)
python3 src/tools/savepoint_manager.py --operation list-full --name my-story

# Clear all savepoints for a story
python3 src/tools/savepoint_manager.py --operation clear --name my-story
```

### Operations

| Operation | Effect | Output |
|-----------|--------|--------|
| `save` | Writes strings to `savepoints/<step>.md` as raw UTF-8 text; writes structured values to `savepoints/<step>.json` as pretty JSON (`indent=2`, `ensure_ascii=False`) | `{"status": "saved", "step": "<step>"}` |
| `load` | Reads and deserialises a savepoint file | `{"step": "<step>", "data": <value>}` |
| `has` | Checks whether a savepoint file exists for the given step | `{"step": "<step>", "exists": true/false}` |
| `list` | Scans the `savepoints/` directory and returns step names only, without loading payloads | `{"savepoints": ["step_1", "step_2", ...]}` |
| `list-full` | Loads every savepoint and returns both step names and payloads | `{"savepoints": {"step_1": <data>, "step_2": <data>, ...}}` |
| `clear` | Removes all savepoint files for the story | `{"status": "cleared"}` |

### Hierarchical Step Names

Step names can contain `/` separators to create a hierarchy:

```
savepoints/
├── chapter_1/
│   ├── outline.md
│   ├── scene_1.md
│   └── recap.json
├── chapter_2/
│   └── outline.md
└── story_state.json
```

This maps naturally to the story generation pipeline phases (outline, character sheets, per-chapter scenes, recaps).

### Storage Format

Savepoints now use an **extension-based split format**:

- `.md` — raw prose or other plain-text savepoints
- `.json` — structured savepoints such as dicts, lists, booleans, numbers, and story state snapshots

The repository checks for `<step>.json` first, then `<step>.md`. New savepoints never use YAML frontmatter, and JSON files are written with `ensure_ascii=False` so Unicode punctuation stays readable on disk.

### Repository Behaviour

`FilesystemSavepointRepository` exposes one savepoint namespace per story and handles both file types transparently:

- `save_savepoint()` chooses `.md` or `.json` based on the runtime data type
- `load_savepoint()` returns parsed JSON for `.json` and raw text for `.md`
- `list_savepoint_names()` returns extension-free step names for resume/discovery flows
- `list_savepoints()` remains available for full payload inspection, but it loads every file and is much heavier
- `delete_savepoint()` and `clear_all_savepoints()` remove both `.md` and `.json` variants

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success — result printed to stdout as JSON |
| 1 | Domain error — story not found, savepoint not found |
| 2 | Argument error — missing required `--step` or `--data` flag for the chosen operation |

### Security

- **Path traversal prevention (story name)** — story names are validated with `Path.is_relative_to()` to ensure they cannot escape the `stories/` directory
- **Path traversal prevention (step name)** — step names are checked for `..` segments and validated with `is_relative_to()` to prevent escaping the `savepoints/` directory
- **Shell injection prevention** — the TypeScript wrapper uses `execFileSync` with an argument array, never shell interpolation
- **Async bridging** — the Python script bridges from sync CLI to async repository methods using `asyncio.run()`
- **Test isolation** — the `STORIES_DIR` environment variable overrides the default stories directory, ensuring tests never touch production data

---

## character-mgr

Manages story character sheets — extract names, generate/update/load character sheets, list characters, and create abridged summaries.

**Source files:**
- `.opencode/tools/character-mgr.ts` — TypeScript wrapper
- `src/tools/character_manager.py` — Python CLI script

### Purpose

During story generation, the pipeline extracts character names from story elements and generates structured character sheets (with chunked sections like background, personality, motivations, etc.). This tool provides file I/O for those character sheets so agents can create, update, inspect, and summarise character data without managing file paths or JSON merging logic.

Character sheets are stored as JSON files at `stories/<name>/characters/<slug>.json`, where `<slug>` is the character name lowercased with spaces replaced by hyphens and non-alphanumeric characters stripped.

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `operation` | `"extract-names" \| "generate-sheet" \| "update-sheet" \| "load-sheet" \| "list" \| "generate-abridged"` | Yes | Operation to perform |
| `name` | string | Yes | Story name (maps to directory under `stories/`) |
| `character` | string | For `generate-sheet`, `update-sheet`, `load-sheet`, `generate-abridged` | Character name (converted to slug for file lookup) |
| `data` | string | For `extract-names`, `generate-sheet`, `update-sheet` | JSON string input |
| `budget` | number | No | Word budget for `generate-abridged` (default: 500) |
| `abridged` | boolean | No | If true, `load-sheet` returns only name, summary, and timestamp |

### CLI Interface (Python script)

```bash
python3 src/tools/character_manager.py --operation <op> --name <name> [--character <name>] [--data '<json>'] [--budget N] [--abridged]
```

**Examples:**

```bash
# Parse a JSON array of character names
python3 src/tools/character_manager.py --operation extract-names --name my-story \
  --data '["Alice", "Bob", "The Dark Knight"]'

# Store a generated character sheet
python3 src/tools/character_manager.py --operation generate-sheet --name my-story \
  --character "Alice" --data '{"sheet": "Full text...", "chunks": {"background": "..."}, "summary": "Brief"}'

# Deep-merge updates into an existing sheet
python3 src/tools/character_manager.py --operation update-sheet --name my-story \
  --character "Alice" --data '{"chunks": {"personality": "Updated traits..."}}'

# Load a full character sheet
python3 src/tools/character_manager.py --operation load-sheet --name my-story \
  --character "Alice"

# Load an abridged version (name + summary only)
python3 src/tools/character_manager.py --operation load-sheet --name my-story \
  --character "Alice" --abridged

# List all characters for a story
python3 src/tools/character_manager.py --operation list --name my-story

# Generate a token-budgeted abridged summary
python3 src/tools/character_manager.py --operation generate-abridged --name my-story \
  --character "Alice" --budget 300
```

### Operations

| Operation | Effect | Output |
|-----------|--------|--------|
| `extract-names` | Parses a JSON array of character names from `--data` | `{"names": ["Alice", "Bob", ...]}` |
| `generate-sheet` | Creates a new character sheet JSON file with name, sheet text, chunks, summary, and timestamp. **Note:** overwrites any existing sheet for the character — use `update-sheet` for partial updates that preserve existing data. | `{"status": "ok", "path": "stories/<name>/characters/<slug>.json"}` |
| `update-sheet` | Deep-merges `--data` into an existing sheet; preserves sibling chunk keys | `{"status": "ok", "path": "stories/<name>/characters/<slug>.json"}` |
| `load-sheet` | Loads a character sheet; with `--abridged`, returns only name, summary, and timestamp | Full or abridged JSON sheet object |
| `list` | Scans `characters/` directory for `.json` files, reads the `name` field from each | `{"characters": ["Alice", "Bob", ...]}` |
| `generate-abridged` | Truncates the `sheet` text to a word limit (budget × 0.75), saves as `summary`, updates the file | `{"summary": "...", "path": "stories/<name>/characters/<slug>.json"}` |

### Character Sheet JSON Format

```json
{
  "name": "Alice",
  "sheet": "Full character sheet text...",
  "chunks": {
    "background": "Born in a small village...",
    "personality": "Introverted but fiercely loyal...",
    "motivations": "Seeks to restore her family honour..."
  },
  "summary": "Abridged summary text...",
  "updated_at": "2026-04-13T10:30:00+00:00"
}
```

### Deep Merge Semantics

The `update-sheet` operation merges at the `chunks` level: new chunk keys are added, existing chunk keys are overwritten, and sibling chunk keys are preserved. Top-level fields (`sheet`, `summary`) are replaced if present in the update data. The `updated_at` timestamp is always refreshed.

### Slug Generation

Character names are converted to filesystem-safe slugs:
1. Lowercase the name
2. Replace spaces with hyphens
3. Strip non-alphanumeric characters (except hyphens)
4. Collapse consecutive hyphens
5. Trim leading/trailing hyphens

| Character Name | Slug | File Path |
|----------------|------|-----------|
| `Alice` | `alice` | `characters/alice.json` |
| `The Dark Knight` | `the-dark-knight` | `characters/the-dark-knight.json` |
| `Dr. Smith` | `dr-smith` | `characters/dr-smith.json` |

### Exit Codes

| Code | Meaning |
|------|----------|
| 0 | Success — result printed to stdout as JSON |
| 1 | Domain error — character sheet not found (update/load/generate-abridged), invalid JSON in `--data` |
| 2 | Argument error — missing required `--character` or `--data` flag for the chosen operation |

### Security

- **Path traversal prevention (story name)** — story names are validated with `Path.is_relative_to()` to ensure they cannot escape the `stories/` directory
- **Path traversal prevention (character name)** — character names are checked for `..` segments and the resolved file path is validated with `is_relative_to()` to prevent escaping the `characters/` directory
- **Shell injection prevention** — the TypeScript wrapper uses `execFileSync` with an argument array, never shell interpolation
- **Test isolation** — the `STORIES_DIR` environment variable overrides the default stories directory, ensuring tests never touch production data

---

## setting-mgr

Manages story setting/location sheets — extract names, generate/update/load setting sheets, list settings, and create abridged summaries.

**Source files:**
- `.opencode/tools/setting-mgr.ts` — TypeScript wrapper
- `src/tools/setting_manager.py` — Python CLI script

### Purpose

During story generation, the pipeline extracts setting/location names from story elements and generates structured setting sheets (with chunked sections like geography, atmosphere, history, etc.). This tool provides file I/O for those setting sheets so agents can create, update, inspect, and summarise setting data without managing file paths or JSON merging logic.

Setting sheets are stored as JSON files at `stories/<name>/settings/<slug>.json`, where `<slug>` is the setting name lowercased with spaces replaced by hyphens and non-alphanumeric characters stripped.

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `operation` | `"extract-names" \| "generate-sheet" \| "update-sheet" \| "load-sheet" \| "list" \| "generate-abridged"` | Yes | Operation to perform |
| `name` | string | Yes | Story name (maps to directory under `stories/`) |
| `setting` | string | For `generate-sheet`, `update-sheet`, `load-sheet`, `generate-abridged` | Setting name (converted to slug for file lookup) |
| `data` | string | For `extract-names`, `generate-sheet`, `update-sheet` | JSON string input |
| `budget` | number | No | Word budget for `generate-abridged` (default: 500) |
| `abridged` | boolean | No | If true, `load-sheet` returns only name, summary, and timestamp |

### CLI Interface (Python script)

```bash
python3 src/tools/setting_manager.py --operation <op> --name <name> [--setting <name>] [--data '<json>'] [--budget N] [--abridged]
```

**Examples:**

```bash
# Parse a JSON array of setting names
python3 src/tools/setting_manager.py --operation extract-names --name my-story \
  --data '["The Grand Library", "Shadow Market", "Crystal Caves"]'

# Store a generated setting sheet
python3 src/tools/setting_manager.py --operation generate-sheet --name my-story \
  --setting "The Grand Library" --data '{"sheet": "Full text...", "chunks": {"geography": "..."}, "summary": "Brief"}'

# Deep-merge updates into an existing sheet
python3 src/tools/setting_manager.py --operation update-sheet --name my-story \
  --setting "The Grand Library" --data '{"chunks": {"atmosphere": "Updated description..."}}'

# Load a full setting sheet
python3 src/tools/setting_manager.py --operation load-sheet --name my-story \
  --setting "The Grand Library"

# Load an abridged version (name + summary only)
python3 src/tools/setting_manager.py --operation load-sheet --name my-story \
  --setting "The Grand Library" --abridged

# List all settings for a story
python3 src/tools/setting_manager.py --operation list --name my-story

# Generate a token-budgeted abridged summary
python3 src/tools/setting_manager.py --operation generate-abridged --name my-story \
  --setting "The Grand Library" --budget 300
```

### Operations

| Operation | Effect | Output |
|-----------|--------|--------|
| `extract-names` | Parses a JSON array of setting names from `--data` | `{"names": ["The Grand Library", "Shadow Market", ...]}` |
| `generate-sheet` | Creates a new setting sheet JSON file with name, sheet text, chunks, summary, and timestamp. **Note:** overwrites any existing sheet for the setting — use `update-sheet` for partial updates that preserve existing data. | `{"status": "ok", "path": "stories/<name>/settings/<slug>.json"}` |
| `update-sheet` | Deep-merges `--data` into an existing sheet; preserves sibling chunk keys | `{"status": "ok", "path": "stories/<name>/settings/<slug>.json"}` |
| `load-sheet` | Loads a setting sheet; with `--abridged`, returns only name, summary, and timestamp | Full or abridged JSON sheet object |
| `list` | Scans `settings/` directory for `.json` files, reads the `name` field from each | `{"settings": ["The Grand Library", "Shadow Market", ...]}` |
| `generate-abridged` | Truncates the `sheet` text to a word limit (budget × 0.75), saves as `summary`, updates the file | `{"summary": "...", "path": "stories/<name>/settings/<slug>.json"}` |

### Setting Sheet JSON Format

```json
{
  "name": "The Grand Library",
  "sheet": "Full setting sheet text...",
  "chunks": {
    "geography": "Located in the heart of the old city...",
    "atmosphere": "Dust motes float through shafts of light...",
    "history": "Founded three centuries ago by the Scholar King..."
  },
  "summary": "Abridged summary text...",
  "updated_at": "2026-04-13T10:30:00+00:00"
}
```

### Deep Merge Semantics

The `update-sheet` operation merges at the `chunks` level: new chunk keys are added, existing chunk keys are overwritten, and sibling chunk keys are preserved. Top-level fields (`sheet`, `summary`) are replaced if present in the update data. The `updated_at` timestamp is always refreshed.

### Slug Generation

Setting names are converted to filesystem-safe slugs:
1. Lowercase the name
2. Replace spaces with hyphens
3. Strip non-alphanumeric characters (except hyphens)
4. Collapse consecutive hyphens
5. Trim leading/trailing hyphens

| Setting Name | Slug | File Path |
|--------------|------|-----------|
| `The Grand Library` | `the-grand-library` | `settings/the-grand-library.json` |
| `Shadow Market` | `shadow-market` | `settings/shadow-market.json` |
| `Dr. Voss's Lab` | `dr-vosss-lab` | `settings/dr-vosss-lab.json` |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success — result printed to stdout as JSON |
| 1 | Domain error — setting sheet not found (update/load/generate-abridged), invalid JSON in `--data` |
| 2 | Argument error — missing required `--setting` or `--data` flag for the chosen operation |

### Security

- **Path traversal prevention (story name)** — story names are validated with `Path.is_relative_to()` to ensure they cannot escape the `stories/` directory
- **Path traversal prevention (setting name)** — setting names are checked for `..` segments and the resolved file path is validated with `is_relative_to()` to prevent escaping the `settings/` directory
- **Shell injection prevention** — the TypeScript wrapper uses `execFileSync` with an argument array, never shell interpolation
- **Test isolation** — the `STORIES_DIR` environment variable overrides the default stories directory, ensuring tests never touch production data

---

## recap-manager

Manages chapter recaps — load, generate (5-stage pipeline), sanitize, and compact. Recaps are JSON event timelines stored as savepoints.

**Source files:**
- `.opencode/tools/recap-manager.ts` — TypeScript wrapper
- `src/tools/recap_manager.py` — Python CLI script
- `src/tools/_llm.py` — Shared LLM client (OpenAI-compatible API)
- `src/application/strategies/outline_chapter/recap_manager.py` — Original `RecapManager` class (reference for business logic)

### Purpose

During story generation, each chapter produces a structured recap of events with timing, importance, and character development details. This tool wraps the recap generation pipeline so agents can generate, refine, and compact recaps without managing the multi-stage LLM workflow directly.

Recaps are stored as savepoints at `chapter_N/recap` under `stories/<name>/savepoints/`.

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `operation` | `"load" \| "generate" \| "sanitize" \| "compact"` | Yes | Operation to perform |
| `name` | string | Yes | Story name (maps to directory under `stories/`) |
| `chapter` | number | Yes | Chapter number |
| `storyStartDate` | string | For `generate`, `sanitize` | Story start date in YYYY-MM-DD format |
| `enableProgrammaticClassification` | boolean | No | Enable programmatic recency classification during sanitize (default: false) |
| `model` | string | No | Override LLM model identifier |

### CLI Interface (Python script)

```bash
python3 src/tools/recap_manager.py --operation <op> --name <name> --chapter <N> [--story-start-date <date>] [--enable-programmatic-classification] [--model <model>]
```

**Examples:**

```bash
# Load an existing recap
python3 src/tools/recap_manager.py --operation load --name my-story --chapter 3

# Generate a recap using the 5-stage pipeline
python3 src/tools/recap_manager.py --operation generate --name my-story \
  --chapter 3 --story-start-date 2024-01-15

# Sanitize and reorganise a recap
python3 src/tools/recap_manager.py --operation sanitize --name my-story \
  --chapter 3 --story-start-date 2024-01-15

# Sanitize with programmatic recency classification
python3 src/tools/recap_manager.py --operation sanitize --name my-story \
  --chapter 3 --story-start-date 2024-01-15 --enable-programmatic-classification

# Compact a recap based on chapter age
python3 src/tools/recap_manager.py --operation compact --name my-story --chapter 12
```

### Operations

| Operation | Effect | Output |
|-----------|--------|--------|
| `load` | Reads recap from savepoint `chapter_N/recap` | `{"status": "success", "operation": "load", "data": <recap>}` |
| `generate` | Runs 5-stage pipeline (extract → time → enrich → format → filter), saves intermediates | `{"status": "success", "operation": "generate", "data": <recap>}` |
| `sanitize` | Merges and organises recap via LLM, optionally classifies event recency | `{"status": "success", "operation": "sanitize", "data": <recap>}` |
| `compact` | Applies progressive compaction based on chapter number (none/light/moderate/heavy) | `{"status": "success", "operation": "compact", "data": <recap>}` |

### Generate Pipeline (5 stages)

1. **Extract events** — `recap/extract_events` prompt extracts events from chapter content as JSON array
2. **Assign timing** — `recap/assign_event_timing` prompt assigns start/end times using story timeline
3. **Enrich details** — `recap/enrich_event_details` prompt adds character development, locations, symbols
4. **Format output** — `recap/format_json` prompt structures events into standardised recap JSON
5. **Filter aged events** — Programmatic: keeps only high-importance events (matches `RecapManager._should_keep_event` logic)

Intermediate results are saved to savepoints: `chapter_N/events`, `chapter_N/timed_events`, `chapter_N/enriched_events`, `chapter_N/formatted_recap`.

### Compaction Levels

| Chapter Range | Compaction Level |
|---------------|-----------------|
| 1–5 | None (returned as-is) |
| 6–10 | Light |
| 11–20 | Moderate |
| 21+ | Heavy |

### LLM Configuration

The tool uses `src/tools/_llm.py` for LLM access, configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_BASE` | `http://127.0.0.1:1234/v1` | OpenAI-compatible API base URL |
| `LLM_MODEL` | `gemma-4-26b-a4b-it-heretic-guff` | Default model identifier |

The `--model` argument overrides `LLM_MODEL` for a single invocation.

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success — result printed to stdout as JSON |
| 1 | Domain error — story/recap not found, LLM failure, invalid JSON |
| 2 | Argument error — missing required `--chapter` or `--story-start-date` flag |

### Security

- **Path traversal prevention** — story names are validated with `Path.is_relative_to()` to ensure they cannot escape the `stories/` directory
- **Shell injection prevention** — the TypeScript wrapper uses `execFileSync` with an argument array, never shell interpolation
- **Test isolation** — the `STORIES_DIR` environment variable overrides the default stories directory, ensuring tests never touch production data

---

## outline-generator

Multi-step outline generation pipeline: analyses a story prompt via an 8-chunk LLM conversation, assembles story elements, generates an initial outline, expands chapters in chunks with continuity analysis, and refines via critique feedback.

**Source files:**
- `.opencode/tools/outline-generator.ts` — TypeScript wrapper
- `src/tools/outline_generator.py` — Python CLI script
- `src/tools/_llm.py` — Shared LLM client (`generate_text`, `generate_text_messages`, `_extract_json_block`)
- `src/infrastructure/prompts/prompt_loader.py` — Prompt template loading
- `src/infrastructure/storage/savepoint_repository.py` — Savepoint persistence

### Purpose

The outline generator is the most complex tool in the system. It orchestrates the entire story analysis and outline creation pipeline — from initial prompt understanding through structured analysis, outline generation, chunked chapter expansion, and refinement. Every sub-step saves its result to a savepoint, making the pipeline fully resumable if interrupted.

The tool uses `generate_text_messages()` from `src/tools/_llm.py` to maintain multi-turn conversation history during the analysis phase, providing coherent context across all 8 analysis chunks.

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `operation` | `"analyze-prompt" \| "generate-elements" \| "generate-outline" \| "expand-chapter" \| "expand-to-scenes" \| "refine"` | Yes | Operation to perform |
| `name` | string | Yes | Story name (directory under `stories/`) |
| `prompt` | string | For `analyze-prompt`; optional for `generate-outline` | Story prompt text |
| `desiredChapters` | integer | For `generate-outline` | Number of desired chapters (must be ≥ 1) |
| `chunkStart` | integer | For `expand-chapter` | Start chapter for chunk expansion (must be ≥ 1) |
| `chunkEnd` | integer | For `expand-chapter` | End chapter for chunk expansion (must be ≥ `chunkStart`) |
| `totalChapters` | integer | For `expand-chapter` | Total chapters in the story (must be ≥ `chunkEnd`) |
| `previousChunks` | string | No | Previous chunk outlines text (for `expand-chapter` continuity) |
| `continuitySummary` | string | No | Continuity summary from prior chunks (for `expand-chapter`) |
| `chapterNum` | integer | For `expand-to-scenes` | Chapter number whose synopsis is being decomposed |
| `chapterSynopsis` | string | For `expand-to-scenes` | Expanded chapter synopsis text to decompose into scene objects |
| `scenesMin` | integer | For `expand-to-scenes` | Minimum scene count to generate (1–30) |
| `scenesMax` | integer | For `expand-to-scenes` | Maximum scene count to generate (1–30, and must be ≥ `scenesMin`) |
| `previousRecap` | string | No | Prior chapter recap for scene-level continuity hints |
| `nextChapterSynopsis` | string | No | Next chapter synopsis used to shape the chapter ending and lead-in |
| `feedback` | string | For `refine` | Critique/feedback text to apply |
| `model` | string | No | Override LLM model identifier |

### CLI Interface (Python script)

```bash
python3 src/tools/outline_generator.py --operation <op> --name <name> [options]
```

**Examples:**

```bash
# Analyze a story prompt (full multi-step pipeline)
python3 src/tools/outline_generator.py --operation analyze-prompt \
  --name my-story --prompt "A detective in 1920s Chicago..."

# Combine analysis chunks into story elements
python3 src/tools/outline_generator.py --operation generate-elements \
  --name my-story

# Generate initial outline with 12 chapters
python3 src/tools/outline_generator.py --operation generate-outline \
  --name my-story --desired-chapters 12

# Expand chapters 1-4 of a 12-chapter story
python3 src/tools/outline_generator.py --operation expand-chapter \
  --name my-story --chunk-start 1 --chunk-end 4 --total-chapters 12

# Expand chapters 5-8 with continuity from prior chunks
python3 src/tools/outline_generator.py --operation expand-chapter \
  --name my-story --chunk-start 5 --chunk-end 8 --total-chapters 12 \
  --previous-chunks "<chapters 1-4 text>" --continuity-summary "<summary>"

# Expand chapter 5 synopsis into 8-16 structured scene definitions
python3 src/tools/outline_generator.py --operation expand-to-scenes \
  --name my-story --chapter-num 5 \
  --chapter-synopsis "<expanded chapter synopsis>" \
  --scenes-min 8 --scenes-max 16 \
  --previous-recap "<chapter 4 recap>" \
  --next-chapter-synopsis "<chapter 6 synopsis>"

# Refine outline with critique feedback
python3 src/tools/outline_generator.py --operation refine \
  --name my-story --feedback "The pacing in chapters 3-5 needs tightening..."
```

### Operations

| Operation | Effect | Output |
|-----------|--------|--------|
| `analyze-prompt` | Runs 4-step pipeline: understand prompt → generate 8 analysis chunks → extract start date → extract base context. Each step saved to savepoint. | `{"status": "success", "operation": "analyze-prompt", "data": {"chunks_generated": 8, "story_start_date": "...", "base_context": "..."}}` |
| `generate-elements` | Concatenates all 8 analysis chunks (with headers) into a single `story_elements` savepoint | `{"status": "success", "operation": "generate-elements", "data": {"story_elements": "..."}}` |
| `generate-outline` | Generates initial outline from story elements + base context using `outline/create` prompt | `{"status": "success", "operation": "generate-outline", "data": {"outline": "..."}}` |
| `expand-chapter` | Generates outline chunk for a chapter range, then runs continuity analysis for the next chunk | `{"status": "success", "operation": "expand-chapter", "data": {"chunk_outline": "...", "continuity_analysis": "..."}}` |
| `expand-to-scenes` | Expands one chapter synopsis into a validated JSON array of scene objects, enforces the requested scene-count band, and writes the result to a scene-definitions savepoint | Returns compact success data with `scene_count` and `savepoint_step`; writes `chapter_{N}/scene_definitions` |
| `refine` | Applies enrichment analysis using `outline/analyze_enrichment` prompt against current outline | `{"status": "success", "operation": "refine", "data": {"refined_outline": "..."}}` |

### Analyze-Prompt Pipeline Detail

The `analyze-prompt` operation executes 4 sequential steps, each checking for existing savepoints before calling the LLM:

1. **Understand prompt** — Sends the story prompt through `multistep/outline/understand_prompt` template. Builds initial conversation context.
2. **Generate 8 analysis chunks** — Iterates through chunk types, appending each as a user/assistant turn in the conversation history:
   - Core Story Foundation
   - Character Foundation
   - Setting Foundation
   - Plot Structure
   - Theme & Message
   - Tone & Style
   - Conflict & Stakes
   - World Rules & Logic
3. **Extract story start date** — Uses the core story foundation chunk to extract a timeline starting point via `multistep/outline/story_start_date` prompt. Falls back to "Present day" on failure.
4. **Extract base context** — Saves the core story foundation chunk as the `base_context` savepoint.

### Savepoint Structure

All intermediate results are persisted under `stories/<name>/savepoints/`:

| Savepoint Key | Created By | Content |
|---------------|-----------|---------|
| `understand_prompt` | `analyze-prompt` | LLM response to prompt analysis |
| `story_analysis/core_story_foundation_chunk` | `analyze-prompt` | Core story foundation analysis |
| `story_analysis/character_foundation_chunk` | `analyze-prompt` | Character foundation analysis |
| `story_analysis/setting_foundation_chunk` | `analyze-prompt` | Setting foundation analysis |
| `story_analysis/plot_structure_chunk` | `analyze-prompt` | Plot structure analysis |
| `story_analysis/theme_message_chunk` | `analyze-prompt` | Theme & message analysis |
| `story_analysis/tone_style_chunk` | `analyze-prompt` | Tone & style analysis |
| `story_analysis/conflict_stakes_chunk` | `analyze-prompt` | Conflict & stakes analysis |
| `story_analysis/world_rules_logic_chunk` | `analyze-prompt` | World rules & logic analysis |
| `story_start_date` | `analyze-prompt` | Extracted story timeline start |
| `base_context` | `analyze-prompt` | Core foundation as base context |
| `story_elements` | `generate-elements` | Combined text of all 8 chunks |
| `initial_outline` | `generate-outline` | Generated outline text |
| `outline_chunk_N_M` | `expand-chapter` | Expanded outline for chapters N–M |
| `continuity_N_M` | `expand-chapter` | Continuity analysis for chunk N–M |
| `chapter_{N}/scene_definitions` | `expand-to-scenes` | JSON array of validated scene objects for chapter `N` |
| `refined_outline` | `refine` | Refined outline incorporating user feedback |

### Resumability

All LLM-calling operations check `_has_savepoint()` before invoking the model. If a savepoint exists, the saved result is loaded and the LLM call is skipped. This means:

- If `analyze-prompt` fails on chunk 5, re-running it resumes from chunk 5 — chunks 1–4 are loaded from savepoints
- `generate-outline` checks for an existing `initial_outline` savepoint before calling the LLM
- `expand-chapter` checks for existing `outline_chunk_N_M` and `continuity_N_M` savepoints before calling the LLM
- Conversation history is reconstructed from saved chunks to maintain coherent multi-turn context
- The `generate-elements` operation is purely deterministic (no LLM) — it concatenates saved chunks

### Conversation History Support

The `analyze-prompt` operation uses `generate_text_messages()` from `src/tools/_llm.py` to pass full conversation history to the LLM. This function accepts a list of `{"role": "...", "content": "..."}` message dicts and calls the OpenAI-compatible chat completions endpoint with the full message array.

This ensures the LLM has context from earlier analysis chunks when generating later ones, producing more coherent and cross-referenced analysis.

### LLM Configuration

The tool uses `src/tools/_llm.py` for LLM access, configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_BASE` | `http://127.0.0.1:1234/v1` | OpenAI-compatible API base URL |
| `LLM_MODEL` | `gemma-4-26b-a4b-it-heretic-guff` | Default model identifier |

The `--model` argument overrides `LLM_MODEL` for a single invocation.

### Argument Validation

Numeric arguments are validated at both layers:

- **TypeScript (Zod)** — `desiredChapters`, `chunkStart`, `chunkEnd`, `totalChapters`, `chapterNum`, `scenesMin`, and `scenesMax` are validated as bounded integers before the Python tool runs
- **Python (argparse and command validation)** — `--desired-chapters` must be ≥ 1; `--chunk-start` must be ≥ 1; `--chunk-end` must be ≥ `--chunk-start`; `--total-chapters` must be ≥ `--chunk-end`; `expand-to-scenes` enforces `1 <= scenesMin <= scenesMax <= 30`

Invalid values produce exit code 1 with a descriptive error message.

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success — result printed to stdout as JSON |
| 1 | Domain error — missing prerequisite savepoints, LLM failure, invalid numeric arguments |
| 2 | Argument error — missing required flag for the chosen operation |

### Security

- **Path traversal prevention** — story names are validated with `Path.is_relative_to()` to ensure they cannot escape the `stories/` directory
- **Shell injection prevention** — the TypeScript wrapper uses `execFileSync` with an argument array, never shell interpolation
- **Test isolation** — the `STORIES_DIR` environment variable overrides the default stories directory, ensuring tests never touch production data

---

## scene-writer

Scene writing pipeline: parse a chapter outline into scene definitions, generate individual scenes, revise scenes with feedback, assemble scenes into a chapter, generate a full chapter in one pass, or analyze chapter prose for scrub and voice issues.

**Source files:**
- `.opencode/tools/scene-writer.ts` — TypeScript wrapper
- `src/tools/scene_writer.py` — Python CLI script
- `src/tools/_llm.py` — Shared LLM client (`generate_text`, `_extract_json_block`, `count_tokens`)
- `src/infrastructure/prompts/prompt_loader.py` — Prompt template loading
- `src/infrastructure/storage/savepoint_repository.py` — Savepoint persistence

### Purpose

The scene writer primarily breaks chapter-level generation into finer-grained scene units. A chapter outline is first parsed into individual scene definitions (structured JSON), then each scene is generated independently. Scenes can be revised with targeted feedback, and once all scenes in a chapter are complete they are assembled into a single chapter document with section headers and separators.

For orchestrator fallback mode (`scene_generation_pipeline: false`), the same tool also supports generating a whole chapter as one LLM call. In that mode, the tool loads chapter context directly from story state and savepoints, writes the completed chapter to both savepoints and story state, and remains resumable through the same savepoint mechanism.

The same tool also owns the prose-analysis prompts used by the late-stage editing passes. `scrub-analyze` performs sentence-level issue extraction for accepted chapter prose, and `voice-analyze` performs manuscript-context voice and pacing analysis. Unlike scene generation operations, these analysis calls are stateless and do not create savepoints.

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `operation` | `"parse-definitions" \| "generate" \| "revise" \| "assemble-chapter" \| "scrub-analyze" \| "voice-analyze" \| "generate-chapter"` | Yes | Operation to perform |
| `name` | string | Yes | Story name (directory under `stories/`) |
| `chapterNum` | integer | For all operations | Chapter number (must be ≥ 1) |
| `sceneNum` | integer | For `generate`, `revise` | Scene number within the chapter (must be ≥ 1) |
| `sceneCount` | integer | For `assemble-chapter` | Total number of scenes in the chapter (must be ≥ 1) |
| `chapterOutline` | string | For `parse-definitions`, `generate`; optional for `revise` | Chapter outline text |
| `sceneDefinition` | string | For `generate`; optional for `revise` | Scene definition as JSON string |
| `sceneContent` | string | No | Current scene content to revise; when omitted, `revise` loads `chapter_N/scene_M` from savepoints |
| `feedback` | string | For `revise` | Revision feedback describing what to improve |
| `chapterTitle` | string | No | Chapter title for `assemble-chapter` (defaults to `"Chapter N"`) |
| `baseContext` | string | No | Base story context (for `generate`) |
| `storyElements` | string | No | Story elements text (for `generate`) |
| `characterSheets` | string | No | Character sheets (for `generate`) |
| `settingSheets` | string | No | Setting sheets (for `generate`) |
| `previousRecap` | string | No | Previous chapter recap (for `generate`) |
| `previousScene` | string | No | Previous scene content (for `generate`); when omitted and `sceneNum > 1`, the tool loads `chapter_N/scene_{M-1}` from savepoints if available |
| `nextSceneDefinition` | string | No | Next scene definition (for `generate`) |
| `nextChapterSynopsis` | string | No | Next chapter synopsis (for `generate`) |
| `additionalContext` | string | No | Extra context appended to `base_context` for `generate-chapter` |
| `chapterText` | string | For `scrub-analyze`, `voice-analyze` | Full chapter text to analyze |
| `priorChaptersSummary` | string | No | Prior-chapter continuity summary for `voice-analyze` |
| `includeContent` | boolean | No | Return full scene or chapter prose in the response for `generate`, `revise`, `assemble-chapter`, and `generate-chapter` (default: `false`, which returns compact savepoint references only) |
| `model` | string | No | Override LLM model identifier |

### CLI Interface (Python script)

```bash
python3 src/tools/scene_writer.py --operation <op> --name <name> [options] [--include-content]
```

**Examples:**

```bash
# Parse chapter outline into scene definitions
python3 src/tools/scene_writer.py --operation parse-definitions \
  --name my-story --chapter-num 3 \
  --chapter-outline "Elena arrives at the ancient city..."

# Generate a single scene
python3 src/tools/scene_writer.py --operation generate \
  --name my-story --chapter-num 3 --scene-num 1 \
  --scene-definition '{"title": "The Arrival", "description": "Elena enters the gate"}' \
  --chapter-outline "Chapter 3 outline text" \
  --base-context "Fantasy world context"

# Returns compact reference data by default
# {
#   "status": "success",
#   "operation": "generate",
#   "data": {
#     "scene_ref": "chapter_3/scene_1",
#     "savepoint_step": "chapter_3/scene_1",
#     "char_count": 1248
#   }
# }

# Revise a scene with feedback
python3 src/tools/scene_writer.py --operation revise \
  --name my-story --chapter-num 3 --scene-num 1 \
  --feedback "Add more tension in the dialogue" \
  --scene-definition '{"title": "The Arrival"}' \
  --chapter-outline "Chapter 3 outline"

# Returns compact reference data by default
# {
#   "status": "success",
#   "operation": "revise",
#   "data": {
#     "scene_ref": "chapter_3/scene_1",
#     "savepoint_step": "chapter_3/scene_1",
#     "char_count": 1312
#   }
# }

# Opt in to full prose in the response when needed
python3 src/tools/scene_writer.py --operation generate \
  --name my-story --chapter-num 3 --scene-num 2 \
  --scene-definition '{"title": "The Council Hall", "description": "Elena meets the council"}' \
  --chapter-outline "Chapter 3 outline text" \
  --include-content

# Response adds a "content" field alongside compact references

# Assemble all scenes into a chapter
python3 src/tools/scene_writer.py --operation assemble-chapter \
  --name my-story --chapter-num 3 --scene-count 4 \
  --chapter-title "The Ancient City"

# Generate a whole chapter in one pass (fallback path)
python3 src/tools/scene_writer.py --operation generate-chapter \
  --name my-story --chapter-num 3 \
  --additional-context "Keep focus on Elena's distrust of the council"

# Analyze accepted chapter prose for scrub issues
python3 src/tools/scene_writer.py --operation scrub-analyze \
  --name my-story --chapter-num 3 \
  --chapter-text "Elena quickly looked around and felt afraid..."

# Analyze chapter voice and pacing in manuscript context
python3 src/tools/scene_writer.py --operation voice-analyze \
  --name my-story --chapter-num 3 \
  --chapter-text "Chapter 3 text..." \
  --prior-chapters-summary "Chapters 1-2 used close third person with sparse exposition"
```

### Operations

| Operation | Effect | Output |
|-----------|--------|--------|
| `parse-definitions` | Sends chapter outline through `scenes/parse_definitions` prompt; LLM returns a JSON array of scene objects. Falls back to a single scene if JSON parsing fails. Saves to savepoint. | `{"status": "success", "operation": "parse-definitions", "data": [{"title": "...", "description": "..."}, ...]}` |
| `generate` | Renders `scenes/create_content` prompt with scene definition and story context, auto-loads `previous_scene` from `chapter_N/scene_{M-1}` when omitted and `scene_num > 1`, calls LLM, and saves the result to `chapter_N/scene_M`. | `{"status": "success", "operation": "generate", "data": {"scene_ref": "chapter_N/scene_M", "savepoint_step": "chapter_N/scene_M", "char_count": N}}` plus `"content"` when `includeContent: true` or `--include-content` is set |
| `revise` | Renders `scenes/revise_content` prompt with current content, feedback, and optional context, auto-loads `scene_content` from `chapter_N/scene_M` when omitted, calls LLM, and overwrites the same scene savepoint. | `{"status": "success", "operation": "revise", "data": {"scene_ref": "chapter_N/scene_M", "savepoint_step": "chapter_N/scene_M", "char_count": N}}` plus `"content"` when `includeContent: true` or `--include-content` is set |
| `assemble-chapter` | Loads all scene savepoints for the chapter, retrieves scene titles from definitions savepoint, concatenates them with `## <title>` headers and `---` separators, and saves the assembled chapter to `chapter_N/chapter_content`. | `{"status": "success", "operation": "assemble-chapter", "data": {"chapter_ref": "chapter_N/chapter_content", "savepoint_step": "chapter_N/chapter_content", "char_count": N, "scene_count": N}}` plus `"content"` when `includeContent: true` or `--include-content` is set |
| `generate-chapter` | Renders `chapters/create_content` for a full chapter fallback flow. Reads `chapters.N.expanded_outline` and `chapters.N+1.expanded_outline` from story state, loads `base_context`, `initial_outline`, and prior chapter recap savepoints, appends optional `additionalContext`, calls LLM, saves to `chapter_N/chapter_content`, and writes the result to `chapters.N.content` in story state. | `{"status": "success", "operation": "generate-chapter", "data": {"chapter_ref": "chapter_N/chapter_content", "savepoint_step": "chapter_N/chapter_content", "char_count": N}}` plus `"content"` when `includeContent: true` or `--include-content` is set |
| `scrub-analyze` | Renders `final_edit/prose_scrub` with accepted chapter text, extracts the JSON block, and returns structured sentence-level issues for adverbs, filter words, repetition, and show-vs-tell drift. No savepoint is written. | `{"status": "success", "operation": "scrub-analyze", "data": {"issues": [{"type": "...", "original_text": "...", "suggested_replacement": "...", "line_context": "..."}], "issues_found": 2}}` |
| `voice-analyze` | Renders `final_edit/voice_consistency_pass` with chapter text plus an optional prior-chapter summary, extracts the JSON block, and returns structured voice, pacing, and coherence issues. No savepoint is written. | `{"status": "success", "operation": "voice-analyze", "data": {"issues": [{"type": "...", "location": "...", "description": "...", "suggested_fix": "..."}], "issues_found": 1}}` |

### Scene Definition Format

The `parse-definitions` operation produces (and `generate` consumes) scene definition objects:

```json
[
  {
    "title": "The Arrival",
    "description": "Elena steps through the city gate for the first time",
    "characters": ["Elena", "Guard Captain"],
    "setting": "City Gate",
    "conflict": "Elena must prove her identity",
    "tone": "Tense, anticipatory",
    "key_events": ["Elena presents her papers", "Guard recognises the seal"],
    "dialogue": "Sample dialogue snippet",
    "ending": "Elena is admitted to the city",
    "lead_in_to_next_scene": "As Elena enters, she notices...",
    "literary_devices": "Foreshadowing of the seal's significance"
  }
]
```

### Prompt Templates

The tool uses three scene-generation templates from `prompts/scenes/`, one full-chapter fallback template from `prompts/chapters/`, and two analysis templates from `prompts/final_edit/`:

| Template | Used By | Purpose |
|----------|---------|---------|
| `scenes/parse_definitions` | `parse-definitions` | Analyse a chapter outline and extract scene objects as JSON |
| `scenes/create_content` | `generate` | Generate 750–1500 words of scene prose from a definition and context |
| `scenes/revise_content` | `revise` | Revise scene content based on specific feedback |
| `chapters/create_content` | `generate-chapter` | Generate a complete chapter from outline, story context, prior recap, and next-chapter synopsis |
| `final_edit/prose_scrub` | `scrub-analyze` | Extract sentence and paragraph-level prose issues as structured JSON |
| `final_edit/voice_consistency_pass` | `voice-analyze` | Extract voice, pacing, and cross-chapter coherence issues as structured JSON |

### Savepoint Structure

Savepoint-backed operations persist intermediate results under `stories/<name>/savepoints/`:

| Savepoint Key | Created By | Content |
|---------------|-----------|---------|
| `chapter_N/scene_definitions` | `parse-definitions` | JSON array of scene definition objects |
| `chapter_N/scene_M` | `generate`, `revise` | Scene prose text |
| `chapter_N/chapter_content` | `generate-chapter`, `assemble-chapter` | Full chapter prose text |

`generate` no longer requires callers to thread prior scene prose manually when the previous scene savepoint already exists. `scrub-analyze` and `voice-analyze` remain stateless with respect to savepoint storage.

### Resumability

The `parse-definitions`, `generate`, and `generate-chapter` operations check for existing savepoints before calling the LLM. If a savepoint exists, the saved result is returned immediately and the LLM call is skipped. This means:

- If `parse-definitions` has already run for a chapter, re-running returns the cached definitions
- If a scene has already been generated, re-running `generate` returns the cached content
- If a full chapter has already been generated through the fallback flow, re-running `generate-chapter` returns the cached chapter content
- The `revise` operation always calls the LLM and overwrites the scene savepoint, since revisions are intentional changes
- `assemble-chapter` is purely deterministic (no LLM) — it reads scene savepoints and concatenates them

### Fallback Behaviour

If the LLM response from `parse-definitions` cannot be parsed as valid JSON, or the parsed result is not a list of dictionaries, the tool falls back to a single scene definition containing the chapter number and the full chapter outline text as description.

### LLM Configuration

The tool uses `src/tools/_llm.py` for LLM access, configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_BASE` | `http://127.0.0.1:1234/v1` | OpenAI-compatible API base URL |
| `LLM_MODEL` | `gemma-4-26b-a4b-it-heretic-guff` | Default model identifier |

The `--model` argument overrides `LLM_MODEL` for a single invocation.

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success — result printed to stdout as JSON |
| 1 | Domain error — missing scenes for assembly, LLM failure, path traversal detected, invalid arguments |
| 2 | Argument error — missing required flag for the chosen operation |

### Security

- **Path traversal prevention** — story names are validated with `Path.is_relative_to()` to ensure they cannot escape the `stories/` directory
- **Shell injection prevention** — the TypeScript wrapper uses `execFileSync` with an argument array, never shell interpolation
- **Test isolation** — the `STORIES_DIR` environment variable overrides the default stories directory, ensuring tests never touch production data

---

## critique-runner

Runs critics against story outlines or assembled chapters, parses scores, checks quality thresholds, and generates structured feedback for iterative refinement.

**Source files:**
- `.opencode/tools/critique-runner.ts` — TypeScript wrapper
- `src/tools/critique_runner.py` — Python CLI script
- `src/application/services/critique_parser.py` — Underlying `CritiqueParser` class

### Purpose

The critique-runner operates in three critique modes and one arc-analysis operation:

- **Outline mode** — evaluates story outlines during the outline refinement loop
- **Chapter mode** — evaluates assembled chapter text during per-chapter quality review
- **Character-voice mode** — evaluates accepted chapter text for character voice consistency
- **Arc-analysis operation** — runs the Phase 2.5 dramatic-arc prompt chain for `story-planner`

The tool orchestrates the critique loop: running all critics for the selected mode, parsing their scores, determining whether the content meets the configured thresholds, and formatting feedback for the next refinement iteration.

Critic sets by mode:

| Mode | Critics |
|------|---------|
| `outline` | `audiobook-producer`, `book-club-moderator`, `commercial-fiction-editor`, `literary-fiction-reviewer`, `publishing-acquisitions-editor`, `subject-expert` |
| `chapter` | `commercial-fiction-editor`, `chapter-pacing`, `chapter-character-consistency` |
| `character-voice` | `character-voice-consistency` |

The seven scoring criteria:

| Criterion | Max Score |
|-----------|-----------|
| Pacing | 15 |
| Details | 15 |
| Flow | 15 |
| Genre | 10 |
| Consistency | 10 |
| Character Arc & Theme | 20 |
| Structure | 15 |

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `operation` | `"run-critics" \| "parse-scores" \| "should-refine" \| "generate-feedback" \| "run-arc-analysis"` | Yes | Operation to perform |
| `name` | string | For `run-critics`, `should-refine`, `generate-feedback`, `run-arc-analysis` | Story name (maps to directory under `stories/`) |
| `iteration` | number | No | Critique iteration number (default: 1) |
| `content` | string | No for critique operations; Yes for `run-arc-analysis` | Content to critique; if omitted for `run-critics`, loads mode-appropriate content from savepoint |
| `mode` | `"outline" \| "chapter" \| "character-voice"` | No | Critique mode (default: `outline`) |
| `criticType` | string | For `parse-scores` | Critic type identifier |
| `responseText` | string | For `parse-scores` | Raw critic response text to parse |
| `qualityThreshold` | number | No | Quality threshold percentage for `should-refine` (default: 85.0) |
| `criterionFloor` | number | No | Minimum per-criterion percentage for `should-refine` (default: 75.0) |
| `model` | string | No | Override LLM model identifier |
| `criticSummary` | string | No | Optional compact critic summary forwarded to `run-arc-analysis` for the synthesis prompt |

### CLI Interface (Python script)

```bash
python3 src/tools/critique_runner.py --operation <op> [--name <name>] [--iteration N] [--content '<text>'] [--mode outline|chapter|character-voice] [--critic-type <type>] [--response-text '<text>'] [--quality-threshold N] [--criterion-floor N] [--model <model>] [--critic-summary '<text>']
```

**Examples:**

```bash
# Run all outline critics (loads outline content from savepoint)
python3 src/tools/critique_runner.py --operation run-critics --name my-story --iteration 1

# Run chapter critics with explicit assembled chapter text
python3 src/tools/critique_runner.py --operation run-critics --name my-story \
  --mode chapter --content "Chapter 1: The Beginning..."

# Parse scores from a single critic response
python3 src/tools/critique_runner.py --operation parse-scores \
  --critic-type commercial-fiction-editor --response-text "### Pacing (12/15)..."

# Check if an outline needs further refinement
python3 src/tools/critique_runner.py --operation should-refine --name my-story \
  --iteration 1 --quality-threshold 85.0

# Check if a chapter needs refinement with a stricter per-criterion floor
python3 src/tools/critique_runner.py --operation should-refine --name my-story \
  --mode chapter --iteration 3 --quality-threshold 85.0 --criterion-floor 80.0

# Generate formatted feedback from critique results
python3 src/tools/critique_runner.py --operation generate-feedback --name my-story \
  --iteration 1

# Run Phase 2.5 arc analysis with outline content and compact critic summary
python3 src/tools/critique_runner.py --operation run-arc-analysis --name my-story \
  --content "# Final Outline..." \
  --critic-summary "audiobook-producer: 84/100\nsubject-expert: 81/100"
```

### Operations

| Operation | Effect | Output |
|-----------|--------|--------|
| `run-critics` | Runs all critics for the selected mode via LLM, parses scores, saves results as `outline_critique_results_iteration_{N}` or `chapter_critique_results_iteration_{N}` | JSON with `iteration`, `mode`, `critic_results`, `average_scores`, `overall_average` |
| `parse-scores` | Parses scores from a single critic response text; valid critic types depend on `mode` | Serialized `CritiqueResult` as JSON |
| `should-refine` | Loads mode-specific critique results from savepoint, checks if any criterion avg < `criterionFloor` or overall avg < `qualityThreshold` | `{should_refine, average_scores, overall_average, threshold, criterion_floor}` |
| `generate-feedback` | Loads critique results from savepoint, formats as structured markdown | `{feedback: "<markdown>"}` |
| `run-arc-analysis` | Runs `outline_arc/arc_distribution`, `outline_arc/promise_payoff`, and `outline_arc/arc_synthesis` sequentially, saving each intermediate result for later inspection | `{arc_assessment, verdict_code, arc_distribution, promise_payoff}` |

### Arc Analysis Workflow

`run-arc-analysis` is used by `story-planner` after the six outline critics complete. The operation:

1. Runs `prompts/outline_arc/arc_distribution.md` against the finalized outline and saves the result to `arc_distribution`.
2. Runs `prompts/outline_arc/promise_payoff.md` against the same outline and saves the result to `arc_promise_payoff`.
3. Runs `prompts/outline_arc/arc_synthesis.md` using the outline, the optional `criticSummary`, and both intermediate analyses, then saves the final report to `arc_assessment`.

The final synthesis is normalized into one of three verdict codes:

| Verdict Code | Meaning |
|--------------|---------|
| `strong` | Arc structure is strong enough to proceed without major concern |
| `minor_concerns` | Arc is viable but notable pacing or payoff issues remain |
| `significant_issues` | Arc problems are serious enough to warrant user review before proceeding |

### Quality Threshold Logic

The `should-refine` operation determines refinement need using two conditions:
- **Any criterion average < criterion_floor** — individual weakness detected (default: 75.0)
- **Overall average < quality_threshold** — general quality below standard (default: 85.0)

If either condition is true, `should_refine` returns `true`.

When `content` is omitted, `run-critics` falls back to mode-appropriate savepoints:

- `outline` mode: previous outline iteration or `outline`
- `chapter` mode: `chapter_assembled`, `chapter_{iteration}_complete`, or `chapter_{iteration}/complete`

For chapter critiques, passing the assembled chapter text explicitly via `content` is more reliable than relying on savepoint fallback.

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success — result printed to stdout as JSON |
| 1 | Domain error — story not found, savepoint not found, critic failed |
| 2 | Argument error — missing required flag for the chosen operation |

### Security

- **Path traversal prevention** — story names are validated with `Path.is_relative_to()` to ensure they cannot escape the `stories/` directory
- **Shell injection prevention** — the TypeScript wrapper uses `execFileSync` with an argument array, never shell interpolation
- **Test isolation** — the `STORIES_DIR` environment variable overrides the default stories directory, ensuring tests never touch production data

---

## story-assembler

Assembles completed chapter outputs into the final manuscript, or generates the structured handoff artifact used to carry continuity into the next chapter expansion pass.

**Source files:**
- `.opencode/tools/story-assembler.ts` — TypeScript wrapper
- `src/tools/story_assembler.py` — Python CLI script
- `src/tools/_llm.py` — Shared LLM client used by `generate-handoff`

### Purpose

`story-assembler` has two distinct responsibilities in the pipeline:

- **Phase 7g** — generate `chapters.{N}.handoff` from the accepted chapter's expanded outline so later chapter expansion can inherit explicit continuity state
- **Phase 8** — assemble all completed chapter content into `stories/<name>/output/story.md`

The `generate-handoff` operation keeps prompt loading, LLM invocation, JSON parsing, and state persistence inside one deterministic tool boundary. The orchestrator now delegates the full handoff-generation step instead of loading `prompts/chapters/generate_handoff.md` inline.

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `operation` | `"assemble" \| "generate-handoff"` | Yes | Operation to perform |
| `storyName` | string | Yes | Story name (maps to directory under `stories/`) |
| `chapterNum` | number | For `generate-handoff` | Chapter number whose handoff artifact should be generated |
| `model` | string | No | Optional model override for `generate-handoff` |

### CLI Interface (Python script)

```bash
python3 src/tools/story_assembler.py <assemble|generate-handoff> --story-name <name> [--chapter-num <N>] [--model <model>]
```

**Examples:**

```bash
# Assemble the final manuscript from completed chapters
python3 src/tools/story_assembler.py assemble --story-name my-story

# Generate a structured handoff artifact for chapter 7
python3 src/tools/story_assembler.py generate-handoff \
  --story-name my-story \
  --chapter-num 7

# Generate a handoff with a specific model override
python3 src/tools/story_assembler.py generate-handoff \
  --story-name my-story \
  --chapter-num 7 \
  --model gpt-4.1-mini
```

### Operations

| Operation | Effect | Output |
|-----------|--------|--------|
| `assemble` | Discovers available chapter numbers from savepoints and story state, loads chapter content, and writes a combined manuscript to `stories/<name>/output/story.md` | `{output_path, chapter_count}` |
| `generate-handoff` | Reads `chapters.{N}.expanded_outline`, chapter title, and story title from `state.json`; renders `prompts/chapters/generate_handoff.md`; calls the LLM; validates returned JSON; and writes the result to `chapters.{N}.handoff` | `{status: "success", chapter_num, handoff_keys}` |

### Handoff Generation Contract

`generate-handoff` expects `chapters.{N}.expanded_outline` to exist in story state. If outline expansion has not run yet, the tool exits with a domain error.

When the required state is present, the tool builds the prompt with four values:

| Prompt Variable | Source |
|-----------------|--------|
| `CHAPTER_NUMBER` | CLI `--chapter-num` |
| `CHAPTER_OUTLINE` | `chapters.{N}.expanded_outline` |
| `CHAPTER_TITLE` | `chapters.{N}.title` or fallback `Chapter N` |
| `STORY_TITLE` | `story_context.title` |

The tool strips Markdown code fences from the model response before JSON parsing, then stores the parsed object at `chapters.{N}.handoff` in `state.json`.

### Assembly Behavior

The `assemble` operation discovers chapter numbers from both savepoints and story state, then loads chapter text from the first available source:

1. `chapter_{N}_complete`
2. `chapter_{N}/complete`
3. `chapter_{N}`
4. `chapters.{N}` in story state (`content`, `text`, `chapter_text`, or `assembled`)

This fallback order lets Phase 8 succeed even when chapter content was persisted through different intermediate surfaces during development or recovery workflows.

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success — result printed to stdout as JSON |
| 1 | Domain error — story not found, no chapter content found, missing `expanded_outline`, or invalid JSON returned by the model |
| 2 | Argument error — missing subcommand or required flags |

### Security

- **Path traversal prevention** — story names are validated against the configured `stories/` root before reads or writes occur
- **State write discipline** — `generate-handoff` updates only `chapters.{N}.handoff` through the existing atomic story-state write helpers
- **Shell injection prevention** — the TypeScript wrapper uses `execFileSync` with an argument array, never shell interpolation
- **Test isolation** — the `STORIES_DIR` environment variable still redirects story I/O for tests and local sandboxes

---

## wiki-init

Initialises a story wiki directory structure with subdirectories, schema template, index, log, and contradictions files.

**Source files:**
- `.opencode/tools/wiki-init.ts` — TypeScript wrapper
- `src/tools/wiki_init.py` — Python CLI script
- `src/tools/_wiki.py` — Shared wiki utilities (`WIKI_SUBDIRS` constant)
- `src/tools/wiki_schema_template.md` — Default schema template (copied as `_schema.md`)

### Purpose

The wiki system ([ADR 004](./planning/adr/004-progressive-wiki-memory-system.md)) stores structured knowledge about a story's world — characters, locations, events, factions, items, plot threads, world rules, themes, relationships, timeline entries, and chapter synopses. Each wiki page is a Markdown file with YAML frontmatter containing typed metadata and pre-computed detail level summaries (L1/L2/L3).

This tool creates the wiki directory structure for a story. It is idempotent — calling it on a story that already has a wiki directory reports success without modifying the existing wiki.

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `operation` | `"init"` | Yes | Operation to perform |
| `name` | string | Yes | Story name (maps to directory under `stories/`) |

### CLI Interface (Python script)

```bash
python3 src/tools/wiki_init.py --operation init --name <name>
```

**Examples:**

```bash
# Initialise a wiki for a new story
python3 src/tools/wiki_init.py --operation init --name my-story

# Safe to call again — reports already_exists
python3 src/tools/wiki_init.py --operation init --name my-story
```

### Operations

| Operation | Effect | Output |
|-----------|--------|--------|
| `init` | Creates `stories/<name>/wiki/` with 11 subdirectories, `_schema.md`, `index.md`, `log.md`, and `contradictions.md`. If wiki already exists, returns without modification. | `{"status": "ok", "wiki_dir": "<path>", "created": true}` or `{"status": "ok", "wiki_dir": "<path>", "created": false, "already_exists": true}` |

### Directory Structure

After initialisation, the wiki directory contains:

```
stories/<name>/wiki/
├── _schema.md            # Page type definitions with YAML frontmatter fields
├── index.md              # Entity index (slug | type | name | aliases)
├── log.md                # Wiki change log
├── contradictions.md     # Contradictions log
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
└── chapters/
```

### Page Types (from `_schema.md`)

The schema template defines 12 page types, each with specific YAML frontmatter fields:

| Page Type | Subdirectory | Extra Fields |
|-----------|-------------|--------------|
| `character` | `characters/` | `role` (protagonist/antagonist/supporting/minor), `status` (alive/dead/unknown/transformed) |
| `location` | `locations/` | `region` (parent region or area) |
| `event` | `events/` | `chapter` (chapter number), `impact` (major/moderate/minor) |
| `faction` | `factions/` | — |
| `item` | `items/` | — |
| `plot_thread` | `plot-threads/` | `status` (active/resolved/dormant) |
| `world_rule` | `world-rules/` | — |
| `theme` | `themes/` | — |
| `relationship` | `relationships/` | — |
| `timeline_entry` | `timeline/` | — |
| `chapter_synopsis` | `chapters/` | — |
| `contradiction` | — | — |

All page types share common frontmatter fields: `type`, `name`, `slug`, `confidence` (verified/planned/speculative), `first_appearance`, `aliases`, `last_updated`, `version`, and `detail_levels` (L1/L2/L3 summaries at ~30/~150/~500 tokens).

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success — result printed to stdout as JSON |
| 1 | Domain error — story directory not found, path traversal detected |

### Security

- **Path traversal prevention** — story names are validated with `Path.is_relative_to()` to ensure they cannot escape the `stories/` directory
- **Shell injection prevention** — the TypeScript wrapper uses `execFileSync` with an argument array, never shell interpolation
- **Idempotent** — calling `init` on an existing wiki does not modify or overwrite any files
- **Test isolation** — the `STORIES_DIR` environment variable overrides the default stories directory, ensuring tests never touch production data

---

## wiki-read

Reads wiki pages by slug, type, or glob pattern with configurable detail levels, or matches entity names in text against the wiki index.

**Source files:**
- `.opencode/tools/wiki-read.ts` — TypeScript wrapper
- `src/tools/wiki_read.py` — Python CLI script
- `src/tools/_wiki.py` — Shared wiki utilities (`parse_frontmatter`, `find_pages`, `read_index`, `match_entities_in_text`)

### Purpose

During story generation, agents need to retrieve wiki page content at varying levels of detail — a headline for context budget management, a brief summary for scene planning, or full content for deep reference. This tool provides structured access to wiki pages with parsed YAML frontmatter and configurable detail levels.

The `match-entities` operation supports the entity matching tier of the context retrieval pipeline ([ADR 005](./planning/adr/005-hybrid-wiki-context-retrieval-pipeline.md)): given a block of text (e.g., a scene outline), it identifies which wiki entities are mentioned by name or alias.

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `operation` | `"read" \| "match-entities"` | Yes | Operation to perform |
| `name` | string | Yes | Story name (maps to directory under `stories/`) |
| `slug` | string | No | Page slug to read (for `read`) |
| `type` | string | No | Page type to filter by, e.g., `character`, `location`, `event` (for `read`) |
| `glob` | string | No | Glob pattern for page matching (for `read`) |
| `detailLevel` | `"headline" \| "brief" \| "full"` | No | Detail level for returned content (default: `brief`) |
| `text` | string | For `match-entities` | Text to match entity names against |

### CLI Interface (Python script)

```bash
python3 src/tools/wiki_read.py --operation <op> --name <name> [options]
```

**Examples:**

```bash
# Read a specific page by slug
python3 src/tools/wiki_read.py --operation read --name my-story --slug elena-blackwood

# Read all character pages at headline level
python3 src/tools/wiki_read.py --operation read --name my-story --type character \
  --detail-level headline

# Read pages matching a glob pattern
python3 src/tools/wiki_read.py --operation read --name my-story --glob "characters/*.md"

# Read all wiki pages (no filter)
python3 src/tools/wiki_read.py --operation read --name my-story --detail-level full

# Find which wiki entities are mentioned in text
python3 src/tools/wiki_read.py --operation match-entities --name my-story \
  --text "Elena walked through the Shadow Market, remembering what Captain Rowe had said"
```

### Operations

| Operation | Effect | Output |
|-----------|--------|--------|
| `read` | Finds pages by slug, type, or glob; parses YAML frontmatter; returns content at the requested detail level | `{"status": "ok", "pages": [{"slug": "...", "type": "...", "metadata": {...}, "content": "..."}]}` |
| `match-entities` | Scans text for entity names and aliases from `index.md` | `{"status": "ok", "matches": [{"name": "...", "slug": "...", "type": "...", "aliases": [...]}]}` |

### Detail Levels

The `read` operation returns content at three detail levels, using pre-computed summaries from the page's YAML frontmatter `detail_levels` field:

| Level | Source | Fallback | Typical Size |
|-------|--------|----------|-------------|
| `headline` | `detail_levels.L1` | First line of body | ~30 tokens |
| `brief` | `detail_levels.L2` | First 3 sentences of body | ~150 tokens |
| `full` | Full body text | — | ~500+ tokens |

### Page Lookup

When filtering by `type`, the tool maps page type names to subdirectories:

| Page Type | Subdirectory |
|-----------|-------------|
| `character` | `characters/` |
| `location` | `locations/` |
| `event` | `events/` |
| `faction` | `factions/` |
| `item` | `items/` |
| `plot_thread` | `plot-threads/` |
| `world_rule` | `world-rules/` |
| `theme` | `themes/` |
| `relationship` | `relationships/` |
| `timeline_entry` | `timeline/` |
| `chapter_synopsis` | `chapters/` |

When filtering by `slug`, all subdirectories and the wiki root are searched for `{slug}.md`.

### Entity Matching

The `match-entities` operation reads `index.md` (format: `- slug | type | name | aliases`) and performs case-insensitive substring matching of each entity's name and aliases against the provided text. Each entity is returned at most once. This is the deterministic Tier 1 signal in the retrieval pipeline.

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success — result printed to stdout as JSON |
| 1 | Domain error — path traversal detected |
| 2 | Argument error — missing `--text` for `match-entities` |

### Security

- **Path traversal prevention** — story names are validated with `Path.is_relative_to()` to ensure they cannot escape the `stories/` directory
- **Shell injection prevention** — the TypeScript wrapper uses `execFileSync` with an argument array, never shell interpolation
- **Graceful empty state** — returns `{"pages": []}` or `{"matches": []}` if the wiki directory does not exist
- **Test isolation** — the `STORIES_DIR` environment variable overrides the default stories directory, ensuring tests never touch production data

---

## wiki-search

Searches wiki pages via ChromaDB: semantic vector search by query text, or metadata-filtered query by JSON where clause. Read-only — does not create or modify collections.

**Source files:**
- `.opencode/tools/wiki-search.ts` — TypeScript wrapper
- `src/tools/wiki_search.py` — Python CLI script

### Purpose

This tool provides the semantic search (Tier 3) and metadata query (Tier 2) capabilities of the context retrieval pipeline ([ADR 005](./planning/adr/005-hybrid-wiki-context-retrieval-pipeline.md)). Wiki pages are embedded into per-story ChromaDB collections (named `wiki-<story-name>`), and this tool queries those collections.

The tool is strictly read-only — it does not create collections or embed documents. If the collection does not exist or is empty, it returns an empty result set.

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `operation` | `"semantic" \| "metadata"` | Yes | Search mode |
| `name` | string | Yes | Story name (used to derive collection name `wiki-<name>`) |
| `query` | string | For `semantic` | Natural language search query |
| `where` | string | For `metadata` | JSON string of ChromaDB where-filter (e.g., `'{"type": "character"}'`) |
| `nResults` | number | No | Maximum results to return (default: 10) |

### CLI Interface (Python script)

```bash
python3 src/tools/wiki_search.py --operation <op> --name <name> [options]
```

**Examples:**

```bash
# Semantic search for relevant wiki pages
python3 src/tools/wiki_search.py --operation semantic --name my-story \
  --query "magical artifacts with healing powers" --n-results 5

# Metadata-filtered query for all character pages
python3 src/tools/wiki_search.py --operation metadata --name my-story \
  --where '{"type": "character"}'

# Metadata query with comparison operator
python3 src/tools/wiki_search.py --operation metadata --name my-story \
  --where '{"first_appearance": {"$lte": 5}}'

# Metadata query with logical operators
python3 src/tools/wiki_search.py --operation metadata --name my-story \
  --where '{"$and": [{"type": "event"}, {"impact": "major"}]}'
```

### Operations

| Operation | Effect | Output |
|-----------|--------|--------|
| `semantic` | Performs vector similarity search over the `wiki-<name>` ChromaDB collection using `query_texts` | `{"status": "ok", "results": [{"slug": "...", "score": 0.85, "excerpt": "...", "metadata": {...}}]}` |
| `metadata` | Filters the `wiki-<name>` collection using ChromaDB `where` clause on document metadata | `{"status": "ok", "results": [{"slug": "...", "score": 1.0, "excerpt": "...", "metadata": {...}}]}` |

### Result Format

Each result in the `results` array contains:

| Field | Type | Description |
|-------|------|-------------|
| `slug` | string | Document ID (typically the page slug) |
| `score` | number | Relevance score: `1.0 - distance` for semantic, `1.0` for metadata |
| `excerpt` | string | First 500 characters of the document content |
| `metadata` | object | ChromaDB document metadata (frontmatter fields) |

### ChromaDB Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `CHROMADB_DIR` | `<project-root>/.chromadb` | Path to the ChromaDB persistent storage directory |

The tool uses `chromadb.PersistentClient` with the configured path. Collections are named `wiki-<story-name>` by convention.

### Where Filter Syntax

The `--where` argument accepts ChromaDB's query operator syntax as a JSON string:

| Pattern | Example |
|---------|---------|
| Simple equality | `{"type": "character"}` |
| Comparison | `{"first_appearance": {"$gt": 5}}` |
| Logical AND | `{"$and": [{"type": "event"}, {"impact": "major"}]}` |
| Logical OR | `{"$or": [{"type": "character"}, {"type": "location"}]}` |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success — result printed to stdout as JSON |
| 1 | Domain error — ChromaDB query failed, path traversal detected |
| 2 | Argument error — missing `--query` for semantic, missing or invalid `--where` for metadata |

### Security

- **Path traversal prevention** — story names are validated with `Path.is_relative_to()` to ensure they cannot escape the `stories/` directory
- **Shell injection prevention** — the TypeScript wrapper uses `execFileSync` with an argument array, never shell interpolation
- **Read-only** — the tool never creates, modifies, or deletes ChromaDB collections or documents
- **Graceful empty state** — returns `{"results": []}` if the collection does not exist or is empty
- **Test isolation** — the `STORIES_DIR` and `CHROMADB_DIR` environment variables override default paths, ensuring tests never touch production data

---

## wiki-snapshot

Assembles a pre-generation context snapshot for a scene using the three-stage hybrid retrieval pipeline defined in [ADR 005](./planning/adr/005-hybrid-wiki-context-retrieval-pipeline.md).

**Source files:**
- `.opencode/tools/wiki-snapshot.ts` — TypeScript wrapper
- `src/tools/wiki_snapshot.py` — Python CLI script

### Purpose

Before generating a scene, the writing agent needs relevant context from the wiki — character details, location descriptions, active plot threads, world rules, and recent events. This tool automates the retrieval, scoring, budget allocation, and assembly of that context into a structured markdown payload.

The pipeline has three stages:

1. **Hybrid Multi-Tier Retrieval** — four retrieval tiers (entity matching, metadata filtering, semantic search, wikilink graph traversal) merged via Reciprocal Rank Fusion
2. **Detail Level Selection & Token Budgeting** — assigns L1/L2/L3 detail levels by relevance rank, with scene-type adaptation and iterative demotion to fit the token budget
3. **Structured Context Assembly** — renders pages at their assigned detail levels into a fixed markdown structure, with optional LLM synthesis for complex scenes

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `operation` | `"snapshot" \| "cache-status"` | Yes | Operation to perform |
| `name` | string | Yes | Story name |
| `chapter` | integer | Yes | Chapter number |
| `scene` | integer | For snapshot | Scene number |
| `outline` | string | For snapshot | Scene outline text (used for entity matching and semantic search) |
| `povCharacter` | string | No | POV character slug (always gets full detail) |
| `primaryLocation` | string | No | Primary location slug (always gets full detail) |
| `characters` | string | No | Comma-separated additional character slugs |
| `locations` | string | No | Comma-separated additional location slugs |
| `sceneType` | `"dialogue" \| "action" \| "exposition" \| "mixed"` | No | Scene type for detail level adaptation |
| `budget` | integer | No | Token budget (default: 15000) |

### CLI Interface (Python script)

```bash
python3 src/tools/wiki_snapshot.py --operation snapshot \
  --name <story_name> \
  --chapter <int> \
  --scene <int> \
  --outline "<scene_outline_text>" \
  --pov-character <slug> \
  --primary-location <slug> \
  --characters <slug1,slug2,...> \
  --locations <slug1,slug2,...> \
  --scene-type dialogue \
  --budget 15000
```

```bash
python3 src/tools/wiki_snapshot.py --operation cache-status \
  --name <story_name> \
  --chapter <int>
```

### Output

**snapshot operation:**
```json
{
  "snapshot": "# Scene Context — Chapter 3, Scene 2\n\n## Characters\n...",
  "stats": {
    "pages_retrieved": 12,
    "pages_included": 10,
    "token_count": 8450,
    "cache_hits": 3,
    "cache_misses": 7,
    "tiers": {"t1": 4, "t2": 2, "t3": 3, "t4": 1}
  }
}
```

**cache-status operation:**
```json
{
  "cached": true,
  "chapter": 3,
  "scene": 2,
  "entity_count": 10,
  "stats": {...}
}
```

### Retrieval Tiers

| Tier | Method | Signal |
|------|--------|--------|
| T1 | Deterministic entity matching | Entity name or alias in scene outline |
| T2 | Metadata-filtered ChromaDB query | Active plot threads, world rules |
| T3 | Semantic vector search | Scene outline embedding similarity |
| T4 | Wikilink graph traversal (1-2 hop) | Pages linked from T1-T3 results (max 5 additional) |

### Relevance Scoring

```
score(p) = 0.40 × entity_match + 0.20 × wikilink_proximity + 0.20 × semantic_similarity + 0.10 × recency + 0.10 × type_priority
```

Pages scoring below 0.15 are dropped.

### Delta Caching

Cache file: `stories/<name>/wiki/.cache/snapshot_cache.json`. Cache is invalidated when the chapter changes. Within a chapter, individual page versions are tracked — only changed pages are re-fetched.

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success — result printed to stdout as JSON |
| 1 | Domain error — invalid slug, path traversal, LLM failure |
| 2 | Argument error — missing required arguments |

### Security

- **Path traversal prevention** — story names validated with `Path.is_relative_to()`, all slugs validated with `_validate_slug()`
- **Shell injection prevention** — TypeScript wrapper uses `execFileSync` with argument array
- **Cache isolation** — cache files scoped to individual story wiki directories

---

## wiki-extract

Extracts wiki entities from outlines, sheet files, and completed chapters, generates L1/L2/L3 detail levels, assembles snake_case wiki batch payloads, and optionally applies them through `wiki-update`.

**Source files:**
- `.opencode/tools/wiki-extract.ts` — TypeScript wrapper
- `src/tools/wiki_extract.py` — Python CLI script
- `src/tools/wiki_update.py` — Shared `run_batch()` helper used when applying assembled batches
- `prompts/wiki/extract_from_outline.md` — Outline extraction prompt
- `prompts/wiki/extract_from_sheet.md` — Character/setting sheet extraction prompt
- `prompts/wiki/extract_from_chapter.md` — Post-chapter extraction prompt
- `prompts/wiki/generate_detail_levels.md` — L1/L2/L3 summary generation prompt

### Purpose

This tool moves the wiki maintainer's most context-heavy work out of the agent's main LLM window. Instead of reading the full outline, all sheet files, or an entire completed chapter directly into the subagent and hand-writing every detail level in-context, the agent now makes a single `wiki-extract` call per mode and receives compact summary counts back.

`wiki-extract` owns four tasks:

- Entity extraction from the outline plus character/setting sheets (`initial-populate`)
- Entity extraction plus change detection from a completed chapter (`update-from-chapter`)
- L1/L2/L3 detail-level generation for newly created entities
- Snake_case batch payload assembly for `wiki-update`

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `operation` | `"initial-populate" \| "update-from-chapter"` | Yes | Extraction operation to perform |
| `name` | string | Yes | Story name (maps to directory under `stories/`) |
| `chapterNumber` | integer | For `update-from-chapter` | Chapter number being processed |
| `chapterTextPath` | string | For `update-from-chapter` | Path to the completed chapter file, relative to the story directory or absolute within it |
| `model` | string | No | Override model name for extraction/detail generation |
| `apply` | boolean | No | Apply the assembled wiki batch (default: `true`). When `false`, returns a dry-run payload instead |

### CLI Interface (Python script)

```bash
python3 src/tools/wiki_extract.py initial-populate --name <story> [--model <model>] [--apply | --dry-run]

python3 src/tools/wiki_extract.py update-from-chapter --name <story> \
  --chapter-number <n> --chapter-text-path <path> \
  [--model <model>] [--apply | --dry-run]
```

### Operations

| Operation | Effect | Output |
|-----------|--------|--------|
| `initial-populate` | Reads `state.json` for the outline, scans `stories/<name>/characters/*.json` and `stories/<name>/settings/*.json`, extracts entities, deduplicates by slug, generates L1/L2/L3 detail levels, assembles a batch payload, and optionally applies it via `run_batch()` | Applied mode: `{"status":"ok","created":<n>,"updated":0,"timeline_events":0,"entity_counts":{...},"applied":true}`. Dry-run mode: `{"status":"ok","applied":false,"creates":[...],"updates":[],"timeline_events":[]}` |
| `update-from-chapter` | Reads a completed chapter file from disk, matches existing entities from the wiki index, extracts new entities plus state changes/aliases/timeline events, generates detail levels for new entities, assembles the batch payload, and optionally applies it via `run_batch()` | Applied mode: `{"status":"ok","created":<n>,"updated":<n>,"timeline_events":<n>,"entity_counts":{...},"applied":true}`. Dry-run mode: `{"status":"ok","applied":false,"creates":[...],"updates":[...],"timeline_events":[...]}` |

### Output Shape

Applied runs return compact summary counts so the agent does not need to hold the full batch payload in-context:

```json
{
  "status": "ok",
  "created": 12,
  "updated": 4,
  "timeline_events": 3,
  "entity_counts": {
    "character": 5,
    "location": 3,
    "plot_thread": 2,
    "event": 2
  },
  "applied": true
}
```

Dry-run runs return the exact `wiki-update batch` payload shape, preserving snake_case keys:

```json
{
  "status": "ok",
  "applied": false,
  "creates": [
    {
      "page_type": "character",
      "page_name": "Captain Elara",
      "slug": "captain-elara",
      "body": "...",
      "confidence": "verified",
      "first_appearance": 3,
      "aliases": ["the captain"],
      "detail_levels": {
        "L1": "...",
        "L2": "...",
        "L3": "..."
      },
      "frontmatter": {
        "role": "supporting",
        "status": "alive"
      }
    }
  ],
  "updates": [
    {
      "slug": "ashenmoor",
      "frontmatter": {
        "status": "under_siege"
      },
      "merge_body": "...",
      "aliases": ["the fortress"]
    }
  ],
  "timeline_events": [
    {
      "time": "Day 5, evening",
      "description": "The siege begins",
      "chapter": 3
    }
  ]
}
```

### Resumability

`wiki-extract` checkpoints each successful LLM call to `stories/<story-name>/.wiki-extract-cache.json`. `initial-populate` and `update-from-chapter` both reuse that per-story cache on retry, so rerunning the same command resumes from the last completed extraction or detail-generation step instead of starting over.

The cache is deleted only after a successful applied run, once `run_batch()` completes. It is retained on timeout, failure, or dry-run because no applied write happened. Missing or corrupt cache data is treated as a cache miss and the tool starts fresh.

**Note:** The cache uses stable identifiers (file paths, entity slugs, chapter numbers) as keys, not content checksums. If you edit a source file (chapter text, character sheet, outline) between a timeout and a retry, the cached extraction from the original content will be replayed. Delete `stories/<story-name>/.wiki-extract-cache.json` before retrying to force a fresh extraction.

### Integration with `wiki-update`

When `apply` is true, `wiki-extract` calls `run_batch()` from `src/tools/wiki_update.py`. That helper preserves the existing `wiki-update batch` contract and returns created, updated, timeline, and per-type summary counts. This keeps extraction and summary generation tool-owned while leaving page writes, rollback semantics, and ChromaDB upserts in the existing deterministic wiki update layer.

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success — result printed to stdout as JSON |
| 1 | Domain error — missing outline, missing or invalid chapter file, invalid LLM JSON response, unsupported entity type, batch apply failure |
| 2 | Argument error — missing required subcommand flags |

### Security

- **Path traversal prevention** — story names are validated with `_validate_story_name()`, and `chapterTextPath` must resolve inside the selected story directory
- **Shell injection prevention** — the TypeScript wrapper passes arguments to the Python script as an array through the shared `runTool()` helper
- **Dry-run support** — `--dry-run` returns the payload without mutating wiki files, useful for inspection and tests
- **Confidence preservation** — duplicate entities are merged with strict confidence precedence: `verified` > `planned` > `speculative`

---

## wiki-update

Creates, updates, and manages wiki pages — the structured CRUD layer for the wiki memory system.

**Source files:**
- `.opencode/tools/wiki-update.ts` — TypeScript wrapper
- `src/tools/wiki_update.py` — Python CLI script
- `src/tools/_wiki.py` — Shared wiki utilities (`parse_frontmatter`, `render_frontmatter`, `find_pages`, `read_index`, `write_index`)
- `src/tools/_io.py` — Shared I/O utilities (`_atomic_write`, `_validate_story_name`)

### Purpose

After a scene is generated, `wiki-extract` or a smaller agent follow-up step produces structured update payloads. This tool consumes those payloads and applies them to the wiki — creating new pages, updating existing ones, appending timeline events, and re-embedding changed content into ChromaDB.

The tool does NOT perform entity extraction itself. It is a deterministic CRUD layer that ensures atomic writes, version tracking, index maintenance, and ChromaDB synchronisation. `wiki-extract` now calls the internal `run_batch()` helper here when it applies assembled payloads.

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `operation` | `"create" \| "update" \| "append-timeline" \| "batch" \| "log"` | Yes | Operation to perform |
| `name` | string | Yes | Story name (maps to directory under `stories/`) |
| `slug` | string | For `create`, `update` | Page slug (lowercase, hyphenated identifier) |
| `pageType` | string | For `create` | Page type: `character`, `location`, `event`, `faction`, `item`, `plot_thread`, `world_rule`, `theme`, `relationship`, `timeline_entry`, `chapter_synopsis` |
| `pageName` | string | For `create` | Display name for the page |
| `body` | string | No | Page body markdown (replaces existing body on update) |
| `mergeBody` | string | No | Content to append to existing body (update only) |
| `confidence` | `"verified" \| "planned" \| "speculative"` | No | Confidence level (default: `verified`) |
| `firstAppearance` | integer | No | Chapter number of first appearance (default: 1) |
| `aliases` | string | No | JSON array string of alternative names |
| `detailLevels` | string | No | JSON object string with `L1`, `L2`, `L3` keys for pre-computed detail summaries |
| `frontmatter` | string | No | JSON object of frontmatter fields to merge (update only) |
| `role` | string | No | Character role — `protagonist`, `antagonist`, `supporting`, `minor` |
| `status` | string | No | Character or plot thread status — `alive`, `dead`, `unknown`, `active`, `resolved`, `dormant` |
| `region` | string | No | Location region (parent area) |
| `chapter` | integer | No | Event chapter number |
| `impact` | string | No | Event impact — `major`, `moderate`, `minor` |
| `events` | string | For `append-timeline` | JSON array of timeline event objects |
| `payload` | string | For `batch` | JSON payload containing `creates`, `updates`, and `timeline_events` arrays |
| `message` | string | For `log` | Log message text |

### CLI Interface (Python script)

```bash
python3 src/tools/wiki_update.py --operation <op> --name <name> [options]
```

**Examples:**

```bash
# Create a new character page
python3 src/tools/wiki_update.py --operation create --name my-story \
  --slug elena-blackwood --page-type character --page-name "Elena Blackwood" \
  --body "A rogue cartographer who maps forbidden territories." \
  --role protagonist --status alive --confidence verified \
  --first-appearance 1 \
  --aliases '["Elena", "The Cartographer"]' \
  --detail-levels '{"L1": "Rogue cartographer protagonist", "L2": "Elena Blackwood is a rogue cartographer who maps forbidden territories.", "L3": "Elena Blackwood is a rogue cartographer..."}'

# Update an existing page (merge frontmatter, append body)
python3 src/tools/wiki_update.py --operation update --name my-story \
  --slug elena-blackwood \
  --frontmatter '{"status": "transformed"}' \
  --merge-body "## Chapter 5\n\nElena discovered her true heritage."

# Append events to the main timeline
python3 src/tools/wiki_update.py --operation append-timeline --name my-story \
  --events '[{"time": "Day 3, morning", "description": "Elena enters the Shadow Market", "chapter": 2}]'

# Batch operation (creates + updates + timeline in one atomic call)
python3 src/tools/wiki_update.py --operation batch --name my-story \
  --payload '{"creates": [{"slug": "shadow-market", "page_type": "location", "page_name": "Shadow Market", "body": "An underground bazaar.", "region": "Old Quarter"}], "updates": [{"slug": "elena-blackwood", "frontmatter": {"status": "active"}, "merge_body": "Visited the Shadow Market."}], "timeline_events": [{"time": "Day 3, morning", "description": "Elena enters the Shadow Market", "chapter": 2}]}'

# Append a custom log entry
python3 src/tools/wiki_update.py --operation log --name my-story \
  --message "Agent completed chapter 2 wiki updates"
```

### Operations

| Operation | Effect | Output |
|-----------|--------|--------|
| `create` | Creates a new wiki page with YAML frontmatter and body in the appropriate type subdirectory; adds entry to `index.md`; appends to `log.md`; upserts into ChromaDB | `{"status": "ok", "slug": "<slug>", "path": "<file_path>"}` |
| `update` | Updates an existing page — merges frontmatter fields, replaces or appends body text, increments `version`, updates `last_updated`; updates `index.md` if name/aliases changed; appends to `log.md`; upserts into ChromaDB | `{"status": "ok", "slug": "<slug>", "version": <n>}` |
| `append-timeline` | Appends events to `timeline/main-timeline.md`, maintaining chronological sort order | `{"status": "ok", "events_added": <n>}` |
| `batch` | Executes multiple creates, updates, and timeline appends in a single atomic operation with rollback on failure | `{"status": "ok", "created": <n>, "updated": <n>, "timeline_events": <n>}` |
| `log` | Appends a timestamped entry to `wiki/log.md` | `{"status": "ok"}` |

### Batch Operations

The `batch` operation accepts a JSON payload with three optional arrays:

```json
{
  "creates": [
    {
      "slug": "new-entity",
      "page_type": "character",
      "page_name": "New Entity",
      "body": "Description text",
      "confidence": "verified",
      "first_appearance": 3,
      "aliases": ["Alias1"],
      "detail_levels": {"L1": "...", "L2": "...", "L3": "..."},
      "role": "supporting",
      "status": "alive"
    }
  ],
  "updates": [
    {
      "slug": "existing-entity",
      "frontmatter": {"status": "dead"},
      "detail_levels": {"L1": "updated headline"},
      "body": "Full replacement body",
      "merge_body": "Content appended to existing body"
    }
  ],
  "timeline_events": [
    {
      "time": "Day 5, evening",
      "description": "The siege begins",
      "chapter": 3
    }
  ]
}
```

**Rollback semantics:** If any operation in the batch fails, previously modified files are restored from in-memory backups and newly created files are deleted. The response includes a `rollback` field (`"full"` or `"partial"`) indicating rollback success.

```json
{
  "status": "error",
  "message": "page 'nonexistent' not found for update",
  "rollback": "full"
}
```

### Version Tracking

Every `update` or batch update increments the page's `version` counter in the YAML frontmatter and sets `last_updated` to the current UTC timestamp. The `wiki-snapshot` tool uses the version counter for delta caching — if a page's version has not changed since the last retrieval, cached content is reused.

### ChromaDB Integration

After every `create` or `update`, the tool upserts the page body and metadata into a per-story ChromaDB collection named `wiki-<story_name>`. The ChromaDB document ID is the page slug. Metadata fields stored include `type`, `name`, `slug`, `confidence`, `first_appearance`, and any type-specific fields (`role`, `status`, `region`, `chapter`, `impact`).

ChromaDB failures are non-fatal — the tool logs a warning to stderr and continues. The `CHROMADB_DIR` environment variable overrides the default `.chromadb` data directory path.

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success — result printed to stdout as JSON |
| 1 | Domain error — wiki not initialised, page already exists (create), page not found (update), batch operation failure |
| 2 | Argument error — missing required flag, invalid JSON in arguments, invalid page type |

### Security

- **Path traversal prevention** — story names are validated with `Path.is_relative_to()` via `_validate_story_name()`; page slugs are validated with `_validate_slug()` to reject traversal patterns
- **Shell injection prevention** — the TypeScript wrapper uses `execFileSync` with an argument array, never shell interpolation
- **Atomic writes** — all file writes use `_atomic_write()` (write to temp file, then `os.replace()`)
- **Batch rollback** — batch operations back up modified files in memory before applying changes, restoring them on failure
- **Test isolation** — the `STORIES_DIR` and `CHROMADB_DIR` environment variables override default paths, ensuring tests never touch production data

---

## wiki-lint

Runs consistency checks across the story wiki — post-chapter contradiction detection, comprehensive periodic lint, and single entity validation. Uses the ConStory-Bench taxonomy for finding classification.

**Source files:**
- `.opencode/tools/wiki-lint.ts` — TypeScript wrapper
- `src/tools/wiki_lint.py` — Python CLI script
- `src/tools/_wiki.py` — Shared wiki utilities (`parse_frontmatter`, `find_pages`, `read_index`, `match_entities_in_text`, `WIKI_SUBDIRS`, `_TYPE_TO_DIR`)
- `src/tools/_io.py` — Shared I/O utilities (`_atomic_write`, `_validate_story_name`)

### Purpose

As a story progresses, the wiki accumulates pages across characters, locations, events, factions, and other entity types. Inconsistencies can develop: dead characters mentioned in new chapters, broken wikilinks, orphan pages missing from the index, stale pages not updated for many chapters, or pages placed in the wrong type directory. This tool provides automated detection of these issues.

All three operations produce findings in a common format with severity levels (error, warning, info), ConStory-Bench categories, and suggested fixes. Findings from `check-chapter` and `check-full` are also appended to `wiki/contradictions.md` for persistent tracking.

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `operation` | `"check-chapter" \| "check-full" \| "check-entity"` | Yes | Lint operation to perform |
| `name` | string | Yes | Story name (maps to directory under `stories/`) |
| `chapter_number` | integer | For `check-chapter` | Chapter number being checked |
| `chapter_text` | string | For `check-chapter` | File path to chapter content (must be within `stories/` directory) |
| `current_chapter` | integer | For `check-full` | Current chapter number (used for staleness calculations) |
| `slug` | string | For `check-entity` | Entity slug to validate |

### CLI Interface (Python script)

```bash
python3 src/tools/wiki_lint.py --operation <op> --name <name> [options]
```

**Examples:**

```bash
# Check a newly written chapter for contradictions
python3 src/tools/wiki_lint.py --operation check-chapter --name my-story \
  --chapter-number 5 --chapter-text stories/my-story/chapters/chapter_5.md

# Run a full wiki lint at chapter 12
python3 src/tools/wiki_lint.py --operation check-full --name my-story \
  --current-chapter 12

# Validate a single entity page
python3 src/tools/wiki_lint.py --operation check-entity --name my-story \
  --slug elena-blackwood
```

### Operations

| Operation | Effect | Output |
|-----------|--------|--------|
| `check-chapter` | Scans chapter text for entity mentions, broken wikilinks, and timeline ordering issues. Appends findings to `contradictions.md`. | Findings JSON (see Output Format below) |
| `check-full` | Comprehensive lint: orphan pages, stale claims, broken wikilinks, timeline ordering, confidence downgrades, index/frontmatter mismatches, wrong directory placement. Appends findings to `contradictions.md`. | Findings JSON |
| `check-entity` | Validates a single entity page: required frontmatter fields, detail levels, wikilink resolution, index presence, correct type directory. Appends findings to `contradictions.md`. | Findings JSON |

### Output Format

All operations return the same JSON structure:

```json
{
  "status": "ok",
  "operation": "<operation>",
  "findings": [
    {
      "severity": "error",
      "category": "characterization",
      "subtype": "status_contradiction",
      "pages": ["elena-blackwood"],
      "message": "Character 'Elena Blackwood' has status 'dead' in wiki but is mentioned in chapter 5",
      "suggested_fix": "Verify if 'Elena Blackwood' should be alive or if the mention is a flashback/memory"
    }
  ],
  "summary": {
    "errors": 1,
    "warnings": 0,
    "info": 0,
    "total": 1
  }
}
```

### check-chapter Checks

Post-chapter contradiction detection runs these checks against the chapter text:

| Check | Severity | Category / Subtype | Description |
|-------|----------|-------------------|-------------|
| Missing entity page | warning | `factual_consistency` / `missing_entity` | Entity mentioned in chapter has no wiki page |
| Dead character mention | error | `characterization` / `status_contradiction` | Character with `status: dead` in wiki is mentioned in the chapter |
| Broken wikilink | warning | `factual_consistency` / `broken_wikilink` | `[[slug]]` in chapter text points to non-existent page |
| Timeline ordering | warning | `timeline_plot_logic` / `chapter_ordering_violation` | Timeline contains entries for chapters ahead of the current one |

### check-full Checks

Comprehensive periodic lint runs these checks across the entire wiki:

| Check | Severity | Category / Subtype | Description |
|-------|----------|-------------------|-------------|
| Orphan page (no index entry) | warning | `factual_consistency` / `orphan_reference` | Page exists on disk but is not listed in `index.md` |
| Orphan index entry (no file) | warning | `factual_consistency` / `orphan_reference` | Index entry has no corresponding `.md` file |
| Stale claim | info | `narrative_style` / `stale_claim` | Page not updated for 5+ chapters |
| Confidence downgrade | info | `narrative_style` / `confidence_downgrade` | Page has `confidence: verified` but not updated for 10+ chapters |
| Broken wikilink | warning | `factual_consistency` / `broken_wikilink` | Wikilink in page body points to non-existent page |
| Timeline ordering | error | `timeline_plot_logic` / `temporal_ordering` | Timeline chapter numbers are not monotonically non-decreasing |
| Type mismatch | warning | `factual_consistency` / `naming_inconsistency` | Index type does not match page frontmatter type |
| Wrong directory | warning | `factual_consistency` / `naming_inconsistency` | Page is in the wrong subdirectory for its type |

### check-entity Checks

Single entity validation runs these checks on one page:

| Check | Severity | Category / Subtype | Description |
|-------|----------|-------------------|-------------|
| Missing page | error | `factual_consistency` / `missing_entity` | No wiki page found for the given slug |
| Missing required field | error | `factual_consistency` / `missing_entity` | Page is missing a required frontmatter field (`type`, `name`, `slug`, `confidence`, `first_appearance`) |
| Missing detail level | warning | `narrative_style` / `stale_claim` | Page is missing L1, L2, or L3 in `detail_levels` |
| Broken wikilink | warning | `factual_consistency` / `broken_wikilink` | Wikilink in page body points to non-existent page |
| Not in index | warning | `factual_consistency` / `orphan_reference` | Page exists but is not listed in `index.md` |
| Wrong directory | warning | `factual_consistency` / `naming_inconsistency` | Page is in the wrong subdirectory for its type |

### ConStory-Bench Categories

Findings are classified using categories from the ConStory-Bench contradiction taxonomy:

| Category | Used For |
|----------|----------|
| `timeline_plot_logic` | Timeline ordering violations |
| `characterization` | Character status contradictions (e.g., dead character mentioned) |
| `factual_consistency` | Missing entities, broken wikilinks, orphans, type mismatches |
| `narrative_style` | Stale claims, missing detail levels, confidence downgrades |
| `world_building` | Reserved for future world-rule violation checks |

### Contradictions Log

The `check-chapter` and `check-full` operations append findings to `wiki/contradictions.md` with a timestamped header:

```markdown
## 2026-04-15T10:30:00Z — Chapter 5 check

- **error** characterization/status_contradiction: Character 'Elena' has status 'dead' — Pages: elena-blackwood
- **warning** factual_consistency/broken_wikilink: Wikilink [[old-castle]] points to non-existent page — Pages: old-castle
```

The `check-entity` operation also appends its findings to `contradictions.md`.

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success — result printed to stdout as JSON |
| 1 | Domain error — story not found, chapter-text file not found, chapter-text path outside stories directory |
| 2 | Argument error — missing required flag for the chosen operation |

### Security

- **Path traversal prevention (story name)** — story names are validated with `_validate_story_name()` (uses `Path.is_relative_to()`)
- **Path traversal prevention (chapter-text)** — chapter text file paths are resolved and validated to be within the `stories/` directory
- **Path traversal prevention (slug)** — slugs are validated with `_validate_slug()` to reject traversal patterns
- **Shell injection prevention** — the TypeScript wrapper uses `execFileSync` with an argument array, never shell interpolation
- **Graceful empty state** — returns `{"findings": []}` if the wiki directory does not exist
- **Test isolation** — the `STORIES_DIR` environment variable overrides the default stories directory, ensuring tests never touch production data

---

## Plugins

Plugins differ from tools: they hook into OpenCode lifecycle events rather than being invoked directly by agents. Plugins are TypeScript files in `.opencode/plugins/` and are registered in `opencode.json`.

### story-compaction

Injects story continuity context into the compaction summary when OpenCode compacts the session context.

**Source file:** `.opencode/plugins/story-compaction.ts`

**Hook:** `experimental.session.compacting`

**Purpose:** When OpenCode compacts the conversation to fit within context limits, narrative state (characters, plot threads, chapter position) is lost. This plugin detects the active story, reads its state and wiki pages, and pushes a structured markdown context block (~4000 tokens) into the compaction output. This ensures agents retain story continuity across compaction boundaries.

**Injected sections:**

| Section | Source | Content |
|---------|--------|---------|
| Current Position | `state.json` chapters | Chapter and scene number |
| Story Direction | `state.json` story_context | Narrative trajectory |
| Active Characters | `state.json` + `wiki/characters/` | Names, roles, L1 summaries |
| Active Plot Threads | `state.json` + `wiki/plot-threads/` | Names, status, L2/L1 summaries |
| Recent Chapter Synopses | `wiki/chapters/` | Last 2 chapters at L2/L1 detail |

**Design:**
- Typed API boundary — local `PluginContext`, `CompactionInput`, and `CompactionOutput` interfaces document the runtime contract with OpenCode
- Zero npm dependencies — Node.js builtins only (`fs`, `path`)
- Path validation on all file reads (`isWithinBase()`)
- Progressive token budget truncation (4000 → 2000 tokens if over budget)
- Graceful degradation — silently returns if no story, state, or wiki exists
- Top-level try/catch prevents plugin errors from affecting OpenCode

See [Compaction Plugin](./features/compaction-plugin.md) for full documentation.

---

## Adding a New Tool

Follow this pattern to add tools to the system:

### 1. Create the Python script

Create `src/tools/<tool_name>.py` with:
- `argparse` for CLI argument parsing
- `sys.path` manipulation to import from `src/`
- Domain logic reused from `src/infrastructure/` or `src/application/`
- Output to stdout, errors to stderr
- Exit codes: 0 (success), 1 (domain error), 2 (argument error)

```python
"""CLI tool for <description>."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from domain.exceptions import ConfigurationError  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="<description>")
    parser.add_argument("--arg-name", required=True, help="<help text>")
    args = parser.parse_args()

    try:
        result = do_work(args.arg_name)
    except ConfigurationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(result)


if __name__ == "__main__":
    main()
```

### 2. Create the TypeScript wrapper

Create `.opencode/tools/<tool-name>.ts` with:
- Zod schema for parameter validation
- `execFileSync` to call the Python script
- Error handling that captures stderr

```typescript
import { z } from "zod";
import { execFileSync } from "child_process";
import { resolve } from "path";

export default {
  name: "<tool-name>",
  description: "<description>",
  parameters: z.object({
    argName: z.string().describe("<description>"),
  }),
  execute: async ({ argName }: { argName: string }) => {
    const projectRoot = resolve(__dirname, "../..");
    const args = ["src/tools/<tool_name>.py", "--arg-name", argName];

    try {
      const stdout = execFileSync("python3", args, {
        cwd: projectRoot,
        encoding: "utf-8",
        stdio: ["pipe", "pipe", "pipe"],
      });
      return stdout.trim();
    } catch (error: unknown) {
      const execError = error as { stderr?: string; message?: string };
      const message = execError.stderr?.trim() || execError.message || "Unknown error";
      return `Error: ${message}`;
    }
  },
};
```

### 3. Write tests

Create `tests/unit/test_<tool_name>_tool.py` testing:
- Successful execution with expected arguments
- Missing required arguments (exit code 2)
- Domain errors (exit code 1)
- Direct class usage (bypasses CLI layer)

### 4. Verify

```bash
ruff check --fix . && ruff format . && mypy src/
pytest tests/unit/test_<tool_name>_tool.py -v
```

---

## rag-query

Indexes story content into a per-story ChromaDB collection and queries it by semantic similarity. Used to retrieve relevant context chunks (outline paragraphs, chapter passages, character details, setting descriptions) for scene generation.

**Source files:**
- `.opencode/tools/rag-query.ts` — TypeScript wrapper
- `src/tools/rag_query.py` — Python CLI script

### Purpose

Each story maintains a ChromaDB collection named `stories-{story_name}` under `.chromadb/`. As content is generated (outline, chapters, character sheets, setting sheets, wiki pages, recaps), other tools call `rag-query index` to embed it. During scene generation, agents call `rag-query query` to retrieve the most relevant content for the scene context.

This replaces the previous PostgreSQL/pgvector RAG system from the pre-migration codebase.

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `operation` | `"index" \| "query"` | Yes | Operation to perform |
| `name` | string | Yes | Story name (maps to `stories/<name>/`) |
| `docId` | string | For `index` | Stable unique identifier for the content chunk (e.g. `"outline"`, `"chapter-1"`, `"character-elena"`) |
| `content` | string | For `index` | Full text content to embed |
| `contentType` | string | No | One of: `outline`, `chapter`, `character`, `setting`, `wiki`, `recap`, `raw-chapter`. Defaults to `outline` for index; acts as a filter for query. |
| `chapterNum` | number | No | Chapter number (stored as `chapter_num` metadata for chapter content) |
| `query` | string | For `query` | Semantic search query text |
| `nResults` | number | No | Number of results to return (default: 10) |

### CLI Interface (Python script)

```bash
python3 src/tools/rag_query.py --operation <op> --name <story> [options]
```

**Examples:**

```bash
# Index the story outline
python3 src/tools/rag_query.py \
  --operation index \
  --name my-story \
  --doc-id outline \
  --content "A hero must save the kingdom..." \
  --content-type outline

# Index a chapter
python3 src/tools/rag_query.py \
  --operation index \
  --name my-story \
  --doc-id chapter-1 \
  --content "Chapter one content..." \
  --content-type chapter \
  --chapter-num 1

# Query for relevant character context
python3 src/tools/rag_query.py \
  --operation query \
  --name my-story \
  --query "warrior character from the north" \
  --content-type character \
  --n-results 5
```

### Operations

| Operation | Effect | Output |
|-----------|--------|--------|
| `index` | Upserts content with metadata into `stories-{name}` ChromaDB collection | `{"status": "ok", "indexed": "<doc_id>", "content_type": "<type>", "story": "<name>"}` |
| `query` | Semantic search, optional content-type filter, returns ranked chunks | `{"status": "ok", "results": [...]}` |

### Query Result Format

```json
{
  "status": "ok",
  "results": [
    {
      "doc_id": "character-elena",
      "score": 0.8741,
      "excerpt": "Elena is a fierce warrior from the northern...",
      "metadata": {
        "story": "my-story",
        "content_type": "character",
        "doc_id": "character-elena"
      }
    }
  ]
}
```

Scores are normalised similarity values in `[0, 1]` — higher is more relevant.

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Domain error — ChromaDB failure |
| 2 | Argument error — missing required flag or invalid content-type |

### Security

- **Path traversal prevention** — story names validated via `_validate_story_name` (same guard as `story-state` and wiki tools)
- **Shell injection prevention** — TypeScript wrapper uses `execFileSync` with argument array
- **CHROMADB_DIR override** — environment variable allows test isolation without touching production data

---

## Related

- [ADR 001: Hybrid Agent-Tool Architecture](./planning/adr/001-hybrid-agent-tool-architecture.md) — Architectural decision establishing the tool pattern
- [Architecture Notes](../.github/notes/architecture.md) — System architecture overview
