# Synthesized Research Report: Progressive Wiki-Based Memory System for AI Story Generation

**Date:** 2026-04-12
**Research Type:** Multi-model synthesis (Claude Opus 4.6 + GPT 5.4 + Gemini 3.1 Pro)
**Brief:** Investigate the Karpathy "LLM Wiki" pattern and its applicability to building a progressive, wiki-based memory system for AI-assisted novel generation — covering schema design, consistency enforcement, token-efficient querying, and integration with the OpenCode agentic architecture.

---

## Synthesis Overview

All three models independently confirmed that the Karpathy LLM Wiki pattern (published 2026-04-04, 5000+ stars) is an excellent fit for long-form story generation, directly addressing the core limitation of standard RAG: knowledge re-derivation on every query. The models achieved strong consensus on architecture (three-layer: raw sources / wiki / schema), page types (characters, locations, events, factions, plot threads, timelines, world rules), scene-level update granularity, and the critical importance of a `confidence` field to distinguish verified/planned/speculative content. All three models identified the same key academic papers (DOME, FactTrack, ConStory-Bench) as directly relevant. The primary area of divergence was search/retrieval strategy — whether the full wiki can fit in context, or whether vector search is always necessary.

**Model Agreement Score:** 9/10 — Very strong alignment across findings, architecture, and recommendations. Minor divergences only in implementation details and depth of source coverage.

---

## Individual Report Summaries

| Model  | Focus Areas | Unique Finds | Sources Cited |
| ------ | ----------- | ------------ | ------------- |
| Claude | Deep academic coverage, tool-level architecture, FactTrack atomic fact decomposition, QMD recommendation, RAPTOR hierarchical summarization | claude-obsidian (full Karpathy implementation), Rowboat (typed entities + backlinks), md2LLM (fine-tuning from wiki), ChronoQA/EACL benchmark | 40+ |
| GPT    | Comprehensive commercial tool survey, Novarrium torture test, agentmemory lifecycle management, Graphify KG, HOMER/LATTICE/HTSIR hierarchical retrieval | Novarrium 25-chapter consistency torture test, agentmemory (Ebbinghaus decay + typed edges), PlotMachines (EMNLP 2020), Long Story Gen via KG (arXiv:2508.03137), "Context Rot" research from Chroma | 40+ |
| Gemini | Concise practical focus, "Archivist" agent concept, markdown-over-JSON argument, ephemeral wiki compilation idea | Action2Dialogue RNB (Recursive Narrative Bank), STORM (automated Wikipedia staging), "Finding Flawed Fictions" benchmark, suggestion to fit full wiki in context | 6 |

---

## Consensus Findings

### ★★★ Unanimous Findings (All Three Models Agree)

```
[U-01] The LLM Wiki pattern is well-suited for progressive story generation
Confidence: ★★★ Unanimous
Category: Architecture
Detail: All three models independently confirmed that the Karpathy LLM Wiki pattern
maps naturally onto story generation. The key insight: instead of re-deriving character
states, location details, and plot context from raw text on every scene, the wiki
pre-compiles and maintains this knowledge as structured, interlinked markdown pages.
This directly solves the "knowledge re-derivation" problem that causes consistency
failures in long-form generation.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: Karpathy gist, VentureBeat analysis, antigravity.codes analysis
```

```
[U-02] No existing system combines the LLM Wiki pattern with story generation
Confidence: ★★★ Unanimous
Category: Architecture
Detail: No production or open-source system applies the full LLM Wiki pattern to
progressive fiction generation. Commercial tools (Sudowrite Story Bible, NovelCrafter
Codex, NovelAI Lorebook) offer manual or semi-automated story wikis but none achieve
fully automated progressive construction. Open-source LLM Wiki implementations
(claude-obsidian, Rowboat) target research/personal knowledge, not fiction.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: Novarrium survey, commercial tool reviews, GitHub searches
```

```
[U-03] Three-layer architecture: raw sources / wiki / schema
Confidence: ★★★ Unanimous
Category: Architecture
Detail: All models recommend preserving Karpathy's three-layer architecture adapted
for fiction:
  Layer 1 (Raw Sources): The generated manuscript chapters (immutable once finalized),
    the original prompt, and the outline. The LLM reads but never modifies these.
  Layer 2 (Wiki): LLM-generated markdown pages for characters, locations, events,
    plot threads, timelines, world rules, chapter synopses. The LLM owns and maintains
    this layer entirely.
  Layer 3 (Schema): A configuration document defining page types, frontmatter
    conventions, cross-reference rules, and update workflows. Co-evolved with the story.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: Karpathy gist architecture section
```

```
[U-04] Core page types: characters, locations, events, factions, items, timelines,
       plot threads, world rules, chapter synopses
Confidence: ★★★ Unanimous
Category: Architecture
Detail: All three models converged on a very similar set of page types, derived from
analysis of fan wikis (Tolkien Gateway, Wookieepedia) and academic literature:
  - Character: profiles with status, traits, arcs, relationships
  - Location: places with controlling factions, events that occurred there
  - Event: plot-significant happenings with participants, consequences
  - Faction/Organization: groups with members, goals, allegiances
  - Item/Artifact: significant objects with owners, properties
  - Timeline: chronological event index
  - Plot Thread: active/resolved/abandoned storylines
  - World Rule: magic systems, physics, social norms
  - Chapter Synopsis: per-chapter digests with key events and state changes
  - Theme: recurring motifs and development arcs
  - Relationship: evolution of connections between characters
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: Wookieepedia templates, Tolkien Gateway, WorldAnvil schemas, Urdr "Unified 7"
```

```
[U-05] YAML frontmatter with confidence field is essential
Confidence: ★★★ Unanimous
Category: Best Practice
Detail: Every wiki page needs structured YAML frontmatter including:
  - type (character|location|event|faction|item|plot_thread|world_rule|etc.)
  - name (canonical name)
  - first_appearance (chapter, scene)
  - last_updated (chapter, scene)
  - status (alive|dead|unknown for characters; active|resolved for plot threads)
  - confidence (verified|planned|speculative) — CRITICAL for distinguishing what has
    been written vs. what the outline plans vs. what the LLM inferred
  - related entities (characters, locations, events) for cross-referencing
  - tags for categorization and search
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: All three models independently produced similar frontmatter schemas
```

```
[U-06] Scene-level update granularity with chapter-level lint
Confidence: ★★★ Unanimous
Category: Best Practice
Detail: The recommended update lifecycle:
  - After each scene: extract new entities, update character/location pages, add to
    timeline, log state changes
  - After each chapter: generate chapter synopsis page, update plot thread statuses,
    run consistency lint
  - Periodic (every 5-10 chapters): full lint pass checking for orphan pages,
    contradictions, stale claims, missing cross-references
A dedicated "wiki maintainer" / "archivist" / "librarian" agent (separate from the
generation agent) should handle updates to avoid polluting the creative context.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: DOME approach, Karpathy ingest/lint operations, all models converged independently
```

```
[U-07] ConStory-Bench provides the consistency error taxonomy
Confidence: ★★★ Unanimous
Category: Best Practice
Detail: Microsoft Research's ConStory-Bench (2026) defines 5 error categories with
19 subtypes for narrative consistency:
  1. Timeline & Plot Logic (6 subtypes)
  2. Characterization (4 subtypes)
  3. World-building & Setting (3 subtypes)
  4. Factual & Detail Consistency (3 subtypes)
  5. Narrative & Style (3 subtypes)
Key empirical finding: errors are most common in factual and temporal dimensions,
tend to appear around the middle of narratives (40-60% mark), and occur in segments
with higher token-level entropy. This taxonomy should be used for the lint operation.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: arXiv:2603.05890, Microsoft Research
```

```
[U-08] DOME's temporal knowledge graphs reduce conflicts by ~88%
Confidence: ★★★ Unanimous
Category: Architecture
Detail: DOME (NAACL 2025) uses a Memory-Enhancement Module (MEM) with temporal
knowledge graphs that stores generated story segments as structured quadruples
<subject, action, object, chapter>. A Temporal Conflict Analyzer detects conflicts
by aggregating triples, summarizing relationship groups, and judging for temporal/
factual contradictions. DOME reduces contextual conflicts by 87.61% in experiments.
This approach directly addresses the consistency enforcement problem.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: arxiv.org/abs/2412.13575, aclanthology.org/2025.naacl-long.63
```

```
[U-09] FactTrack provides time-aware world state tracking
Confidence: ★★★ Unanimous
Category: Architecture
Detail: FactTrack (NAACL 2025, UC Berkeley) decomposes events into directional
atomic facts (pre-facts, post-facts, static facts), determines validity intervals,
detects contradictions with existing facts, and updates the world state. Crucially,
it achieves near-GPT-4 performance using LLaMA2-7B-Chat, making it viable for local
LLM deployment. This provides the theoretical foundation for the wiki's consistency
checking layer.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: arxiv.org/abs/2407.16347, aclanthology.org/2025.naacl-long.144
```

```
[U-10] Persistent error propagation is the #1 risk
Confidence: ★★★ Unanimous
Category: Security
Detail: All three models identified the "persistent error" problem as the primary
risk: if the wiki records something incorrectly (character traits, location
descriptions, event outcomes), all subsequent generation builds on that error.
Unlike RAG (where hallucinations are ephemeral), wiki errors compound.
Agreed mitigations: provenance tracking (every fact cites its source chapter/scene),
confidence scoring, regular lint passes, human review for high-impact changes (deaths,
major reveals, allegiance shifts).
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: Karpathy gist comments, VentureBeat analysis, all models converged
```

```
[U-11] Pre-generation "world state snapshot" is the key workflow innovation
Confidence: ★★★ Unanimous
Category: Best Practice
Detail: Before generating each scene, a tool should query the wiki for:
  - Current status of all characters in the scene
  - Location details and current state
  - Active plot threads relevant to this scene
  - Applicable world rules/constraints
  - Recent timeline events
This "snapshot" is injected into the generation prompt as contextual constraints,
ensuring the generated text is consistent with established facts. This is where the
wiki pattern fundamentally outperforms RAG: the snapshot is pre-synthesized and
authoritative, not pieced together from scattered chunks.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: All models independently proposed this workflow
```

```
[U-12] Markdown files with git versioning is the recommended storage format
Confidence: ★★★ Unanimous
Category: Architecture
Detail: All three models recommend markdown files with YAML frontmatter, stored in
a git repository. Benefits: human-readable and inspectable, LLM-native format (better
than JSON for narrative content), version history enables chapter-level rollback,
Obsidian compatibility for visual browsing. Use [[wikilinks]] for in-text cross-
references alongside structured frontmatter for programmatic traversal.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: Karpathy gist, claude-obsidian, Rowboat, all models converged
```

```
[U-13] Dedicated wiki-maintainer agent separate from story generator
Confidence: ★★★ Unanimous
Category: Architecture
Detail: All models recommend a dedicated agent (variously called "wiki maintainer,"
"archivist," or "librarian") that handles wiki updates separately from the creative
generation agent. Rationale: wiki maintenance adds tool calls and context that would
pollute the creative agent's context window. The maintainer runs post-generation,
reads the newly written content, extracts entities/events/state changes, and updates
wiki pages. This agent can use a different (potentially smaller/faster) model.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: All models proposed this independently
```

### ★★☆ Majority Findings (Two of Three Models Agree)

```
[M-01] QMD is the recommended search engine for wiki content
Confidence: ★★☆ Majority
Category: Architecture
Detail: QMD (by Tobi Lütke) is a local search engine for markdown with hybrid BM25
+ vector search + LLM re-ranking (Reciprocal Rank Fusion). Available as both CLI and
MCP server. Designed specifically for markdown knowledge bases. Uses SQLite FTS5 and
node-llama-cpp with GGUF models — fully local. Karpathy explicitly recommends it.
Models: Claude ✓ GPT ✓ Gemini ✗
Dissenting view: Gemini didn't find or mention QMD. Focused on fitting wiki in context.
Sources: github.com/ehc-io/qmd, Karpathy gist "Optional: CLI tools" section
```

```
[M-02] index.md + log.md are essential navigation files
Confidence: ★★☆ Majority
Category: Best Practice
Detail: Per Karpathy's pattern: index.md serves as a content catalog (every page
listed with one-line summary, organized by category) — the LLM reads this first to
find relevant pages. log.md is an append-only chronological record of all wiki
operations (ingests, queries, lints, updates). Both are critical for wiki navigation
and understanding what has changed recently.
Models: Claude ✓ GPT ✓ Gemini ✗ (mentioned index.md but not as prominently)
Dissenting view: Gemini mentioned the concept but didn't detail log.md.
Sources: Karpathy gist "Indexing and logging" section
```

```
[M-03] Hierarchical summarization enables token-efficient retrieval
Confidence: ★★☆ Majority
Category: Performance
Detail: Each wiki page should have multiple summary levels: a 1-line summary (for
index.md scanning, ~10 tokens), a 3-sentence brief (for quick context, ~50 tokens),
and a full body (for deep loading, ~500-2000 tokens). Chapter synopses should exist
at chapter, act, and full-story levels. This is inspired by RAPTOR (Stanford, ICLR
2024) — recursive abstractive processing for tree-organized retrieval.
Academic support: HOMER (ICLR 2024, hierarchical context merging), HMT (NAACL 2025,
brain-inspired memory hierarchy), LATTICE (ICLR 2026, logarithmic search complexity).
Models: Claude ✓ GPT ✓ Gemini ✗
Dissenting view: Gemini suggested simply fitting the full wiki in context rather than
hierarchical summarization. This may work early but fails as the novel grows.
Sources: RAPTOR (arxiv.org/abs/2401.18059), HOMER, HMT, LATTICE
```

```
[M-04] Commercial fiction tools fail at automated consistency maintenance
Confidence: ★★☆ Majority
Category: Architecture
Detail: Novarrium's 25-chapter "torture test" across Sudowrite, NovelCrafter, NovelAI,
and Claude found that all major tools failed at long-form consistency maintenance.
Key findings: manual maintenance burden grows unsustainably, no tool proactively detects
contradictions, and consistency degrades significantly after ~15 chapters. This
validates the need for an automated, wiki-based consistency system.
Models: Claude ✗ GPT ✓ Gemini ✓ (implied)
Dissenting view: Claude listed the commercial tools but didn't cite the Novarrium test.
Sources: novarrium.com torture test, commercial tool reviews
```

```
[M-05] agentmemory provides relevant lifecycle management patterns
Confidence: ★★☆ Majority
Category: Architecture
Detail: rohitg00/agentmemory implements: Ebbinghaus-curve memory decay (speculative
facts fade if not reinforced), tiered eviction (hot/warm/cold storage), entity
extraction with temporal versioning, typed relationship edges (supports, contradicts,
evolved_into, depends_on), citation chains, and an MCP server. The LLM Wiki v2 gist
extends Karpathy's pattern with these lifecycle management lessons.
Models: Claude ✓ GPT ✓ Gemini ✗
Dissenting view: Gemini didn't find agentmemory.
Sources: github.com/rohitg00/agentmemory, LLM Wiki v2 gist
```

### ★☆☆ Singular Findings (Only One Model Reported)

```
[S-01] "Context Rot" research shows LLM performance degrades with context length
Confidence: ★☆☆ Singular
Category: Performance
Model: GPT
Detail: Chroma's research demonstrates that LLM performance actively degrades with
increasing context, even within stated context limits. This argues against naively
loading entire wiki contents into context and in favour of targeted retrieval.
Assessment: Likely accurate — GPT cited Chroma's blog directly. This is an important
counterpoint to Gemini's suggestion to fit the full wiki in context.
Sources: trychroma.com/research/context-rot
```

```
[S-02] Action2Dialogue's Recursive Narrative Bank (RNB)
Confidence: ★☆☆ Singular
Category: Architecture
Model: Gemini
Detail: The Action2Dialogue paper (arXiv:2505.16819) implements a Recursive Narrative
Bank where dialogue and scene events update a continuous memory buffer, grounding new
scenes in established facts. This is a running-context memory model rather than a
wiki model, but shares the "progressive accumulation" principle.
Assessment: Relevant as an alternative architecture reference. The RNB is more like
a running summary than a structured wiki, but the extraction-and-filing pattern
is similar.
Sources: arxiv.org/html/2505.16819v3
```

```
[S-03] STORM framework for automated Wikipedia-like article staging
Confidence: ★☆☆ Singular
Category: Architecture
Model: Gemini
Detail: STORM uses multi-perspective questioning to automate Wikipedia-like article
creation. The "pre-writing" stage searches for sources and generates outlines; the
"writing" stage compiles full articles with citations.
Assessment: Relevant as an article-generation pattern but designed for factual topics,
not fiction. The multi-perspective approach could inform character/setting page generation.
Sources: dev.to/foxgem/overview-storm
```

```
[S-04] STORYTELLER/NEKG uses Neo4j for narrative entity knowledge graphs
Confidence: ★☆☆ Singular
Category: Architecture
Model: GPT
Detail: The STORYTELLER system (ACL Findings 2025) implements a Narrative Entity
Knowledge Graph using Neo4j, where nodes are entities and edges are typed relationships.
Supports both "current storyline analysis" and "future plot generation" through logical
relationship reasoning.
Assessment: Relevant but adds Neo4j as a heavyweight dependency. The typed-relationship
pattern can be implemented in markdown frontmatter without a graph database for our
scale (~200-500 wiki pages).
Sources: aclanthology.org/2025.findings-acl.1071
```

```
[S-05] "Ephemeral Wiki" compilation for per-scene context
Confidence: ★☆☆ Singular
Category: Best Practice
Model: Gemini
Detail: If the full wiki exceeds context limits, compile an "Ephemeral Wiki" — a
temporary markdown file containing only the characters, locations, and lore pertinent
to the specific upcoming scene. The wiki maintainer agent creates this compilation,
which is then loaded by the generator agent.
Assessment: This is essentially the "world state snapshot" (U-11) with a different name
and emphasis on creating a single compiled file rather than loading individual pages.
A valid implementation approach.
Sources: Gemini's analysis
```

```
[S-06] Graphify achieves 71.5x fewer tokens per query via knowledge graph
Confidence: ★☆☆ Singular
Category: Performance
Model: GPT
Detail: Graphify generates a knowledge graph from any folder of files, using SHA256
cache for incremental updates. Claims 71.5x fewer tokens per query compared to
reading raw files.
Assessment: Impressive efficiency claim. Could serve as an alternative to or
complement for ChromaDB. Worth investigating but the 71.5x number needs verification.
Sources: analyticsvidhya.com/blog/2026/04/graphify-guide/
```

```
[S-07] "Finding Flawed Fictions" benchmark for plot hole detection
Confidence: ★☆☆ Singular
Category: Architecture
Model: Gemini
Detail: OpenReview benchmark that details how generation loops introduce plot holes
and measures the effectiveness of explicit file-by-file fact-checking as mitigation.
Assessment: Directly relevant as a validation methodology for the wiki consistency
checker. Should be investigated as a testing framework.
Sources: openreview.net/forum?id=ptmgWRCWmu
```

---

## Divergence Analysis

```
[D-01] Topic: Can the full wiki fit in context, or is retrieval always needed?
Claude says: No — with 65536 tokens, you need selective loading. Budget ~35K for wiki
  content, which allows ~15-25 pages. Recommends hybrid index.md + ChromaDB + keyword-
  triggered injection.
GPT says: No — "The context window isn't a database." Recommends hybrid retrieval with
  QMD (BM25 + vector + reranking). Cites "Context Rot" research showing performance
  degrades with context length. Provides detailed token budget: ~20K for wiki.
Gemini says: Maybe yes — "Modern LLMs possess 64K–1M token context limits. For a
  moderately sized novel, the entire text of the wiki might fit directly in the context
  window." Suggests the full wiki often outperforms RAG for reasoning.
Assessment: Claude and GPT are correct for this project's 65536-token constraint. A
  full novel wiki (~200-500 pages × ~1000 tokens = 200K-500K tokens) far exceeds the
  context window. Even a partial wiki of ~50 pages would consume ~50K tokens, leaving
  almost nothing for generation. Gemini's claim applies only to models with 128K+ context
  and very small wikis. For this project, selective retrieval is mandatory.
Resolution: Selective retrieval is required. Use index.md for navigation, ChromaDB for
  semantic search, and the "world state snapshot" pattern for per-scene context assembly.
  Budget ~15-20K tokens maximum for wiki content per scene generation.
```

```
[D-02] Topic: Should the wiki use markdown or structured data?
Claude says: Markdown with YAML frontmatter. Use [[wikilinks]] in body, structured
  fields in frontmatter. ChromaDB as derived index.
GPT says: Hybrid — YAML frontmatter for structured data, markdown body for narrative.
  Same conclusion as Claude.
Gemini says: "Use Markdown Over JSON for Lore. Markdown is the native 'thought format'
  for LLMs, allowing them to embed nuanced relationship dynamics that JSON arrays
  struggle to capture."
Assessment: Full consensus on markdown as primary format. Gemini's framing ("thought
  format for LLMs") is accurate — LLMs generate better content when reading/writing
  markdown than structured JSON. The YAML frontmatter provides just enough structure
  for programmatic queries.
Resolution: Markdown with YAML frontmatter. No structured database (Neo4j/JSON)
  needed at this project's scale.
```

```
[D-03] Topic: What search/retrieval system to use for wiki content?
Claude says: QMD (hybrid BM25 + vector) as primary, ChromaDB as fallback.
GPT says: QMD as primary, ChromaDB for vector layer, possibly add BM25 separately.
  Also mentions kb-mcp and MinerU as alternatives.
Gemini says: No specific search system recommended. Suggests direct file reading or
  fitting wiki in context.
Assessment: Claude and GPT agree on QMD. Gemini's omission is likely because it
  didn't search for search tools specifically. QMD is the most complete option
  (BM25 + vector + reranking, MCP server, designed for markdown, fully local,
  recommended by Karpathy himself). However, the project already has ChromaDB —
  adding QMD as an additional dependency needs justification.
Resolution: Evaluate QMD vs. ChromaDB + simple BM25 during implementation. QMD is
  the ideal solution but ChromaDB is already in the stack. Start with ChromaDB;
  add QMD if retrieval quality is insufficient.
```

```
[D-04] Topic: Depth of source coverage
Claude says: 40+ sources, including 25+ URLs. Deep academic coverage with specific
  paper details, implementation code references, and architectural analysis.
GPT says: 40+ sources with 30+ URLs. Broadest coverage — found commercial tools,
  academic papers, community projects, and blog analyses that other models missed.
Gemini says: ~6 sources. Focused on high-level pattern application rather than
  exhaustive source mining.
Assessment: GPT and Claude both conducted thorough, wide-ranging research. Gemini's
  report is concise but significantly less sourced. However, Gemini's unique finds
  (Action2Dialogue RNB, STORM, "Finding Flawed Fictions") suggest it searched different
  corners of the space.
Resolution: GPT and Claude provide the evidence base; Gemini provides complementary
  architectural intuitions. All unique finds are worth evaluating.
```

---

## Recommendations

Prioritized by consensus level, then relevance:

### High Confidence (Unanimous)

1. **[U-03] ★★★ Adopt the three-layer architecture (raw / wiki / schema)** — The manuscript chapters are raw sources (immutable once written). The wiki is a directory of LLM-maintained markdown pages. The schema defines conventions and workflows. This is the highest-confidence recommendation.

2. **[U-11] ★★★ Implement pre-generation "world state snapshot"** — Before each scene, a tool queries the wiki for relevant characters, locations, plot threads, world rules, and recent events. This pre-synthesized snapshot is injected into the generation prompt as constraints. This is the killer feature that distinguishes the wiki from RAG.

3. **[U-06] ★★★ Scene-level updates, chapter-level linting** — Update wiki after each scene (extract entities, state changes). Generate chapter synopsis and run consistency lint after each chapter. Full lint every 5-10 chapters.

4. **[U-13] ★★★ Dedicated wiki-maintainer agent** — A separate subagent handles wiki updates after generation. This avoids polluting the creative agent's context window with extraction/filing tasks. Can use a smaller/faster model.

5. **[U-04] ★★★ Standardize on ~12 page types** — Characters, locations, events, factions, items, timelines, plot threads, world rules, chapter synopses, themes, relationships, and a contradictions log. Use YAML frontmatter with the `confidence` field (verified/planned/speculative).

6. **[U-08] ★★★ Use DOME-style temporal fact tracking for contradiction detection** — Store generated facts as structured quadruples. Cross-check new facts against the existing world state before accepting. The 87.61% conflict reduction is compelling.

7. **[U-07] ★★★ Adopt ConStory-Bench's error taxonomy for lint operations** — Focus consistency checks on the 5 error categories, prioritizing factual and temporal dimensions (the most common error types).

8. **[U-12] ★★★ Markdown + git for storage** — Every wiki page is a markdown file with YAML frontmatter. Git provides version history, enabling chapter-level rollback. Obsidian-compatible for visual browsing.

### Medium Confidence (Majority)

9. **[M-03] ★★☆ Implement hierarchical summarization** — Each wiki page has a 1-line summary, 3-sentence brief, and full body. Chapter synopses at chapter/act/story levels. This enables flexible token budget allocation during retrieval.

10. **[M-01] ★★☆ Evaluate QMD for wiki search** — QMD's hybrid BM25 + vector + LLM reranking, with MCP server, is the ideal search layer. But ChromaDB is already in the stack. Start with ChromaDB; evaluate QMD if retrieval quality is insufficient.

11. **[M-05] ★★☆ Consider agentmemory-style lifecycle management** — Ebbinghaus decay for speculative facts that aren't reinforced, typed relationship edges (supports/contradicts/evolved_into), citation chains. Valuable additions once the core wiki is working.

### Worth Investigating (Singular)

12. **[S-01] ★☆☆ Test "Context Rot" assertions** — Empirically test whether loading wiki content into local LLM context degrades quality at the margins. If confirmed, this strengthens the case for selective retrieval over full-wiki loading.

13. **[S-07] ★☆☆ Evaluate "Finding Flawed Fictions" as a testing framework** — Use this benchmark to validate the wiki's consistency checking capabilities.

14. **[S-06] ★☆☆ Investigate Graphify for token-efficient KG** — The 71.5x token reduction claim is worth verifying. Could complement ChromaDB.

---

## Proposed Wiki Architecture for the AI Story Writer

### Directory Layout

```
stories/<story-name>/
├── raw/                         # Layer 1: Immutable sources
│   ├── prompt.txt               # Original story prompt
│   ├── outline.md               # Generated outline (finalized)
│   └── reference/               # Any human-supplied reference material
│
├── wiki/                        # Layer 2: LLM-maintained knowledge base
│   ├── _schema.md               # Layer 3: Conventions, page types, workflows
│   ├── index.md                 # Content catalog with 1-line summaries per page
│   ├── log.md                   # Chronological operations log (append-only)
│   ├── contradictions.md        # Logged contradictions and resolutions
│   ├── characters/
│   │   ├── elena-blackwood.md   # Character page
│   │   └── marcus-thorne.md
│   ├── locations/
│   │   ├── silverport.md
│   │   └── the-narrows.md
│   ├── factions/
│   │   └── merchant-guild.md
│   ├── items/
│   │   └── moonstone-blade.md
│   ├── events/
│   │   └── siege-of-silverport.md
│   ├── plot-threads/
│   │   ├── succession-crisis.md
│   │   └── forbidden-magic.md
│   ├── world-rules/
│   │   ├── magic-system.md
│   │   └── political-structure.md
│   ├── themes/
│   │   └── power-and-corruption.md
│   ├── relationships/
│   │   └── elena-marcus.md
│   ├── timeline/
│   │   └── main-timeline.md     # Ordered events with story timestamps
│   └── chapters/
│       ├── chapter-01.md        # Chapter synopsis (brief + detailed)
│       └── chapter-02.md
│
├── chapters/                    # Generated chapter text (manuscript)
│   ├── chapter-01.md
│   └── chapter-02.md
│
├── state.json                   # Pipeline state (current phase, settings)
└── savepoints/                  # Checkpoint system
```

### Page Template: Character

```markdown
---
type: character
name: "Elena Blackwood"
slug: elena-blackwood
status: alive
first_appearance: { chapter: 1, scene: 2 }
last_updated: { chapter: 12, scene: 3 }
confidence: verified
allegiance: [merchant-guild, house-blackwood]
allegiance_changes:
  - { chapter: 8, from: "independent", to: "merchant-guild", reason: "Sought protection after assassination attempt" }
current_location: silverport
relationships:
  - { target: marcus-thorne, type: rival, since_chapter: 5 }
  - { target: sophia-crane, type: mentor, since_chapter: 1 }
tags: [protagonist, magic-user, noble]
---

# Elena Blackwood

<!-- 1-LINE SUMMARY (for index.md) -->
Noble-born merchant mage navigating guild politics while concealing forbidden magical abilities.

<!-- BRIEF (3 sentences, for quick context loading) -->
Elena Blackwood is the youngest daughter of House Blackwood, secretly trained in forbidden siphon magic by her mentor Sophia Crane. After fleeing an assassination attempt in Chapter 8, she allied with the Merchant Guild to secure protection. She currently operates from Silverport, balancing guild duties with her investigation into the source of the magical corruption spreading through the city.

## Current State (Chapter 12)

- **Location:** Silverport, Guild Quarter
- **Emotional state:** Determined but increasingly paranoid
- **Active goals:** Expose the corruption source; protect Sophia from guild scrutiny
- **Recent developments:** Discovered Marcus Thorne is also investigating the corruption (Ch 11); uneasy truce formed

## Physical Description

Tall, dark-haired woman in her late twenties with sharp green eyes. Carries a silver merchant's chain (guild membership) and a concealed obsidian focus stone. Dresses practically — traveling clothes over merchant attire.

## Personality & Traits

- Intelligent and strategic, but prone to acting alone rather than trusting others
- Deep loyalty to those she considers family (Sophia, House Blackwood retainers)
- Struggles with the ethical implications of siphon magic
- Quick-tempered when her competence is questioned

## Arc Progression

| Chapter | Development |
|---------|-------------|
| 1-3 | Established as competent but isolated. Introduced to siphon magic. |
| 4-7 | Growing confidence in magic. Conflict with Marcus escalates. |
| 8 | Crisis point: assassination attempt. Forced to seek guild protection. |
| 9-12 | Learning to trust allies. Discovering shared enemy with Marcus. |

## Relationships

- **[[Sophia Crane]]** — Mentor. Trained Elena in siphon magic. Elena is deeply protective. (Since Ch 1)
- **[[Marcus Thorne]]** — Rival turned uneasy ally. Competitive dynamic. (Rival since Ch 5, truce Ch 11)
- **[[Lord Blackwood]]** — Father. Estranged since Elena left House Blackwood. (Background)

## Key Events

- [[assassination-attempt-ch8]] — Survived assassination; fled to guild
- [[corruption-discovery-ch10]] — Found first evidence of magical corruption
- [[marcus-truce-ch11]] — Formed uneasy alliance with rival
```

### Pre-Scene Workflow (context assembly)

```
┌──────────────────────────────────────────────────────────┐
│ Scene Task: Chapter 13, Scene 2                           │
│ Outline says: "Elena and Marcus infiltrate the old        │
│ library to find records of past corruption events"        │
└─────────────────────┬────────────────────────────────────┘
                      │
      ┌───────────────▼───────────────┐
      │    wiki_get_scene_context()    │
      │    (world state snapshot tool) │
      └───────────────┬───────────────┘
                      │ reads wiki/index.md
                      │ identifies relevant pages
                      │ loads with token budgeting
                      ▼
    ┌─────────────────────────────────────────────┐
    │ ASSEMBLED CONTEXT (~15K tokens)              │
    │                                              │
    │ Characters (briefs):                         │
    │   elena-blackwood.md → Brief + Current State │
    │   marcus-thorne.md → Brief + Current State   │
    │                                              │
    │ Location:                                    │
    │   old-library.md → Full page                 │
    │                                              │
    │ Relevant plot threads:                       │
    │   corruption-investigation.md → Active       │
    │   marcus-truce.md → Recent (Ch 11)           │
    │                                              │
    │ World rules:                                 │
    │   magic-system.md → Siphon magic constraints │
    │                                              │
    │ Timeline:                                    │
    │   Last 3 events from main-timeline.md        │
    │                                              │
    │ Previous scene recap:                        │
    │   chapter-13-scene-1 summary                 │
    │                                              │
    │ Consistency constraints:                     │
    │   - Elena is in Silverport (confirmed Ch 12) │
    │   - Marcus has no weapons (taken Ch 12)      │
    │   - Library is unguarded at night (Ch 4 lore)│
    └─────────────────────────────────────────────┘
                      │
                      ▼
    ┌─────────────────────────────────────────────┐
    │ GENERATE SCENE (~16K output budget)          │
    └─────────────────────────────────────────────┘
                      │
                      ▼
    ┌─────────────────────────────────────────────┐
    │ wiki_update() — post-generation              │
    │                                              │
    │ Extracts from generated scene:               │
    │   - Elena found a journal (new item)         │
    │   - Marcus revealed he can read Old Script   │
    │   - Library has a hidden basement (location)  │
    │                                              │
    │ Updates:                                     │
    │   characters/marcus-thorne.md → add skill    │
    │   items/ancient-journal.md → create new page │
    │   locations/old-library.md → add basement    │
    │   timeline/main-timeline.md → add event      │
    │   wiki/log.md → append operation record      │
    │   wiki/index.md → add new pages              │
    └─────────────────────────────────────────────┘
```

### Token Budget (65536 total)

| Component | Tokens | Notes |
|-----------|--------|-------|
| System prompt + agent instructions | ~2000 | Fixed |
| Tool descriptions | ~2000 | Fixed |
| Scene outline / plan | ~2000 | Current chapter outline |
| Wiki snapshot (characters) | ~4000 | 2-4 characters × brief + current state |
| Wiki snapshot (location) | ~1000 | Current location page |
| Wiki snapshot (plot threads) | ~2000 | 2-3 active threads |
| Wiki snapshot (world rules) | ~1000 | Applicable rules |
| Wiki snapshot (timeline) | ~1000 | Recent events |
| Previous scene / recap | ~3000 | Summary of preceding scene |
| Prompt template | ~3000 | Rendered scene generation prompt |
| **Reserved for generation** | **~44000** | Scene text output |
| **Total** | **~65000** | ~500 token safety margin |

---

## OpenCode Integration Plan

### New Tools (additions to the existing migration task list)

| Tool | Description | Operations |
|------|-------------|------------|
| `wiki-init` | Initialize wiki structure for a new story | Create directory tree, _schema.md, index.md, log.md |
| `wiki-snapshot` | Assemble pre-generation context from wiki | Read index → identify relevant pages → load with token budget → return compiled context |
| `wiki-update` | Update wiki after scene generation | Extract entities/events/state changes from generated text → update pages → update index → append log |
| `wiki-lint` | Run consistency checks | Detect contradictions, orphans, stale claims, missing cross-references → return report |
| `wiki-read` | Read specific wiki page(s) | Load page by slug, return content |
| `wiki-search` | Search wiki content | ChromaDB semantic search + keyword matching → return relevant pages |

### New Agent

| Agent | Type | Model | Description |
|-------|------|-------|-------------|
| `wiki-maintainer` | Subagent | Smaller/faster model (e.g., 7b) | Handles all wiki updates post-generation. Extracts entities and state changes from generated text, updates wiki pages, runs lite consistency checks. Invoked by orchestrator after each scene. |

### New Skills

| Skill | Description |
|-------|-------------|
| `wiki-conventions` | Wiki page type definitions, frontmatter schemas, naming conventions, cross-reference rules |
| `wiki-maintenance` | Update workflows, lint procedures, contradiction handling, confidence scoring rules |

---

## Gaps / Uncertainties

1. **No production validation** — No system has combined the LLM Wiki pattern with progressive story generation at novel scale. This is novel territory requiring empirical testing.

2. **Entity extraction quality** — NER on fictional text (fantasy names, invented locations) is harder than factual text. Local LLMs may struggle with reliable entity extraction, especially for subtle state changes (emotional shifts, implied revelations).

3. **Wiki maintenance token cost** — Each scene generates 1 scene but triggers 5-15 wiki page updates, each requiring an LLM call. For a 100-scene novel, this means ~1000+ maintenance LLM calls beyond generation itself.

4. **Contradiction detection accuracy** — FactTrack achieves near-GPT-4 with LLaMA2-7B, but accuracy on fictional content with invented terminology is untested.

5. **Schema evolution** — The wiki schema must evolve as the story develops. Early chapters may not need faction pages; a twist may introduce a magic system that requires new world-rule pages. The schema co-evolution mechanism needs design.

6. **Outline divergence handling** — When the LLM generates content that diverges from the outline, the system must decide which source to trust. This requires clear rules in the schema (outline wins? generated text wins? flag for human decision?).

7. **Context Rot** — Loading selective but substantial wiki content into a 65536-token window may still degrade generation quality at the margins. Empirical testing needed.

8. **Git integration complexity** — Atomic commits per chapter's wiki updates add git operations to every scene. Performance impact on large repos needs validation.

---

## Combined Source List

Deduplicated across all three model reports:

**Karpathy LLM Wiki & Extensions:**
- [Karpathy LLM Wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — Core pattern — cited by: Claude, GPT, Gemini
- [LLM Wiki v2 (rohitg00)](https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2) — Lifecycle management extensions — cited by: Claude, GPT
- [agentmemory (rohitg00)](https://github.com/rohitg00/agentmemory) — Memory engine with Ebbinghaus decay — cited by: Claude, GPT
- [claude-obsidian (AgriciDaniel)](https://github.com/AgriciDaniel/claude-obsidian) — Full Claude Code LLM Wiki implementation — cited by: Claude
- [Rowboat](https://github.com/rowboatlabs/rowboat) — Typed entities + backlinks knowledge base — cited by: Claude
- [VentureBeat analysis](https://venturebeat.com/data/karpathy-shares-llm-knowledge-base-architecture-that-bypasses-rag-with-an) — cited by: Claude, GPT
- [Antigravity.codes guide](https://antigravity.codes/blog/karpathy-llm-wiki-idea-file) — cited by: GPT, Gemini

**Academic Papers — Story Generation & Consistency:**
- [DOME (NAACL 2025)](https://aclanthology.org/2025.naacl-long.63.pdf) — Temporal KG memory, 87.61% conflict reduction — cited by: Claude, GPT, Gemini
- [FactTrack (NAACL 2025)](https://aclanthology.org/2025.naacl-long.144.pdf) — Time-aware world state tracking — cited by: Claude, GPT, Gemini
- [ConStory-Bench (Microsoft Research, 2026)](https://huggingface.co/papers/2603.05890) — Consistency error taxonomy — cited by: Claude, GPT, Gemini
- [KG-based storytelling (arXiv:2505.24803)](https://arxiv.org/html/2505.24803v2) — KG for story coherence — cited by: Claude, GPT
- [STORYTELLER/NEKG (ACL Findings 2025)](https://aclanthology.org/2025.findings-acl.1071.pdf) — Neo4j narrative entity KG — cited by: GPT
- [Long Story Gen via KG (arXiv:2508.03137)](https://arxiv.org/pdf/2508.03137) — KG for entity/relation tracking — cited by: GPT
- [Survey on LLMs for Story Gen (EMNLP 2025)](https://aclanthology.org/2025.findings-emnlp.750.pdf) — Comprehensive survey — cited by: Claude, GPT
- [ChronoQA / Entity-Event KG (EACL 2026)](https://aclanthology.org/2026.eacl-long.90.pdf) — cited by: Claude
- [PlotMachines (EMNLP 2020)](https://aclanthology.org/2020.emnlp-main.215/) — Outline-conditioned generation — cited by: GPT
- [Building Narrative Structures from KGs (ESWC 2022)](https://2022.eswc-conferences.org/wp-content/uploads/2022/05/phd_Blin_paper_181.pdf) — cited by: Claude
- [Action2Dialogue / RNB (arXiv:2505.16819)](https://arxiv.org/html/2505.16819v3) — Recursive Narrative Bank — cited by: Gemini
- [Finding Flawed Fictions](https://openreview.net/forum?id=ptmgWRCWmu) — Plot hole detection benchmark — cited by: Gemini
- [STORM](https://dev.to/foxgem/overview-storm) — Automated Wikipedia article staging — cited by: Gemini

**Academic Papers — Hierarchical Retrieval & Memory:**
- [RAPTOR (Stanford, ICLR 2024)](https://arxiv.org/abs/2401.18059) — Hierarchical summarization for retrieval — cited by: Claude, GPT
- [HOMER (ICLR 2024)](https://openreview.net/forum?id=ulaUJFd96G) — Hierarchical context merging — cited by: GPT
- [HMT (NAACL 2025)](https://aclanthology.org/2025.naacl-long.410.pdf) — Hierarchical Memory Transformer — cited by: GPT
- [LATTICE (ICLR 2026)](https://openreview.net/forum?id=p0gxvlUoZM) — Logarithmic retrieval via semantic tree — cited by: GPT
- [Context Rot (Chroma, 2025)](https://www.trychroma.com/research/context-rot) — LLM performance degrades with context length — cited by: GPT
- [HTSIR (Microsoft, AAAI 2026)](https://www.microsoft.com/en-us/research/wp-content/uploads/2026/01/AAAI_Chenxueyu.pdf) — Hierarchical retrieval — cited by: GPT

**Tools & Implementations:**
- [QMD](https://github.com/ehc-io/qmd) — Local hybrid markdown search, MCP server — cited by: Claude, GPT
- [Graphify](https://www.analyticsvidhya.com/blog/2026/04/graphify-guide/) — KG from file folders, 71.5x token reduction — cited by: GPT
- [kb-mcp](https://mcpmarket.com/server/knowledge-base-6) — Alternative markdown MCP server — cited by: GPT
- [md2LLM](https://github.com/Aryan1718/md2LLM) — Fine-tuning from wiki markdown — cited by: Claude

**Commercial Fiction Tools:**
- [Novarrium 25-chapter torture test](https://novarrium.com/blog/ai-writing-tools-keep-contradicting-themselves) — All tools fail at consistency — cited by: GPT
- [Sudowrite Story Bible](https://sudowrite.com/blog/story-ai-generator-the-complete-guide-for-fiction-writers) — cited by: Claude, GPT
- [NovelCrafter Codex](https://intellectualead.com/novelcrafter-review-guide/) — cited by: GPT
- [NovelAI Lorebook](https://docs.novelai.net/en/text/lorebook/) — cited by: Claude
- [Urdr](https://urdr.io/blog/world-anvil-vs-campfire-vs-urdr) — AI worldbuilding — cited by: Claude, GPT, Gemini
- [World Anvil](https://www.worldanvil.com/) — Manual worldbuilding wiki — cited by: Claude, GPT, Gemini
- [SidekickWriter](https://sidekickwriter.com) — World Bible feature — cited by: Claude

**Fan Wiki Structure References:**
- [Wookieepedia infobox templates](https://starwars.fandom.com/wiki/Wookieepedia:Templates/Infoboxes) — 76 template categories — cited by: Claude, GPT
- [Tolkien Gateway infobox templates](https://tolkiengateway.net/wiki/Category:Infobox_templates) — cited by: Claude
