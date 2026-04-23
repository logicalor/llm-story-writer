# Extract Wiki Entities from Character or Setting Sheet

You are extracting wiki entities from a structured story sheet.

Sheet type: `{sheet_type}`
Primary entity name: `{entity_name}`
Sheets authoritative: `{sheets_are_authoritative}`

<SHEET_TEXT>
{sheet_text}
</SHEET_TEXT>

## Task

Return one JSON object with:
- `primary_entity`: the main entity described by the sheet
- `related_entities`: additional entities implied directly by the sheet

Output schema:

```json
{
  "primary_entity": {
    "name": "Display Name",
    "type": "character",
    "aliases": ["Alias"],
    "description": "Terse factual description grounded in the sheet.",
    "confidence": "planned",
    "frontmatter": {}
  },
  "related_entities": []
}
```

## Confidence

- Use `planned` by default.
- If `Sheets authoritative` is `true`, you may use `verified` when the sheet directly defines the fact.

## Sheet-specific rules

### If `{sheet_type}` is `character`
- `primary_entity.type` must be `character`.
- Related entities may include:
  - `relationship`
  - `location`
  - `item`
  - `faction`
- Put character-specific metadata in `frontmatter` when explicit:
  - `role`
  - `status`

### If `{sheet_type}` is `setting`
- `primary_entity.type` should usually be `location`.
- Related entities may include:
  - `item`
  - `faction`
  - `world_rule`
- Put location-specific metadata in `frontmatter` when explicit:
  - `region`

## Rules

- Extract only facts directly supported by the sheet.
- Do not duplicate the primary entity inside `related_entities`.
- Use exact singular wiki types: `character`, `location`, `plot_thread`, `event`, `theme`, `world_rule`, `relationship`, `item`, `faction`.
- Keep descriptions terse and factual.
- Use aliases only when the sheet clearly supports them.
- Return an empty `related_entities` array if none qualify.

## Example

```json
{
  "primary_entity": {
    "name": "Mira Vale",
    "type": "character",
    "aliases": ["Captain Vale"],
    "description": "A disciplined pilot whose loyalty is divided between her crew and the regime she serves.",
    "confidence": "planned",
    "frontmatter": {
      "role": "protagonist",
      "status": "alive"
    }
  },
  "related_entities": [
    {
      "name": "Mira and Tomas",
      "type": "relationship",
      "aliases": [],
      "description": "A strained sibling relationship marked by political distrust.",
      "confidence": "planned",
      "frontmatter": {}
    }
  ]
}
```

Return only valid JSON. No markdown fences. No commentary.