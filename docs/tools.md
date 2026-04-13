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
| `budget` | number | No | Token budget for `generate-abridged` (default: 500) |
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
| `budget` | number | No | Token budget for `generate-abridged` (default: 500) |
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
