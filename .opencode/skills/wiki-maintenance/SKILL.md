---
name: wiki-maintenance
description: Entity extraction rules, confidence taxonomy, and structured output formats for wiki memory maintenance
version: 1.0.0
---

# Wiki Maintenance Skill

Rules and formats for automated wiki maintenance during story generation. Two modes: initial population (from outline and character/setting sheets) and incremental updates (from generated scenes).

---

## Entity Types

The wiki supports 12 entity types. Each type has specific frontmatter fields beyond the common set (`page_type`, `confidence`, `first_appearance`, `aliases`).

| Type | Extra Frontmatter | Notes |
|------|-------------------|-------|
| `character` | `role`: protagonist\|antagonist\|supporting\|minor, `status`: alive\|dead\|unknown\|transformed | Core entity — most wiki pages are characters |
| `location` | `region` | Geographic/spatial entity |
| `event` | `chapter`, `impact`: major\|moderate\|minor | Plot-critical occurrences |
| `faction` | (none beyond common) | Organisations, groups, alliances |
| `item` | (none beyond common) | Significant objects, artifacts, weapons |
| `plot_thread` | `status`: active\|resolved\|dormant | Narrative threads tracked across chapters |
| `world_rule` | (none beyond common) | Magic systems, physical laws, social rules |
| `theme` | (none beyond common) | Thematic elements and motifs |
| `relationship` | (none beyond common) | Connections between entities |
| `timeline_entry` | (chapter-scoped) | Chronological event records |
| `chapter_synopsis` | (none beyond common) | Per-chapter narrative summaries |
| `contradiction` | (none beyond common) | Detected inconsistencies for resolution |

---

## Confidence Taxonomy

Every wiki page and extracted fact carries a confidence level. These levels are strict — apply them consistently.

### `verified`
- Entity or fact **explicitly stated** in generated text.
- Direct quotes, clear descriptions, named introductions.
- **Default** for post-scene extraction (Mode 2).
- Example: "Captain Elara drew her blade" → character `elara` exists, status `alive`, role from context.

### `planned`
- Entity or fact from the **outline** that hasn't been generated yet.
- **Default** for initial wiki population (Mode 1).
- Example: Outline says "Chapter 12: Marcus betrays the guild" → event `marcus-betrayal` is `planned`.

### `speculative`
- Entity or fact **inferred** from context but not explicitly stated.
- LLM interpretation of subtext, implied relationships, unstated world rules.
- **Must include reasoning** in the page body explaining the inference.
- Example: Two characters always appear together → inferred relationship is `speculative`.

### Confidence Rules
- Never overwrite `verified` with `planned` or `speculative`.
- `planned` upgrades to `verified` when the scene containing the entity is generated.
- `speculative` upgrades to `verified` only when explicitly confirmed in generated text.
- `speculative` downgrades to `contradiction` if generated text contradicts the inference.

---

## Alias Identification Rules

Aliases are alternative names by which an entity is referenced in text. Correct alias identification prevents duplicate entity creation.

**Valid aliases:**
- Formal titles: "Lord Blackwood" for character "James Blackwood"
- Nicknames used in dialogue or narration: "Jimmy" for "James Blackwood"
- Abbreviated references: "the Captain" for "Captain Elara"
- Relationship-based references: "the old man" for an established elderly character
- Cultural or contextual names: "the Blade of Ashenmoor" for a named sword

**NOT aliases:**
- General descriptions that could apply to multiple entities ("the tall man", "the soldier")
- Pronouns (he, she, they)
- One-time metaphorical references ("a shadow among shadows")
- Category nouns ("the king") unless only one king exists in the story

**Alias arrays are additive** — never remove existing aliases, only add new ones discovered in generated text.

---

## Alias Handling Edge Cases

Beyond the standard alias identification rules, handle these edge cases:

### Cultural Naming Conventions
- Names that change with marriage, title acquisition, or cultural rites (e.g., "Kael" becomes "Kael the Blooded" after a ritual). Add the new form as an alias — do not replace the slug or original name. Track the transition chapter in the page body.
- Cultures with patronymic or matronymic naming (e.g., "Aldric son of Aldric") — use the most distinctive component as the slug and list full forms as aliases.

### Shared Aliases
- When multiple entities share an alias (e.g., "the Captain" could refer to Elara or a ship captain), disambiguate by context: chapter number, scene location, and surrounding entity references.
- If disambiguation is ambiguous, do **not** assign the alias to either entity. Log the ambiguity as a `speculative` note in both pages.
- Once narrative context makes the referent clear, assign the alias to the correct entity and remove the ambiguity note.

### Retrospective Alias Discovery
- An alias may appear in text before the entity it refers to has been created (e.g., "the Shadow" is mentioned in Chapter 2, but the character is not introduced until Chapter 5).
- When the entity is created, backfill the alias and update `first_appearance` to the earliest chapter where any alias was used.
- If the alias was previously assigned to a different entity speculatively, reassign it and downgrade the old assignment.

---

## Extraction Rules per Scene

After each scene is generated, extract the following categories of information. Process in order — later categories depend on earlier ones.

### 1. New Entities
Characters, locations, items, factions mentioned **for the first time** (not already in the wiki). Check `wiki-read` (operation: `match-entities`) against scene text before creating.

### 2. State Changes
- Character movements (location changes)
- Emotional shifts (mood, disposition)
- Relationship changes (alliances formed/broken, trust gained/lost)
- Status changes (alive→dead, unknown→alive, active→resolved)
- Power/knowledge changes (abilities gained/lost, secrets revealed)

### 3. New Events
Significant plot events with impact classification:
- `major` — changes the story's direction, affects multiple characters/threads
- `moderate` — advances a plot thread meaningfully, affects 1-2 characters
- `minor` — establishes atmosphere, provides context, foreshadows

### 4. Revealed Information
- World rules explicitly stated or demonstrated
- Theme developments and motif occurrences
- Backstory revelations
- Lore details

### 5. Plot Thread Progression
- Existing threads advancing (update status, add detail)
- New threads introduced (create with `active` status)
- Threads resolved (update status to `resolved`)

### 6. Aliases
New ways entities are referenced in the scene text. Apply alias identification rules above.

---

## Structured Output Format

All wiki operations produced by the agent use this JSON batch payload format, passed to `wiki-update` (operation: `batch`) via the `payload` parameter. The payload contains three top-level arrays: `creates`, `updates`, and `timeline_events`.

### Batch Payload
```json
{
  "creates": [
    {
      "slug": "entity-slug",
      "page_type": "character",
      "page_name": "Display Name",
      "confidence": "verified",
      "first_appearance": 1,
      "aliases": ["alias1", "alias2"],
      "body": "Full description with [[related-entity]] wikilinks to related entities.",
      "detail_levels": {
        "L1": "~30 token headline",
        "L2": "~150 token brief",
        "L3": "~500 token full description"
      },
      "role": "supporting",
      "status": "alive"
    }
  ],
  "updates": [
    {
      "slug": "existing-entity",
      "merge_body": "New information to merge into existing page body.",
      "frontmatter": { "confidence": "verified" },
      "aliases": ["new-alias"],
      "detail_levels": { "L1": "...", "L2": "...", "L3": "..." }
    }
  ],
  "timeline_events": [
    {
      "time": "Day 3, evening",
      "description": "Event description [Ch.3/Sc.2, verified]",
      "chapter": 3
    }
  ]
}
```

> **Naming convention:** Batch payload JSON keys use `snake_case` (e.g., `page_type`, `page_name`, `first_appearance`, `detail_levels`, `merge_body`). This differs from direct tool call parameters, which use `camelCase` (e.g., `pageType`, `pageName`, `firstAppearance`, `detailLevels`, `mergeBody`). Always use `snake_case` inside the `payload` JSON string passed to `wiki-update (operation: batch)`.

### Field Reference

**Create entries** require `slug`, `page_type`, and `page_name`. Optional fields: `body`, `confidence`, `first_appearance`, `aliases`, `detail_levels`, and type-specific fields (`role`, `status`, `region`, `chapter`, `impact`).

**Update entries** require `slug`. Optional fields: `frontmatter` (object of fields to merge), `detail_levels`, `body` (full replacement), `merge_body` (appended to existing body).

**Timeline entries** require `time`, `description`, and `chapter`. Events are appended to `timeline/main-timeline.md` in chronological order.

### Mixed Batch
A single payload can combine creates, updates, and timeline events. Group all operations for a scene into one batch call. All three arrays are optional — include only the arrays that contain entries.

---

## Detail Level Guidelines

Every entity page must include three detail levels for the context retrieval pipeline. Generate all three during creation and update on changes.

### L1 — Headline (~30 tokens)
One sentence capturing the essential identity or role. Used in high-density context assembly when many entities need mention.

> Captain Elara Voss, commander of the Ashenmoor garrison and reluctant leader of the northern resistance.

### L2 — Brief (~150 tokens)
Three sentences covering identity, current state, and primary relationship or role in the story. Used as the default detail level in scene context assembly.

> Captain Elara Voss commands the Ashenmoor garrison, a remote frontier outpost on the edge of the Thornwild. Once a decorated soldier of the Crown, she was reassigned to Ashenmoor after publicly questioning the King's war council. She now leads a growing resistance movement among the northern lords, driven more by duty to her soldiers than any political ambition.

### L3 — Full (~500 tokens)
Complete description including background, personality, relationships, current state, and narrative significance. Used when an entity is the POV character or central to the current scene.

---

## Chapter Boundary Procedures

At the end of each chapter (after the final scene is generated and wiki-updated), run consistency checks.

### Steps
1. Run `wiki-lint` (operation: `check-chapter`) with:
   - `name`: story name
   - `chapter_number`: the completed chapter number
   - `chapter_text`: file path to the assembled chapter text
2. Review lint results for:
   - **Missing cross-references** — entities mentioned together that lack wikilinks
   - **Orphaned entities** — wiki pages with no incoming wikilinks
   - **Stale information** — pages with `planned` confidence for events that should now be `verified`
   - **Confidence downgrades** — `verified` facts contradicted by new text
3. Fix critical lint issues before proceeding to the next chapter. Non-critical issues are logged for later review.

---

## ConStory-Bench Error Taxonomy

Consistency errors detected during wiki lint operations are classified by category and subtype for structured tracking. This taxonomy is based on ConStory-Bench and is used by `wiki-lint` to categorize findings.

| Category | Subtypes | Description |
|----------|----------|-------------|
| **Character Consistency** | Physical description drift, personality contradiction, ability inconsistency, knowledge state error | Character attributes change without narrative justification |
| **Temporal Consistency** | Timeline contradiction, duration error, sequence violation, age inconsistency | Events or durations conflict with established timeline |
| **Spatial Consistency** | Travel time error, location description drift, impossible geography | Physical world rules are violated |
| **Plot Consistency** | Thread contradiction, resolved thread resurrection, dropped thread, prophecy/setup abandonment | Narrative threads contradict or are lost |
| **Reference Consistency** | Entity name drift, alias confusion, missing cross-reference, orphaned entity | Entity references are inconsistent or broken |

Each lint finding must include:
- **Category** and **subtype** from the table above
- **Severity:** `critical` (blocks next chapter) or `non-critical` (logged for review)
- **Provenance:** the source chapter/scene and the contradicting chapter/scene
- **Affected entities:** slugs of all wiki pages involved

---

## Provenance Tracking

Every extracted fact must include provenance information to support traceability and contradiction detection.

| Field | Required | Description |
|-------|----------|-------------|
| Source chapter | Yes | Chapter number where the fact was extracted |
| Source scene | If scene-level | Scene number within the chapter |
| Confidence | Yes | `verified`, `planned`, or `speculative` |
| Reasoning | If `speculative` | Why this fact was inferred |

Provenance is embedded in the page body or timeline events, not as separate metadata. Format: `[Ch.3/Sc.2, verified]` inline notation or structured timeline entries with chapter/scene fields.
