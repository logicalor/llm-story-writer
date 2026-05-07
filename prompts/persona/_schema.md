# Author Persona Schema

This document defines the Markdown output contract for the `persona/generate` prompt.

## Frontmatter

The document must begin with a YAML frontmatter block.

| Field | Type | Constraints | Notes |
| --- | --- | --- | --- |
| `genre` | string | Required, non-empty | Broad shelf/category label |
| `subgenre` | string | Required, non-empty | More specific narrative mode or market positioning |
| `pov` | string | Required, non-empty | Narrative point of view, such as `First person` or `Third person limited` |
| `tense` | string | Required, non-empty | Dominant narrative tense |
| `created_at` | string | Required, ISO 8601 timestamp | Generation timestamp |

## Section Order

The body must appear in this order:

| Order | Section | Target length | Coverage |
| --- | --- | --- | --- |
| 1 | `## Identity` | 50-100 words | Concise overall author stance in second person |
| 2 | `## Prose Texture` | 30-60 words | Sentence length, vocabulary register, sensory emphasis, metaphor habit |
| 3 | `## Dialogue Style` | 30-60 words | Register, subtext level, attribution style, idiom |
| 4 | `## Pacing Philosophy` | 30-60 words | Scene-to-summary ratio, action density, introspection density |
| 5 | `## Thematic Sensibility` | 30-60 words | Preoccupations, moral framework, what the author never does |
| 6 | `## Narrative Philosophy` | 30-60 words | POV stance, interiority depth, conflict approach, resolution style |
| 7 | `## Anti-Patterns` | 5-10 bullets | Specific things the author avoids |

## Section Rules

- All prose sections must use second person.
- `## Identity` must be one paragraph.
- Each trait section should be one compact paragraph.
- Trait sections describe stable craft habits, not plot events or character facts.
- Total target length is driven by the prompt variable `{{word_budget}}`, with default 225 and valid range 100-500.

## Anti-Patterns Format

`## Anti-Patterns` must use Markdown bullet points.

- Use 5-10 bullets.
- Keep each bullet short and directive.
- Phrase each bullet as a negative rule or avoidance pattern.
- Focus on stylistic or narrative behaviors the author specifically avoids.

## Example Skeleton

```md
---
genre: Mystery
subgenre: Psychological mystery
pov: First person
tense: Present
created_at: 2026-05-08T12:00:00Z
---

## Identity
You write...

## Prose Texture
You favour...

## Dialogue Style
You write...

## Pacing Philosophy
You prefer...

## Thematic Sensibility
You return to...

## Narrative Philosophy
You keep...

## Anti-Patterns
- Do not...
```