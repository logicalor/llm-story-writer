# Compaction Plugin

> OpenCode plugin that injects story continuity context into the session compaction summary.

## Overview

When working on long story sessions, OpenCode periodically compacts the conversation context to stay within token limits. Without intervention, this compaction discards narrative state — the agent loses track of characters, plot threads, and where it is in the story.

The compaction plugin hooks into OpenCode's `experimental.session.compacting` event to inject a structured context block into the compacted summary. This ensures agents retain narrative continuity across compaction boundaries without manual re-prompting.

The plugin is implemented as a single TypeScript file with zero npm dependencies — it uses only Node.js builtins (`fs`, `path`).

## When It Activates

The plugin activates automatically whenever OpenCode compacts the session context. This happens:

- When the conversation approaches the model's context window limit
- When OpenCode decides the session history exceeds its compaction threshold

The plugin registers a handler for the `experimental.session.compacting` hook. During compaction, OpenCode calls this handler with an `output` object containing a `context` array. The plugin pushes its story continuity block into this array, and OpenCode includes it in the compaction summary sent to the model.

If no story exists, no state is available, or any error occurs, the plugin silently returns without injecting anything — OpenCode proceeds with its default compaction behaviour.

## Plugin API Types

The plugin defines local TypeScript interfaces for its API boundary with OpenCode. These replace untyped parameters and document the runtime contract, even though OpenCode does not publish SDK types.

```typescript
/** Context object provided by OpenCode to plugin entry point. */
interface PluginContext {
  directory?: string;
  worktree?: string;
}

/** Input parameter for the compaction hook (currently unused). */
interface CompactionInput {}

/** Output parameter for the compaction hook — append context blocks here. */
interface CompactionOutput {
  context: string[];
}
```

| Interface | Used By | Purpose |
|-----------|---------|---------|
| `PluginContext` | `ctx` parameter of the default export | Provides the project root path (`directory` or `worktree`) |
| `CompactionInput` | `_input` parameter of the hook handler | Reserved for future use by OpenCode; currently empty |
| `CompactionOutput` | `output` parameter of the hook handler | Contains the `context` array that the plugin pushes its continuity block into |

These interfaces are local to the plugin file and reflect the observed runtime behaviour. They may need updating if OpenCode's plugin API changes.

## What Context It Injects

The plugin assembles a structured markdown block under the heading `## Story Continuity Context`, containing up to five sections:

### Current Position

The chapter and scene number where generation left off, derived from the highest-numbered chapter and scene keys in `state.json`.

```
### Current Position
Chapter 5, Scene 3
```

### Story Direction

The `story_direction` field from `state.json`, which describes the narrative trajectory. Truncated to fit within a 200-token budget.

### Active Characters

A merged list of characters from `state.json` and wiki `characters/` pages. Each entry includes the character's role and a one-line summary (sourced from the wiki page's `detail_levels.L1` frontmatter field). State characters appear first; wiki-only characters are appended.

```
### Active Characters
- **Elena Blackwood** (protagonist): A determined detective haunted by her past
- **Marcus Cole** (antagonist): Charismatic crime lord with hidden motives
```

### Active Plot Threads

A merged list of plot threads from `state.json` and wiki `plot-threads/` pages. Each entry includes the thread's status and a summary (sourced from `detail_levels.L2` or `detail_levels.L1`).

```
### Active Plot Threads
- **The Missing Witness** (active): Key witness disappeared after the courthouse scene
- **Underground Network** (active): Elena discovered a smuggling operation in Chapter 3
```

### Recent Chapter Synopses

Synopses for the two most recent chapters, sourced from wiki `chapters/` pages. Uses `detail_levels.L2` (or falls back to `L1`) from the page frontmatter. Chapters are sorted by filename (e.g., `chapter-01.md`, `chapter-02.md`).

```
### Recent Chapter Synopses
#### Chapter 4
Elena followed the trail to the abandoned warehouse...

#### Chapter 5
The confrontation at the docks revealed Marcus's true intentions...
```

## Token Budget Strategy

The plugin targets a total budget of approximately 4000 tokens across all sections:

| Section | Initial Budget | Tight Budget |
|---------|---------------|-------------|
| Story Direction | 200 tokens | 100 tokens (400 chars) |
| Active Characters | 800 tokens | 400 tokens |
| Active Plot Threads | 800 tokens | 400 tokens |
| Recent Chapter Synopses | 2000 tokens | 800 tokens |
| **Total** | **~4000 tokens** | **~2000 tokens** |

Token estimation uses a simple heuristic: `ceil(character_count / 4)`.

If the assembled context exceeds 4000 tokens after the initial build, the plugin rebuilds with tighter budgets (the "Tight Budget" column). Each section builder progressively removes entries from the bottom until it fits within budget. For synopses, the builder drops older chapters first and falls back from L2 to L1 detail levels.

## How the Plugin Detects the Current Story

The plugin scans the `stories/` directory for subdirectories containing a `state.json` file. It selects the story with the most recently modified `state.json` (by filesystem mtime). This heuristic works because the active story's state file is updated frequently during generation.

Detection steps:

1. Resolve `stories/` relative to the project root (from `ctx.directory` or `ctx.worktree`)
2. List all entries in `stories/`
3. For each entry, check if `stories/<name>/state.json` exists
4. Select the entry whose `state.json` has the highest `mtimeMs`
5. If no valid state files exist, return silently

## Data Sources

The plugin reads from two sources within the detected story directory:

| Source | Path | Data |
|--------|------|------|
| Story state | `stories/<name>/state.json` | Characters, plot threads, chapter/scene structure, story direction |
| Wiki pages | `stories/<name>/wiki/characters/*.md` | Character metadata and L1 summaries |
| Wiki pages | `stories/<name>/wiki/plot-threads/*.md` | Plot thread status and L2/L1 summaries |
| Wiki pages | `stories/<name>/wiki/chapters/*.md` | Chapter synopses at L2/L1 detail levels |

Wiki pages use YAML frontmatter parsed by a built-in regex-based parser that handles one level of nesting (sufficient for `detail_levels.L1`, `detail_levels.L2`, etc.).

## Graceful Degradation

The plugin is designed to never interfere with OpenCode's operation:

- **No story directory** — returns silently
- **No `state.json`** — returns silently
- **No wiki directory** — builds context from state only (no character summaries, synopses)
- **Empty wiki subdirectories** — skips those sections
- **Malformed JSON or YAML** — skips the affected data source
- **Path traversal attempts** — all file paths are validated with `isWithinBase()` before reading
- **Any uncaught exception** — wrapped in a top-level try/catch that silently swallows errors

If the assembled context contains only the header and no substantive sections, the plugin returns without injecting anything.

## Security

- **Path validation** — every file path is checked with `isWithinBase()` before reading, preventing traversal outside the `stories/` directory
- **No shell execution** — the plugin reads files directly via `fs.readFileSync`, no subprocess calls
- **No network access** — all data sources are local filesystem reads
- **No external dependencies** — uses only Node.js builtins (`fs`, `path`)

## Key Files

- `.opencode/plugins/story-compaction.ts` — the plugin implementation
- `tests/unit/test_compaction_plugin.py` — structural verification tests

## Testing

The plugin includes structural verification tests in `tests/unit/test_compaction_plugin.py` that verify:

- Plugin file exists at the expected path
- Contains the `experimental.session.compacting` hook registration
- Contains all required section headers
- Has a `default export`
- Includes error handling (try/catch)
- Includes path validation logic
- References the 4000-token budget
- Uses no external dependencies (only `fs` and `path` imports)

Run tests:

```bash
pytest tests/unit/test_compaction_plugin.py -v
```

## Related

- [Tools Reference](../tools.md#story-compaction) — Plugin entry in the tools/plugins reference
- [ADR 004: Progressive Wiki Memory System](../planning/adr/004-progressive-wiki-memory-system.md) — Wiki page format and detail levels used by the plugin
- [Story Orchestrator](./story-orchestrator.md) — Pipeline controller that generates the state and wiki data consumed by this plugin
- Issue #23 — Initial implementation
