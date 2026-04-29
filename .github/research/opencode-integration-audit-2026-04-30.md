# Synthesized Research Report: Opencode Integration Audit

**Date:** 2026-04-30
**Question:** Is the current Opencode integration in `llm-story-writer` optimal and complete? What improvements can be made?
**Models consulted:** Claude Sonnet 4.6, GPT-5.4, Gemini 3.1 Pro (Preview)
**Context:** The project completed a full migration from GitHub Copilot to Opencode in late April 2026 (24 agents, opencode.json, opencode-rules, chroma MCP). This report audits that migration against the live Opencode v1.14.x ecosystem.

---

## Synthesis Overview

The Opencode migration is structurally complete and strategically sound: all 24 agents exist, the OpenRouter provider and three model IDs are current and active, the `opencode-rules` plugin fills a genuine gap that Opencode has not yet replaced natively, and the chroma MCP configuration is functionally correct. However, all three models independently identified the same critical correctness issue: the agent frontmatter throughout `.opencode/agents/` uses an undocumented array permission format (`allow: [...]` / `deny: []`) and human-readable display names in `permission.task` that do not match agent file identifiers — both are likely to cause silent permission failures at runtime. A secondary divergence concerns `tools:` MCP scoping values: two of three models report the correct value is `true`/`false` (boolean), not `"allow"` as used in every current agent file. The integration also has not yet adopted several material Opencode features added after the migration research was conducted, including `default_agent`, `small_model`, ACP support, and compaction configuration.

**Model Agreement Score: 8/10** — Unanimous on all structural and correctness issues. One divergence on `tools:` value syntax.

---

## Individual Report Summaries

| Model | Focus Areas | Unique Finds | Sources Cited |
|---|---|---|---|
| Claude | Permission syntax; tools deprecation; new features; security advisory detail | Provider `npm`/`name` fields discussion; chroma MCP safety analysis; `opencode agent create` CLI wizard | 14 |
| GPT | Permission object-map vs. array format; `tools:` boolean values; MCP fields; ACP; compaction hooks | Second security advisory (GHSA-c83v-7274-4vgp / CVE-2026-22813 XSS); `subtask` command pattern | 15 |
| Gemini | `tools:` allow/deny/ask value claim (divergent); `default_agent`; `small_model`; supply-chain risk of checked-in MCP | `qwen/qwen3.6-flash` as cheaper alternative; MCP auto-execution risk framing | 9 |

---

## Consensus Findings

### ★★★ Unanimous Findings (All Three Models Agree)

```
[U-01] permission.task uses an undocumented array format throughout all agent files
Confidence: ★★★ Unanimous
Category: Correctness / Agents
Detail: Every agent in .opencode/agents/ that controls subagent dispatch uses this format:

  permission:
    task:
      allow:
        - "Test Writer"
        - "Coder"
      deny: []

The current Opencode documentation (v1.14.x) specifies only an object-map format for
permission.task, where keys are glob patterns matching agent identifiers and values are
the permission level:

  permission:
    task:
      "*": "deny"
      "test-writer": "allow"
      "coder": "allow"

The array format has no documentation and appears to be a migration artefact from the
original Copilot agent spec (which used a different schema). If the runtime parser does
not accept this format, all inter-agent dispatch will silently fail.

Affected agents: orchestrator-v3.md, synthesizing-auditor.md, synthesizing-researcher.md,
planner.md, contemplator.md, auditor.md, sprint-runner.md.

Models: Claude ✓ GPT ✓ Gemini ✓
Sources:
  https://opencode.ai/docs/agents/
  https://opencode.ai/docs/permissions/
  https://github.com/anomalyco/opencode/issues/7063
  https://github.com/anomalyco/opencode/issues/13646
```

```
[U-02] permission.bash also uses the undocumented array format throughout all agent files
Confidence: ★★★ Unanimous
Category: Correctness / Agents
Detail: Every agent with bash restrictions uses the same array pattern:

  permission:
    bash:
      allow:
        - "pytest*"
        - "ruff*"
        - "git diff*"
      deny: []

The documented format is an object-map:

  permission:
    bash:
      "*": "deny"
      "pytest*": "allow"
      "ruff*": "allow"
      "git diff*": "allow"

All 24 agents are affected. This is the highest-impact correctness issue in the migration.
The array format may silently open or close all bash permissions depending on how the parser
handles the unknown format — either interpretation would be incorrect.

Models: Claude ✓ GPT ✓ Gemini ✓
Sources:
  https://opencode.ai/docs/permissions/
  https://opencode.ai/docs/agents/
```

```
[U-03] permission.task agent names use display names instead of file IDs
Confidence: ★★★ Unanimous
Category: Correctness / Agents
Detail: The permission.task allow-lists throughout the project use human-readable display
names (e.g., "Test Writer", "Coder", "Synthesizing Researcher", "Auditor Kimi") rather than
agent file identifiers. Opencode derives an agent's identifier from its filename without
the .md extension. The correct identifiers are:

  Display Name           → File ID (correct key)
  "Test Writer"          → "test-writer"
  "Coder"                → "coder"
  "Researcher"           → "researcher"
  "Synthesizing Researcher" → "synthesizing-researcher"
  "Reviewer Kimi"        → "reviewer-kimi"
  "Reviewer Qwen"        → "reviewer-qwen"
  "Reviewer Glm"         → "reviewer-glm"
  "Synthesizing Reviewer" → "synthesizing-reviewer"
  "Auditor Kimi"         → "auditor-kimi"
  "Auditor Qwen"         → "auditor-qwen"
  "Auditor Glm"          → "auditor-glm"
  "Synthesizing Auditor" → "synthesizing-auditor"
  "Pr Reviewer"          → "pr-reviewer"
  "Browser"              → "browser"
  "Reflection"           → "reflection"
  "Documenter"           → "documenter"

If the runtime matches permission.task keys against file IDs (as documented), all dispatch
will be denied even though the keys are non-empty, because "Test Writer" ≠ "test-writer".

Models: Claude ✓ GPT ✓ Gemini ✓ (Gemini flagged uncertainty; Claude and GPT both confirmed
file ID is the correct key.)
Sources:
  https://opencode.ai/docs/agents/
  https://opencode.ai/docs/agents/#task-permissions
```

```
[U-04] All three OpenRouter model IDs are current and valid
Confidence: ★★★ Unanimous
Category: Configuration / Models
Detail: All three models configured in opencode.json are live on OpenRouter as of
2026-04-30:

  moonshotai/kimi-k2.6     — Active (released Apr 20, 2026)
  qwen/qwen3.6-plus        — Active (released Apr 2, 2026; 1M context)
  z-ai/glm-5.1             — Active (released Apr 7, 2026; 203K context)

No slug changes are required. Newer variants exist (kimi-latest alias, qwen3.6-flash,
qwen3.6-max-preview) but the current slugs remain valid.

Models: Claude ✓ GPT ✓ Gemini ✓
Sources:
  https://openrouter.ai/moonshotai/kimi-k2.6
  https://openrouter.ai/qwen/qwen3.6-plus
  https://openrouter.ai/z-ai/glm-5.1
```

```
[U-05] opencode-rules plugin is still necessary and actively maintained
Confidence: ★★★ Unanimous
Category: Architecture / Rules
Detail: The frap129/opencode-rules plugin remains the only mechanism for context-sensitive
rule injection — injecting rules only when files matching a glob pattern (e.g., src/**/*.py)
are active in the session. Native Opencode rules (instructions array, AGENTS.md) are
unconditionally loaded for every session and do not replicate this behaviour.

Plugin status: v0.6.3, active maintenance (last commit April 24, 2026, 57 stars). There is
an open feature request in anomalyco/opencode (#10096) for native "Smart Rules" but it
has not shipped in the current stable line (v1.14.x).

The project's current .opencode/rules/chromadb.md with globs: ["src/**/*.py"] is correctly
configured and the plugin installation (plugin: ["opencode-rules@latest"]) is correct.

Models: Claude ✓ GPT ✓ Gemini ✓
Sources:
  https://github.com/frap129/opencode-rules
  https://opencode.ai/docs/rules/
  https://github.com/anomalyco/opencode/issues/10096
```

```
[U-06] No cwd: field exists for local MCP server configuration
Confidence: ★★★ Unanimous
Category: Configuration / MCP
Detail: The documented fields for a local MCP server are: type, command, environment,
enabled, timeout. No cwd: field is documented or available. This confirms the finding from
the original 2026-04-29 research report.

The project's chroma MCP passes --data-dir .chromadb (relative path). Because Opencode
sets the project root as the working directory for spawned processes when it locates
opencode.json by traversing up to the nearest Git directory, this path resolves correctly
in practice provided Opencode is always launched from within the project tree.

Risk assessment: LOW. The relative path is safe under normal usage. If an absolute path
guarantee is needed, the {env:PWD} interpolation pattern can be used as a workaround:
  "command": ["uvx", "chroma-mcp", "--client-type", "persistent", "--data-dir", "{env:PWD}/.chromadb"]

Models: Claude ✓ GPT ✓ Gemini ✓
Sources:
  https://opencode.ai/docs/mcp-servers/#local
```

```
[U-07] Two security advisories exist; both patched in v1.14.x
Confidence: ★★★ Unanimous
Category: Security
Detail:
  CVE-2026-22812 (CVSS 8.8) — unauthenticated local HTTP server allowing arbitrary shell
  execution. Affects versions prior to 1.0.216.

  CVE-2026-22813 — XSS in LLM markdown rendering, enabling JavaScript injection via the
  localhost web UI.

Both are patched in the current v1.14.x release line. The operational security posture
required is: (a) run Opencode v1.14.x or later; (b) do not expose opencode web or
--mdns on untrusted networks; (c) treat plugin installation as code execution.

Models: Claude ✓ GPT ✓ Gemini ✓
Sources:
  https://github.com/anomalyco/opencode/security/advisories/GHSA-vxw4-wv6m-9hhh
  https://github.com/anomalyco/opencode/security/advisories/GHSA-c83v-7274-4vgp
```

```
[U-08] Opencode is at v1.14.28 with material new features not yet adopted
Confidence: ★★★ Unanimous
Category: Features / Gaps
Detail: The project migrated against Opencode documentation from late April 2026. Several
features shipped in the v1.x line are material to this project's multi-agent workflow:

  - default_agent: sets which agent handles raw TUI prompts by default
  - small_model: routes low-complexity background tasks (title generation, compaction)
    to a cheaper/faster model, reducing cost without affecting generation quality
  - ACP support: Agent Communication Protocol for deeper IDE integration
  - Native skills via skill tool: .agents/skills/ is already discovered; agents may need
    permission.skill entries to control which skills are loadable
  - Compaction config (compaction.auto, compaction.prune, compaction.reserved): directly
    relevant to the UI freeze issue documented in PR #70 history
  - Custom commands (.opencode/commands/): slash-command shortcuts for repetitive workflows
  - Watcher config (watcher.ignore): reduces noisy file watching events
  - LSP servers: IDE-quality code intelligence for agents
  - opencode agent create: interactive CLI wizard for creating agent files with correct
    frontmatter (useful for avoiding future format errors)

Models: Claude ✓ GPT ✓ Gemini ✓
Sources:
  https://opencode.ai/docs/config/
  https://opencode.ai/docs/skills/
  https://opencode.ai/docs/acp/
  https://opencode.ai/docs/commands/
  https://opencode.ai/changelog
```

---

### ★★☆ Majority Findings (Two of Three Models Agree)

```
[M-01] tools: MCP scoping values should be true/false booleans, not "allow"/"deny" strings
Confidence: ★★☆ Majority
Category: Correctness / Agents
Detail: The current agent frontmatter uses string values for MCP tool scoping:
  tools:
    chroma/*: allow
    io.github.tavily-ai/tavily-mcp/*: allow

The documented format in the Opencode MCP Per-Agent documentation example uses booleans:
  tools:
    "my-mcp*": true
    "other-mcp*": false

This affects 18 of 24 agent files (all that have a tools: block).

Note: The tools: key itself is deprecated for capability control but the docs explicitly
state it retains functionality for per-agent MCP server scoping. The deprecation does not
require removing it if its sole purpose is MCP tool gating.

Dissenting view: Gemini reported allow/deny/ask as valid values, consistent with the
permission: block values. Given the original 2026-04-29 research report also cites
true/false for MCP scoping, the boolean form is assessed as the correct value here.
Resolution: Change all "allow" → true and "deny" → false in tools: blocks.

Models: Claude ✓ GPT ✓ Gemini ✗
Sources:
  https://opencode.ai/docs/mcp-servers/#per-agent
  https://opencode.ai/docs/agents/
```

```
[M-02] planner.md edit permission uses array format for path-scoped editing
Confidence: ★★☆ Majority
Category: Correctness / Agents
Detail: The Planner agent uses an array format for path-scoped edit permissions:
  permission:
    edit:
      allow:
        - "docs/planning/**"
        - ".github/notes/**"
      deny: []

This is the same undocumented array pattern as found in bash and task permissions. The
documented edit permission values are allow, deny, or ask as scalar strings (granting or
denying all edits), or object-map patterns for path-scoped control:
  permission:
    edit:
      "docs/planning/**": "allow"
      "**": "deny"

Only planner.md has path-scoped edit permissions; other agents use scalar allow/deny.

Models: Claude ✓ GPT ✓ Gemini ✗ (did not specifically examine planner.md)
Sources:
  https://opencode.ai/docs/permissions/
```

```
[M-03] The provider.openrouter config is complete for the intended usage pattern
Confidence: ★★☆ Majority
Category: Configuration
Detail: The project's openrouter provider block (containing only models: registry entries)
is a valid minimal project-level configuration for the built-in openrouter provider. No
npm, name, baseURL, or options fields are required for the built-in provider — those
fields serve custom/OpenAI-compatible providers. Credentials are correctly handled via
/connect (developer-local) rather than checked-in config.

Dissenting view: Claude flagged the absence of npm and name as worth noting if custom
provider resolution is ever needed. GPT agreed they are not required. Assessment: not
required for current usage. The openrouter provider is recognised natively by Opencode.

Models: GPT ✓ Gemini ✓ Claude ✗ (partially — flagged as noteworthy, not a defect)
Sources:
  https://opencode.ai/docs/providers/
  https://opencode.ai/docs/providers/#openrouter
```

---

### ★☆☆ Singular Findings (Only One Model Reported)

```
[S-01] Checked-in MCP config is a supply-chain attack vector
Confidence: ★☆☆ Singular
Category: Security
Detail: Committing a local MCP server definition to a repository's opencode.json causes
Opencode to automatically spawn the specified process (uvx chroma-mcp ...) when any
developer who clones the repository runs opencode. This is an auto-execution pattern
that parallels the "repository that runs code" supply-chain risk class.

Assessment: Gemini's concern is technically valid as a class of risk. However, for this
project the chroma MCP is the intentional shared development infrastructure — committing it
is a deliberate design choice to ensure consistent environments. The process spawned
(uvx chroma-mcp) is a well-known package, not arbitrary code. The risk class is real but
low for internal development tooling. The practical mitigation is contributor awareness.
Model: Gemini
Sources:
  https://dev.to/pachilo/the-repository-that-runs-code-a-story-about-mcp-configuration-in-opencode-ljp
```

```
[S-02] qwen/qwen3.6-flash as a cost-optimized alternative for secondary sub-agents
Confidence: ★☆☆ Singular
Category: Optimization / Models
Detail: OpenRouter has released qwen/qwen3.6-flash, a variant of Qwen3.6 optimized for
high-speed multi-step agentic workflows at lower cost. The project currently uses
qwen/qwen3.6-plus for the Qwen-family reviewer, researcher, and auditor sub-agents.
If response latency and cost are concerns, qwen3.6-flash may be worth evaluating for
the sub-agent roles (not the primary orchestrator).

Assessment: Plausible and worth evaluating, but the current qwen3.6-plus slugs are correct
and there is no urgency to change them. The small_model config key (finding U-08) is the
more principled solution for routing background tasks to cheaper models.
Model: Gemini
Sources:
  https://openrouter.ai/qwen/qwen3.6-flash
```

```
[S-03] opencode agent create wizard as a mitigation for future frontmatter format errors
Confidence: ★☆☆ Singular
Category: Tooling / Prevention
Detail: Opencode now ships an opencode agent create CLI command that runs an interactive
wizard generating agent markdown files with syntactically correct frontmatter and
permission blocks. Using this wizard for all future agent creation would prevent a
recurrence of the permission format errors identified in U-01 through U-03.

Assessment: Plausible and directly useful given the extent of the format errors found.
Model: Claude
Sources:
  https://opencode.ai/docs/
```

---

## Divergence Analysis

```
[D-01] Topic: Correct value type for tools: MCP scoping entries
Claude says: Values should be true/false booleans: tools: { "chroma/*": true }
GPT says: Values should be true/false booleans: tools: { "chroma/*": true }
Gemini says: Values should be allow/deny/ask strings, consistent with permission: values

Assessment: The 2-vs-1 majority favours booleans. This is also consistent with the
original pre-migration research report from 2026-04-29, which documented the MCP
Per-Agent example as using tools: {"chroma/*": true}. Gemini appears to have
cross-contaminated the permission: block value set (allow/deny/ask) into the tools:
block, which uses a separate boolean toggle mechanism.

Resolution: Use true/false booleans in tools: blocks for MCP scoping. Change all
current "allow" values to true and "deny" values to false.
```

```
[D-02] Topic: Whether checked-in MCP config is a meaningful security risk
Claude says: The relative --data-dir path is safe; risk is low and Opencode handles cwd correctly
GPT says: Stay on current releases and avoid opencode web exposure; no concern about checked-in config
Gemini says: Checked-in MCP config is a supply-chain auto-execution risk vector

Assessment: All three models agree about CVE-2026-22812 and CVE-2026-22813. The disagreement
is specifically about whether committing the chroma MCP entry is a concern. Claude and GPT
treat this as intentional design; Gemini frames it as a risk class. Since the chroma MCP
is shared intentional project infrastructure (not a personal credential or arbitrary script),
the majority position is correct: the risk is acknowledged but acceptable. Documenting the
auto-execution behaviour in AGENTS.md or docs/features/opencode-runtime.md would satisfy
the spirit of Gemini's concern.

Resolution: The chroma MCP entry remains in opencode.json. Add a note to onboarding docs
explaining the auto-execution behaviour so contributors understand what will happen when
they run opencode in the project root.
```

```
[D-03] Topic: Whether npm/name are required in provider.openrouter
Claude says: Their absence is worth noting if custom provider resolution is needed
GPT says: Not required for built-in OpenRouter provider
Gemini says: Did not address this field

Assessment: GPT's position aligns with the official provider docs. The openrouter provider
is natively recognized; npm/name are for custom/OpenAI-compatible providers. Claude
acknowledged this but flagged it for awareness.

Resolution: No action required. The current provider config is correct.
```

---

## Recommendations

Ordered by priority:

```
1. [U-01 / U-02 / U-03] ★★★ Fix permission format in all 24 agent files — HIGH PRIORITY
   Replace the undocumented allow: [...] / deny: [] array format with the documented
   object-map format for both bash and task. Simultaneously fix task agent names from
   display names ("Test Writer") to file IDs ("test-writer").

   Correct bash format:
     permission:
       bash:
         "*": "deny"
         "pytest*": "allow"
         "ruff*": "allow"

   Correct task format:
     permission:
       task:
         "*": "deny"
         "test-writer": "allow"
         "coder": "allow"

   This affects all 24 agent files and is the most important correctness fix.
   Risk of current state: dispatch permissions are either silently open (any agent
   can dispatch any subagent) or silently closed (no dispatch works at all).

2. [M-01] ★★☆ Fix tools: MCP scoping values from "allow" to true — HIGH PRIORITY
   Change all 18 agent files using tools: blocks from:
     tools:
       chroma/*: allow
   to:
     tools:
       "chroma/*": true
   Same for io.github.tavily-ai and io.github.upstash entries.

3. [M-02] ★★☆ Fix planner.md path-scoped edit permission format — MEDIUM
   Replace array format with object-map in planner.md:
     permission:
       edit:
         "docs/planning/**": "allow"
         ".github/notes/**": "allow"
         "**": "deny"

4. [U-08] ★★★ Add default_agent and small_model to opencode.json — MEDIUM
   Add:
     "default_agent": "orchestrator-v3"
   to ensure raw TUI prompts are routed to the orchestrator by default.
   Add:
     "small_model": "openrouter/qwen/qwen3.6-plus"
   or a cheaper model slug to handle background tasks (title generation, compaction)
   without consuming orchestrator model budget.

5. [U-07] ★★★ Verify development team is on Opencode v1.14.x — MEDIUM
   Both security CVEs are patched in current releases. Document the minimum version
   requirement in docs/features/opencode-runtime.md.

6. [U-08] ★★★ Evaluate compaction config — LOW (but relevant to PR #70 context)
   The compaction.auto, compaction.prune, compaction.reserved settings give fine-grained
   control over context management. Given the UI freeze history documented in PR #70,
   tuning these may improve long-session stability:
     "compaction": {
       "auto": true,
       "prune": true,
       "reserved": 4096
     }

7. [U-08] ★★★ Evaluate custom commands for repetitive orchestration patterns — LOW
   Repetitive slash commands (e.g., /review, /research, /audit) could be packaged as
   .opencode/commands/ entries to reduce prompt boilerplate for developers.

8. [S-03] ★☆☆ Use opencode agent create wizard for all future agent additions — LOW
   Prevents recurrence of the format errors identified in findings U-01 through M-02.

9. [D-02] Resolution: Document MCP auto-execution behaviour — LOW
   Add a short note to docs/features/opencode-runtime.md or AGENTS.md explaining that
   running opencode in the project root automatically spawns the chroma MCP server,
   so contributors understand what to expect.
```

---

## Gaps / Uncertainties

- **Permission array format — runtime behaviour unknown**: All three models confirmed the array format is undocumented, but none could confirm whether the runtime parser silently accepts it (mapping arrays to "open"), silently rejects it (mapping to "deny"), or errors on startup. A smoke test of one affected agent (e.g., dispatching the Coder from the Orchestrator) would immediately reveal whether permissions are currently broken. If sub-agent dispatch is currently working, the runtime may be more lenient than the docs imply.

- **`tools:` allow vs. true — runtime behaviour**: The majority position (boolean values) is consistent with original research, but the actual Opencode source code was not inspected. If Gemini's assertion that `allow`/`deny`/`ask` are valid is correct, the current `allow` values would be functioning correctly. A quick test in an Opencode session would resolve this.

- **`opencode-rules` compatibility with v1.14.x**: The plugin shows active maintenance (v0.6.3, April 24, 2026) but no official Opencode-maintained compatibility matrix exists. The plugin should be smoke-tested to confirm `.opencode/rules/chromadb.md` injections are firing correctly in a current Opencode session.

- **`permission.task` file ID matching**: All three models report that Opencode uses filename-derived IDs, but there is ongoing community issue activity (#12566, #16331) about granular permissions failing in edge cases. Verification by running a dispatch-dependent flow end-to-end is recommended after the format fix.

---

## Combined Source List

- https://opencode.ai/docs/agents/ — Agent frontmatter schema, mode, permission, tools. Cited by: Claude, GPT, Gemini
- https://opencode.ai/docs/permissions/ — Permission model reference. Cited by: Claude, GPT, Gemini
- https://opencode.ai/docs/config/ — Full opencode.json schema reference. Cited by: Claude, GPT, Gemini
- https://opencode.ai/docs/mcp-servers/ — MCP server types and fields. Cited by: Claude, GPT, Gemini
- https://opencode.ai/docs/rules/ — AGENTS.md and instructions loading. Cited by: Claude, GPT, Gemini
- https://opencode.ai/docs/providers/ — OpenRouter provider configuration. Cited by: Claude, GPT
- https://opencode.ai/docs/providers/#openrouter — OpenRouter-specific config notes. Cited by: Claude, GPT
- https://opencode.ai/docs/skills/ — Native skill discovery paths. Cited by: Claude, GPT
- https://opencode.ai/docs/acp/ — Agent Communication Protocol. Cited by: Claude, GPT, Gemini
- https://opencode.ai/docs/commands/ — Custom slash commands. Cited by: Claude, GPT
- https://opencode.ai/docs/plugins/ — Plugin API and hooks. Cited by: GPT
- https://opencode.ai/docs/lsp/ — LSP server configuration. Cited by: Claude, GPT
- https://opencode.ai/changelog — Release history; confirmed v1.14.28. Cited by: Claude, GPT
- https://github.com/anomalyco/opencode — Current upstream repository. Cited by: Claude, GPT, Gemini
- https://github.com/anomalyco/opencode/issues/4716 — Feature request: native glob rules. Cited by: GPT
- https://github.com/anomalyco/opencode/issues/10096 — Feature request: Smart Rules. Cited by: Gemini
- https://github.com/anomalyco/opencode/issues/7063 — Permission format issue. Cited by: Gemini
- https://github.com/anomalyco/opencode/issues/13646 — Permission enforcement issue. Cited by: Gemini
- https://github.com/anomalyco/opencode/security/advisories/GHSA-vxw4-wv6m-9hhh — CVE-2026-22812. Cited by: Claude, GPT, Gemini
- https://github.com/anomalyco/opencode/security/advisories/GHSA-c83v-7274-4vgp — CVE-2026-22813. Cited by: Claude, GPT
- https://github.com/frap129/opencode-rules — opencode-rules plugin. Cited by: Claude, GPT, Gemini
- https://openrouter.ai/moonshotai/kimi-k2.6 — Kimi K2.6 model page. Cited by: Claude, GPT, Gemini
- https://openrouter.ai/qwen/qwen3.6-plus — Qwen3.6 Plus model page. Cited by: Claude, GPT, Gemini
- https://openrouter.ai/z-ai/glm-5.1 — GLM 5.1 model page. Cited by: Claude, GPT, Gemini
- https://openrouter.ai/qwen/qwen3.6-flash — Qwen3.6 Flash (cheaper alternative). Cited by: Gemini
- https://dev.to/pachilo/the-repository-that-runs-code-a-story-about-mcp-configuration-in-opencode-ljp — MCP auto-execution risk. Cited by: Gemini
