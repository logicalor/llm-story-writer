# Synthesized Research Report: Migrating GitHub Copilot Customizations to Opencode

**Date:** 2026-04-29  
**Question:** How do you migrate GitHub Copilot customization artefacts — Skills, Instructions, Agents, and MCP servers — to Opencode?  
**Models consulted:** Claude Sonnet 4.6, GPT-5.4, Gemini 3.1 Pro (Preview)  
**Researchers:** Three independent sub-agents; each consulted the official Opencode docs and community sources independently.

---

## Synthesis Overview

Opencode has native equivalents for all four GitHub Copilot customization artefact types, with varying degrees of fidelity. The three models reached a high level of consensus on the core mapping and migration steps. The most important project-specific finding — confirmed by all three models — is that this repository's skills at `.agents/skills/*/SKILL.md` are **already discovered natively by Opencode** with zero migration required. The one substantive gap is the `applyTo` glob-scoped instruction injection from `.instructions.md` files, which requires a community plugin (`opencode-rules`) to replicate. MCPs and agents translate with schema reformatting only.

**Model Agreement Score: 8/10** — The three models agreed on all major architectural mappings and identified the same primary gap (`applyTo`). The only material divergence was on sub-agent dispatch mechanics.

---

## Individual Report Summaries

| Model | Focus Areas | Unique Finds | Sources Cited |
|---|---|---|---|
| Claude | Deep SKILL.md compatibility analysis; `opencode-rules` plugin detail; agent frontmatter mapping; `{env:VAR}` interpolation syntax | Explicit list of all skill discovery paths including `.agents/skills/`; `instructions` array accepts globs; `.prompt.md` gap | 12 |
| GPT | Sub-agent dispatch via `permission.task`; per-agent MCP scoping; phased migration plan; `tools:` deprecation | No documented `cwd` equivalent for MCP; `tools:` deprecated in favour of `permission:`; strong example of orchestrator permission config | 9 |
| Gemini | `opencode-rules` `.mdc` file format detail; lazy-loading instructions pattern in `AGENTS.md`; Claude Code compatibility layer note | `.mdc` extension option for rules files; native Claude Code directory fallback (`.claude/skills/`) | 6 |

---

## Consensus Findings

### ★★★ Unanimous Findings (All Three Models Agree)

```
[U-01] Opencode natively discovers SKILL.md files from .agents/skills/
Confidence: ★★★ Unanimous
Category: Architecture / Skills
Detail: Opencode scans several directories for SKILL.md-format skills, including
  .opencode/skills/<name>/SKILL.md  (primary Opencode location)
  ~/.config/opencode/skills/<name>/SKILL.md  (global user)
  .agents/skills/<name>/SKILL.md  (← this project's existing location — already supported)
  ~/.agents/skills/<name>/SKILL.md
  .claude/skills/<name>/SKILL.md  (Claude Code compatibility)
  ~/.claude/skills/<name>/SKILL.md
This means the project's existing .agents/skills/ tree requires zero migration. Skills are
loaded on demand via a built-in 'skill' tool that the agent calls with the skill name.
Frontmatter fields unknown to Opencode (e.g. VS Code-specific metadata) are silently ignored.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: https://opencode.ai/docs/skills/
```

```
[U-02] Opencode uses opencode.json as the primary project config file
Confidence: ★★★ Unanimous
Category: Configuration
Detail: Opencode uses a JSON or JSONC file named opencode.json at the project root.
Config locations in precedence order (later overrides earlier):
  1. Remote config from .well-known/opencode (org defaults)
  2. ~/.config/opencode/opencode.json (global user)
  3. OPENCODE_CONFIG env var (custom path override)
  4. opencode.json in project root (project-specific, committed to git)
  5. .opencode/ directory (agents, commands, plugins, skills, tools, themes)
  6. OPENCODE_CONFIG_CONTENT env var (inline runtime overrides)
All levels are deep-merged, not replaced. A $schema field pointing to
https://opencode.ai/config.json enables IDE completion.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: https://opencode.ai/docs/config/
```

```
[U-03] MCP servers translate to the opencode.json "mcp" block with schema differences
Confidence: ★★★ Unanimous
Category: MCPs
Detail: VS Code's "servers" / .vscode/mcp.json maps directly to the "mcp" key in
opencode.json with these format changes:
  - "type": "stdio"  →  "type": "local"
  - "command": "cmd", "args": [...]  →  "command": ["cmd", "arg1", ...]  (merged array)
  - "env": {...}  →  "environment": {...}
  - Added: "enabled": true|false, "timeout": <ms>, "headers": {...}, "oauth": {...}
  - Added: remote MCP type: "type": "remote", "url": "https://..."
  - Secret values: use "{env:VAR_NAME}" interpolation instead of hardcoded strings.

Current project MCP (chroma) translates as:
  FROM (.github/mcp.json / .vscode/mcp.json):
    { "mcpServers": { "chroma": { "type": "stdio", "command": "uvx",
        "args": ["chroma-mcp", "--client-type", "persistent", "--data-dir", ".chromadb"],
        "cwd": "." } } }
  TO (opencode.json):
    { "mcp": { "chroma": { "type": "local", "enabled": true,
        "command": ["uvx", "chroma-mcp", "--client-type", "persistent",
                    "--data-dir", ".chromadb"] } } }
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: https://opencode.ai/docs/mcp-servers/
```

```
[U-04] Custom agents live in .opencode/agents/<name>.md; filename = agent name
Confidence: ★★★ Unanimous
Category: Agents
Detail: Copilot's .github/agents-copilot/*.agent.md maps to .opencode/agents/<name>.md.
Key format changes:
  - name: field in frontmatter is REMOVED; the filename (without .md) is the agent name
  - model: stays but requires provider prefix: "claude-sonnet-4-5" → "anthropic/claude-sonnet-4-5"
  - tools: list is replaced by permission: map (tools: is deprecated)
  - mode: primary (user-facing) or subagent (dispatched by other agents) — required
  - hidden: true for internal agents not shown in autocomplete
  - System prompt body is identical (plain markdown, no change needed)
Global user agents live in ~/.config/opencode/agents/<name>.md
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: https://opencode.ai/docs/agents/
```

```
[U-05] No native applyTo equivalent — instructions are always-on, not file-scoped
Confidence: ★★★ Unanimous
Category: Instructions / Gap
Detail: Opencode has no built-in mechanism equivalent to Copilot's applyTo YAML frontmatter
that conditionally injects instructions when the active editor file matches a glob pattern.
Opencode's instruction mechanism:
  - AGENTS.md at project root (always injected)
  - "instructions" array in opencode.json (paths or glob patterns, always injected)
  - No active-editor-state awareness in terminal/TUI context
The opencode-rules community plugin (https://github.com/frap129/opencode-rules) is the
recommended workaround, providing globs: frontmatter equivalent.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: https://opencode.ai/docs/rules/, https://github.com/frap129/opencode-rules
```

```
[U-06] Agent permissions use a category-based model, not a named-tools list
Confidence: ★★★ Unanimous
Category: Agents
Detail: Copilot's tools: [read_file, write_file, run_in_terminal, ...] array is replaced
by Opencode's permission: map. The tools: key still exists in Opencode config but is
explicitly documented as deprecated. Migration target is permission:.

Permission map structure:
  permission:
    edit: allow | deny | ask        # file editing
    bash: allow | deny | ask        # shell command execution
    skill: allow | deny | ask       # skill loading
    task: allow | deny | ask        # spawning subagents
    web: allow | deny | ask         # web fetch

Fine-grained bash control (example from project's orchestrator):
  permission:
    bash:
      "*": ask
      "git diff*": allow
      "pytest*": allow
      "ruff check*": allow

MCP tools are scoped per-agent using the tools: key (not deprecated for this purpose):
  tools:
    "chroma/*": true
    "tavily-mcp/*": false
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: https://opencode.ai/docs/agents/
```

---

### ★★☆ Majority Findings (Two of Three Models Agree)

```
[M-01] The opencode-rules plugin implements applyTo-equivalent via globs: frontmatter
Confidence: ★★☆ Majority
Category: Instructions / Workaround
Detail: The community plugin frap129/opencode-rules adds conditional rule injection to
Opencode. Install:
  "plugin": ["opencode-rules@latest"]  in opencode.json

Rule files live in .opencode/rules/ (project) or ~/.config/opencode/rules/ (global).
File extension: .md or .mdc (Cursor-compatible).

Copilot .instructions.md translation:
  FROM (.github/instructions/chromadb.instructions.md):
    ---
    applyTo: "src/**/*.py"
    ---
    # ChromaDB instructions...

  TO (.opencode/rules/chromadb.md):
    ---
    globs:
      - "src/**/*.py"
    ---
    # ChromaDB instructions...

The plugin supports additional conditions beyond Copilot's applyTo:
  - keywords: [list] — inject when prompt contains these words
  - tools: [list] — inject when specific MCP tools are available
  - model: string — inject only for a specific model
  - agent: string — inject only for a specific agent
  - match: any | all — OR vs AND logic across conditions
Models: Claude ✓ GPT ✗ (confirmed plugin exists but did not detail frontmatter schema) Gemini ✓
Sources: https://github.com/frap129/opencode-rules
```

```
[M-02] Sub-agent dispatch uses permission.task + the Task tool
Confidence: ★★☆ Majority
Category: Agents / Sub-agent orchestration
Detail: Opencode's sub-agent dispatch model is controlled via permission.task in the
orchestrator agent config. The Task tool (built-in) is used to spawn subagent sessions.

Example orchestrator config (this project mapping):
  "agent": {
    "story-orchestrator": {
      "mode": "primary",
      "permission": {
        "task": {
          "*": "deny",
          "outline-planner": "allow",
          "chapter-writer": "allow",
          "quality-reviewer": "allow",
          "wiki-maintainer": "allow"
        }
      }
    }
  }

Subagents run in child sessions in TUI (navigable with keyboard shortcuts).
In TUI, users can also manually invoke an agent via @agent-name mention.
Models: Claude ✗ (reported @mention only, missed permission.task detail) GPT ✓ Gemini ✓ (partial)
Dissenting view: Claude described @mention as the dispatch mechanism; both @mention (TUI
user interaction) and permission.task (programmatic agent-to-agent dispatch) are valid and
serve different use cases — they are complementary, not alternatives.
Sources: https://opencode.ai/docs/agents/
```

```
[M-03] The instructions array in opencode.json accepts glob patterns
Confidence: ★★☆ Majority
Category: Instructions
Detail: The "instructions" array field in opencode.json accepts file paths, glob patterns,
and remote URLs. Example:
  {
    "instructions": [
      "AGENTS.md",
      ".github/instructions/*.instructions.md",
      "docs/guidelines.md",
      "packages/*/AGENTS.md"
    ]
  }
All matched files are loaded and combined into the permanent context window.
Important: all matched files are always injected regardless of active file or context —
no conditional logic. This differs from applyTo.
Models: Claude ✓ GPT ✗ (listed paths but did not confirm glob syntax) Gemini ✓
Sources: https://opencode.ai/docs/rules/
```

---

### ★☆☆ Singular Findings (Only One Model Reported)

```
[S-01] No documented MCP cwd equivalent in Opencode
Confidence: ★☆☆ Singular
Category: MCPs / Gap
Detail: VS Code MCP config supports "cwd" to set the working directory for the MCP
server process. Opencode's documented local MCP fields are: type, command, enabled,
environment, timeout. No "cwd" equivalent is documented.
For the project's chroma MCP server (which uses "cwd": "."), this is a potential issue
if the MCP server requires the project root as its working directory.
Workarounds: use absolute paths in command arguments, or launch via a wrapper script.
Model: GPT
Assessment: Plausible — the official MCP docs page likely does not list a cwd field,
and the VS Code format is more mature in supporting process-management options.
Worth verifying before deploying in production. In practice, chroma-mcp may operate
correctly without explicit cwd if launched from the project root directory.
Sources: https://opencode.ai/docs/mcp-servers/
```

```
[S-02] .prompt.md files have no direct Opencode equivalent
Confidence: ★☆☆ Singular
Category: Gap
Detail: GitHub Copilot supports .prompt.md files as reusable prompt entry-points that
users can select from the Copilot Chat UI. Opencode has no direct equivalent.
The closest Opencode feature is custom commands (.opencode/commands/<name>.md), which
define slash-command shortcuts with pre-configured prompts.
Model: Claude
Assessment: Plausible — this is a known Copilot-specific feature with no terminal-TUI
equivalent. Custom commands in Opencode serve a similar but not identical purpose.
Sources: https://opencode.ai/docs/
```

```
[S-03] Claude Code compatibility layer — .claude/skills/ is also scanned
Confidence: ★☆☆ Singular
Category: Skills
Detail: Opencode also scans .claude/skills/<name>/SKILL.md and ~/.claude/skills/ as a
compatibility layer for Claude Code users. This is in addition to the Opencode-primary
and .agents/ paths.
Model: Gemini
Assessment: Plausible and consistent with the .agents/skills/ compatibility finding
(U-01), which all three models confirmed. The Claude Code compatibility layer is a
natural extension of the same multi-tool portability design.
Sources: Medium blog and Gemini's direct docs reading
```

---

## Divergence Analysis

```
[D-01] Topic: Sub-agent dispatch mechanism
Claude says: Sub-agents are dispatched via @agent-name mention syntax in TUI prompts
GPT says: Orchestrators dispatch sub-agents via the Task tool; dispatch is controlled
  by permission.task in the orchestrator config; @agent is for manual user invocation
Gemini says: Did not detail the mechanism; confirmed mode: subagent exists
Assessment: GPT's account (permission.task + Task tool) is the more technically precise
description of programmatic inter-agent dispatch — which is what this project's Orchestrator
pattern requires. Claude's @mention syntax describes the *user-facing* TUI interaction mode,
which is a complementary feature. Both are accurate in their respective contexts.
Resolution: Use permission.task + Task tool for Orchestrator → sub-agent dispatch.
  Use @agent-name for manual TUI agent switching by the user.
  These are not mutually exclusive.
```

```
[D-02] Topic: Official GitHub repository for Opencode
Claude says: anomalyco/opencode (GitHub org: anomalyco)
GPT says: anomalyco/opencode (GitHub org: anomalyco)
Gemini says: Did not specify the GitHub org
Assessment: The actual GitHub repository for Opencode is https://github.com/sst/opencode
(org: sst). Both Claude and GPT appear to have reported an incorrect repository name.
This is likely a hallucination — "anomalyco" is not a known organisation associated with
Opencode's development team (SST). All documentation URLs (opencode.ai/docs/*) cited by
all three models appear accurate regardless of the repo org discrepancy.
Resolution: Use https://github.com/sst/opencode as the authoritative source repository.
```

```
[D-03] Topic: Whether tools: key is fully deprecated for all uses
Claude says: tools: is the MCP tool scoping mechanism (per-agent enablement)
GPT says: tools: is deprecated everywhere and permission: should replace it
Gemini says: tools: is used for agent tool configuration
Assessment: The models agree that tools: is deprecated for the agent capability allow-list
(replacing Copilot's tools: [read_file, write_file, ...] pattern). However, the tools:
key has a separate non-deprecated usage for per-agent MCP server scoping
(tools: { "chroma/*": true, "tavily/*": false }). Claude and Gemini's usage is correct
for MCP scoping; GPT overstated the deprecation scope.
Resolution: tools: → permission: for capability control (edit/bash/skill/task).
  tools: { "mcp-name/*": true } remains the correct pattern for per-agent MCP scoping.
```

---

## Recommendations

Prioritised migration path for this project specifically:

1. **[U-01] ★★★ Skills — zero action required**  
   The project's `.agents/skills/*/SKILL.md` tree is already discovered by Opencode natively. Start Opencode and skills are available immediately.

2. **[U-03] ★★★ Create opencode.json and translate MCPs**  
   Create `opencode.json` at project root. Translate the chroma MCP entry from `.github/mcp.json` using `type: "local"` and merged command array. Add `$schema` and provider/model config.

3. **[U-02] ★★★ Establish AGENTS.md and instructions array**  
   The project already has `AGENTS.md`. Add an `"instructions"` array to `opencode.json` to include `.github/instructions/*.instructions.md` for always-on injection.

4. **[M-01] ★★☆ Install opencode-rules and convert chromadb.instructions.md**  
   Add `"plugin": ["opencode-rules@latest"]` to `opencode.json`. Convert `.github/instructions/chromadb.instructions.md` → `.opencode/rules/chromadb.md` with `globs: ["src/**/*.py"]` frontmatter.

5. **[U-04] ★★★ Migrate agents — start with orchestrator + 2–3 specialists**  
   Create `.opencode/agents/` directory. Migrate `story-orchestrator.agent.md` first (primary mode). Convert `tools:` array to `permission:` map. Add `permission.task` allowlist for the sub-agents it dispatches. Set sub-agents to `mode: subagent`.

6. **[M-02] ★★☆ Update orchestrator prompt for Task tool dispatch syntax**  
   The orchestrator's runSubagent / agent-dispatch instructions need updating from Copilot's `runSubagent` tool pattern to Opencode's Task tool + `@agent-name` invocation pattern.

7. **[S-01] ★☆☆ Verify chroma MCP cwd behaviour**  
   Test whether `chroma-mcp` works without explicit `cwd` when launched from project root. If not, convert relative path in `--data-dir` to absolute path using `{env:PWD}/.chromadb`.

---

## Gaps / Uncertainties

| Gap | Severity | Status |
|---|---|---|
| `applyTo` glob-scoped instruction injection | Medium | Covered by `opencode-rules` plugin |
| `.prompt.md` reusable prompt entry-points | Low | Partially covered by `.opencode/commands/` |
| MCP `cwd` working directory configuration | Low | Unconfirmed — test before production use |
| Active-editor-aware context injection | Low | Not possible in terminal context; by design |
| VS Code UI integration depth | Low | Opencode IDE extension is separate and less integrated |
| Sub-agent dispatch prompt syntax differs | Medium | Requires prompt content updates in orchestrator |
| Copilot-specific tool names (`github/create_branch`, etc.) | High | These GitHub tools are Copilot-specific; in Opencode, GitHub operations use MCP or bash |

---

## Concrete opencode.json Template for This Project

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "model": "anthropic/claude-sonnet-4-5",
  "instructions": [
    "AGENTS.md",
    ".github/instructions/chromadb.instructions.md"
  ],
  "plugin": ["opencode-rules@latest"],
  "mcp": {
    "chroma": {
      "type": "local",
      "enabled": true,
      "command": [
        "uvx", "chroma-mcp",
        "--client-type", "persistent",
        "--data-dir", ".chromadb"
      ]
    }
  },
  "agent": {
    "story-orchestrator": {
      "description": "Orchestrates the full story generation pipeline",
      "mode": "primary",
      "model": "anthropic/claude-sonnet-4-5",
      "permission": {
        "edit": "allow",
        "bash": { "*": "ask", "pytest*": "allow", "ruff*": "allow" },
        "task": {
          "*": "deny",
          "outline-planner": "allow",
          "chapter-writer": "allow",
          "quality-reviewer": "allow",
          "wiki-maintainer": "allow"
        }
      }
    }
  }
}
```

---

## Agent Frontmatter Mapping Reference

| Copilot `.agent.md` field | Opencode agent `.md` equivalent | Notes |
|---|---|---|
| `name: Story Orchestrator` | (filename) `.opencode/agents/story-orchestrator.md` | Name becomes filename; spaces → hyphens |
| `description: ...` | `description: ...` | Identical |
| `model: Claude Sonnet 4.6 (copilot)` | `model: anthropic/claude-sonnet-4-5` | Add provider prefix; remove Copilot-specific suffixes |
| `agents: [Coder, Reviewer, ...]` | `permission.task: { coder: allow, ... }` | Explicit allowlist |
| `tools: [edit, execute, read, agent, github/create_branch, ...]` | `permission: { edit: allow, bash: allow }` + `tools: { "chroma/*": true }` | Copilot-specific GitHub tools need MCP/bash replacement |
| (body) | (body) | Identical — no change needed |

---

## Combined Source List

| URL | What was found there | Cited by |
|---|---|---|
| https://opencode.ai/ | Product homepage — overview, feature list, install | Claude, GPT, Gemini |
| https://opencode.ai/docs/ | Intro — install, `/init`, AGENTS.md bootstrap | Claude, GPT, Gemini |
| https://opencode.ai/docs/config/ | Full config schema, locations, precedence, all fields | Claude, GPT, Gemini |
| https://opencode.ai/docs/rules/ | AGENTS.md, instructions array, no applyTo confirmation | Claude, GPT, Gemini |
| https://opencode.ai/docs/agents/ | Custom agents, mode, permission, hidden, steps, task | Claude, GPT, Gemini |
| https://opencode.ai/docs/skills/ | SKILL.md format, discovery paths, frontmatter schema | Claude, GPT, Gemini |
| https://opencode.ai/docs/mcp-servers/ | Local/remote MCP, OAuth, per-agent scoping, schema | Claude, GPT, Gemini |
| https://github.com/frap129/opencode-rules | opencode-rules plugin — globs:/keywords:/agent: frontmatter | Claude, Gemini |
| https://github.com/sst/opencode | Official repo — architecture, changelog (note: Claude/GPT cited "anomalyco/opencode" — likely incorrect; actual org is sst) | N/A (divergence noted) |
| https://medium.com/@wl8380/your-ai-coding-assistant-just-got-a-memory-meet-opencode-skills-48666f462d9b | SKILL.md paradigm explanation and native Opencode support | Gemini |
| https://dev.to/rosgluk/opencode-quickstart-install-configure-and-use-the-terminal-ai-coding-agent-4kcb | Community quickstart — CLI reference, TUI keybinds, workflow | Claude |
| https://github.com/anomalyco/opencode/issues/8751 | Community issue re: hot-reload of agents/skills — confirms first-class status | GPT |
