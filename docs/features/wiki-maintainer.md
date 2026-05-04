# Wiki Maintainer Subagent

> Automated entity extraction and wiki memory maintenance during story generation — populates and updates the wiki knowledge base as the story evolves.

## Overview

The wiki maintainer is a specialised subagent invoked by the `story-orchestrator` to manage the wiki memory system ([ADR 004](../planning/adr/004-progressive-wiki-memory-system.md)). It extracts entities from story content — characters, locations, events, factions, items, plot threads, world rules, and themes — and maintains structured wiki pages with confidence scoring, provenance tracking, and multi-level detail summaries.

Issue #144 refined that workflow to fix context bloat in the subagent. The most content-heavy work — reading full source material, extracting structured entities, generating L1/L2/L3 detail levels, and assembling the batch payload — now runs inside the `wiki-extract` Python tool instead of inside the agent's main LLM context. The agent remains responsible for orchestration, plausibility review, wikilink cleanup, and lint follow-up.

Issue #183 completes the post-chapter persistence path. `WikiMaintainerAgent` no longer streams a free-form response that the pipeline cannot apply. It now calls `update_wiki_from_chapter()` in `src/tools/wiki_extract.py`, which runs the `wiki/extract_from_chapter` prompt, applies the resulting batch through `run_batch()`, writes markdown pages under `stories/<name>/wiki/`, and returns the actual created and updated slug lists. That makes ADR 004's structured wiki pages and ADR 005's retrieval-ready detail levels operational during the live chapter loop rather than design-only.

Issue #344 completes ADR 004's authority shift. Initial wiki bootstrap now treats character and setting sheet JSON as the canonical pre-chapter entity source, with outline extraction used only as supplementary input when outline text exists. During the chapter loop, `WikiMaintainerAgent` is now the sole post-chapter entity state manager; the orchestrator no longer runs separate character or setting sheet evolvers after each chapter.

The agent operates in two distinct modes, mapped to pipeline phases:

- **Mode 1: Initial Wiki Population** (wiki-bootstrap phase, before Chapter 1) — Seeds the wiki from the approved outline savepoint plus character and setting sheets before chapter generation begins.
- **Mode 2: Post-Chapter Incremental Update** (chapter loop) — After each assembled chapter, extracts new entities, state changes, events, and aliases from the generated text to keep the wiki current.

The wiki maintainer runs on a smaller 7b model (`deepseek-r1-abliterated:7b`) through the project's OpenAI-compatible inference server configuration, with instructions kept concise and structured for reliable execution at that model size.

## Key Files

| File | Purpose |
|------|---------|
| `prompts/skills/wiki-maintenance/SKILL.md` | Skill reference — entity schemas, confidence taxonomy, output formats, error taxonomy |
| `prompts/skills/wiki-conventions/SKILL.md` | Skill reference — page type schemas, YAML frontmatter specs, wikilink conventions, naming rules |
| `src/tools/wiki_extract.py` | Extraction pipeline and programmatic APIs: `bootstrap_wiki_from_story()` for initial wiki seeding and `update_wiki_from_chapter()` for post-chapter incremental updates |
| `src/presentation/agents/wiki_maintainer.py` | Agent wrapper that invokes the extraction pipeline on a worker thread and emits wiki context events |
| `tests/unit/test_wiki_maintainer.py` | Unit coverage for populated slug lists, emitted wiki events, and non-streaming execution |
| `tests/unit/test_wiki_bootstrap.py` | Unit coverage for `bootstrap_wiki_from_story()` — outline extraction, sheet extraction, idempotent skipping, empty-outline short-circuit |

## Tools

The wiki maintainer uses six tools to inspect and update the wiki:

| Tool | Purpose |
|------|---------|
| `wiki-extract` | Tool-owned extraction pipeline for initial population and post-chapter updates; generates detail levels and batch payloads, then optionally applies them |
| `wiki-read` | Read wiki pages by slug/type/glob; match entity names in text |
| `wiki-update` | Create/update pages, append timeline entries, execute batch operations |
| `wiki-lint` | Run consistency checks at chapter boundaries |
| `wiki-search` | Semantic and metadata search for existing entities |
| `story-state` | Read current story state (outline, characters, settings) |

See [Tools Reference](../tools.md) for full documentation of each tool's arguments, operations, and CLI interface.

## Workflow — Mode 1: Initial Wiki Population (wiki-bootstrap phase)

Called once after wiki initialization and character/setting sheet generation, before Chapter 1. The heavy extraction pass is tool-owned so the runtime does not have to carry the full outline, every sheet, every detail level, and the complete batch payload in agent context.

1. **Run `bootstrap_wiki_from_story()`** — The tool loads character and setting sheets from disk as the canonical bootstrap source, adds outline-derived entities only when the approved outline savepoint is non-empty, deduplicates everything by slug, assigns `planned` confidence by default, generates L1/L2/L3 detail levels, skips already-existing slugs for idempotent reruns, assembles the batch payload, and applies it through `wiki-update`'s internal `run_batch()` helper.
2. **Review returned counts** — The bootstrap call returns `{created, skipped, entity_counts}` so the orchestrator or operator can see how many pages were seeded versus already present.
3. **Proceed even on failure** — The orchestrator treats this phase as non-fatal. If bootstrap raises, it logs the error, still marks `wiki_populated`, and continues into the chapter loop.
4. **Spot-check seeded pages** — If counts or created pages look wrong, rerun with a model override or follow up with targeted `wiki-update` edits.

## Workflow — Mode 2: Post-Chapter Incremental Update (chapter loop)

Called after each approved chapter is assembled. Updates the wiki with `verified` information from the generated text while keeping the full chapter and matched entity snapshots inside the tool boundary.

1. **Call `update_wiki_from_chapter()` via `asyncio.to_thread`** — `WikiMaintainerAgent` hands the accepted chapter text to the tool-owned programmatic API instead of streaming model output through the provider.
2. **Run `wiki/extract_from_chapter` and build the batch** — `wiki-extract` matches existing wiki entities, asks the extraction prompt for `new_entities`, `state_changes`, `new_aliases`, and `timeline_events`, generates L1/L2/L3 detail levels for new pages, and assembles the batch payload. Each successful LLM call is checkpointed in `stories/<story-name>/.wiki-extract-cache.json`, so a retry after timeout resumes from the last completed step.
3. **Persist changes through `run_batch()`** — The tool writes created and updated markdown pages under `stories/<story-name>/wiki/`, records timeline entries, and returns a summary with create/update counts plus concrete `new_slugs` and `updated_slugs` values.
4. **Emit wiki context events per page** — The agent publishes one `WikiContextEvent` for each created or updated slug so the surrounding pipeline and TUI surfaces can show concrete wiki mutations instead of placeholder status text.

The extraction rules themselves do not change: the tool still follows the wiki-maintenance skill's schema, confidence taxonomy, alias rules, and detail-level targets. The change is ownership, not output format.

Recap-derived wiki event pages are handled adjacent to this workflow rather than inside `WikiMaintainerAgent` itself. After `RecapWriterAgent` finishes, `src/presentation/orchestrator.py` parses recap `events` and creates or updates wiki `event` pages with verified provenance fields including `timestamp`, `participants`, `importance`, `emotional_state`, `causal_context`, and `chapter_provenance`.

The tool retry contract is explicit for this workflow: savepoints are written after each completed extraction or detail-generation step, so no agent-level recovery flow is required. Retrying the same `wiki-extract` call with the same parameters continues from the last cached step until the apply succeeds. If the source inputs (sheets, outline, or chapter text) were edited between the original run and the retry, delete `stories/<story-name>/.wiki-extract-cache.json` first to ensure a fresh extraction.

## Entity Types

The wiki supports 12 entity types, each with specific frontmatter fields beyond the common set (`page_type`, `confidence`, `first_appearance`, `aliases`).

| Type | Extra Frontmatter | Notes |
|------|-------------------|-------|
| `character` | `role`, `status` | Core entity — most wiki pages are characters |
| `location` | `region` | Geographic/spatial entities |
| `event` | `chapter`, `impact` | Plot-critical occurrences |
| `faction` | — | Organisations, groups, alliances |
| `item` | — | Significant objects, artifacts, weapons |
| `plot_thread` | `status` | Narrative threads tracked across chapters |
| `world_rule` | — | Magic systems, physical laws, social rules |
| `theme` | — | Thematic elements and motifs |
| `relationship` | — | Connections between entities |
| `timeline_entry` | — | Chronological event records |
| `chapter_synopsis` | — | Per-chapter narrative summaries |
| `contradiction` | — | Detected inconsistencies for resolution |

## Confidence Taxonomy

Every wiki page carries a confidence level that governs how facts are treated:

| Level | Meaning | Default Mode |
|-------|---------|--------------|
| `verified` | Explicitly stated in generated text | Mode 2 (post-chapter) |
| `planned` | From the outline, not yet generated | Mode 1 (initial population) |
| `speculative` | Inferred from context, not explicitly stated | Either mode, with reasoning |

**Key rules:**
- Never overwrite `verified` with `planned` or `speculative`.
- `planned` upgrades to `verified` when the scene containing the entity is generated.
- `speculative` upgrades to `verified` only when explicitly confirmed in generated text.
- `speculative` downgrades to `contradiction` if generated text contradicts the inference.

## Detail Levels

Every entity page includes three pre-computed detail summaries for the context retrieval pipeline ([ADR 005](../planning/adr/005-hybrid-wiki-context-retrieval-pipeline.md)):

| Level | Target Size | Use Case |
|-------|-------------|----------|
| L1 | ~30 tokens | High-density context assembly with many entities |
| L2 | ~150 tokens | Default detail level in scene context snapshots |
| L3 | ~500 tokens | POV characters or entities central to the current scene |

## Alias Identification

The agent identifies alternative names for entities to prevent duplicate wiki page creation:

- Formal titles ("Lord Blackwood" → "James Blackwood")
- Nicknames used in dialogue ("Jimmy" → "James Blackwood")
- Abbreviated references ("the Captain" → "Captain Elara")
- Relationship-based references ("the old man" → established elderly character)

Alias arrays are additive — the agent never removes existing aliases, only adds new ones.

## Provenance Tracking

Every extracted fact includes source provenance for traceability and contradiction detection:

| Field | Required | Description |
|-------|----------|-------------|
| Source chapter | Yes | Chapter number where the fact was extracted |
| Source scene | If scene-level | Scene number within the chapter |
| Confidence | Yes | `verified`, `planned`, or `speculative` |
| Reasoning | If `speculative` | Why this fact was inferred |

Provenance appears inline in the page body (e.g., `[Ch.3/Sc.2, verified]`) or as structured fields in timeline events.

## Chapter Boundary Procedures

At the end of each chapter, the wiki maintainer runs `wiki-lint` to check for:

- **Missing cross-references** — entities mentioned together that lack wikilinks
- **Orphaned entities** — wiki pages with no incoming wikilinks
- **Stale information** — pages with `planned` confidence for events that should now be `verified`
- **Confidence conflicts** — `verified` facts contradicted by new text

Critical issues are fixed immediately. Non-critical issues are reported to the orchestrator for later review.

## ConStory-Bench Error Taxonomy

Consistency errors detected during wiki lint operations are classified by category and subtype, based on the ConStory-Bench taxonomy. The `wiki-lint` tool uses these categories to produce structured findings.

| Category | Subtypes | Description |
|----------|----------|-------------|
| **Character Consistency** | Physical description drift, personality contradiction, ability inconsistency, knowledge state error | Character attributes change without narrative justification |
| **Temporal Consistency** | Timeline contradiction, duration error, sequence violation, age inconsistency | Events or durations conflict with established timeline |
| **Spatial Consistency** | Travel time error, location description drift, impossible geography | Physical world rules are violated |
| **Plot Consistency** | Thread contradiction, resolved thread resurrection, dropped thread, prophecy/setup abandonment | Narrative threads contradict or are lost |
| **Reference Consistency** | Entity name drift, alias confusion, missing cross-reference, orphaned entity | Entity references are inconsistent or broken |

Each lint finding includes category, subtype, severity (`critical` or `non-critical`), provenance (source and contradicting chapter/scene), and affected entity slugs. See the wiki-maintenance skill for the full specification.

## Alias Handling Edge Cases

Beyond the standard alias identification rules, the wiki maintainer handles three edge case categories:

- **Cultural naming conventions** — Names that change with marriage, title acquisition, or cultural rites are added as aliases without replacing the slug. Patronymic and matronymic naming uses the most distinctive component as the slug.
- **Shared aliases** — When multiple entities share an alias (e.g., "the Captain" could refer to different characters), disambiguation uses chapter number, scene location, and surrounding entity references. Ambiguous cases are logged as `speculative` notes until context clarifies the referent.
- **Retrospective alias discovery** — An alias may appear in text before the entity it refers to is introduced. When the entity is created, the alias is backfilled and `first_appearance` is updated to the earliest chapter where any alias was used.

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| Empty or implausible `wiki-extract` result | Re-run once with narrower focus or a model override. If still sparse, proceed and log the issue for orchestrator review. |
| `wiki-extract` timeout before apply completes | Retry the same tool call with the same parameters. Per-step checkpoints let `initial-populate` and `update-from-chapter` resume from the last successful LLM call, so no agent-level recovery logic is needed. |
| Validation or batch failure during apply | `wiki-extract` surfaces the error from `run_batch()`. Report it to the orchestrator and use targeted `wiki-update` repairs if recovery is simple. |
| Critical `wiki-lint` issues | Report to orchestrator; do not halt the pipeline. |
| Potential duplicate entity | Always check `wiki-search` before creating. If a match exists, update instead of creating. |

## Model Configuration

`WikiMaintainerAgent` does not load a dedicated agent prompt at runtime. It calls `tools.wiki_extract.update_wiki_from_chapter()` on a worker thread via `asyncio.to_thread`, and the extraction tool owns the prompt-driven work internally.

The wiki maintainer continues to run on a smaller 7b model for lightweight maintenance work. Instructions stay explicit and sequential so the workflow remains reliable at that model size.

The agent uses two skill-reference documents:
- **wiki-maintenance** — entity extraction rules, confidence taxonomy, structured output formats, detail level guidelines, chapter boundary procedures, and ConStory-Bench error taxonomy
- **wiki-conventions** — page type schemas, YAML frontmatter specifications for all 12 entity types, wikilink conventions, slug naming rules, and detail level format reference

The current workflow keeps the 7b agent within a smaller context envelope by delegating content-heavy extraction and summary generation to `wiki-extract`. The agent now spends its context budget on review and cleanup rather than on carrying every source document and generated batch entry inline.

## Related

- [Story Orchestrator](./story-orchestrator.md) — Parent agent that invokes the wiki maintainer
- [Tools Reference](../tools.md) — Full documentation for wiki-extract, wiki-read, wiki-update, wiki-lint, wiki-search, story-state
- [ADR 004: Progressive Wiki Memory System](../planning/adr/004-progressive-wiki-memory-system.md) — Wiki page format, YAML frontmatter, wikilinks
- [ADR 005: Hybrid Wiki Context Retrieval Pipeline](../planning/adr/005-hybrid-wiki-context-retrieval-pipeline.md) — Three-stage retrieval pipeline using wiki detail levels
- Issue [#183](https://github.com/logicalor/llm-story-writer/issues/183) — Persist wiki pages after each chapter through the extraction pipeline
- Issue [#22](https://github.com/logicalor/llm-story-writer/issues/22) — Initial implementation
