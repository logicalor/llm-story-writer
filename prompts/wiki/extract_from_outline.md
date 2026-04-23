# Extract Wiki Entities from Story Outline

You are extracting planned wiki entities from a story outline for story `{story_name}`.

<OUTLINE>
{outline}
</OUTLINE>

## Task

Return a JSON array of entity objects extracted from the outline.

Entity categories to extract:
- Characters
- Locations
- Plot threads
- Events
- Themes
- World rules

Use these exact singular `type` values:
- `character`
- `location`
- `plot_thread`
- `event`
- `theme`
- `world_rule`

Every entity object must have this shape:

```json
{
  "name": "Display Name",
  "type": "character",
  "aliases": ["Optional Alias"],
  "description": "One concise factual paragraph describing what the outline establishes.",
  "confidence": "planned"
}
```

## Rules

- Extract only entities explicitly supported by the outline.
- Confidence must always be `planned`.
- Use aliases only when the outline clearly gives alternate names or titles.
- Do not invent details beyond the outline.
- Do not emit duplicate entities.
- Prefer specific named entities over generic roles.
- Keep descriptions terse and factual.
- Return `[]` when no entities are present.

## Example

Input outline excerpt:

```text
Chapter 1: Captain Elara arrives at Blackglass Harbor.
The Smuggler Pact pressures her to recover the Ash Compass.
The story explores loyalty versus survival.
Ships may only cross the storm belt during the moonless tide.
```

Output:

```json
[
  {
    "name": "Captain Elara",
    "type": "character",
    "aliases": [],
    "description": "A captain who arrives at Blackglass Harbor and becomes central to the opening conflict.",
    "confidence": "planned"
  },
  {
    "name": "Blackglass Harbor",
    "type": "location",
    "aliases": [],
    "description": "A harbor location where the opening chapter takes place.",
    "confidence": "planned"
  },
  {
    "name": "Recover the Ash Compass",
    "type": "plot_thread",
    "aliases": [],
    "description": "A recovery objective that drives the opening conflict around the Ash Compass.",
    "confidence": "planned"
  },
  {
    "name": "Moonless Tide Passage",
    "type": "world_rule",
    "aliases": [],
    "description": "Ships may only cross the storm belt during the moonless tide.",
    "confidence": "planned"
  }
]
```

Return only valid JSON. No markdown fences. No commentary.