# Wiki Conventions Skill

Authoritative reference for wiki page structure, naming conventions, frontmatter schemas, and cross-reference patterns. Use this skill when creating, reading, or validating wiki pages.

---

## Directory Structure

Every story's wiki lives in `stories/<name>/wiki/` with the following layout:

```
stories/<name>/wiki/
├── _schema.md          # Schema definition
├── characters/         # Character pages
├── locations/          # Location pages
├── events/             # Event pages
├── factions/           # Faction pages
├── items/              # Item pages
├── plot-threads/       # Plot thread pages
├── world-rules/        # World rule pages
├── themes/             # Theme pages
├── relationships/      # Relationship pages
├── timeline/           # Timeline entries
├── chapter-synopses/   # Per-chapter synopses
└── contradictions/     # Detected contradictions
```

---

## Common Frontmatter Fields

All page types share these frontmatter fields:

```yaml
page_type: <type>
confidence: verified|planned|speculative
first_appearance: <chapter number>
aliases: [list of alternative names]
```

See the wiki-maintenance skill for confidence taxonomy rules.

---

## Page Type Schemas

The wiki supports 12 entity types. Each type has specific frontmatter fields beyond the common set.

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

## Index Format

`index.md` is the flat registry of all wiki entities. Format per entry:

```
- slug | type | name | aliases | path
```

- `slug` — kebab-case identifier (no `/` characters)
- `type` — entity type (character, location, event, etc.)
- `name` — display name
- `aliases` — comma-separated alternative names (may be blank)
- `path` — wiki-relative file path, e.g. `characters/emre.md`

**Type → subdirectory mapping:**

| Type | Subdirectory |
|------|-------------|
| `character` | `characters/` |
| `location` | `locations/` |
| `event` | `events/` |
| `faction` | `factions/` |
| `item` | `items/` |
| `plot_thread` | `plot-threads/` |
| `world_rule` | `world-rules/` |
| `theme` | `themes/` |
| `relationship` | `relationships/` |
| `timeline_entry` | `timeline/` |
| `chapter_synopsis` | `chapters/` |

**Never construct a wiki file path from a bare slug.** Wiki pages live in subdirectories — `wiki/emre.md` does not exist; `wiki/characters/emre.md` does. Always use the `path` column from `index.md` or call `wiki-read` to access page content.

---

## Wikilink Conventions

- **Format:** `[[entity-slug]]` — always reference by slug, not display name
- Wikilinks appear in page body text to create cross-references between entities
- Used by the retrieval pipeline (T4) for graph traversal — pages linked from high-relevance pages are pulled into context automatically
- Every entity mentioned in a page body should have a corresponding wikilink

---

## Slug Naming Rules

All entity pages use slugified filenames. Rules:

- **Lowercase, hyphen-separated:** "Captain Elara Voss" → `elara-voss`
- **Drop titles/honorifics** from slugs unless essential for disambiguation: "Lord Blackwood" → `blackwood`, but "King Aldric" → `king-aldric` if multiple Aldrics exist
- **Locations** use the specific name: "The Thornwild" → `thornwild`
- **Events** use a descriptive slug: "Battle of Ashenmoor" → `battle-of-ashenmoor`
- **Plot threads** use the thread concept: "Marcus's Betrayal" → `marcus-betrayal`
- **Factions** use the group name: "The Northern Alliance" → `northern-alliance`
- **Items** use the item name: "Blade of the Dawn" → `blade-of-the-dawn`

Slugs are permanent — once assigned, a slug never changes (even if the entity's display name evolves). Aliases handle alternative references.

---

## Detail Level Format

Every entity page must include three detail levels for the context retrieval pipeline (see context-budgeting skill for how these are used).

### L1 — Headline (~30 tokens)

One sentence capturing the essential identity or role. Used in high-density context assembly when many entities need mention.

### L2 — Brief (~150 tokens)

Three sentences covering identity, current state, and primary relationship or role in the story. Used as the default detail level in scene context assembly.

### L3 — Full (~500 tokens)

Complete description including background, personality, relationships, current state, and narrative significance. Used when an entity is the POV character or central to the current scene.

---

## Example Pages

### Character: `characters/elara-voss.md`

```markdown
---
page_type: character
confidence: verified
first_appearance: 1
aliases: ["Captain Voss", "the Captain", "Elara"]
role: protagonist
status: alive
---
# Elara Voss

Captain Elara Voss commands the [[ashenmoor]] garrison, a remote frontier outpost on the edge of the [[thornwild]]. A decorated soldier of the Crown, she was reassigned after publicly questioning the King's war council. Her relationship with [[marcus-blackwood]] has grown strained since rumours of his involvement with the [[northern-alliance]] surfaced.

She carries the [[blade-of-the-dawn]], a ceremonial sword granted by the Crown that she now wields against its interests.

## Detail Levels

### L1
Captain Elara Voss, commander of the Ashenmoor garrison and reluctant leader of the northern resistance.

### L2
Captain Elara Voss commands the Ashenmoor garrison, a remote frontier outpost on the edge of the Thornwild. Once a decorated soldier of the Crown, she was reassigned to Ashenmoor after publicly questioning the King's war council. She now leads a growing resistance movement among the northern lords, driven more by duty to her soldiers than any political ambition.

### L3
Captain Elara Voss commands the Ashenmoor garrison, a remote frontier outpost on the edge of the Thornwild — a dark, ancient forest that locals believe is haunted. A former rising star in the Crown's military, she earned distinction during the Siege of Hartfall, where her tactical brilliance saved a regiment from encirclement. Her reassignment to Ashenmoor was officially a "strategic redeployment" but widely understood as punishment for publicly confronting General Aldric about the disastrous southern campaign.

At Ashenmoor, Elara discovered that the northern lords were already organising quiet resistance against the Crown's increasing taxation and military conscription. Rather than report their activities, she began coordinating with them — initially to protect her own garrison from supply shortages, but gradually out of genuine conviction that the Crown had lost its mandate. Her deputy, Lieutenant Kael, is fiercely loyal but uneasy about the path she's chosen.

Elara's relationship with Marcus Blackwood, once her closest ally at court, has fractured since his apparent defection to the northern cause preceded her own by months — and she suspects he may have engineered her reassignment to recruit her.
```

### Location: `locations/ashenmoor.md`

```markdown
---
page_type: location
confidence: verified
first_appearance: 1
aliases: ["the garrison", "Ashenmoor fortress"]
region: Northern Marches
---
# Ashenmoor

Ashenmoor is a remote frontier garrison on the northern edge of the kingdom, perched on grey cliffs overlooking the [[thornwild]]. The fortress serves as the Crown's northernmost military outpost and the de facto seat of power in the Northern Marches.

The garrison houses approximately 200 soldiers under [[elara-voss]]'s command. Its stone walls predate the current kingdom by centuries, built by a civilisation whose name has been forgotten. The lower levels contain sealed passages that the soldiers avoid.

## Detail Levels

### L1
Ashenmoor, a remote frontier garrison on the edge of the Thornwild, serving as the Crown's northernmost military outpost.

### L2
Ashenmoor is a remote frontier garrison perched on grey cliffs overlooking the Thornwild in the Northern Marches. The fortress houses approximately 200 soldiers under Captain Elara Voss's command and serves as the Crown's northernmost military outpost. Its ancient stone walls predate the current kingdom, and sealed passages in its lower levels remain unexplored.

### L3
Ashenmoor is a remote frontier garrison perched on grey cliffs overlooking the Thornwild — a vast, ancient forest that marks the kingdom's northern boundary. The fortress serves as the Crown's northernmost military outpost and the de facto seat of power in the sparsely populated Northern Marches region.

The garrison houses approximately 200 soldiers under Captain Elara Voss's command. Supplies arrive monthly via the King's Road, a three-day journey from the nearest town of Greyhaven. In winter, the road becomes impassable for weeks at a time, forcing the garrison to rely on stored provisions and whatever trade the local villages can provide.

The fortress itself is far older than the current kingdom. Its massive stone walls were built by a civilisation whose name has been lost to history — the same builders who constructed the sealed passages in the lower levels. Soldiers report strange sounds from behind the sealed doors, and standing orders prohibit exploration. The garrison's chapel was built over what appears to be an altar of the old civilisation, and the chaplain has noted that prayers spoken there sometimes produce unexpected echoes.
```

### Event: `events/battle-of-ashenmoor.md`

```markdown
---
page_type: event
confidence: planned
first_appearance: 12
aliases: ["the siege", "the Battle"]
chapter: 12
impact: major
---
# Battle of Ashenmoor

The Crown's punitive force besieges [[ashenmoor]] after [[elara-voss]]'s open declaration of support for the [[northern-alliance]]. The battle marks the point of no return for the northern rebellion.

[[marcus-blackwood]] arrives with reinforcements from the eastern lords, but his true allegiance remains ambiguous — it is unclear whether he has come to aid Elara or to ensure the Crown's victory from within.

## Detail Levels

### L1
The Crown's punitive force besieges Ashenmoor after Captain Voss's open declaration of support for the northern rebellion.

### L2
The Crown dispatches a punitive force to besiege Ashenmoor after Captain Elara Voss openly declares support for the Northern Alliance. The battle marks the point of no return for the rebellion. Marcus Blackwood arrives with eastern reinforcements, but his true allegiance remains ambiguous.

### L3
The Crown dispatches a punitive force of 800 soldiers under General Aldric's command to besiege Ashenmoor after Captain Elara Voss's open declaration of support for the Northern Alliance. The siege lasts three days, during which Elara's garrison of 200 holds the ancient fortress against repeated assaults, exploiting the narrow approach along the cliff road and the fortress's pre-kingdom defensive architecture.

On the second night, Marcus Blackwood arrives with 300 reinforcements from the eastern lords. His dramatic entrance through the Thornwild — a route considered impassable — shifts the military balance, but his true allegiance remains deeply ambiguous. He claims to support the northern cause, but Elara suspects he may be positioning himself as a power broker between Crown and rebellion.

The battle's outcome depends on whether the sealed lower passages of Ashenmoor can be opened. Elara discovers that the old civilisation's altar in the chapel holds the key, but using it may unleash forces that neither side can control.
```