---
name: context-budgeting
description: Token budget strategy and context assembly rules for the 65536-token context window
version: 1.0.0
---

# Context Budgeting Skill

Token budget strategy, context assembly rules, and retrieval pipeline reference for working within the 65536-token context window. Use this skill when assembling pre-generation context, loading story state, or deciding what to include in a generation prompt.

---

## Token Budget Table

Budget allocation per tool call (from ADR 002):

| Category | Budget | Notes |
|----------|--------|-------|
| System overhead (prompt + tools) | ~4000 tokens | Fixed, unavoidable |
| Story context (loaded by tool) | ~25000 tokens | Chapter outline + relevant sheets + recap |
| Prompt template | ~5000 tokens | Rendered template with variables |
| Input (previous content, if revision) | ~15000 tokens | Truncated/compacted if needed |
| Reserved for generation output | ~16000 tokens | Model output space |
| **Total** | **~65000 tokens** | |

Token counting uses `tiktoken` (cl100k_base encoding) as an approximation for local models. The exact tokenizer varies by model, but cl100k_base provides a reasonable upper bound for planning purposes.

---

## Concrete Rules

1. **Use `wiki-snapshot` for scene context** instead of raw file loading. The snapshot tool handles retrieval, scoring, detail level selection, and token budgeting automatically.
2. **Never load more than 3 character wiki pages simultaneously.** Use brief/L2 detail level when loading multiple characters. Only the POV character gets L3.
3. **Always use wiki chapter synopses** instead of full chapter text. Synopses are pre-compacted to ~150 tokens per chapter.
4. **Load only the current chapter outline** (not the full outline). The full outline can exceed 10K tokens for a 30+ chapter novel.
5. **Prefer wiki queries over holding state in conversation.** Each subagent invocation gets a fresh context window — use tools to load what you need rather than accumulating state across turns.

---

## Three-Stage Retrieval Pipeline

The `wiki-snapshot` tool implements a three-stage hybrid retrieval and context assembly pipeline (from ADR 005).

### Stage 1: Hybrid Multi-Tier Retrieval

Four retrieval tiers run sequentially, with results merged via Reciprocal Rank Fusion (RRF):

| Tier | Method | Priority | Signal |
|------|--------|----------|--------|
| T1 | Deterministic entity matching | HIGHEST | Entity name or alias appears in scene outline |
| T2 | Metadata-filtered ChromaDB query | HIGH | Frontmatter fields match (e.g., `type=plot_thread, status=active`) |
| T3 | Semantic vector search | SUPPLEMENTARY | Scene outline embedding ↔ page embedding cosine similarity |
| T4 | Wikilink graph traversal (1-2 hop) | MEDIUM | Pages linked from T1/T2/T3 results (max 5 additional) |

T1 is the foundational tier: the wiki index maintains a complete name → slug mapping (including aliases from frontmatter), enabling O(1) deterministic lookup.

T4 exploits the wiki's existing `[[wikilinks]]` as a lightweight knowledge graph, providing relationship-aware retrieval without the expense of full GraphRAG.

### Composite Scoring Formula

Each retrieved page receives a relevance score:

```
score(p) = 0.35 × entity_match(p)
         + 0.20 × rrf(p)
         + 0.15 × wikilink_proximity(p)
         + 0.10 × semantic_similarity(p)
         + 0.10 × recency(p)
         + 0.10 × type_priority(p)
```

Pages scoring below 0.15 are dropped.

### Stage 2: Detail Level Selection & Token Budgeting

Every wiki page has pre-computed content at three detail levels:

| Level | Name | Tokens | Use Case |
|-------|------|--------|----------|
| L1 | Headline | ~30 | Background entities, budget overflow fallback |
| L2 | Brief | ~150 | Secondary scene characters, supporting context |
| L3 | Full | ~500 | POV character, primary location, central plot thread |

Pages are sorted by relevance score and assigned detail levels top-down within the ~15K wiki-page allocation of the ~25K story context budget.

#### Priority Tiers

- **Protected tier:** POV character + primary location → always L3, never demoted
- **High-priority:** scene characters, active plot threads → L3 when budget allows, L2 when tight
- **Medium-priority:** world rules, graph-traversed entities → L2 default
- **Low-priority:** themes, distant relationships → L1

When total exceeds budget, lower-priority pages demote L3→L2→L1 starting from the bottom of the ranked list. If the token budget still cannot be satisfied after L1 demotion, non-protected pages are dropped entirely in ascending relevance order until the budget fits.

### Stage 3: Structured Context Assembly

Pages are loaded at their assigned detail level and assembled into a fixed-structure markdown document:

```markdown
## Scene Context
### Characters
[POV character — L3 full profile]
[Scene characters — L2/L3 brief/full profiles]
[Background characters — L1 headlines]
### Location
[Current location — L3 full description]
### Active Plot Threads
[Relevant threads — L2 brief descriptions]
### World Rules
[Applicable rules — L2 brief descriptions]
### Recent Events
[Last 2-3 timeline entries]
### Relationships
[Between scene characters — L1/L2 descriptions]
```

---

## Scene-Type Adaptation

The retrieval pipeline adjusts detail level allocation based on the type of scene being generated:

| Scene Type | Budget Shift |
|------------|-------------|
| **Dialogue-heavy** | Shift budget toward character profiles + relationships |
| **Action** | Shift budget toward world rules + location details |
| **First-appearance** | Allocate L3 to new entities regardless of computed priority |

Scene type is inferred from the scene outline keywords and structure.

---

## Delta Caching Strategy

Consecutive scenes within a chapter share 60-90% of their context. The delta caching strategy avoids redundant retrieval:

1. **Compare entity sets** between the current scene and the previous scene
2. **Kept entities:** check page `version` counter — if unchanged since last retrieval, reuse cached content verbatim; if bumped by wiki-update, re-fetch
3. **New entities:** full retrieval + scoring + detail level assignment
4. **Removed entities:** drop from cache
5. **Always refresh:** recent timeline entries (new events from prior scene)
6. **Chapter boundaries:** invalidate entire scene cache (new timeline position, potentially new location/characters)

Target cache hit rate: >60% for consecutive scenes in the same chapter.

---

## Subagent Isolation

Each subagent invocation gets a fresh context window. The orchestrator delegates to subagents precisely to avoid context accumulation across chapters. This means:

- The orchestrator's conversation history does not pollute the chapter-writer's context
- Each scene generation starts with a clean budget allocation
- The compaction plugin provides a safety net for the orchestrator's own conversation history
