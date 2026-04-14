# Wiki Schema

This file defines the structure and conventions for wiki pages in a story wiki.

## Page Types

### character

YAML frontmatter fields:

```yaml
type: character
name: "Full Name"
slug: full-name
confidence: verified | planned | speculative
first_appearance: 1          # chapter number
aliases: ["Nick Name", "Title Name"]
last_updated: "2026-01-01T00:00:00Z"
version: 1
role: protagonist | antagonist | supporting | minor
status: alive | dead | unknown | transformed
detail_levels:
  L1: "One-line summary (~30 tokens)"
  L2: "Three-sentence summary (~150 tokens)"
  L3: "Full description (~500 tokens)"
```

### location

```yaml
type: location
name: "Location Name"
slug: location-name
confidence: verified | planned | speculative
first_appearance: 1
aliases: []
last_updated: "2026-01-01T00:00:00Z"
version: 1
region: "Parent Region or Area"
detail_levels:
  L1: "One-line summary (~30 tokens)"
  L2: "Three-sentence summary (~150 tokens)"
  L3: "Full description (~500 tokens)"
```

### event

```yaml
type: event
name: "Event Name"
slug: event-name
confidence: verified | planned | speculative
first_appearance: 1
aliases: []
last_updated: "2026-01-01T00:00:00Z"
version: 1
chapter: 1                   # chapter where event occurs
impact: major | moderate | minor
detail_levels:
  L1: "One-line summary (~30 tokens)"
  L2: "Three-sentence summary (~150 tokens)"
  L3: "Full description (~500 tokens)"
```

### faction

```yaml
type: faction
name: "Faction Name"
slug: faction-name
confidence: verified | planned | speculative
first_appearance: 1
aliases: []
last_updated: "2026-01-01T00:00:00Z"
version: 1
detail_levels:
  L1: "One-line summary (~30 tokens)"
  L2: "Three-sentence summary (~150 tokens)"
  L3: "Full description (~500 tokens)"
```

### item

```yaml
type: item
name: "Item Name"
slug: item-name
confidence: verified | planned | speculative
first_appearance: 1
aliases: []
last_updated: "2026-01-01T00:00:00Z"
version: 1
detail_levels:
  L1: "One-line summary (~30 tokens)"
  L2: "Three-sentence summary (~150 tokens)"
  L3: "Full description (~500 tokens)"
```

### plot_thread

```yaml
type: plot_thread
name: "Thread Name"
slug: thread-name
confidence: verified | planned | speculative
first_appearance: 1
aliases: []
last_updated: "2026-01-01T00:00:00Z"
version: 1
status: active | resolved | dormant
detail_levels:
  L1: "One-line summary (~30 tokens)"
  L2: "Three-sentence summary (~150 tokens)"
  L3: "Full description (~500 tokens)"
```

### world_rule

```yaml
type: world_rule
name: "Rule Name"
slug: rule-name
confidence: verified | planned | speculative
first_appearance: 1
aliases: []
last_updated: "2026-01-01T00:00:00Z"
version: 1
detail_levels:
  L1: "One-line summary (~30 tokens)"
  L2: "Three-sentence summary (~150 tokens)"
  L3: "Full description (~500 tokens)"
```

### theme

```yaml
type: theme
name: "Theme Name"
slug: theme-name
confidence: verified | planned | speculative
first_appearance: 1
aliases: []
last_updated: "2026-01-01T00:00:00Z"
version: 1
detail_levels:
  L1: "One-line summary (~30 tokens)"
  L2: "Three-sentence summary (~150 tokens)"
  L3: "Full description (~500 tokens)"
```

### relationship

```yaml
type: relationship
name: "Entity A ↔ Entity B"
slug: entity-a-entity-b
confidence: verified | planned | speculative
first_appearance: 1
aliases: []
last_updated: "2026-01-01T00:00:00Z"
version: 1
detail_levels:
  L1: "One-line summary (~30 tokens)"
  L2: "Three-sentence summary (~150 tokens)"
  L3: "Full description (~500 tokens)"
```

### timeline_entry

```yaml
type: timeline_entry
name: "Event at Time"
slug: event-at-time
confidence: verified | planned | speculative
first_appearance: 1
aliases: []
last_updated: "2026-01-01T00:00:00Z"
version: 1
detail_levels:
  L1: "One-line summary (~30 tokens)"
  L2: "Three-sentence summary (~150 tokens)"
  L3: "Full description (~500 tokens)"
```

### chapter_synopsis

```yaml
type: chapter_synopsis
name: "Chapter N Synopsis"
slug: chapter-n-synopsis
confidence: verified | planned | speculative
first_appearance: 1
aliases: []
last_updated: "2026-01-01T00:00:00Z"
version: 1
detail_levels:
  L1: "One-line summary (~30 tokens)"
  L2: "Three-sentence summary (~150 tokens)"
  L3: "Full description (~500 tokens)"
```

### contradiction

```yaml
type: contradiction
name: "Contradiction Description"
slug: contradiction-description
confidence: verified | planned | speculative
first_appearance: 1
aliases: []
last_updated: "2026-01-01T00:00:00Z"
version: 1
detail_levels:
  L1: "One-line summary (~30 tokens)"
  L2: "Three-sentence summary (~150 tokens)"
  L3: "Full description (~500 tokens)"
```

## Wikilink Conventions

Cross-reference between wiki pages using `[[entity-slug]]` syntax within the markdown body of any page.

Examples:

- `[[john-smith]]` — links to the character page with slug `john-smith`
- `[[castle-of-winds]]` — links to the location page with slug `castle-of-winds`
- `[[the-great-war]]` — links to the event page with slug `the-great-war`

Wikilinks are used by the retrieval pipeline (ADR 005) for graph traversal (Tier 4) to discover related entities.

## Confidence Taxonomy

- **verified** — Confirmed by story text. The fact appears explicitly in a published chapter.
- **planned** — Outlined but not yet written. The fact exists in the story outline or plan but has not appeared in manuscript text.
- **speculative** — Inferred by agent. The wiki-maintainer agent deduced this fact from context but it has not been explicitly stated or planned.

## Naming Rules

- **Slug format:** kebab-case (lowercase, hyphens between words, no special characters)
- **File naming:** `{slug}.md` stored in the type subdirectory (e.g., `characters/john-smith.md`)
- **Slug generation:** lowercase the name, replace spaces and special characters with hyphens, strip leading/trailing hyphens, collapse consecutive hyphens
