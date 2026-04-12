# Synthesized Research Report: Hybrid Wiki Context Search and Synthesis

**Date:** 2026-04-12
**Research Type:** Multi-model synthesis (Claude Opus 4.6 + GPT 5.4 + Gemini 3.1 Pro)
**Brief:** Investigate the retrieval and synthesis layer for a structured wiki-based memory system — how to efficiently search, select, and synthesize wiki content into a coherent context payload before injecting it into the scene generation prompt. Covers search strategies, context synthesis vs. raw concatenation, query decomposition, token budgeting, relevance scoring, caching, and evaluation.

---

## Synthesis Overview

All three models converged strongly on a three-stage pipeline architecture: **hybrid multi-tier retrieval → hierarchical detail-level selection → structured context assembly** (with an optional lightweight LLM synthesis step). The most critical finding, unanimous across all models, is that **entity mention matching is the primary retrieval signal for narrative context** — not semantic similarity. Standard vector search misses narratively relevant but semantically dissimilar pages (a character's wiki page is "relevant" because the character is named in the scene, not because the page text is topically similar to the scene outline). The models also unanimously agreed that synthesized/reconstructed context significantly outperforms raw chunk concatenation, with CASC and Oreo demonstrating +35% coherence improvement and +7% accuracy with 12x token reduction respectively. There is one notable divergence: whether the final assembly step should be deterministic (template-based) or LLM-mediated.

**Model Agreement Score:** 9/10 — Very strong alignment across search architecture, decomposition strategy, and caching patterns. Minor divergences only on synthesis execution method and wikilink traversal weighting.

---

## Individual Report Summaries

| Model  | Focus Areas | Unique Finds | Sources Cited |
| ------ | ----------- | ------------ | ------------- |
| Claude | Three-tier retrieval cascade, CASC/RECOMP benchmarks, multi-signal relevance scoring with weights, RAG+CAG hybrid caching, GROVE story generation, CRAG evaluator pattern | CASC detailed metrics (4.60 vs 3.25 coherence), RECOMP 6% compression rate, CRAG evaluator as lightweight reranker, GROVE retrieval-augmented story gen, RAG+CAG hot/cold split | 30+ |
| GPT    | Four-layer retrieval, StructRAG adaptive format routing, Oreo context reconstructor, AdaGReS token budgeting, RAGBoost KV-cache, Novarrium Logic-Locking, conStory-Bench evaluation | StructRAG (adaptive output structure), Oreo (+6.87% accuracy, 12.87x token reduction), AdaGReS (redundancy-aware greedy selection), RAGBoost (KV-cache prefix reuse), Novarrium 3-stage logic-locking | 35+ |
| Gemini | PAR2-RAG coverage/reasoning separation, QMD markdown-aware chunking, delta caching with 7b model, attention entropy from raw concatenation, aggressive adaptive budget allocation | PAR2-RAG (coverage expansion vs reasoning refinement separation), "attention entropy" concept for raw concatenation, suggestion to use 7b model as agentic query planner | 8 |

---

## Consensus Findings

### ★★★ Unanimous Findings (All Three Models Agree)

```
[U-01] Entity mention matching is the primary retrieval signal, not semantic similarity
Confidence: ★★★ Unanimous
Category: Architecture
Detail: For narrative context retrieval, the single most important signal is whether
an entity (character, location, faction, item) is explicitly named in the scene
outline. A character page is "relevant" because the character appears in the scene,
regardless of semantic similarity between the page embedding and the scene text.
All three models assign entity mention matching the highest weight or priority:
  - Claude: weight 0.4 (highest of 5 signals)
  - GPT: "weight 1.0, automatically included regardless of semantic score"
  - Gemini: "functionally 100%, bypassing semantic similarity"
This mirrors how NovelCrafter Codex and NovelAI Lorebook work in production (keyword-
triggered entry injection).
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: NovelCrafter docs, NovelAI Lorebook docs, all models converged independently
```

```
[U-02] Hybrid multi-tier retrieval beats any single method
Confidence: ★★★ Unanimous
Category: Architecture
Detail: All three models recommend a multi-tier retrieval pipeline combining:
  Tier 1 — Deterministic entity matching: Parse scene outline for entity names →
    directly load their wiki pages. Guaranteed recall for explicit mentions.
  Tier 2 — Structured metadata query: Filter ChromaDB by YAML frontmatter fields
    (page type, tags, status) to find category-relevant pages (e.g., "all active
    plot threads").
  Tier 3 — Semantic vector search: Embed scene outline, query ChromaDB for nearest
    neighbors to catch thematically related but not explicitly named content.
  Tier 4 — Wikilink graph traversal: Follow [[wikilinks]] from T1/T2/T3 results
    to discover related entities (e.g., character → faction → faction rules).
Results are merged via Reciprocal Rank Fusion (RRF). BM25+vector hybrid alone
improved accuracy from 60% to 85% in one practitioner's internal documentation
benchmark.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: QMD architecture, LanceDB hybrid search blog, Reddit r/Rag benchmarks
```

```
[U-03] Synthesized/reconstructed context significantly outperforms raw concatenation
Confidence: ★★★ Unanimous
Category: Best Practice
Detail: Multiple papers demonstrate that raw chunk concatenation wastes tokens and
degrades generation quality. Synthesized context wins across all measured dimensions:
  - CASC: Coherence 4.60 vs 3.25 (+42%), Completeness 4.45 vs 4.10, Conciseness
    4.20 vs 2.50 (+68%) — raw Top-5 RAG vs synthesis
  - Oreo: +6.87% accuracy, 12.87x input token reduction via query-aware
    context reconstruction
  - RECOMP: 6% compression rate with minimal performance loss
  - Gemini: raw concatenation causes "attention entropy" — LLM struggles to parse
    disjointed facts
The synthesis step transforms scattered wiki pages into a structured, prioritized
"scene context brief" that the generation LLM can parse efficiently.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: CASC (arXiv 2508.19357), Oreo (arXiv 2502.13019), RECOMP (ICLR 2024)
```

```
[U-04] Decompose retrieval by entity type, not a single multi-faceted query
Confidence: ★★★ Unanimous
Category: Architecture
Detail: All three models recommend decomposing scene context retrieval into
type-specific sub-queries rather than using a single query:
  1. Characters: Extract names from scene outline → load character pages (T1)
  2. Location: Extract location name → load location page (T1)
  3. Plot threads: Match by tags/relationships (T2) + semantic search (T3)
  4. World rules: Semantic search for applicable rules (T3)
  5. Timeline: Load most recent chapter synopses (T1/T2, recency filter)
  6. Relationships: Wikilink traversal between scene characters (T4)
Each sub-query uses the most appropriate retrieval tier. Results are merged and
deduplicated before assembly. This is simpler, more predictable, and more efficient
than LLM-based query decomposition — named entities can be extracted deterministically.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: NVIDIA Query Decomposition Blueprint, ACL 2025 question decomposition,
  PAR2-RAG (arXiv 2603.29085)
```

```
[U-05] Pre-compute hierarchical detail levels per wiki page for token budgeting
Confidence: ★★★ Unanimous
Category: Best Practice
Detail: Every wiki page should have pre-computed summaries at multiple detail levels,
enabling the retrieval system to select the right granularity based on token budget:
  Level 1 (Headline): ~20-30 tokens. Name + role + current state. For background
    entities or when budget is tight.
  Level 2 (Brief): ~100-150 tokens. Key facts, current status, primary motivation.
    For secondary scene characters.
  Level 3 (Full): ~300-500 tokens. Complete relevant wiki content. For POV character,
    primary location, central plot thread.
These levels should be pre-generated by the wiki-maintainer agent (7b model) when
pages are created/updated — not computed at retrieval time. When token budget is
exceeded during assembly, the system falls back from L3 → L2 → L1 for lower-priority
entities, never dropping them entirely.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: RAPTOR hierarchical abstraction, All models converged independently
```

```
[U-06] Wikilink graph traversal catches related entities that semantic search misses
Confidence: ★★★ Unanimous
Category: Architecture
Detail: The wiki's [[wikilinks]] form a lightweight knowledge graph that should be
traversed during retrieval. When Character A is explicitly mentioned in the scene,
following 1-2 hops of wikilinks discovers:
  - Character A's faction → faction rules/goals
  - Character A's home location → location details
  - Character A's relationships → related characters not in the scene outline
  - Plot threads linked to Character A → active storylines
This provides the relationship-aware retrieval benefits of GraphRAG/LightRAG
without the expensive graph construction step — the wiki already IS the graph.
All models agree this is preferable to full GraphRAG for ~200-500 structured pages.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: LightRAG (EMNLP Findings 2025), GraphRAG evaluation (arXiv 2502.11371)
```

```
[U-07] Cache aggressively between consecutive scenes, using delta updates
Confidence: ★★★ Unanimous
Category: Performance
Detail: Consecutive scenes in the same chapter share 60-90% of their context (same
characters, same location, same active plot threads). All three models recommend
caching the assembled context and computing incremental deltas rather than rebuilding:
  - Detect which entities enter/exit the scene
  - Detect which wiki pages were updated by the previous scene's wiki-maintainer
  - Only re-retrieve and re-synthesize changed entities
  - Reuse cached content for unchanged entities verbatim
This eliminates redundant retrieval, embedding queries, and synthesis LLM calls
for the majority of the context payload. Chapter boundaries invalidate the cache
(new timeline position, new chapter synopsis, potentially new location/characters).
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: RAGBoost (arXiv 2511.03475), semantic caching literature, all converged
```

```
[U-08] Token budget allocation should be adaptive based on scene type
Confidence: ★★★ Unanimous
Category: Best Practice
Detail: Within the ~15K token budget for wiki context, allocation should adapt to
scene requirements rather than being fixed:
  - Dialogue-heavy scenes: more budget for character profiles + relationships
  - Action scenes: more budget for world rules + location details
  - Exposition scenes: more budget for plot threads + timeline
  - First-appearance scenes: maximum tokens for new characters/locations
  - Recurring scenes: compressed summaries for familiar entities
When budget is exceeded, demote entries from L3 → L2 → L1 starting with the
lowest-priority entities (themes, distant relationships, background lore). Protected
tier (POV character, scene outline, primary location) is never compressed.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: Redis context overflow blog, token budget management literature
```

### ★★☆ Majority Findings (Two of Three Models Agree)

```
[M-01] Full GraphRAG is overkill; LightRAG or native wikilinks are sufficient
Confidence: ★★☆ Majority
Category: Architecture
Detail: Microsoft GraphRAG was designed for corpus-scale exploration and has 2.3x
higher latency, costs $20-500 for indexing, and actually underperforms vanilla RAG
by 13.4% on simple factual queries. LightRAG offers dual-level retrieval (entity +
relationship) with simpler graph construction and better efficiency. For ~200-500
structured wiki pages, the most practical approach is to use the wiki's existing
[[wikilinks]] as a free, pre-built knowledge graph — no external graph DB needed.
Models: Claude ✓ GPT ✓ Gemini ✗
Dissenting view: Gemini mentioned GraphRAG as useful for "bridge information" but
didn't contrast it with LightRAG or discuss the cost/latency tradeoff.
Sources: GraphRAG evaluation (arXiv 2502.11371), LightRAG (EMNLP Findings 2025)
```

```
[M-02] DOME's temporal KG provides the consistency enforcement model
Confidence: ★★☆ Majority
Category: Architecture
Detail: DOME stores story content as <subject, action, object, chapter_index>
quadruples in a temporal KG. When generating new content, it queries the KG for
relevant triples using entity matching + LLM semantic filtering (threshold 0.75
cosine similarity). This achieves 87.6% conflict reduction. The pattern maps to
the wiki: wiki pages are the "compiled" form of these quadruples, and the lint
tool performs the temporal conflict analysis.
Models: Claude ✓ GPT ✓ Gemini ✗
Dissenting view: Gemini didn't mention DOME in this report.
Sources: DOME (NAACL 2025, arXiv 2412.13575)
```

```
[M-03] RAPTOR tree-based retrieval is of moderate utility — the wiki already provides structure
Confidence: ★★☆ Majority
Category: Architecture
Detail: RAPTOR recursively clusters and summarizes text chunks into a tree,
enabling retrieval at multiple abstraction levels. For wiki pages that are already
entity-sized and structured (one page per character, location, etc.), RAPTOR's
tree construction is largely redundant — the wiki's page types and hierarchical
summaries (L1/L2/L3) already provide the same multi-level abstraction. The key
RAPTOR insight (retrieve at the right level of detail) IS valuable and should be
adopted as the L1/L2/L3 detail level system.
Models: Claude ✓ GPT ✓ Gemini ✗
Dissenting view: Gemini rated RAPTOR more highly, recommending it as a core component
("RAPTOR-lite") rather than noting its redundancy with the wiki's existing structure.
Sources: RAPTOR (ICLR 2024, arXiv 2401.18059)
```

```
[M-04] NovelCrafter Codex uses automatic entity linking + "Always Include" global entries
Confidence: ★★☆ Majority
Category: Best Practice
Detail: NovelCrafter's Codex provides two key patterns:
  1. "Global Entries" (always included): Writing style, genre conventions, tone
     rules — injected into every generation prompt regardless of scene
  2. "Automatic Linking": When an entity name appears in the scene text, the Codex
     entry is automatically included in context
  3. "Relations": One-way links between entries (Kingdom → Houses, Guards, Laws).
     Parent mention automatically includes linked children.
These patterns should be adopted: world rules and genre/style guidance are "always
include;" character/location pages use automatic entity linking; wikilink relations
provide the cascading inclusion.
Models: Claude ✓ GPT ✓ Gemini ✗ (mentioned Codex but with less detail on internals)
Sources: NovelCrafter official docs, NovelCrafter Codex cookbook
```

```
[M-05] Entity extraction from scene outline should be deterministic, not LLM-based
Confidence: ★★☆ Majority
Category: Best Practice
Detail: When decomposing a scene outline into sub-queries, the entity name extraction
step should be deterministic (regex matching against a known entity name list, or
rule-based NER) rather than LLM-mediated. This is faster, cheaper, and more
reliable — the wiki maintains the authoritative entity name list in index.md.
Models: Claude ✓ GPT ✓ Gemini ✗
Dissenting view: Gemini recommends using the 7b maintenance model as an "agentic
query planner" to decompose the intent, which is LLM-based but potentially catches
implicit references that regex misses.
Sources: Claude and GPT converged independently
```

### ★☆☆ Singular Findings (Only One Model Reported)

```
[S-01] StructRAG: Adapt retrieval output format based on scene type
Confidence: ★☆☆ Singular
Category: Architecture
Model: GPT
Detail: StructRAG (Li et al., 2024) dynamically selects the optimal structure type
(table, graph, catalogue, chunk) at inference time and restructures documents
accordingly. For narrative contexts, this means dialogue scenes might receive
character profiles in Q&A format, while battle scenes might receive location details
in spatial layout format. Outperforms both RAG and GraphRAG.
Assessment: Interesting concept but adds complexity (LLM call for format routing).
The fixed hierarchical detail levels (L1/L2/L3) already handle most of this need
with simpler implementation. Worth revisiting if generation quality is insufficient.
Sources: arXiv 2410.08815
```

```
[S-02] Oreo: Plug-in context reconstructor between retriever and generator
Confidence: ★☆☆ Singular
Category: Architecture
Model: GPT
Detail: Oreo is a plug-in module that replaces raw chunk concatenation with query-
aware context reconstruction. Improves average accuracy by 6.87% while reducing
input token length by 12.87x. Acts as an intermediate synthesis layer — exactly
the "context synthesis" step in the pipeline.
Assessment: Strongly relevant. The 12.87x token reduction with quality improvement
validates the synthesis approach. However, the model used for reconstruction matters;
Oreo's benchmarks may use larger models than our 7b target.
Sources: arXiv 2502.13019
```

```
[S-03] PAR2-RAG: Separate coverage expansion from reasoning refinement
Confidence: ★☆☆ Singular
Category: Architecture
Model: Gemini
Detail: PAR2-RAG explicitly separates "coverage expansion" (finding all relevant
documents) from "reasoning refinement" (synthesizing and reasoning over them). For
scene context, this means: first, cast a wide net to find all potentially relevant
wiki pages (expand coverage); then, filter/prioritize/synthesize (refine reasoning).
This avoids "early commitment bias" where iterative systems like IRCoT lock onto
the first retrieval results and miss important context.
Assessment: Architecturally sound and maps naturally to the T1 → T2 → T3 → T4
cascade followed by synthesis. The wiki system's decomposed retrieval already
implements this pattern implicitly — T1 (entity matching) is coverage, synthesis
is refinement.
Sources: arXiv 2603.29085
```

```
[S-04] AdaGReS: Redundancy-aware greedy context selection for token-budgeted RAG
Confidence: ★☆☆ Singular
Category: Performance
Model: GPT
Detail: AdaGReS proposes Adaptive Greedy Context Selection that optimizes globally
rather than locally, adapting the relevance-redundancy tradeoff based on candidate
pool statistics. Key insight: selecting too many redundant chunks directly wastes
token budget and degrades generation quality. It avoids selecting chunks that add
marginal information when similar content is already included.
Assessment: Directly relevant to our token budgeting challenge. When multiple wiki
pages share overlapping information (e.g., two characters who are both members of
the same faction), AdaGReS-style deduplication prevents repeating the faction
description in both character contexts.
Sources: arXiv 2512.25052
```

```
[S-05] RAGBoost: KV-cache prefix reuse for overlapping retrieval across turns
Confidence: ★☆☆ Singular
Category: Performance
Model: GPT
Detail: RAGBoost optimizes KV-cache reuse for RAG by reordering documents to align
prefixes with previously cached contexts. Achieves up to 300% speedup via semantic
caching of query→result mappings. Key observation: real-world RAG workloads exhibit
overlapping retrieved documents across turns — directly applicable to consecutive
scene generation.
Assessment: Highly relevant for local Ollama deployment. If the static context
(world rules, character backstories, "always include" entries) is placed first in
the prompt, Ollama's KV cache can reuse those computations across scenes. The
caching architecture should structure prompts to front-load stable context.
Sources: arXiv 2511.03475
```

```
[S-06] Novarrium Logic-Locking: 3-stage fact extraction → injection → verification
Confidence: ★☆☆ Singular
Category: Architecture
Model: GPT
Detail: Novarrium (commercial, 2026) implements a three-stage pipeline:
  1. Automatic fact extraction from generated text
  2. Relevance-weighted fact injection into each prompt
  3. Post-generation verification against fact base
Claims to maintain consistency across 25+ chapters where all competitors fail by
chapter ~15.
Assessment: The three-stage pattern (extract → inject → verify) maps precisely to
our wiki-update → wiki-snapshot → wiki-lint pipeline. The "relevance-weighted
injection" step is the context synthesis layer being researched here.
Sources: novarrium.com
```

```
[S-07] "Attention entropy" from raw concatenation degrades LLM generation
Confidence: ★☆☆ Singular
Category: Best Practice
Model: Gemini
Detail: Simply concatenating retrieved chunks leads to "attention entropy" where the
LLM struggles to parse disjointed facts, heavily degrading generation quality and
logical flow. This provides a named mechanism for why synthesis beats concatenation —
the model's attention mechanism loses focus when presented with incoherent context.
Assessment: The mechanism is plausible and consistent with the "lost in the middle"
effect (Liu et al., 2023) and the "context rot" finding from the previous research
round. Strengthens the case for structured synthesis.
Sources: Gemini's analysis
```

---

## Divergence Analysis

```
[D-01] Topic: Should the final context assembly be deterministic or LLM-mediated?
Claude says: Use a lightweight LLM synthesis call (7b model) to "weave retrieved
  content into a single structured scene context brief." The synthesis prompt would
  ask the LLM to produce a coherent narrative context covering characters, location,
  plot threads, world rules, and timeline.
GPT says: Deterministic structural assembly using pre-computed detail levels and a
  fixed template. "No risk of the synthesis LLM introducing hallucinations or losing
  critical details. Deterministic — same inputs always produce the same context.
  No additional LLM latency per-scene for context construction."
Gemini says: LLM synthesis with the 7b maintenance model. "Pre-synthesis using a
  smaller model (your 7b maintenance model) to digest retrieved chunks into a cohesive
  Scene Context Payload."
Assessment: GPT makes the strongest case — deterministic assembly avoids synthesis
  hallucinations, is faster, and is reproducible. However, Claude and Gemini are right
  that a synthesis step can weave connections and omit irrelevance in ways templates
  cannot. The optimal approach is a HYBRID: deterministic structural assembly as the
  default (template-based, fast, reliable), with an OPTIONAL lightweight LLM synthesis
  pass for complex scenes involving many inter-entity relationships. The LLM pass
  should condense/connect but never invent new facts.
Resolution: Default to deterministic template assembly. Offer an optional LLM
  synthesis pass when scene complexity exceeds a threshold (e.g., >5 characters,
  >3 active plot threads). The synthesis LLM must be instructed to ONLY restructure
  and condense, never add information not in the source pages.
```

```
[D-02] Topic: Wikilink traversal weighting in relevance scoring
Claude says: Weight wikilink proximity at 0.2 (out of a 1.0 total across 5 signals).
  This is lower than entity mention matching (0.4), equal to semantic similarity (0.2).
GPT says: Weight 1-hop wikilinks at 0.7, 2-hop at 0.4. This is much higher than
  Claude's 0.2, making wikilink traversal the second-most important signal after
  entity mention (1.0).
Gemini says: "Forcefully boost" graph proximity "above purely semantic vector
  matches" — qualitative, not quantified, but implies high weight.
Assessment: GPT's weighting is likely too aggressive — giving 1-hop wikilinks 0.7
  could flood the context with tangentially related entities (every linked faction,
  location, and relationship for every character). Claude's 0.2 may be too conservative
  for entities tightly connected to scene participants. A middle ground is appropriate.
Resolution: Weight 1-hop wikilinks at 0.4 (same as entity mention), 2-hop at 0.15.
  Apply a max of 5 graph-traversed entities to prevent context flooding. Graph
  traversal is valuable but must be bounded — the wiki graph can be dense.
```

```
[D-03] Topic: Entity extraction method (deterministic vs. LLM-based)
Claude says: Deterministic — parse scene outline for entity names using a known
  entity name list (from wiki index.md).
GPT says: Deterministic — "regex or NER."
Gemini says: LLM-based — "use the 7b maintenance model to decompose the user's
  scene intent into specific sub-queries."
Assessment: Claude and GPT are correct for explicit entity references. However,
  Gemini raises a valid edge case: scene outlines may contain implicit references
  ("the old king's sword" referring to the Sunstone) that regex matching would miss.
Resolution: Use deterministic matching as the primary method (fast, reliable). Add
  a fallback: if deterministic matching finds <2 entities, run the 7b model for
  implicit reference resolution. Also maintain an alias list in wiki frontmatter
  (name + aliases) for fuzzy matching.
```

```
[D-04] Topic: RAPTOR's applicability to the wiki
Claude says: "Moderate fit — useful if wiki pages themselves are long. Less useful
  when pages are already entity-sized (one character = one page). Overkill for short,
  structured wiki pages."
GPT says: "Less necessary when wiki pages are already structured with hierarchical
  headings. The pre-built wiki structure already provides the tree."
Gemini says: Highly applicable. "Following RAPTOR's abstraction approach, secondary
  entities mentioned in the prompt receive a 1-line summary, while focal characters/
  locations are fed fully into the synthesis step." Recommends "RAPTOR-lite."
Assessment: Claude and GPT are correct that RAPTOR tree construction is redundant
  for entity-sized wiki pages (~500 tokens each). Gemini is correct that RAPTOR's
  PRINCIPLE of multi-level abstraction is valuable. All three models agree on the
  L1/L2/L3 detail level system, which is the practical implementation of RAPTOR's
  insight without the expensive tree construction.
Resolution: Don't build RAPTOR trees. Do pre-compute L1/L2/L3 summaries per page
  (which captures RAPTOR's key benefit). This is what all three models actually
  recommend in their detail-level sections, despite the disagreement about RAPTOR
  as a named system.
```

---

## Recommendations

### Primary Architecture: Three-Stage Context Pipeline

```
┌────────────────────────────────────────────────────────────────┐
│ STAGE 1: HYBRID MULTI-TIER RETRIEVAL                           │
│                                                                │
│ Input: Scene outline (chapter N, scene M)                      │
│                                                                │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ T1: Entity Matching (deterministic)                       │   │
│ │ Parse scene outline for entity names (match against       │   │
│ │ wiki index.md name list + aliases). Load matched pages.   │   │
│ │ Priority: HIGHEST — these are always included.            │   │
│ └──────────────────────────────────────────────────────────┘   │
│                          ↓                                     │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ T2: Metadata-Filtered Structured Query                    │   │
│ │ ChromaDB where-filter on YAML frontmatter:                │   │
│ │   type=plot_thread AND status=active                      │   │
│ │   type=world_rule AND tags OVERLAP scene_tags             │   │
│ │ Priority: HIGH — catches type-relevant but unnamed pages. │   │
│ └──────────────────────────────────────────────────────────┘   │
│                          ↓                                     │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ T3: Semantic Vector Search                                │   │
│ │ Embed scene outline → ChromaDB top-K nearest neighbors    │   │
│ │ Priority: SUPPLEMENTARY — catches thematic relevance.     │   │
│ └──────────────────────────────────────────────────────────┘   │
│                          ↓                                     │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ T4: Wikilink Graph Traversal                              │   │
│ │ From T1/T2/T3 results, follow [[wikilinks]] 1-2 hops.    │   │
│ │ Max 5 additional entities. Priority: MEDIUM.              │   │
│ └──────────────────────────────────────────────────────────┘   │
│                          ↓                                     │
│ Merge all results via Reciprocal Rank Fusion (RRF)             │
│ Deduplicate by page slug                                       │
│                                                                │
│ Output: Ranked list of wiki page slugs with relevance scores   │
└────────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────────┐
│ STAGE 2: DETAIL LEVEL SELECTION & TOKEN BUDGETING              │
│                                                                │
│ For each retrieved page, select detail level based on:         │
│   - Relevance score (top pages → L3, middle → L2, low → L1)  │
│   - Running token count (demote L3 → L2 → L1 when over limit)│
│   - Protected tier (POV character, primary location: always L3)│
│   - Scene type adaptation (dialogue→characters, action→rules)  │
│   - First-appearance bonus (new entities always L3)            │
│                                                                │
│ Token budget enforcement (15K total):                          │
│   POV character (L3):           500-800 tokens   [PROTECTED]   │
│   Scene characters (L2-L3):    100-500 each, max 4             │
│   Location (L3):               300-500 tokens   [PROTECTED]    │
│   Active plot threads (L2):    200 each, max 3                 │
│   World rules (L2):            200 each, max 3                 │
│   Recent timeline (L2):        500-800 tokens                  │
│   Relationships (L1-L2):       100-200 each                    │
│   Themes/tone (L1):            100 tokens                      │
│   Previous scene recap (L2):   300-500 tokens                  │
│   Reserve:                     ~1500 tokens                    │
│                                                                │
│ Output: Page slugs with assigned detail levels                 │
└────────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────────┐
│ STAGE 3: STRUCTURED CONTEXT ASSEMBLY                           │
│                                                                │
│ DEFAULT: Deterministic template assembly                       │
│ Load each page at its assigned detail level (L1/L2/L3)         │
│ Assemble into a fixed-structure markdown document:             │
│                                                                │
│   ## Scene Context                                             │
│   ### Characters                                               │
│   [POV character — full profile]                               │
│   [Scene characters — brief profiles]                          │
│   [Background characters — one-liners]                         │
│   ### Location                                                 │
│   [Current location — full description]                        │
│   ### Active Plot Threads                                      │
│   [Relevant threads — brief descriptions]                      │
│   ### World Rules                                              │
│   [Applicable rules — brief descriptions]                      │
│   ### Recent Events                                            │
│   [Last 2-3 timeline entries]                                  │
│   ### Relationships                                            │
│   [Between scene characters — one-liners]                      │
│                                                                │
│ OPTIONAL (complex scenes): LLM synthesis pass                  │
│ If >5 characters or >3 plot threads or first chapter scene:    │
│   Run 7b model to condense + connect (never add, only reshape) │
│                                                                │
│ Output: Assembled "Scene Context Brief" (~15K tokens max)      │
└────────────────────────────────────────────────────────────────┘
```

### Relevance Scoring Formula

For each retrieved wiki page $p$, compute a composite relevance score:

$$\text{score}(p) = 0.40 \cdot \text{entity\_match}(p) + 0.20 \cdot \text{wikilink}(p) + 0.20 \cdot \text{semantic}(p) + 0.10 \cdot \text{recency}(p) + 0.10 \cdot \text{type\_priority}(p)$$

Where:
- $\text{entity\_match}(p)$: 1.0 if entity name appears in scene outline, 0.0 otherwise
- $\text{wikilink}(p)$: 0.8 for 1-hop from matched entity, 0.3 for 2-hop, 0.0 otherwise
- $\text{semantic}(p)$: Normalized cosine similarity (0.0–1.0) of page embedding vs. scene embedding
- $\text{recency}(p)$: 1.0 if last_updated within 2 chapters, decaying to 0.2 for 10+ chapters ago
- $\text{type\_priority}(p)$: Static per type (characters: 0.9, locations: 0.8, plot_threads: 0.7, world_rules: 0.6, events: 0.5, factions: 0.5, themes: 0.3)

Pages with $\text{score}(p) < 0.15$ are dropped. Remaining pages are sorted by score; detail levels assigned top-down.

### Caching Architecture

```
Scene Context Cache
├── permanent/ (never invalidated within a story)
│   ├── world_rules_L2[]        # All world rules at brief level
│   └── genre_tone_style_L1     # "Always Include" entry
│
├── chapter/ (invalidated at chapter boundaries)
│   ├── chapter_synopsis_history # Last 2-3 chapter synopses
│   ├── active_plot_threads[]    # Active threads with status
│   └── thematic_guidance        # Current act's themes
│
├── scene/ (diff-updated per scene)
│   ├── characters{}             # {slug: (content, detail_level, page_hash)}
│   ├── location                 # Current location page
│   ├── relationships[]          # Between scene characters
│   └── recent_timeline[]        # Last 3 events
│
└── metadata
    ├── page_versions{}          # {slug: version_counter}
    └── last_entity_set          # Set of entity slugs in last scene
```

**Delta update algorithm:**
1. Parse new scene outline for entity names
2. Compare to `last_entity_set`: added = new - old, removed = old - new, kept = old ∩ new
3. For `kept` entities: check `page_versions` — if version bumped since last retrieval, re-fetch; otherwise reuse cached content
4. For `added` entities: full retrieval + detail level assignment
5. For `removed` entities: drop from cache
6. Always refresh: `recent_timeline` (new events from prior scene)
7. Re-assemble only the changed sections of the context document

### Evaluation Framework

| Level | Metric | Method | Target |
|-------|--------|--------|--------|
| **Retrieval** | Entity coverage | % of scene-mentioned entities present in context | >95% |
| **Retrieval** | Precision@K | % of retrieved pages actually relevant (human-judged) | >85% |
| **Budget** | Token utilization | % of 15K budget used for high/medium priority content | >80% |
| **Budget** | Compression ratio | Assembled context tokens / total raw page tokens | <0.4 |
| **Quality** | Coherence | LLM-as-judge: is the context internally consistent? | >4.0/5.0 |
| **Downstream** | Conflict rate | Contradictions per 10K generated words (DOME metric) | <0.5% |
| **Downstream** | Faithfulness (RAGAS) | Generated facts grounded in provided context | >0.95 |
| **Performance** | Cache hit rate | % of context pages reused between consecutive scenes | >60% |

---

## Gaps / Uncertainties

1. **7b model synthesis quality** — All synthesis research (CASC, Oreo, RECOMP) benchmarks use GPT-4 or 70B+ models. Whether a local 7b model can produce adequate synthesis quality for narrative context is unvalidated. This is why deterministic assembly is recommended as the default, with LLM synthesis as an optional enhancement.

2. **nomic-embed-text on fiction domain** — No specific benchmarks for nomic-embed-text on fictional/narrative content. Embedding quality for fantasy names, invented locations, and genre-specific terminology may differ from general benchmarks.

3. **Optimal relevance score weights** — The proposed weights (0.40/0.20/0.20/0.10/0.10) are reasoned from first principles and production patterns but are not empirically validated for narrative retrieval. These should be tuned empirically.

4. **Wikilink graph density** — For heavily interlinked wikis, 1-hop traversal from 3-4 entities could return dozens of related pages. The max-5 cap is a conservative guard; optimal bounds depend on actual wiki graph topology.

5. **LATTICE system** — None of the three models could find a system named "LATTICE" performing "logarithmic semantic tree search." This may be an unpublished or differently-named concept.

6. **Karpathy Wiki query internals** — The query operation is described conceptually ("LLM searches for relevant pages") but no implementation details on the search algorithm are published.

7. **Implicit reference resolution** — Scene outlines may refer to entities implicitly ("the old king's sword" → "Moonstone Blade"). Regex matching against a name list won't catch these. Alias lists help but implicit metonymic references require NLU.

---

## Combined Source List

**Context Synthesis & Compression:**
- [CASC: Context-Adaptive Synthesis and Compression](https://arxiv.org/html/2508.19357v1) — Synthesis >> concatenation with human eval scores — cited by: Claude, GPT
- [Oreo: Plug-in Context Reconstructor](https://arxiv.org/html/2502.13019v2) — +6.87% accuracy, 12.87x token reduction — cited by: GPT
- [RECOMP: Context Compression for RAG](https://arxiv.org/html/2310.04408v1) — 6% compression rate, extractive + abstractive (ICLR 2024) — cited by: Claude
- [RAG vs Prompt Stuffing (W&B)](https://wandb.ai/byyoung3/rag-eval/reports/RAG-vs-prompt-stuffing-Do-we-still-need-vector-retrieval---VmlldzoxMzE5Mjk0NA) — Selection quality > quantity — cited by: GPT

**Hybrid Retrieval & Search:**
- [QMD Architecture Overview](https://www.mintlify.com/tobi/qmd/architecture/overview) — BM25 + Vector + LLM reranker hybrid — cited by: Claude
- [QMD GitHub](https://github.com/tobi/qmd) — Markdown-aware chunking — cited by: Gemini
- [Blended RAG (arXiv 2404.07220)](https://arxiv.org/html/2404.07220) — BM25 + KNN + Sparse Encoder evaluation — cited by: Claude
- [RankRAG (NeurIPS 2024)](https://proceedings.neurips.cc/paper_files/paper/2024/file/db93ccb6cf392f352570dd5af0a223d3-Paper-Conference.pdf) — Context ranking unified with RAG — cited by: Claude
- [Hybrid Search with LanceDB](https://www.lancedb.com/blog/hybrid-search-combining-bm25-and-semantic-search-for-better-results-with-lan-1358038fe7e6) — BM25 + vector fusion — cited by: GPT
- [Hybrid RAG in the Real World (NetApp)](https://community.netapp.com/t5/Tech-ONTAP-Blogs/Hybrid-RAG-in-the-Real-World-Graphs-BM25-and-the-End-of-Black-Box-Retrieval/ba-p/464834) — Production hybrid RAG architectures — cited by: GPT
- [Reddit r/Rag BM25+vector benchmarks](https://www.reddit.com/r/Rag/comments/1rf7xf6/) — 60% → 85% accuracy with hybrid — cited by: GPT

**Graph Retrieval:**
- [LightRAG (EMNLP Findings 2025)](https://aclanthology.org/2025.findings-emnlp.568.pdf) — Dual-level entity+relationship retrieval — cited by: Claude, GPT
- [GraphRAG evaluation (arXiv 2502.11371)](https://arxiv.org/html/2502.11371v3) — GraphRAG underperforms vanilla RAG by 13.4% on factual queries — cited by: GPT
- [When to use Graphs in RAG (arXiv 2506.05690)](https://arxiv.org/html/2506.05690v3) — cited by: GPT

**Hierarchical & Structured Retrieval:**
- [RAPTOR (ICLR 2024)](https://arxiv.org/html/2401.18059v1) — Tree-based hierarchical retrieval — cited by: Claude, GPT, Gemini
- [StructRAG (arXiv 2410.08815)](https://arxiv.org/html/2410.08815v1) — Adaptive structure selection — cited by: GPT
- [PAR2-RAG (arXiv 2603.29085)](https://arxiv.org/html/2603.29085v1) — Coverage expansion vs reasoning refinement — cited by: Gemini

**Query Decomposition & Multi-Hop:**
- [IRCoT (ACL 2023)](https://arxiv.org/html/2212.10509v2) — Interleaved retrieval and chain-of-thought — cited by: Claude, GPT
- [Question Decomposition for RAG (ACL 2025)](https://aclanthology.org/2025.acl-srw.32.pdf) — Decomposition improves multi-hop coverage — cited by: GPT
- [NVIDIA Query Decomposition Blueprint](https://docs.nvidia.com/rag/2.3.0/query_decomposition.html) — Production sub-query decomposition — cited by: Claude
- [Query Decomposition Survey (arXiv 2412.17558)](https://arxiv.org/html/2412.17558v3) — Taxonomy of decomposition approaches — cited by: Claude

**Token Budgeting:**
- [AdaGReS (arXiv 2512.25052)](https://arxiv.org/html/2512.25052v1) — Redundancy-aware greedy context selection — cited by: GPT
- [Context Window Overflow (Redis)](https://redis.io/blog/context-window-overflow) — Token allocation as zero-sum game — cited by: GPT
- [Token Budget Strategies (tianpan.co)](https://tianpan.co/blog/2025-10-20-token-budget-strategies-llm-production) — Tiered allocation patterns — cited by: Claude
- [RAG Prompt Engineering (mbrenndoerfer.com)](https://mbrenndoerfer.com/writing/rag-prompt-engineering-context-citations) — Weighted budget formula — cited by: Claude
- [Token Budget Management (apxml.com)](https://apxml.com/courses/getting-started-with-llm-toolkit/chapter-3-context-and-token-management/managing-token-budgets) — Architectural strategies — cited by: Gemini

**Agentic RAG:**
- [Agentic RAG Survey (arXiv 2501.09136)](https://arxiv.org/html/2501.09136v1) — Comprehensive taxonomy — cited by: Claude
- [Agentic RAG Architecture (Galileo)](https://galileo.ai/blog/agentic-rag-integration-ai-architecture) — Query decomposition + multi-tool — cited by: Gemini
- [Agentic RAG with Knowledge Graphs (arXiv 2507.16507)](https://arxiv.org/html/2507.16507v1) — Multi-hop reasoning — cited by: Gemini

**Caching:**
- [RAGBoost (arXiv 2511.03475)](https://arxiv.org/html/2511.03475v1) — KV-cache prefix reuse — cited by: GPT
- [Semantic Caching for RAG](https://boringbot.substack.com/p/semantic-caching-for-rag-systems) — 300% speedup — cited by: GPT

**Narrative/Story Generation:**
- [DOME (NAACL 2025)](https://arxiv.org/html/2412.13575v1) — Temporal KG memory, 87.6% conflict reduction — cited by: Claude, GPT
- [GROVE (EMNLP 2023 Findings)](https://aclanthology.org/2023.findings-emnlp.262.pdf) — Retrieval-augmented story generation — cited by: Claude
- [ConStory-Bench (Microsoft)](https://picrew.github.io/constory-bench.github.io/) — Consistency error taxonomy — cited by: GPT
- [Novarrium Logic-Locking](https://novarrium.com/blog/ai-writing-tools-keep-contradicting-themselves) — Three-stage fact locking — cited by: GPT

**Production Fiction Systems:**
- [NovelCrafter Codex](https://www.novelcrafter.com/blog/your-personal-wiki-the-codex) — Automatic entity linking — cited by: Claude, GPT
- [NovelCrafter Codex Scene Context](https://www.novelcrafter.com/courses/codex-cookbook/codex-scenes) — Scene-level attachment — cited by: Claude
- [NovelCrafter Codex Relations](https://www.novelcrafter.com/courses/codex-cookbook/codex-relationships) — One-way link inclusion — cited by: Claude
- [NovelCrafter Help: The Codex](https://www.novelcrafter.com/help/docs/codex/the-codex) — Global entries + typed categories — cited by: Gemini
- [NovelAI Lorebook](https://docs.novelai.net/en/text/lorebook/) — Keyword-triggered injection — cited by: GPT
- [Sudowrite vs NovelCrafter](https://sudowrite.com/blog/sudowrite-vs-novelcrafter-the-ultimate-ai-showdown-for-novelists/) — Codex vs Story Bible — cited by: Claude, GPT

**Evaluation:**
- [RAGAS Framework](https://superlinked.com/vectorhub/articles/evaluating-retrieval-augmented-generation-framework) — Faithfulness, relevance metrics — cited by: Claude, GPT
- [Entity Retrieval Evaluation (ACL 2025)](https://aclanthology.org/2025.knowledgenlp-1.1.pdf) — nDCG for entity-based retrieval — cited by: Claude

**General RAG Architecture:**
- [Self-RAG, CRAG, Adaptive RAG comparison](https://blog.gopenai.com/building-an-effective-rag-pipeline) — cited by: Claude
- [Advanced RAG Techniques (Pinecone)](https://www.pinecone.io/learn/advanced-rag-techniques/) — cited by: Claude
- [Hybrid Retrieval with ChromaDB (Dataquest)](https://www.dataquest.io/blog/metadata-filtering-and-hybrid-search-for-vector-databases/) — cited by: Claude
- [Context Engineering for AI Agents (Maxim)](https://www.getmaxim.ai/articles/context-engineering-for-ai-agents-production-optimization-strategies/) — cited by: Claude
- [LLM Wiki vs RAG (MindStudio)](https://www.mindstudio.ai/blog/llm-wiki-vs-rag-markdown-knowledge-base-comparison/) — cited by: GPT
- [Karpathy LLM Wiki Guide (Starmorph)](https://blog.starmorph.com/blog/karpathy-llm-wiki-knowledge-base-guide) — cited by: Claude
- [Karpathy LLM Wiki (VentureBeat)](https://venturebeat.com/data/karpathy-shares-llm-knowledge-base-architecture-that-bypasses-rag-with-an) — cited by: Claude
- [Karpathy LLM Wiki (Antigravity)](https://antigravity.codes/blog/karpathy-llm-wiki-idea-file) — cited by: Claude
