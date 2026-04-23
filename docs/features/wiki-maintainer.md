# Wiki Maintainer Subagent

> Automated entity extraction and wiki memory maintenance during story generation — populates and updates the wiki knowledge base as the story evolves.

## Overview

The wiki maintainer is a specialised subagent invoked by the `story-orchestrator` to manage the wiki memory system ([ADR 004](../planning/adr/004-progressive-wiki-memory-system.md)). It extracts entities from story content — characters, locations, events, factions, items, plot threads, world rules, and themes — and maintains structured wiki pages with confidence scoring, provenance tracking, and multi-level detail summaries.

Issue #144 refined that workflow to fix context bloat in the subagent. The most content-heavy work — reading full source material, extracting structured entities, generating L1/L2/L3 detail levels, and assembling the batch payload — now runs inside the `wiki-extract` Python tool instead of inside the agent's main LLM context. The agent remains responsible for orchestration, plausibility review, wikilink cleanup, and lint follow-up.

The agent operates in two distinct modes, mapped to pipeline phases:

- **Mode 1: Initial Wiki Population** (Phase 6) — Extracts all known entities from the outline, character sheets, and setting sheets to populate the wiki before chapter generation begins.
- **Mode 2: Post-Chapter Incremental Update** (Phase 7c) — After each assembled chapter, extracts new entities, state changes, events, and aliases from the generated text to keep the wiki current.

The wiki maintainer runs on a smaller 7b model (`deepseek-r1-abliterated:7b`) through the project's OpenAI-compatible inference server configuration, with instructions kept concise and structured for reliable execution at that model size.

## Key Files

| File | Purpose |
|------|---------|
| `.opencode/agents/wiki-maintainer.md` | Agent definition — workflows, tools, constraints, error handling |
| `.opencode/skills/wiki-maintenance/SKILL.md` | Skill reference — entity schemas, confidence taxonomy, output formats, error taxonomy |
| `.opencode/skills/wiki-conventions/SKILL.md` | Skill reference — page type schemas, YAML frontmatter specs, wikilink conventions, naming rules |
| `opencode.json` | Agent registration with 7b model configuration via the OpenAI-compatible provider adapter |

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

## Workflow — Mode 1: Initial Wiki Population (Phase 6)

Called once after outline and character/setting sheets are generated. The heavy extraction pass is tool-owned so the subagent does not have to carry the full outline, every sheet, every detail level, and the complete batch payload in its own context window.

1. **Run `wiki-extract initial-populate`** — The tool reads `state.json`, character sheets, and setting sheets from disk; extracts entities from each source; deduplicates them by slug; assigns `planned` confidence by default; generates L1/L2/L3 detail levels; assembles the snake_case batch payload; and applies it through `wiki-update`'s internal `run_batch()` helper. Each successful LLM call is checkpointed in `stories/<story-name>/.wiki-extract-cache.json`, so a retry after timeout resumes from the last completed step.
2. **Review returned counts** — The agent inspects summary counts such as created page totals and `entity_counts` by type. This is the main compaction fix: the agent sees counts instead of the full payload.
3. **Establish wikilinks** — Review created pages and add missing `[[slug]]` links where relationships, events, locations, or plot threads should cross-reference one another.
4. **Spot-check for plausibility** — If counts or created pages look wrong, rerun with a model override or follow up with targeted `wiki-update` edits.

## Workflow — Mode 2: Post-Chapter Incremental Update (Phase 7c)

Called after each chapter is assembled. Updates the wiki with `verified` information from the generated text while keeping the full chapter and matched entity snapshots inside the tool boundary.

1. **Run `wiki-extract update-from-chapter`** — The tool reads the completed chapter file from disk, matches existing entities from the wiki index, extracts new entities plus state changes, aliases, and timeline events, generates L1/L2/L3 summaries for newly created entities, assembles the batch payload, and applies it. Each successful LLM call is checkpointed in `stories/<story-name>/.wiki-extract-cache.json`, so a retry after timeout resumes from the last completed step.
2. **Review returned counts** — The agent inspects create, update, and timeline totals and checks whether the counts look plausible for the chapter.
3. **Add or repair wikilinks** — Use `wiki-update` for short follow-up edits when created or updated pages need explicit cross-links.
4. **Run chapter boundary lint** — Call `wiki-lint` (operation: `check-chapter`) and fix critical issues. This stays agent-owned because it is a short validation step with chapter-aware judgment.

The extraction rules themselves do not change: the tool still follows the wiki-maintenance skill's schema, confidence taxonomy, alias rules, and detail-level targets. The change is ownership, not output format.

The shared `.opencode/_run.ts` timeout message is now accurate for this tool: savepoints are written after each completed extraction or detail-generation step, so no agent-level recovery flow is required. Retrying the same `wiki-extract` call with the same parameters continues from the last cached step until the apply succeeds. If the source inputs (sheets, outline, or chapter text) were edited between the original run and the retry, delete `stories/<story-name>/.wiki-extract-cache.json` first to ensure a fresh extraction.

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

The wiki maintainer is registered in `opencode.json` with a 7b model for efficient operation. The provider key uses the `@ai-sdk/openai-compatible` adapter and targets the generic `/v1` API of whichever local server is configured:

```json
{
  "wiki-maintainer": {
    "model": "lmstudio/huihui_ai/deepseek-r1-abliterated:7b",
    "instructions": ".opencode/agents/wiki-maintainer.md",
    "skills": ["wiki-maintenance", "wiki-conventions"]
  }
}
```

The smaller model keeps wiki maintenance lightweight. Instructions are structured as explicit, sequential steps to ensure reliable execution at this model size.

The agent uses two skills:
- **wiki-maintenance** — entity extraction rules, confidence taxonomy, structured output formats, detail level guidelines, chapter boundary procedures, and ConStory-Bench error taxonomy
- **wiki-conventions** — page type schemas, YAML frontmatter specifications for all 12 entity types, wikilink conventions, slug naming rules, and detail level format reference

The current workflow keeps the 7b agent within a smaller context envelope by delegating content-heavy extraction and summary generation to `wiki-extract`. The agent now spends its context budget on review and cleanup rather than on carrying every source document and generated batch entry inline.

## Related

- [Story Orchestrator](./story-orchestrator.md) — Parent agent that invokes the wiki maintainer
- [Tools Reference](../tools.md) — Full documentation for wiki-extract, wiki-read, wiki-update, wiki-lint, wiki-search, story-state
- [ADR 004: Progressive Wiki Memory System](../planning/adr/004-progressive-wiki-memory-system.md) — Wiki page format, YAML frontmatter, wikilinks
- [ADR 005: Hybrid Wiki Context Retrieval Pipeline](../planning/adr/005-hybrid-wiki-context-retrieval-pipeline.md) — Three-stage retrieval pipeline using wiki detail levels
- Issue [#22](https://github.com/logicalor/llm-story-writer/issues/22) — Initial implementation
