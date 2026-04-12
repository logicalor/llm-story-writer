# ADR 001: Hybrid Agent-Tool Architecture for Story Generation

**Date:** 2026-04-12
**Status:** Proposed

## Context

The AI Story Writer is being migrated from a monolithic Python pipeline to an OpenCode agentic architecture. The key architectural decision is how to distribute responsibility between the agent layer (LLM-driven orchestration) and the tool layer (deterministic code execution).

Three approaches were considered:

1. **Pure agent** — The agent receives prompt templates and generates everything through conversation, with minimal tools (just file I/O). Simple but non-deterministic, high token overhead, and loses pipeline control.

2. **Pure tool** — The agent is thin; a Python orchestrator drives the pipeline by calling tools in a fixed order. Deterministic but defeats the purpose of the migration — no interactive steering, no natural language reconfiguration.

3. **Hybrid** — Agents handle coordination, creative decisions, and human interaction. Tools handle deterministic operations (prompt loading, state I/O, embedding, critique parsing). The agent decides *when* and *what*; the tool executes *how*.

## Decision

Adopt the **hybrid approach** (option 3).

**Agent responsibilities:**
- Pipeline phase sequencing and transition decisions
- Human interaction (approval gates, steering, feedback)
- Creative quality judgments (when to stop revising, which critique to prioritize)
- Context assembly decisions (which character sheets are relevant for this scene)
- Error recovery and adaptation (if a scene fails quality, decide whether to regenerate or revise)

**Tool responsibilities:**
- Prompt template loading and variable substitution (deterministic)
- File I/O: story state, savepoints, character/setting sheets (deterministic)
- Token counting and context budget enforcement (deterministic)
- Critique score parsing and threshold comparison (deterministic)
- RAG embedding and retrieval (deterministic query, semantic ranking)
- Content chunking (deterministic)

**Boundary rule:** If an operation has a single correct output for a given input, it's a tool. If an operation requires judgment, creativity, or human-like decision-making, it's an agent responsibility.

## Consequences

### Positive

- Agents gain interactive steering without losing pipeline reliability
- Tools are independently testable with deterministic inputs/outputs
- Pipeline steps can be reordered by changing agent instructions, not code
- Token overhead is bounded — agents make decisions, tools do the heavy lifting
- Existing Python domain logic is preserved in tools, reducing migration risk

### Negative

- Two implementation languages (TypeScript for tool definitions, Python for logic) add complexity
- Tool interface design requires careful consideration of granularity — too fine-grained means too many agent decisions, too coarse means the agent can't steer
- Local LLM reliability for tool-use sequences is unproven at this pipeline complexity

### Neutral

- The hybrid pattern is well-documented in the OpenCode ecosystem (cf. Hightower pipeline)
- The 65536-token context window is sufficient for the hybrid approach because state lives in files, not in conversation
