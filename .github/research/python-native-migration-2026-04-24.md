# Synthesized Research Report: Python-Native Orchestration Migration

**Research question:** How should the `llm-story-writer` system replace OpenCode (TypeScript/Node.js agent harness) with a Python-native orchestration layer, TUI, and tool execution pipeline?

**Date:** 2026-04-24  
**Models consulted:** Claude Opus 4.6, GPT 5.4, Gemini 3.1 Pro  
**Sources combined:** 50+ URLs across three independent research runs

---

## Synthesis Overview

All three models converged strongly on the TUI choice (Textual, unanimous) and on preserving the existing Python domain architecture. The primary divergence is the orchestration framework: Claude recommends LangGraph; GPT and Gemini recommend plain Python with LangGraph as an optional upgrade path. On the basis of source strength, the architecture of the existing codebase, and the sequential (non-cyclic) nature of story generation, the GPT/Gemini position is better supported. The existing `src/application/services/` layer already implements all domain logic — OpenCode is a harness, not a framework — and the migration should complete that separation rather than introduce a new framework.

**Model Agreement Score: 8/10** — Strong agreement on TUI, LLM client, architecture preservation, and migration steps; meaningful divergence only on whether to adopt LangGraph or use plain Python.

---

## Individual Report Summaries

| Model | Focus Areas | Unique Finds | Sources Cited |
|---|---|---|---|
| Claude | Code-level LangGraph API, `interrupt()` gates, SQLite checkpointer, TUI streaming | `langgraph-supervisor-py`, LangGraph Functional API, `@entrypoint`/`@task` decorators | 22 |
| GPT | Architecture philosophy ("replace a harness, not build a framework"), typed handoff objects, phase-gate abstraction | Incremental migration order, typed pipeline state object as plain JSON, Pydantic AI as leaf-step helper | 24+ |
| Gemini | Pydantic AI + Plain Python combination, clean architecture preservation, Textual reactive UI | Context overload link to VS Code freeze (depth-2 nesting per repo memory), `AsyncOpenAI` + SSE | ~15 |

---

## Consensus Findings

### ★★★ Unanimous Findings (All Three Models Agree)

```
[U-01] Textual is the correct TUI framework
Confidence: ★★★ Unanimous
Category: Architecture
Detail: All three models independently identified Textual as the only viable Python TUI 
option for this use case. The @work(thread=True) + call_from_thread() pattern is the 
confirmed standard for streaming LLM token output into a live-updating widget. Textual's 
CSS grid layout handles multi-panel display (status pane, output pane, approval input). 
Rich objects render natively inside Textual since both share the same author/team. 
Textual v6.x released April 2026 — very active maintenance.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: textual.textualize.io/guide/workers, Textual @work API docs,
         Textual blog post on LLM streaming pattern
```

```
[U-02] OpenAI Python SDK with base_url for LM Studio
Confidence: ★★★ Unanimous
Category: API
Detail: The openai Python SDK supports custom base_url natively. Set api_key to any 
non-empty string (e.g., "lm-studio") since LM Studio does not validate it. Use 
AsyncOpenAI for async/streaming pipelines. All three models confirmed LM Studio's 
official docs explicitly support the OpenAI client redirected to the local endpoint.

  from openai import AsyncOpenAI
  client = AsyncOpenAI(
      base_url="http://127.0.0.1:1234/v1",
      api_key="lm-studio",
      timeout=60.0,
      max_retries=3,
  )

Models: Claude ✓ GPT ✓ Gemini ✓
Sources: lmstudio.ai/docs/app/api/endpoints/openai, openai-python GitHub
```

```
[U-03] TypeScript tool wrappers must be replaced with direct Python imports
Confidence: ★★★ Unanimous
Category: Architecture
Detail: Current flow: TypeScript wrapper → subprocess → src/tools/script.py. New flow: 
Python orchestrator → import src.tools.module → call function directly. This eliminates 
subprocess serialization overhead, the TypeScript maintenance burden, and cross-language 
error handling complexity. The existing src/tools/*.py scripts are already the real 
implementation. All three models agree this is the single most impactful mechanical change.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: Project codebase analysis
```

```
[U-04] Existing Markdown prompt files should be preserved and loaded as system prompts
Confidence: ★★★ Unanimous
Category: Best Practice
Detail: The current .opencode/agents/*.md files contain valuable system prompt content. 
Strip YAML frontmatter (split on "---") and load the body as a plain string. No structural 
changes to Markdown content are required.

  def load_system_prompt(name: str) -> str:
      content = Path(f"prompts/{name}.md").read_text()
      if content.startswith("---"):
          _, _, body = content.split("---", 2)
          return body.strip()
      return content.strip()

Models: Claude ✓ GPT ✓ Gemini ✓
Sources: All three model research runs; YAML frontmatter strip confirmed stable
```

```
[U-05] The existing clean architecture (domain/application/infrastructure) must be preserved
Confidence: ★★★ Unanimous
Category: Architecture
Detail: All three models independently warned that adopting a heavy orchestration framework 
(CrewAI, AG2) would force the existing clean architecture to "contort" to framework patterns. 
The new Python harness should wrap src/application/services/ directly, not re-implement 
story generation logic inside framework nodes, crews, or chat transcripts.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: All three model research runs
```

```
[U-06] Rich is not sufficient alone as the TUI — it is a rendering companion
Confidence: ★★★ Unanimous
Category: Architecture
Detail: Rich provides excellent output formatting but has no interactive event loop, no 
input handling, and no layout engine for full-screen applications. It is the correct 
rendering companion inside Textual (which is built on Rich) but cannot replace OpenCode's 
interactive harness on its own.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: Rich docs, Textual docs, all three model reports
```

```
[U-07] API key must be non-empty for LM Studio via OpenAI SDK
Confidence: ★★★ Unanimous
Category: Compatibility
Detail: The OpenAI Python SDK validates that api_key is a non-empty string even for local 
endpoints. Passing api_key="" will raise a validation error. Pass any non-empty string: 
"lm-studio", "sk-local", or "EMPTY". This applies regardless of which framework wraps 
the SDK call.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: LM Studio docs, openai-python source validation
```

---

### ★★☆ Majority Findings (Two of Three Models Agree)

```
[M-01] Plain Python is the best orchestration layer for this pipeline
Confidence: ★★☆ Majority
Category: Architecture
Detail: GPT and Gemini both argue that the story generation pipeline is fundamentally a 
sequential, deterministic, phase-gated workflow — not a cyclic agent graph. The codebase 
already has JSON state, savepoints, and well-factored services. The migration task is 
"replace a harness," not "build an autonomous agent framework." Plain Python (direct 
service calls, Python state machine, asyncio) is the lowest-risk, best-fit solution.
Models: Claude ✗  GPT ✓  Gemini ✓
Dissenting view: Claude recommends LangGraph primarily for checkpointing and interrupt() 
  approval gates. See Divergence Analysis [D-01].
Sources: GPT and Gemini research runs; architectural reasoning from project context
```

```
[M-02] LangGraph is the best framework IF a framework is adopted
Confidence: ★★☆ Majority
Category: Architecture
Detail: Claude (primary recommendation) and GPT (recommended fallback) both identify 
LangGraph as the strongest framework option when durable, resumable execution is required. 
The langgraph-supervisor-py library provides a create_supervisor() factory that maps 
directly to the existing story-orchestrator → specialist-agent dispatch pattern. 
SqliteSaver checkpointers require no external infrastructure.
Models: Claude ✓  GPT ✓  Gemini ✗
Dissenting view: Gemini recommends Pydantic AI + Plain Python, citing over-engineering risk.
Sources: Claude report (LangGraph supervisor code examples), GPT report (LangGraph as upgrade path)
```

```
[M-03] LangGraph create_react_agent requires function-calling support — risky for quantized models
Confidence: ★★☆ Majority
Category: Compatibility
Detail: LangGraph's prebuilt ReAct agent pattern uses tool-calling format that many smaller 
quantized local models do not support. If the local model does not support tool calling, 
create_react_agent fails. The workaround is plain StateGraph nodes that call tools directly 
in Python. This materially reduces LangGraph's advantage over plain Python for this stack.
Models: Claude ✓  GPT ✓  Gemini ✗
Sources: LangGraph docs, Claude and GPT research runs
```

```
[M-04] CrewAI's embedding subsystem requires explicit local override
Confidence: ★★☆ Majority
Category: Compatibility
Detail: CrewAI's built-in memory/knowledge features default to OpenAI embeddings even 
when the main LLM is local. This requires an explicit CREWAI_EMBEDDINGS_PROVIDER override. 
Since the project already uses ChromaDB via src/infrastructure/, CrewAI's built-in memory 
should be disabled entirely. This adds friction and is a reason to avoid CrewAI as the 
primary harness.
Models: Claude ✓  GPT ✓  Gemini ✗
Sources: CrewAI docs, community forum thread on CrewAI + LM Studio
```

```
[M-05] Typed handoff objects between pipeline phases are better than raw text
Confidence: ★★☆ Majority
Category: Best Practice
Detail: Define structured handoff payload types between pipeline phases (e.g., 
OutlineResult, ChapterPlan, WikiUpdateBatch) rather than passing free-form text or 
accumulated chat histories. This makes savepoints auditable, prevents hidden state 
accumulation, and maps cleanly to Python dataclasses or Pydantic models.
Models: Claude ✗  GPT ✓  Gemini ✓
Sources: GPT and Gemini research runs
```

```
[M-06] AutoGen v0.4 requires explicit model_info dict for non-OpenAI models
Confidence: ★★☆ Majority
Category: Compatibility
Detail: AutoGen v0.4 (AG2) infers model capabilities from model name patterns, which fails 
for local models. The model_info dict with explicit function_calling: True/False is required. 
AutoGen is not recommended as a primary orchestration choice — its group-chat model is 
misaligned with a sequential phase pipeline.
Models: Claude ✓  GPT ✓  Gemini ✗
Sources: AG2 migration docs, vLLM framework integration docs
```

---

### ★☆☆ Singular Findings (Only One Model Reported)

```
[S-01] Pydantic AI as a leaf-step helper for typed structured outputs
Confidence: ★☆☆ Singular
Category: Best Practice
Detail: Pydantic AI is not recommended as the top-level harness, but may be useful as a 
helper library for steps that need guaranteed structured JSON outputs (e.g., parsing 
chapter events, extracting story state changes from LLM responses). It wraps an 
OpenAI-compatible client with Pydantic-validated response schemas.
Model: Gemini (primary); GPT (partial endorsement)
Assessment: Likely accurate for specific structured-output use cases in src/domain/. 
  Worth evaluating after the core migration is stable. Not required for Phase 1.
Sources: ai.pydantic.dev/models/openai
```

```
[S-02] LangGraph Functional API (@entrypoint / @task) for sequential flows
Confidence: ★☆☆ Singular
Category: API
Detail: Claude found a LangGraph "Functional API" using @entrypoint and @task decorators 
for sequential (non-graph) workflows — simpler than the full StateGraph. Still provides 
SqliteSaver checkpointing and interrupt() gates. Represents a middle ground between 
full LangGraph and plain Python.
Model: Claude
Assessment: Plausible per LangGraph docs. Relevant if LangGraph is later adopted. 
  Only one model confirmed — verify stability before relying on it.
Sources: Context7 langgraph-supervisor-py docs
```

```
[S-03] textual-web allows the same TUI to run in a browser
Confidence: ★☆☆ Singular
Category: Best Practice
Detail: Textual has an optional textual-web companion that serves the same TUI in a 
browser with no code changes. Not required for the core migration but relevant for 
future remote-access or sharing scenarios.
Model: Claude
Assessment: Accurate per Textual docs. Deferred feature.
Sources: Textual docs
```

---

## Divergence Analysis

```
[D-01] Topic: LangGraph vs. Plain Python as the primary orchestration layer

Claude says: LangGraph with langgraph-supervisor-py is the best fit. The supervisor→subagent 
  dispatch is a direct architectural match. interrupt() provides free approval gates. 
  SqliteSaver replaces the JSON savepoint mechanism.

GPT says: Plain Python is the best overall fit. The pipeline is sequential and the domain 
  logic is already well-factored. Use LangGraph only if durable graph execution becomes 
  a first-class requirement.

Gemini says: Plain Python + Pydantic AI. LangGraph complexity is not warranted. An asyncio 
  approval gate is simpler than interrupt() + Command(resume=...).

Assessment: GPT and Gemini have the stronger argument. Three factors favor plain Python:
  (1) The story pipeline is sequential and non-cyclic — graph semantics are unnecessary.
  (2) The codebase already has JSON savepoints, state management, and ChromaDB — replacing 
      these with LangGraph checkpointers would be scope creep.
  (3) LangGraph's ReAct pattern requires reliable function-calling support; quantized 
      local models like Gemma-4 may not provide this consistently. Falling back to plain 
      StateGraph nodes removes LangGraph's primary advantage.
  Claude's case for LangGraph is strongest at approval gates and checkpointing, but both 
  are achievable with plain Python asyncio and the existing savepoint system.

Resolution: Start with plain Python orchestration. Document the LangGraph Functional API 
  (@entrypoint / @task) as a deferred upgrade path if durable resumable execution is 
  later required.
```

```
[D-02] Topic: Whether LangChain adds value as a layer above the OpenAI SDK

Claude says: LangChain's ChatOpenAI wrapper is the primary interface for LangGraph nodes.
GPT says: LangChain is "too broad" — warns that provider-specific non-standard fields from 
  third-party OpenAI-compatible servers may not be preserved.
Gemini says: Does not recommend LangChain — prefers direct OpenAI SDK.

Assessment: GPT and Gemini are more conservative and better supported. The OpenAI SDK's 
  base_url support is first-class and LM Studio is explicitly documented to work with it. 
  LangChain is an unnecessary layer unless LangGraph is adopted (where it becomes a 
  transitive dependency automatically).

Resolution: Use OpenAI Python SDK directly. If LangGraph is later adopted, LangChain 
  becomes a transitive dependency automatically — no explicit dependency needed.
```

---

## Recommendations

```
Priority 1 — Immediate, unblocks everything else

1. [U-03] ★★★  Replace all TypeScript tool wrappers with direct Python imports.
   Delete .opencode/tools/*.ts. Call src/tools/*.py functions directly from 
   the Python orchestrator.

Priority 2 — Core architecture

2. [U-01] ★★★  Use Textual as the TUI framework.
   Build Textual App shell with @work(thread=True) workers, RichLog streaming 
   panel, Input widget for approval gates, CSS grid multi-panel layout.

3. [U-02] ★★★  Use AsyncOpenAI(base_url=..., api_key="lm-studio") as the LLM client.
   Wire into existing src/infrastructure/providers/ abstraction layer.

4. [M-01] ★★☆  Use plain Python as the orchestration layer.
   Each OpenCode agent → Python class or async function. Pipeline phases are 
   sequential Python. Approval gates are asyncio awaits. State reuses existing 
   JSON savepoint system.

Priority 3 — Quality and correctness

5. [U-04] ★★★  Preserve all .opencode/agents/*.md prompt files.
   Relocate to prompts/agents/. Load with pathlib + frontmatter stripping at 
   startup. No content changes required.

6. [U-05] ★★★  Wrap existing src/application/services/ from the new orchestrator.
   Do not re-implement domain logic. The orchestrator coordinates — it does not 
   compute.

7. [M-05] ★★☆  Define typed handoff objects (dataclasses or Pydantic models) 
   between pipeline phases. Prevents hidden state accumulation; makes savepoints 
   auditable.

Priority 4 — Deferred

8. [S-01] ★☆☆  Evaluate Pydantic AI for leaf-step structured output parsing 
   after core migration is stable.

9. [M-02] ★★☆  Document LangGraph (@entrypoint / @task Functional API) as an 
   upgrade path if durable resumable execution becomes a first-class requirement.
```

---

## Proposed Migration Phases

### Phase 1 — Remove TypeScript layer
- Replace `.opencode/tools/*.ts` wrappers with direct Python imports of `src/tools/*.py`
- Remove `.opencode/` directory, `opencode.json`, TypeScript package files
- Verify existing pytest unit tests still pass (domain logic is unchanged)
- Update `pyproject.toml` as the unified entry point

### Phase 2 — Build Python pipeline runner (headless first)
- Create `src/presentation/pipeline.py` (or `src/presentation/orchestrator.py`)
- Model each OpenCode agent as a Python async class/function
- Pipeline phases are sequential async calls into `src/application/services/`
- Implement typed handoff objects (`OutlineResult`, `ChapterPlan`, etc.)
- Wire `AsyncOpenAI` client into `src/infrastructure/providers/`
- Load agent system prompts from `prompts/agents/` at startup
- Implement approval gate as `asyncio.Event` or simple `input()` prompt
- Validate headless pipeline runs correctly before adding TUI

### Phase 3 — Build Textual TUI
- Create `src/presentation/tui.py` with `textual.App` subclass
- Layout: left panel = pipeline phase progress, center = streaming LLM output (`RichLog`), footer = approval input
- `@work(thread=True)` worker invokes pipeline synchronous stream; forwards token deltas via `call_from_thread()`
- Approval gates: mount `Input` widget, await `Input.Submitted`, resume pipeline worker
- Wire Textual app as the entry point: `python -m src.presentation.tui`

### Phase 4 — Pin versions and clean up
- Pin `textual>=6.0,<7.0`, `openai>=1.0`, `pydantic>=2.0`
- Remove all OpenCode/Node.js references from README, docs, config
- Update `AGENTS.md` with new stack
- Run full `pytest` suite, `ruff check --fix .`, `mypy src/`

---

## Gaps / Uncertainties

- **Function-calling reliability of Gemma-4 26B with local quantized formats.** LangGraph's ReAct agent and most framework "tool calling" patterns depend on reliable function-call formatted responses. Not validated for `gemma-4-26b-a4b-it-heretic-guff`. If function calling is unreliable, all framework-level tool dispatch must fall back to plain Python — making plain Python the default-safe choice regardless.
- **LangGraph Functional API stability.** Only one model confirmed `@entrypoint` / `@task` decorators. Verify currency and stability before relying on it.
- **Pydantic AI multi-agent patterns.** Known GitHub issues with tool strictness on OpenAI-compatible servers. Validate against LM Studio before adopting for tool-calling steps.
- **Textual v6 breaking changes.** Pin to `textual>=6.0,<7.0` and review the v6 migration guide before building.
- **AsyncSqliteSaver requirement.** If LangGraph is adopted, use `AsyncSqliteSaver` (not `SqliteSaver`) in async contexts to avoid blocking the event loop.

---

## Combined Source List

- https://textual.textualize.io/guide/workers/ — Textual @work worker pattern — Claude, GPT, Gemini
- https://textual.textualize.io/blog/2024/09/15/anatomy-of-a-textual-user-interface — Textual author's LLM streaming TUI blog post — Claude
- https://textual.textualize.io/widget_gallery/ — Full widget reference — GPT
- https://textual.textualize.io/how-to/design-a-layout/ — CSS grid layout — GPT
- https://lmstudio.ai/docs/app/api/endpoints/openai — LM Studio OpenAI-compat endpoint official docs — Claude, GPT, Gemini
- https://github.com/openai/openai-python — OpenAI Python SDK; base_url, AsyncOpenAI, retry — GPT, Gemini
- https://github.com/langchain-ai/langgraph — LangGraph (30.1k stars, active Apr 2026) — GPT
- https://github.com/langchain-ai/langgraph-supervisor-py — create_supervisor() API — Claude
- https://docs.langchain.com/oss/python/langgraph/persistence — LangGraph checkpointing — Claude, GPT
- https://docs.crewai.com/en/learn/llm-connections — CrewAI + LM Studio local LLM — Claude, GPT
- https://community.crewai.com/t/how-to-set-lm-studio-as-the-llm-provider-in-crewai/1798 — CrewAI LM Studio community thread — Claude
- https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/migration-guide.html — AutoGen v0.4 migration — GPT
- https://docs.ag2.ai/latest/ — AG2 official docs — GPT
- https://ai.pydantic.dev/models/openai/ — PydanticAI OpenAI provider with base_url — Claude, Gemini
- https://ai.pydantic.dev/multi-agent-applications/ — PydanticAI multi-agent patterns — GPT
- https://github.com/pydantic/pydantic-ai/issues/1561 — PydanticAI tool strictness edge case — GPT
- https://python-prompt-toolkit.readthedocs.io/en/stable/pages/full_screen_apps.html — Prompt Toolkit full-screen — GPT
- https://newsletter.victordibia.com/p/autogen-vs-crewai-vs-langgraph-vs — 10-dimension framework comparison — Claude
- https://langwatch.ai/blog/best-ai-agent-frameworks-in-2025-comparing-langgraph-dspy-crewai-agno-and-more — Production framework evaluation — Claude
- https://atlan.com/know/best-ai-agent-harness-tools-2026/ — Harness tools comparison 2026 — Claude
- https://python.plainenglish.io/autogen-vs-crewai-vs-langgraph-2026-comparison-guide-fd8490397977 — 2026 comparison guide — Claude
