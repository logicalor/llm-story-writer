# ADR 004: Progressive Wiki Memory System

**Date:** 2026-04-12
**Status:** Proposed

## Context

Long-form story generation (novel-length, 20-50 chapters) suffers from consistency degradation as the narrative grows. The current system uses per-chapter recaps and character/setting sheets loaded into context, but these are passive artifacts — they require the generation agent to re-derive world state from scattered sources on every scene. This leads to:

1. **Consistency failures** — character traits, location details, timeline events, and plot threads drift or contradict as chapters accumulate
2. **Context inefficiency** — loading raw character sheets, setting sheets, and recaps into the 65536-token window is wasteful when only a subset is relevant to the current scene
3. **No proactive contradiction detection** — errors propagate silently; once a wrong fact enters a recap, all subsequent generation builds on it

The Karpathy LLM Wiki pattern (published 2026-04-04) proposes a structured, LLM-maintained knowledge base that pre-compiles and maintains knowledge as interlinked markdown pages, eliminating the "knowledge re-derivation" problem. Multi-model research (Claude, GPT, Gemini — see [research report](../../.github/research/story-wiki-memory-system-2026-04-12.md)) unanimously confirmed this pattern's applicability to fiction generation, with no existing system combining the two.

## Decision

Implement a progressive wiki-based memory system as an integral part of the story generation pipeline. The wiki follows a three-layer architecture:

1. **Raw sources** (immutable): manuscript chapters, the original prompt, the finalized outline
2. **Wiki** (LLM-maintained): structured markdown pages with YAML frontmatter for ~12 entity types — characters, locations, events, factions, items, plot threads, timelines, world rules, chapter synopses, themes, relationships, and a contradictions log
3. **Schema** (`_schema.md`): defines page types, frontmatter conventions, cross-reference rules, update lifecycle, and confidence taxonomy

Key architectural decisions:

- **Storage format:** Markdown files with YAML frontmatter, stored in `stories/<name>/wiki/`, version-controlled via git
- **Update granularity:** Scene-level updates (extract entities/state changes after each scene), chapter-level lint (consistency checks after each chapter)
- **Dedicated agent:** A `wiki-maintainer` subagent (separate from the creative generator, using a smaller/faster model) handles all wiki updates to avoid polluting the creative agent's context
- **Pre-generation snapshots:** A `wiki-snapshot` tool assembles a token-budgeted "world state snapshot" before each scene, injecting relevant characters, locations, plot threads, world rules, and timeline events into the generation prompt as authoritative constraints
- **Consistency enforcement:** Wiki lint uses the ConStory-Bench error taxonomy (5 categories, 19 subtypes) and DOME-style temporal fact tracking to detect contradictions
- **Confidence tracking:** Every wiki fact carries a `confidence` field (verified/planned/speculative) and provenance (source chapter/scene) to distinguish established facts from outline plans and LLM inferences

## Consequences

### Positive

- Pre-synthesized context eliminates knowledge re-derivation — the generation agent receives authoritative world state rather than piecing it together from scattered chunks
- Proactive contradiction detection catches errors before they propagate
- Token-efficient: hierarchical summary levels (1-line, 3-sentence, full) enable flexible context budgeting within the 65536-token window
- Human-readable and inspectable — writers can review and edit the wiki directly (markdown, Obsidian-compatible)
- Git versioning enables chapter-level rollback of both manuscript and world state
- The wiki serves as a persistent creative memory that survives context compaction

### Negative

- **Increased LLM call overhead:** Each scene triggers 5-15 wiki page updates via the wiki-maintainer agent, adding ~1000+ LLM calls for a 100-scene novel
- **Entity extraction quality risk:** NER on fictional text (fantasy names, invented locations) with local 7b models is untested and may require the 24b model
- **Persistent error propagation:** If the wiki records something incorrectly, all subsequent generation builds on that error (mitigated by confidence scoring and provenance tracking, but not eliminated)
- **Schema evolution complexity:** The wiki schema must evolve as the story develops; new page types may be needed mid-story
- **Implementation scope:** Adds 5 new tasks (Tasks 13-16, 20) and touches 4 existing tasks (17, 19, 21, 23), increasing the migration from 21 to 26 tasks

### Neutral

- The wiki coexists with (and partially supersedes) the existing character sheets and setting sheets — these artifacts become the initial data source for wiki population but the wiki becomes the authoritative source after initialization
- ChromaDB (ADR 003) serves double duty: RAG index for story content AND semantic search index for wiki pages
- The wiki-maintainer agent can potentially be swapped out for a rule-based extractor if LLM extraction proves unreliable, without changing the rest of the architecture
