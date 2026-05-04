# ADR 013: Wiki Context Injection vs. Tool-Calling for Chapter Generation

**Date:** 2026-05-04
**Status:** Accepted

---

## Context

`ChapterWriterAgent` needs wiki knowledge during prose generation. Two architectures were considered:

**Option A — Pre-injection (snapshot before generation)**
Run the four-tier wiki retrieval pipeline before each LLM call and inject the result into the system prompt as `base_context`. The LLM receives curated, relevance-ranked context passively.

**Option B — Tool-calling (wiki-search as LLM tool)**
Expose `wiki-search` as an OpenAI function-calling tool. The LLM decides when to call it during inference, receives results in a tool-result message, and continues generation with that context.

---

## Decision

Implement **Option A** first. Option B is deferred.

---

## Rationale

### Option A advantages

1. **Works with all models.** Function calling requires explicit model support (OpenAI GPT-4+, certain local models). The deployment uses a local OpenAI-compatible API where function calling availability is model-dependent. Option A is model-agnostic.

2. **Existing pipeline already built.** `src/tools/wiki_snapshot.py` implements the full four-tier retrieval + RRF ranking + structured assembly pipeline (ADR 005). Option A is approximately 10–20% new code (Python API wrapper + wiring). Option B requires a new `generate_with_tools` method on `ModelProvider`, a tool-dispatch loop, tool schema definitions, and multi-turn message management — substantially more surface area.

3. **Deterministic and debuggable.** Pre-injected context can be logged, diffed, and tested directly. Tool-calling output is non-deterministic (the model may call the tool zero, one, or multiple times per generation).

4. **Revision path is simpler.** On `revise` calls, pre-injection re-runs the snapshot before the revision prompt, ensuring the revised draft has the same wiki context as the original. With tool-calling, it is unclear whether the model would re-query or rely on previous tool results.

5. **Token budget control.** The snapshot pipeline enforces a configurable token budget and detail level selection. With tool-calling, the model could request arbitrarily large pages.

### Option B advantages

1. **Dynamic, query-driven retrieval.** The LLM can fetch precisely what it needs at the moment it needs it, rather than receiving a pre-assembled context that may miss something the model would have searched for.

2. **Reusable capability.** A `generate_with_tools` provider method would enable other agents (consistency checker, quality reviewer) to use wiki-search dynamically.

### Why Option B is deferred (not abandoned)

Option B becomes compelling when:
- A function-calling capable model is confirmed in the deployment.
- Track A has been validated and the pre-injection approach's limitations are understood empirically.
- Other agents need the same tool-calling capability (consolidation justifies the provider-layer work).

---

## Consequences

### Positive

- Chapter generation gains wiki context immediately with low implementation risk.
- No model compatibility concerns.
- `wiki_snapshot.py` gets a clean Python API that other components can use.
- The provider layer stays simple; no multi-turn tool-dispatch complexity.

### Negative

- Context is not query-driven; the model receives what the retrieval pipeline thinks is relevant rather than what it would have asked for.
- If the wiki snapshot misses a relevant entity, the model cannot compensate by querying during generation.

### Neutral

- Track B can be implemented on top of Track A without conflict — both can coexist (snapshot provides baseline context; tool-calling allows supplemental queries).
