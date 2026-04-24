# Custom Commands

> Historical note on the retired OpenCode slash-command interface that preceded the Python-native CLI.

## Overview

Issue #164 / PR #175 removed `.opencode/commands/` and the OpenCode slash-command interface from the repository. This document is retained as a historical record of that surface.

Custom commands were formerly defined as Markdown files in `.opencode/commands/`, with each file mapping to a slash command in the OpenCode TUI (for example `/new-story` or `/continue`). Commands used YAML frontmatter to declare metadata and optionally route to a specific agent.

Four commands route to the `story-orchestrator` agent for pipeline operations. Three informational commands use the default agent and rely on shell output injection (`!command`) and file inclusion (`@file`) to assemble read-only summaries without invoking Python tools directly.

No new Python tools were required — the commands composed existing tools (`story-state`, `savepoint-mgr`, `wiki-lint`, `scene-writer`, and others) through agent orchestration. The supported operator entry point is now the Python-native `story-writer` CLI.

## Command Reference

### /new-story

**Usage:** `/new-story <prompt-file>`
**Agent:** `story-orchestrator`

Initializes a new story and starts the full generation pipeline. The argument is a path to a prompt file containing the user's creative brief.

**Behaviour:**

1. Verifies the prompt file exists at the given path
2. Reads the prompt file contents
3. Begins the ten-phase pipeline from Phase 1 (initialization) through to completion

**Example:**

```
/new-story prompts/my-epic-fantasy.md
```

---

### /continue

**Usage:** `/continue [story-name]`
**Agent:** `story-orchestrator`

Resumes story generation from the most recent savepoint. If no story name is provided, the command lists available stories and asks the user to choose.

**Behaviour:**

1. Lists available stories via `story-state --operation list`
2. If a story name was given, selects that story; otherwise prompts for selection
3. Lists savepoint names for the chosen story via the lean `savepoint-mgr list` operation
4. Identifies the most recent savepoint and resumes the pipeline from that point

**Example:**

```
/continue my-epic-fantasy
/continue
```

---

### /regenerate

**Usage:** `/regenerate chapter N` or `/regenerate scene C S`
**Agent:** `story-orchestrator`

Regenerates a specific chapter or scene. The command parses the arguments to determine the target:

- `chapter N` — regenerates chapter N entirely (e.g., `chapter 5`)
- `scene C S` — regenerates scene S of chapter C (e.g., `scene 3 2`)

**Behaviour:**

1. Identifies the active story from current state
2. Parses the arguments to determine the regeneration target
3. Checks which wiki entities were introduced or modified in the target content
4. Considers rolling back wiki entries affected by the content being regenerated
5. Regenerates the content using the existing pipeline tools
6. Updates the wiki with any new or changed entities from the regenerated content
7. Runs `wiki-lint` to verify consistency after the update

**Example:**

```
/regenerate chapter 5
/regenerate scene 3 2
```

---

### /savepoint

**Usage:** `/savepoint [name]`
**Agent:** `story-orchestrator`

Creates a manual savepoint for the current story. If no name is provided, a timestamped name is generated automatically with a `manual_` prefix.

**Behaviour:**

1. Reads the story state to identify the active story
2. Creates a savepoint via `savepoint-mgr` with the given or generated name
3. Includes the current story state as the savepoint data
4. Confirms the savepoint was created

**Example:**

```
/savepoint before-climax-rewrite
/savepoint
```

---

### /status

**Usage:** `/status [story-name]`
**Agent:** default

Displays a formatted progress summary for a story. If no story name is provided, the command lists available stories and asks the user to choose.

**Behaviour:**

The command injects three shell commands into the prompt context to gather data:

- `story-state --operation list` — lists available stories
- `story-state --operation read --name <story>` — reads full story state
- `savepoint_manager.py --operation list --name <story>` — lists savepoint names only, avoiding large payload dumps

It also runs a `find` command to count wiki pages. The agent assembles these outputs into a human-readable summary including:

- Story name and creative direction
- Chapters completed vs total planned
- Current pipeline phase (derived from the most recent savepoint)
- Available savepoint names for resume/debugging
- Wiki statistics — page counts by subdirectory

**Example:**

```
/status my-epic-fantasy
/status
```

---

### /settings

**Usage:** `/settings [key] [value]`
**Agent:** default

Views or modifies generation settings from `config.md`'s YAML frontmatter. The command includes the full `config.md` file via `@config.md` file inclusion syntax.

**Behaviour:**

- No arguments — displays all current settings in a formatted table grouped by section (models, generation, translation, infrastructure)
- One argument (key only) — shows that setting's current value
- Two arguments (key and value) — modifies the setting in `config.md`, preserving YAML structure and formatting

**Example:**

```
/settings
/settings generation.wanted_chapters
/settings generation.wanted_chapters 30
```

---

### /wiki

**Usage:** `/wiki [story-name]`
**Agent:** default

Displays a wiki health summary for a story. If no story name is provided, the command lists available stories and asks the user to choose.

**Behaviour:**

The command injects shell commands to gather wiki data:

- `story-state --operation list` — lists available stories
- `find` — counts wiki pages (excluding internal files)
- `ls -la` — lists wiki subdirectories with timestamps
- `wiki-lint --operation check-full` — runs full consistency check

The agent assembles a wiki health report including:

- Total number of wiki pages
- Page counts per subdirectory (characters, locations, events, factions, items, plot-threads, world-rules, themes, relationships, timeline, chapters)
- Last update timestamps
- Any issues or warnings from lint results

**Example:**

```
/wiki my-epic-fantasy
/wiki
```

## Command File Format

Each command was a Markdown file in `.opencode/commands/` with YAML frontmatter. That directory is now deleted; only the reusable prompt bodies for `continue` and `regenerate` were preserved under `prompts/agents/continue.md` and `prompts/agents/regenerate.md`.

```yaml
---
description: Short description shown in command palette
agent: story-orchestrator  # optional — routes to a specific agent
---

Command body text with instructions for the agent.

Arguments are referenced via $1, $2, or $ARGUMENTS.
Shell output is injected with !command syntax.
Files are included with @filepath syntax.
```

### Frontmatter Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | string | Yes | Short description displayed in the OpenCode command palette |
| `agent` | string | No | Agent to route the command to. Omit for default agent. |

### Template Syntax

| Syntax | Purpose | Example |
|--------|---------|---------|
| `$1`, `$2` | Positional arguments | `$1` = first argument after command name |
| `$ARGUMENTS` | All arguments as a single string | Used when argument parsing is complex |
| `!command` | Shell output injection — runs a command and inlines its output | `!python3 src/tools/story_state.py --operation list` |
| `@filepath` | File inclusion — inlines the file's contents | `@config.md` |

## Agent Routing

| Command | Agent | Rationale |
|---------|-------|-----------|
| `/new-story` | `story-orchestrator` | Requires full pipeline orchestration |
| `/continue` | `story-orchestrator` | Requires pipeline resume logic |
| `/regenerate` | `story-orchestrator` | Requires chapter/scene generation and wiki rollback |
| `/savepoint` | `story-orchestrator` | Needs access to story state for savepoint data |
| `/status` | default | Read-only — assembles data from shell output injection |
| `/settings` | default | Read-only or simple config file edit |
| `/wiki` | default | Read-only — assembles data from shell output injection |

## Testing

Before Issue #164 removed the command surface, 12 verification tests in `tests/unit/test_commands.py` confirmed:

- All 7 command files existed in `.opencode/commands/`
- All commands have valid YAML frontmatter with non-empty `description` fields
- Orchestrator commands (`new-story`, `continue`, `regenerate`, `savepoint`) have `agent: story-orchestrator`
- Informational commands (`status`, `settings`, `wiki`) do not have an `agent` field
- `new-story` references `$1` for the prompt file argument
- `regenerate` references `$ARGUMENTS` for flexible argument parsing
- `continue` injects the story list via `!python3` shell syntax
- `status` uses shell injection for data gathering and the names-only savepoint list
- `settings` includes `@config.md` for file context
- `wiki` references `wiki_lint.py` for health checks
- The `.gitkeep` placeholder had been removed

Those tests were deleted with the command surface and are no longer runnable in the current repository.

## Related

- [Story Orchestrator](./story-orchestrator.md) — Agent that executes pipeline commands
- [Tools Reference](../tools.md) — Deterministic tools composed by commands
- [ADR 001: Hybrid Agent-Tool Architecture](../planning/adr/001-hybrid-agent-tool-architecture.md) — Architecture establishing the agent-tool pattern
