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
