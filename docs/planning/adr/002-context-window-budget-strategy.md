# ADR 002: Context Window Budget Strategy for 65536-Token Limit

**Date:** 2026-04-12
**Status:** Proposed

## Context

The deployment target uses local LLMs with a 65536-token context window. The story generation pipeline involves multiple types of context that must coexist within this budget:

- Agent system prompt (~1500 tokens)
- Tool/skill descriptions (~2000 tokens)
- Conversation history (variable, grows over session)
- Story state context (outline, character sheets, settings, recaps — potentially 100k+ tokens for a full novel)
- Prompt template content (1k-5k tokens per template)
- Generated output (variable)

Without active management, context exhaustion is inevitable during multi-chapter generation.

## Decision

Implement a **selective loading** strategy with explicit token budgets per context category, enforced by the Python tool layer rather than relying on the agent to self-regulate.

**Budget allocation per tool call:**

| Category | Budget | Notes |
|----------|--------|-------|
| System overhead (prompt + tools) | ~4000 tokens | Fixed, unavoidable |
| Story context (loaded by tool) | ~25000 tokens | Chapter outline + relevant sheets + recap |
| Prompt template | ~5000 tokens | Rendered template with variables |
| Input (previous content, if revision) | ~15000 tokens | Truncated/compacted if needed |
| Reserved for generation output | ~16000 tokens | Model output space |
| **Total** | **~65000 tokens** | |

**Enforcement mechanism:**
1. Tools that load context (character sheets, recaps, outlines) accept a `max_tokens` parameter
2. Tools return abridged/compacted versions when full content exceeds the budget
3. The `context-budgeting` skill instructs agents to request abridged versions by default
4. The scene-writer tool assembles context and verifies total token count before returning

**Token counting:** Use `tiktoken` (cl100k_base encoding) as an approximation for local models. The exact tokenizer varies by model, but cl100k_base provides a reasonable upper bound for planning purposes.

**Subagent isolation:** Each subagent invocation gets a fresh context window. The orchestrator delegates to subagents precisely to avoid context accumulation across chapters.

## Consequences

### Positive

- Context exhaustion is prevented by design, not by hope
- Each pipeline step has a documented and verifiable token budget
- Abridged content loading is deterministic and testable
- Subagent delegation naturally provides context isolation

### Negative

- Abridged character/setting sheets lose detail — the agent sees a summary, not the full sheet
- Token counting with cl100k_base is approximate; some models may tokenize differently by ~10-15%
- Maximum tokens available for generation output (~16k) constrains scene length

### Neutral

- The compaction plugin provides a safety net for the orchestrator's conversation history
- Progressive recap compaction (already implemented in the current pipeline) naturally produces context-efficient summaries
