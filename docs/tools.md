# Tools Reference

> Custom tools in the hybrid agent-tool architecture — TypeScript wrappers calling Python domain logic via subprocess.

## Overview

Tools follow the pattern established in [ADR 001](./planning/adr/001-hybrid-agent-tool-architecture.md): OpenCode agents handle orchestration and creative decisions; tools handle deterministic operations with single correct outputs for given inputs.

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

Prompt templates are Markdown files in the `prompts/` directory (131 templates across 10 categories). This tool provides deterministic template loading and variable substitution so agents can retrieve rendered prompts without managing file paths or parsing logic.

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

Manages story savepoints — save, load, check, list, and clear checkpoint data used to resume story generation from intermediate steps.

**Source files:**
- `.opencode/tools/savepoint-mgr.ts` — TypeScript wrapper
- `src/tools/savepoint_manager.py` — Python CLI script
- `src/infrastructure/storage/savepoint_repository.py` — Underlying `FilesystemSavepointRepository` class

### Purpose

During story generation, intermediate results (outlines, character sheets, chapter recaps, etc.) are saved as savepoints under `stories/<name>/savepoints/`. This tool provides CLI access to the `FilesystemSavepointRepository` so agents can checkpoint and resume multi-step generation pipelines without re-running expensive LLM calls.

Savepoints support **hierarchical step names** (e.g., `chapter_1/scene_2`) for organising checkpoints by phase and sub-step.

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `operation` | `"save" \| "load" \| "has" \| "list" \| "clear"` | Yes | Operation to perform |
| `name` | string | Yes | Story name (maps to directory under `stories/`) |
| `step` | string | For `save`, `load`, `has` | Step name, supports hierarchical paths like `chapter_1/scene_2` |
| `data` | string | For `save` | JSON string of the data to save |

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

# Clear all savepoints for a story
python3 src/tools/savepoint_manager.py --operation clear --name my-story
```

### Operations

| Operation | Effect | Output |
|-----------|--------|--------|
| `save` | Serialises `--data` as a savepoint file under `savepoints/<step>.md` | `{"status": "saved", "step": "<step>"}` |
| `load` | Reads and deserialises a savepoint file | `{"step": "<step>", "data": <value>}` |
| `has` | Checks whether a savepoint file exists for the given step | `{"step": "<step>", "exists": true/false}` |
| `list` | Scans the `savepoints/` directory for all saved steps | `{"savepoints": {"step_1": <data>, "step_2": <data>, ...}}` |
| `clear` | Removes all savepoint files for the story | `{"status": "cleared"}` |

### Hierarchical Step Names

Step names can contain `/` separators to create a hierarchy:

```
savepoints/
├── chapter_1/
│   ├── outline.md
│   ├── scene_1.md
│   └── scene_2.md
├── chapter_2/
│   └── outline.md
└── characters.md
```

This maps naturally to the story generation pipeline phases (outline, character sheets, per-chapter scenes, recaps).

### Backward Compatibility

Savepoint files use **Markdown with YAML frontmatter** format. The `FilesystemSavepointRepository` reads and writes `.md` files with YAML frontmatter containing the serialised data.

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
| `LLM_API_BASE` | `http://localhost:11434/v1` | OpenAI-compatible API base URL |
| `LLM_MODEL` | `huihui_ai/magistral-abliterated:24b` | Default model identifier |

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
| `operation` | `"analyze-prompt" \| "generate-elements" \| "generate-outline" \| "expand-chapter" \| "refine"` | Yes | Operation to perform |
| `name` | string | Yes | Story name (directory under `stories/`) |
| `prompt` | string | For `analyze-prompt`; optional for `generate-outline` | Story prompt text |
| `desiredChapters` | integer | For `generate-outline` | Number of desired chapters (must be ≥ 1) |
| `chunkStart` | integer | For `expand-chapter` | Start chapter for chunk expansion (must be ≥ 1) |
| `chunkEnd` | integer | For `expand-chapter` | End chapter for chunk expansion (must be ≥ `chunkStart`) |
| `totalChapters` | integer | For `expand-chapter` | Total chapters in the story (must be ≥ `chunkEnd`) |
| `previousChunks` | string | No | Previous chunk outlines text (for `expand-chapter` continuity) |
| `continuitySummary` | string | No | Continuity summary from prior chunks (for `expand-chapter`) |
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
| `LLM_API_BASE` | `http://localhost:11434/v1` | OpenAI-compatible API base URL |
| `LLM_MODEL` | `huihui_ai/magistral-abliterated:24b` | Default model identifier |

The `--model` argument overrides `LLM_MODEL` for a single invocation.

### Argument Validation

Numeric arguments are validated at both layers:

- **TypeScript (Zod)** — `desiredChapters`, `chunkStart`, `chunkEnd`, and `totalChapters` are validated as positive integers (`.int().min(1)`)
- **Python (argparse)** — `--desired-chapters` must be ≥ 1; `--chunk-start` must be ≥ 1; `--chunk-end` must be ≥ `--chunk-start`; `--total-chapters` must be ≥ `--chunk-end`

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

Scene writing pipeline: parse a chapter outline into scene definitions, generate individual scenes, revise scenes with feedback, or assemble scenes into a chapter.

**Source files:**
- `.opencode/tools/scene-writer.ts` — TypeScript wrapper
- `src/tools/scene_writer.py` — Python CLI script
- `src/tools/_llm.py` — Shared LLM client (`generate_text`, `_extract_json_block`, `count_tokens`)
- `src/infrastructure/prompts/prompt_loader.py` — Prompt template loading
- `src/infrastructure/storage/savepoint_repository.py` — Savepoint persistence

### Purpose

The scene writer breaks chapter-level generation into finer-grained scene units. A chapter outline is first parsed into individual scene definitions (structured JSON), then each scene is generated independently. Scenes can be revised with targeted feedback, and once all scenes in a chapter are complete they are assembled into a single chapter document with section headers and separators.

All LLM-backed operations save their results to savepoints, making the pipeline fully resumable if interrupted.

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `operation` | `"parse-definitions" \| "generate" \| "revise" \| "assemble-chapter"` | Yes | Operation to perform |
| `name` | string | Yes | Story name (directory under `stories/`) |
| `chapterNum` | integer | For all except as noted | Chapter number (must be ≥ 1) |
| `sceneNum` | integer | For `generate`, `revise` | Scene number within the chapter (must be ≥ 1) |
| `sceneCount` | integer | For `assemble-chapter` | Total number of scenes in the chapter (must be ≥ 1) |
| `chapterOutline` | string | For `parse-definitions`, `generate`; optional for `revise` | Chapter outline text |
| `sceneDefinition` | string | For `generate`; optional for `revise` | Scene definition as JSON string |
| `sceneContent` | string | For `revise` | Current scene content to revise |
| `feedback` | string | For `revise` | Revision feedback describing what to improve |
| `chapterTitle` | string | No | Chapter title for `assemble-chapter` (defaults to `"Chapter N"`) |
| `baseContext` | string | No | Base story context (for `generate`) |
| `storyElements` | string | No | Story elements text (for `generate`) |
| `characterSheets` | string | No | Character sheets (for `generate`) |
| `settingSheets` | string | No | Setting sheets (for `generate`) |
| `previousRecap` | string | No | Previous chapter recap (for `generate`) |
| `previousScene` | string | No | Previous scene content (for `generate`) |
| `nextSceneDefinition` | string | No | Next scene definition (for `generate`) |
| `nextChapterSynopsis` | string | No | Next chapter synopsis (for `generate`) |
| `model` | string | No | Override LLM model identifier |

### CLI Interface (Python script)

```bash
python3 src/tools/scene_writer.py --operation <op> --name <name> [options]
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
  --base-context "Fantasy world context" \
  --previous-scene "Previous scene text"

# Revise a scene with feedback
python3 src/tools/scene_writer.py --operation revise \
  --name my-story --chapter-num 3 --scene-num 1 \
  --scene-content "The sun set over the city..." \
  --feedback "Add more tension in the dialogue" \
  --scene-definition '{"title": "The Arrival"}' \
  --chapter-outline "Chapter 3 outline"

# Assemble all scenes into a chapter
python3 src/tools/scene_writer.py --operation assemble-chapter \
  --name my-story --chapter-num 3 --scene-count 4 \
  --chapter-title "The Ancient City"
```

### Operations

| Operation | Effect | Output |
|-----------|--------|--------|
| `parse-definitions` | Sends chapter outline through `scenes/parse_definitions` prompt; LLM returns a JSON array of scene objects. Falls back to a single scene if JSON parsing fails. Saves to savepoint. | `{"status": "success", "operation": "parse-definitions", "data": [{"title": "...", "description": "..."}, ...]}` |
| `generate` | Renders `scenes/create_content` prompt with scene definition and full story context, calls LLM, saves result to savepoint | `{"status": "success", "operation": "generate", "data": "<scene text>"}` |
| `revise` | Renders `scenes/revise_content` prompt with current content, feedback, and optional context, calls LLM, overwrites the scene savepoint | `{"status": "success", "operation": "revise", "data": "<revised text>"}` |
| `assemble-chapter` | Loads all scene savepoints for the chapter, retrieves scene titles from definitions savepoint, concatenates with `## <title>` headers and `---` separators | `{"status": "success", "operation": "assemble-chapter", "data": "# <title>\n\n## Scene 1\n\n..."}` |

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

The tool uses three prompt templates from the `prompts/scenes/` directory:

| Template | Used By | Purpose |
|----------|---------|---------|
| `scenes/parse_definitions` | `parse-definitions` | Analyse a chapter outline and extract scene objects as JSON |
| `scenes/create_content` | `generate` | Generate 750–1500 words of scene prose from a definition and context |
| `scenes/revise_content` | `revise` | Revise scene content based on specific feedback |

### Savepoint Structure

All intermediate results are persisted under `stories/<name>/savepoints/`:

| Savepoint Key | Created By | Content |
|---------------|-----------|---------|
| `chapter_N/scene_definitions` | `parse-definitions` | JSON array of scene definition objects |
| `chapter_N/scene_M` | `generate`, `revise` | Scene prose text |

### Resumability

The `parse-definitions` and `generate` operations check for existing savepoints before calling the LLM. If a savepoint exists, the saved result is returned immediately and the LLM call is skipped. This means:

- If `parse-definitions` has already run for a chapter, re-running returns the cached definitions
- If a scene has already been generated, re-running `generate` returns the cached content
- The `revise` operation always calls the LLM and overwrites the scene savepoint, since revisions are intentional changes
- `assemble-chapter` is purely deterministic (no LLM) — it reads scene savepoints and concatenates them

### Fallback Behaviour

If the LLM response from `parse-definitions` cannot be parsed as valid JSON, or the parsed result is not a list of dictionaries, the tool falls back to a single scene definition containing the chapter number and the full chapter outline text as description.

### LLM Configuration

The tool uses `src/tools/_llm.py` for LLM access, configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_BASE` | `http://localhost:11434/v1` | OpenAI-compatible API base URL |
| `LLM_MODEL` | `huihui_ai/magistral-abliterated:24b` | Default model identifier |

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

## Related

- [ADR 001: Hybrid Agent-Tool Architecture](./planning/adr/001-hybrid-agent-tool-architecture.md) — Architectural decision establishing the tool pattern
- [Architecture Notes](../.github/notes/architecture.md) — System architecture overview
