# Synthesized Research Report: OpenCode Agentic Infrastructure for AI Story Writer Rebuild

**Date:** 2026-04-12
**Research Type:** Multi-model synthesis (Claude Opus 4.6 + GPT 5.4 + Gemini 3.1 Pro)
**Brief:** Investigate OpenCode's agentic infrastructure (agents, skills, MCP, memory/RAG, custom tools, plugins) and assess how the AI Story Writer application (~18k LoC Python/LangChain) could be rebuilt as an agent-driven pseudo-application running inside OpenCode.

---

## Synthesis Overview

All three models independently confirmed that OpenCode is a mature, open-source, terminal-native AI coding agent (GitHub: `anomalyco/opencode`, 100K–140K+ stars) with a rich extensibility surface: custom agents, skills, custom tools, MCP server integration, a plugin system with lifecycle hooks, and an HTTP API with SDK. The models achieved strong consensus that rebuilding the AI Story Writer inside OpenCode is **feasible but requires significant custom infrastructure** — OpenCode provides the shell (orchestration, LLM calls, tool execution) but not the engine (state management, RAG, prompt templates, domain logic). The primary risks are context window exhaustion during long-running generation, non-determinism, and the lack of precedent for applications of this complexity running inside any agentic coding tool.

**Model Agreement Score:** 8/10 — Strong agreement on architecture and capabilities; minor divergences on feasibility assessment and ecosystem depth.

---

## Individual Report Summaries

| Model  | Focus Areas | Unique Finds | Sources Cited |
| ------ | ----------- | ------------ | ------------- |
| Claude | Architecture deep-dive, client/server design, SDK-driven hybrid approach, detailed tradeoff analysis | OpenCode Zen (curated model service); explicit token overhead estimate (3–5x for orchestration); session size limits as gap | 18 |
| GPT    | Founding history (TermAI→OpenCode fork), community ecosystem projects, documented pipeline example, auto-compaction bug | Rick Hightower's "Self-Healing Documentation Pipeline" as concrete example; 5+ community orchestration projects; GitHub issue #8089 (compaction bug); session.fork() for savepoints; Agent Client Protocol (ACP) | 18 |
| Gemini | Practical migration strategy, "orchestration drift" risk, narrative compaction fidelity concern | Orchestration drift warning (agents editing wrong files); narrative compaction harder than code compaction; simplicity emphasis for migration | 4 |

---

## Consensus Findings

### ★★★ Unanimous Findings (All Three Models Agree)

```
[U-01] OpenCode is an open-source, terminal-native AI coding agent with client/server architecture
Confidence: ★★★ Unanimous
Category: Architecture
Detail: OpenCode (anomalyco/opencode, MIT license) is a Go TUI + Bun/TypeScript HTTP server.
It exposes an OpenAPI 3.1 REST API (default port 4096), supports 75+ LLM providers via the
Vercel AI SDK, and runs as a standalone binary — not a VS Code extension, not related to
GitHub Copilot. Desktop app (beta), IDE plugins (VS Code, Neovim, JetBrains), and web UI
also available. Headless mode via `opencode serve` enables programmatic control.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: opencode.ai/docs, github.com/anomalyco/opencode, cefboud.com deep dive, InfoQ article
```

```
[U-02] Agent system supports primary agents, subagents, and custom agents via JSON/Markdown
Confidence: ★★★ Unanimous
Category: Architecture
Detail: Two built-in primary agents (Build: full tools, Plan: read-only/ask). Two built-in
subagents (General: full tools/parallel work, Explore: read-only). Custom agents defined in
opencode.json (JSON) or .opencode/agents/ (Markdown with YAML frontmatter). Configuration:
description (required), model, prompt (supports {file:./path}), temperature, top_p, steps
(max iterations), mode (primary/subagent/all), hidden, color, permission. Subagents invoked
via Task tool, run in child sessions, return results to parent. Sequential and parallel
orchestration supported.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: opencode.ai/docs/agents, opencode.ai/docs/config
```

```
[U-03] Skills are instruction-only Markdown documents, lazy-loaded on demand
Confidence: ★★★ Unanimous
Category: Architecture
Detail: SKILL.md files in .opencode/skills/<name>/ (project), ~/.config/opencode/skills/
(global), or .claude/skills/ (Claude Code compat). YAML frontmatter (name, description,
metadata). Agents see skill names+descriptions via the skill tool, call skill({ name })
to load full content into context. Skills are NOT executable — they provide instructions,
conventions, and prompt templates that guide agent behavior. Naming: lowercase alphanumeric
with hyphens, 1–64 chars.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: opencode.ai/docs/skills
```

```
[U-04] First-class MCP server integration — local and remote
Confidence: ★★★ Unanimous
Category: Architecture
Detail: MCP servers configured in opencode.json under "mcp" key. Local servers specify
command + environment; remote servers specify URL + headers. MCP tools appear alongside
built-in tools transparently. Per-agent control via permission glob patterns. OAuth support
with Dynamic Client Registration (RFC 7591). Custom MCP servers can be created for any
domain-specific functionality (e.g., wrapping ChromaDB for RAG). Warning: MCP tools add
to context token usage.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: opencode.ai/docs/mcp-servers
```

```
[U-05] No built-in RAG, vector store, or persistent cross-session memory
Confidence: ★★★ Unanimous
Category: Architecture
Detail: OpenCode has NO built-in vector store, embedding pipeline, or semantic search.
Cross-session memory must be implemented via: (a) AGENTS.md / instructions for always-loaded
context, (b) skills for lazy-loaded domain knowledge, (c) custom tools or MCP servers
wrapping external stores (ChromaDB, SQLite, PostgreSQL), (d) plugins with lifecycle hooks,
(e) file-system persistence (JSON/Markdown). Session data persists in internal SQLite but
conversation context is limited by model context window. Auto-compaction summarizes
history when nearing limits.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: opencode.ai/docs/plugins, community projects (opencode-supermemory, opencode-mem, hmem)
```

```
[U-06] Custom tools defined in TypeScript/JavaScript, can invoke any language
Confidence: ★★★ Unanimous
Category: Architecture
Detail: Custom tools in .opencode/tools/ (project) or ~/.config/opencode/tools/ (global).
TypeScript files using @opencode-ai/plugin — define description, Zod schema args, async
execute function. Execute can invoke Python scripts, APIs, databases via Bun subprocess.
Context provides agent, sessionID, messageID, directory, worktree. Multiple tools per file
via named exports. This is the primary mechanism for wrapping existing Python pipeline
logic into the agent framework.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: opencode.ai/docs/tools, opencode.ai/docs/custom-tools
```

```
[U-07] File-based JSON state + compaction hooks is the recommended state persistence pattern
Confidence: ★★★ Unanimous
Category: Best Practice
Detail: All three models independently recommend: (a) custom tools that read/write JSON
state files (savepoints, outlines, character sheets, progress tracking), (b) the
experimental.session.compacting plugin hook to inject critical story state into compaction
summaries so it survives context reset, (c) AGENTS.md for bootstrapping context on session
start. This pattern mirrors the JSON manifest approach used in documented multi-agent
pipelines.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: opencode.ai/docs/plugins, Hightower documentation pipeline article
```

```
[U-08] Context window exhaustion is the #1 risk for long-running story generation
Confidence: ★★★ Unanimous
Category: Performance
Detail: Auto-compaction helps but loses detail — narrative nuance, character voice,
plot threading may degrade after compaction. Each pipeline step adds context. With 130
templates, character sheets, outlines, and story text, context fills quickly. Mitigations:
use subagents (each gets fresh context), save intermediate outputs to files, load only
what's needed per step, use compaction hooks for critical state, break work into
per-chapter sessions.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: GitHub issue #8089, arxiv paper on context management, HN discussions
```

```
[U-09] Hybrid approach recommended — agent orchestration + traditional code for complex logic
Confidence: ★★★ Unanimous
Category: Best Practice
Detail: Don't rely solely on LLM orchestration for deterministic pipeline steps. Encode
pipeline order in agent instructions or SDK scripts. Implement complex logic (state
management, savepoint/restore, file orchestration, prompt template rendering) as traditional
code (Python scripts) invoked by custom tools. The agent layer handles coordination,
creative decisions, and natural-language interaction; the tool layer handles deterministic
execution.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: All three models converged on this independently
```

```
[U-10] Start with a minimal prototype — single chapter generation — before scaling
Confidence: ★★★ Unanimous
Category: Best Practice
Detail: All three models recommend validating the architecture with a focused proof-of-concept:
outline generation → character extraction → single scene generation. Create 3–5 custom tools
(load-state, generate-scene, save-state, load-prompt-template, query-rag), one custom
"story-writer" agent, and one skill category. Validate end-to-end before adding the full
130-template pipeline.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: All three models converged on this independently
```

```
[U-11] ~130 prompt templates should use hybrid skill + custom tool approach
Confidence: ★★★ Unanimous
Category: Best Practice
Detail: Loading 130 skills would exhaust context tokens (descriptions alone would be large).
Recommended: (a) group templates into ~10–15 category skills (e.g., "scene-generation",
"character-extraction", "outline-planning") containing related prompts, (b) build a custom
"prompt-loader" tool that reads template files from disk and renders variables, (c) use
agent prompts for role-specific instructions. Templates stored as plain text files in a
prompts/ directory.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: opencode.ai/docs/skills, context window management best practices
```

```
[U-12] Non-determinism and token costs are significant tradeoffs vs traditional architecture
Confidence: ★★★ Unanimous
Category: Performance
Detail: Agent-driven architecture introduces: (a) non-determinism — same prompt may produce
different execution paths, (b) 3–5x token overhead for orchestration compared to direct LLM
calls (Claude's estimate), (c) slower execution — every decision requires LLM inference,
(d) probabilistic error handling vs deterministic try/catch. Benefits: natural language
reconfiguration, interactive human-in-the-loop collaboration, reduced boilerplate code.
The tradeoff favors agent-driven when human collaboration and adaptability are more valuable
than determinism and cost efficiency.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: All three models independently produced tradeoff tables
```

### ★★☆ Majority Findings (Two of Three Models Agree)

```
[M-01] Community orchestration ecosystem provides pipeline infrastructure
Confidence: ★★☆ Majority
Category: Architecture
Detail: Multiple community projects extend OpenCode with orchestration capabilities:
opencode-conductor (protocol-driven workflow automation), micode (structured brainstorm →
plan → implement), @openspoon/subtask2 (granular flow control via commands),
opencode-background-agents (async delegation), opencode-workspace (16-component
multi-agent harness). These could serve as starting points or inspiration for the story
generation pipeline orchestration.
Models: Claude ✗ GPT ✓ Gemini ✓
Dissenting view: Claude did not find or mention these community projects.
Sources: GPT cited multiple GitHub repos; Gemini referenced micode specifically
```

```
[M-02] Plugin system with lifecycle hooks enables deep integration
Confidence: ★★☆ Majority
Category: Architecture
Detail: OpenCode plugins (TypeScript, .opencode/plugins/) provide hooks for tool execution
(before/after), session events (compacting, idle), and can define tools dynamically. The
experimental.session.compacting hook is critical for story state preservation. Plugins can
intercept tool calls for logging/auditing, inject context, and manage cross-session state.
Models: Claude ✓ GPT ✓ Gemini ✗
Dissenting view: Gemini mentioned the compaction hook but didn't detail the broader plugin
system (tool execution hooks, session events, dynamic tool definition).
Sources: opencode.ai/docs/plugins
```

```
[M-03] SDK-driven orchestration provides programmatic control as an alternative
Confidence: ★★☆ Majority
Category: Architecture
Detail: The OpenCode SDK (JS/TS) can create sessions, send messages, collect results, and
manage state entirely outside OpenCode's interactive model. This enables a traditional
script to drive the story generation pipeline while leveraging OpenCode's LLM integration
and tool execution. Tradeoff: full programmatic control but loses interactive agent benefit.
Models: Claude ✓ GPT ✓ Gemini ✗
Dissenting view: Gemini focused on the interactive TUI model and did not explore SDK-driven
orchestration as an alternative.
Sources: opencode.ai/docs/sdk, opencode.ai/docs/server
```

```
[M-04] Custom commands serve as the "UI" for agent-driven applications
Confidence: ★★☆ Majority
Category: Best Practice
Detail: Commands defined in .opencode/commands/ (e.g., /new-story, /continue-chapter,
/regenerate-scene, /savepoint, /restore) provide user-facing entry points. Each command
triggers a specific prompt/workflow combination, creating a CLI-like interface within the
agent environment.
Models: Claude ✗ GPT ✓ Gemini ✓ (implied)
Dissenting view: Claude did not discuss custom commands as an interface pattern.
Sources: opencode.ai/docs/commands
```

### ★☆☆ Singular Findings (Only One Model Reported)

```
[S-01] Session.fork() as savepoint mechanism
Confidence: ★☆☆ Singular
Category: Architecture
Model: GPT
Detail: The SDK supports session.fork({ messageID }) — forking a session at any message to
create a branch point. This could serve as a "savepoint" mechanism, allowing rollback to
any point in the generation process.
Assessment: Likely accurate — GPT cited the SDK docs directly. Not mentioned by others
probably because it's SDK-specific and less obvious for the savepoint use case.
Sources: opencode.ai/docs/sdk
```

```
[S-02] Rick Hightower's "Self-Healing Documentation Pipeline" as precedent
Confidence: ★☆☆ Singular
Category: Best Practice
Model: GPT
Detail: A published Medium article by Rick Hightower describes a multi-agent OpenCode
workflow: Workflow Orchestrator (primary) coordinates specialized subagents for mermaid
extraction, image generation, markdown rebuilding, PDF conversion, and validation. Uses
JSON manifests for pipeline state and validation gates for quality.
Assessment: Likely accurate — GPT cited a specific Medium article URL. This is the most
concrete documented example of a multi-step pipeline running inside OpenCode. Highly
relevant as a pattern, though significantly simpler than the story generation use case.
Sources: medium.com/@richardhightower/opencode-agents-another-path-to-self-healing-documentation-pipelines
```

```
[S-03] Orchestration drift — agents editing files they shouldn't
Confidence: ★☆☆ Singular
Category: Security
Model: Gemini
Detail: Without strict permission configuration, agents left to resolve multi-step story
workflows may attempt to "fix" problems by editing tool files, configuration, or other
system files rather than operating only on story output files. Restrictive agent
configuration (bash: ask, edit restricted to output directories) is essential.
Assessment: This is a valid operational concern based on common agent behavior patterns.
While Claude and GPT didn't flag it explicitly, it follows from the permission system
documentation. Worth encoding in agent definitions.
Sources: General agent behavior patterns, opencode.ai/docs/agents
```

```
[S-04] Narrative compaction is harder than code compaction
Confidence: ★☆☆ Singular
Category: Performance
Model: Gemini
Detail: While OpenCode's compaction works well for coding (summarizing "currently refactoring
component X"), compacting a complex narrative with nuanced character arcs, voice, and plot
threading is fundamentally harder. The compaction prompt may not preserve the subtleties
needed for narrative continuity.
Assessment: This is an insightful and likely correct observation. Creative writing state
has higher information density and more subtle dependencies than code state. This risk
is real and may require more sophisticated compaction hooks than a simple JSON state dump.
Sources: Gemini's own analysis; not from a cited source but logically sound
```

```
[S-05] Token overhead estimated at 3–5x for agent orchestration vs direct LLM calls
Confidence: ★☆☆ Singular
Category: Performance
Model: Claude
Detail: Rough estimate that agent-mediated orchestration costs 3–5x more tokens than direct
LLM calls, because each decision point (which tool to call, how to format arguments, how
to interpret results, what to do next) requires LLM inference.
Assessment: No source cited for this specific multiplier. It's a reasonable estimate based
on the overhead of multi-turn tool-use conversations, but should be validated empirically
for the story generation use case.
Sources: Claude's analysis (no external citation)
```

---

## Divergence Analysis

```
[D-01] Topic: Feasibility assessment
Claude says: "Moderate" feasibility — emphasizes tradeoffs, warns about fighting against
  coding-optimized defaults, recommends considering whether traditional architecture is
  more appropriate for a fully automated pipeline.
GPT says: More optimistic — provides detailed implementation recommendations, cites
  community examples, suggests the building blocks are mature enough.
Gemini says: Most optimistic — "entirely possible to recreate a pipeline app within OpenCode
  via its multi-agent capabilities," emphasizes reduced boilerplate benefits.
Assessment: Claude's moderate assessment is most balanced. The building blocks exist (all
  agree), but the absence of any published example at this scale (130 templates, progressive
  state, multi-chapter generation) means significant risk. GPT's community project citations
  add credibility, but those projects are simpler than the full story generation pipeline.
  Gemini may underestimate the complexity Gap. Resolution: feasible with caveats — prototype
  first, validate architecture before committing to full rebuild.
Resolution: Feasibility is MODERATE. The architecture can work but requires significant
  custom infrastructure and carries risks that don't exist in traditional architectures.
```

```
[D-02] Topic: Community ecosystem depth
Claude says: Minimal mention of community projects.
GPT says: Lists 5+ community orchestration projects (opencode-conductor, micode,
  @openspoon/subtask2, opencode-background-agents, opencode-workspace) plus memory plugins
  (opencode-supermemory, opencode-mem, hmem).
Gemini says: Mentions micode only.
Assessment: GPT found significantly more community ecosystem information. This is likely
  because GPT searched more broadly for community projects. These projects are relevant
  as starting points or patterns. GPT's finding is the most complete.
Resolution: The community ecosystem is richer than Claude and Gemini reported. The
  orchestration projects (especially opencode-conductor and micode) and memory plugins
  (especially hmem and opencode-mem) should be evaluated in the planning phase.
```

```
[D-03] Topic: SDK-driven orchestration as primary vs complementary approach
Claude says: SDK-driven orchestration is a valid primary approach — an external script
  creates sessions, sends prompts, manages state. Loses interactive benefit but gains
  deterministic control.
GPT says: SDK mentioned as complementary to the interactive agent model. Session forking
  as a savepoint mechanism.
Gemini says: Does not discuss SDK-driven approach.
Assessment: Both patterns are valid and serve different use cases. For automated batch
  generation (generate a whole novel), SDK-driven is superior. For interactive co-creation
  (human guides the story), agent-driven is superior. The story writer likely needs both
  modes.
Resolution: Plan for both modes — SDK-driven for batch generation, interactive agent
  for collaborative writing. This dual-mode architecture should be a design goal.
```

```
[D-04] Topic: GitHub star count
Claude says: 95K–120K+
GPT says: 140K
Gemini says: Not specified
Assessment: Minor factual discrepancy. The project is growing rapidly. GPT's count may
  reflect a more recent data point. Not significant for the research conclusions.
Resolution: Use "100K+" as an approximate figure.
```

---

## Recommendations

Prioritized by consensus level, then relevance:

### High Confidence (Unanimous)

1. **[U-09] ★★★ Adopt a hybrid architecture** — Agent orchestration for coordination and creative decisions; traditional Python code (wrapped in custom tools) for deterministic pipeline steps, state management, and prompt template rendering. This is the highest-confidence recommendation across all three models.

2. **[U-10] ★★★ Start with a minimal prototype** — Single chapter generation: outline → character extraction → one scene. 3–5 custom tools, one story-writer agent, one skill category. Validate before scaling.

3. **[U-07] ★★★ Use file-based JSON state + compaction hooks** — Custom tools read/write story state JSON. The `experimental.session.compacting` hook injects critical state into compaction summaries. AGENTS.md bootstraps context on session start.

4. **[U-11] ★★★ Hybrid skill + tool approach for 130 templates** — ~10–15 category skills for discovery; a custom `prompt-loader` tool for precise template loading and rendering. Templates as plain text files in `prompts/`.

5. **[U-06] ★★★ Wrap existing Python logic as custom tools** — Each pipeline step (outline generation, character extraction, scene generation, state management) becomes a TypeScript tool definition that invokes a Python script. Preserve working domain logic; change only the orchestration layer.

6. **[U-04] ★★★ Build a ChromaDB MCP server for RAG** — Wrap the existing RAG/ChromaDB infrastructure as a local MCP server. Agents query it transparently for character/setting/plot context retrieval.

7. **[U-02] ★★★ Define specialized agents for each pipeline phase** — An orchestrator primary agent with focused subagents: `outline-planner`, `character-extractor`, `scene-writer`, `state-manager`. Each has restricted permissions and a focused system prompt.

### Medium Confidence (Majority)

8. **[M-04] ★★☆ Use custom commands as the user interface** — `/new-story`, `/continue`, `/regenerate-scene`, `/savepoint`, `/restore` commands provide a CLI-like interface within the agent environment.

9. **[M-01] ★★☆ Evaluate community orchestration projects** — opencode-conductor and micode may provide pipeline orchestration patterns or usable infrastructure. Evaluate before building from scratch.

10. **[M-03] ★★☆ Plan for dual-mode operation** — SDK-driven for batch/automated generation; interactive agent mode for human-in-the-loop collaborative writing.

### Lower Confidence (Worth Investigating)

11. **[S-01] ★☆☆ Explore session.fork() for savepoints** — May provide a complementary savepoint mechanism alongside file-based checkpoints.

12. **[S-03] ★☆☆ Enforce strict agent permissions** — Prevent orchestration drift by restricting each agent's edit scope to output directories only. Use `permission.edit` and `permission.bash` extensively.

13. **[S-04] ★☆☆ Design narrative-aware compaction** — The compaction hook must go beyond simple JSON state dumps. Preserve character voice notes, active plot threads, foreshadowing elements, and tonal consistency markers. Test compaction quality empirically.

---

## Gaps / Uncertainties

1. **No precedent at this scale.** No published example exists of an application as complex as the AI Story Writer (130 templates, progressive state, multi-chapter generation with character continuity) running inside OpenCode or any similar agentic coding tool. The feasibility assessment is based on capability analysis, not proven patterns.

2. **Narrative compaction fidelity is untested.** Whether the compaction mechanism can preserve the subtleties of creative writing state (character voices, plot threads, tonal shifts) is unknown. This must be tested empirically in the prototype phase.

3. **Auto-compaction has known bugs.** GitHub issue #8089 shows `context_length_exceeded` errors despite auto-compaction being enabled. This is especially concerning for long-running story generation sessions.

4. **Plugin API stability.** The `experimental.session.compacting` hook is explicitly marked experimental. The plugin API may change, potentially breaking the state persistence mechanism.

5. **Token cost modeling.** No tooling exists for estimating the token overhead of agent-mediated workflows vs. direct LLM calls. The 3–5x estimate (Claude) is unverified. Empirical measurement during prototype is essential.

6. **SDK documentation is thin.** Few end-to-end examples of programmatic workflow orchestration via the SDK. The dual-mode operation (recommendation #10) will require exploration.

7. **OpenCode's rapid evolution.** The project is under active development (last docs update: April 7–11, 2026). The `tools` config is already deprecated in favor of `permission`. APIs may change frequently. Pin to a specific version for stability.

8. **Multi-model orchestration in practice.** Using different models for different pipeline steps (e.g., Claude for creative writing, GPT for extraction, local model for classification) is supported per-agent but lacks documented production experience.

---

## Proposed Architecture Sketch

For planning purposes, here is a high-level architecture based on the consensus findings:

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface                        │
│  Custom Commands: /new-story /continue /savepoint etc.   │
│  TUI (interactive) │ SDK script (automated batch)        │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│              Story Orchestrator (Primary Agent)           │
│  Model: claude-opus-4.6 / high-quality creative model    │
│  Prompt: {file:./prompts/orchestrator.txt}               │
│  Permission: task.* = allow, edit = deny                 │
│  Responsibilities: coordinate pipeline, human dialogue   │
└──┬───────┬────────┬────────┬────────┬───────────────────┘
   │       │        │        │        │
   ▼       ▼        ▼        ▼        ▼
┌──────┐┌──────┐┌───────┐┌──────┐┌──────────┐
│Outline││Char- ││Scene  ││State ││RAG       │
│Planner││acter ││Writer ││Mgr   ││Retriever │
│Agent  ││Agent ││Agent  ││Agent ││Agent     │
└──┬───┘└──┬───┘└──┬────┘└──┬───┘└──┬───────┘
   │       │       │        │       │
   ▼       ▼       ▼        ▼       ▼
┌─────────────────────────────────────────────────────────┐
│                    Custom Tools Layer                     │
│  .opencode/tools/                                        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ │
│  │prompt-loader  │ │story-state   │ │generate-scene    │ │
│  │(load+render   │ │(read/write   │ │(invoke Python    │ │
│  │ templates)    │ │ JSON state)  │ │ generation)      │ │
│  └──────────────┘ └──────────────┘ └──────────────────┘ │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ │
│  │extract-chars  │ │savepoint     │ │validate-output   │ │
│  │(character     │ │(checkpoint   │ │(consistency      │ │
│  │ extraction)   │ │ progress)    │ │ checks)          │ │
│  └──────────────┘ └──────────────┘ └──────────────────┘ │
└──────────────────────┬──────────────────────────────────┘
                       │ subprocess calls
                       ▼
┌─────────────────────────────────────────────────────────┐
│            Python Domain Logic (preserved)                │
│  src/generate_scene.py, src/extract_characters.py, etc.  │
│  Reused from current codebase, stripped of LangChain      │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                    External Services                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ │
│  │ChromaDB MCP  │ │Prompt        │ │Story State       │ │
│  │Server (RAG)  │ │Templates     │ │Files (JSON)      │ │
│  └──────────────┘ │(.txt files)  │ └──────────────────┘ │
│                    └──────────────┘                       │
└─────────────────────────────────────────────────────────┘

Skills (.opencode/skills/):
  scene-generation/    — Scene writing conventions, pacing rules
  character-voice/     — Character consistency, dialogue patterns
  world-building/      — Setting descriptions, continuity rules
  story-structure/     — Outline format, chapter structure, plot arcs
  ...10–15 categories covering the 130 templates

Plugin (.opencode/plugins/story-compaction.ts):
  experimental.session.compacting → injects story state JSON
```

---

## Combined Source List

Deduplicated list of all sources cited across all three reports:

- [opencode.ai](https://opencode.ai/) — Official website — cited by: Claude, GPT, Gemini
- [opencode.ai/docs](https://opencode.ai/docs/) — Official documentation (agents, tools, skills, plugins, SDK, MCP, commands, ecosystem) — cited by: Claude, GPT, Gemini
- [github.com/anomalyco/opencode](https://github.com/anomalyco/opencode) — GitHub repository (100K+ stars, MIT) — cited by: Claude, GPT, Gemini
- [ssntpl.com/opencode-open-source-ai-coding-agent-guide](https://ssntpl.com/opencode-open-source-ai-coding-agent-guide/) — Enterprise deployment guide — cited by: Claude, GPT, Gemini
- [cefboud.com/posts/coding-agents-internals-opencode-deepdive](https://cefboud.com/posts/coding-agents-internals-opencode-deepdive/) — Deep technical analysis of internals — cited by: Claude, GPT
- [tembo.io/blog/coding-cli-tools-comparison](https://www.tembo.io/blog/coding-cli-tools-comparison) — 2026 CLI tools comparison — cited by: Claude, GPT
- [morphllm.com/ai-coding-agent](https://www.morphllm.com/ai-coding-agent) — 15 AI coding agents compared — cited by: Claude, GPT
- [innfactory.ai/en/blog/ai-assisted-software-development-with-opencode](https://innfactory.ai/en/blog/ai-assisted-software-development-with-opencode/) — Enterprise adoption case study — cited by: Claude, GPT
- [arxiv.org/html/2603.05344](https://arxiv.org/html/2603.05344v1) — "Building Effective AI Coding Agents for the Terminal" — cited by: Claude, GPT
- [medium.com/@richardhightower/opencode-agents-another-path-to-self-healing-documentation-pipelines](https://medium.com/@richardhightower/opencode-agents-another-path-to-self-healing-documentation-pipelines-51cd74580fc7) — Multi-agent documentation pipeline example — cited by: GPT
- [techfundingnews.com/opencode-the-background-story](https://techfundingnews.com/opencode-the-background-story-on-the-most-popular-open-source-coding-agent-in-the-world/) — Founding story — cited by: GPT
- [infoq.com/news/2026/02/opencode-coding-agent](https://www.infoq.com/news/2026/02/opencode-coding-agent/) — InfoQ technical overview — cited by: GPT
- [truefoundry.com/blog/opencode-token-usage](https://www.truefoundry.com/blog/opencode-token-usage-how-it-works-and-how-to-optimize-it) — Token usage optimization — cited by: GPT
- [supermemory.ai/blog/infinitely-running-stateful-coding-agents](https://supermemory.ai/blog/infinitely-running-stateful-coding-agents/) — Supermemory plugin — cited by: GPT
- [github.com/tickernelz/opencode-mem](https://github.com/tickernelz/opencode-mem) — Community memory plugin — cited by: GPT
- [github.com/anomalyco/opencode/issues/8089](https://github.com/anomalyco/opencode/issues/8089) — Auto-compaction bug report — cited by: GPT
- [news.ycombinator.com/item?id=47103237](https://news.ycombinator.com/item?id=47103237) — hmem hierarchical memory MCP — cited by: Claude, GPT
- [news.ycombinator.com/item?id=44738140](https://news.ycombinator.com/item?id=44738140) — TermAI → OpenCode fork history — cited by: GPT
- [news.ycombinator.com/item?id=47368651](https://news.ycombinator.com/item?id=47368651) — Context window management discussion — cited by: Claude
- [velvetshark.com/openclaw-memory-masterclass](https://velvetshark.com/openclaw-memory-masterclass) — Memory protocol patterns — cited by: Claude
- [linkedin.com/posts/harryjmunro_your-ai-agents-are-dying](https://www.linkedin.com/posts/harryjmunro_your-ai-agents-are-dying-and-you-dont-even-activity-7430629112869871616-TinT) — Context exhaustion patterns — cited by: Claude
- [annjose.com/post/agentic-coding-basics](https://annjose.com/post/agentic-coding-basics/) — MCP/skills taxonomy — cited by: Claude
- [railway.com/agents](https://railway.com/agents) — OpenCode integration — cited by: Claude
- [nxcode.io/resources/news/opencode-vs-claude-code-vs-cursor-2026](https://www.nxcode.io/resources/news/opencode-vs-claude-code-vs-cursor-2026) — Tool comparison — cited by: Gemini
- [augmentcode.com/tools/codex-2-0-vs-cursor-vs-copilot-cli-vs-opencode-which-wins](https://www.augmentcode.com/tools/codex-2-0-vs-cursor-vs-copilot-cli-vs-opencode-which-wins) — Tool comparison — cited by: Gemini
- [pub.towardsai.net/long-context-compaction-for-ai-agents](https://pub.towardsai.net/long-context-compaction-for-ai-agents-part-1-design-principles-2bf4a5748154) — Compaction design principles — cited by: Claude
