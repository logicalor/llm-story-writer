# Extract Wiki Updates from Completed Chapter

You are extracting verified wiki updates from completed chapter `{chapter_number}`.

Known entities already in the wiki:

<EXISTING_ENTITIES>
{existing_entities}
</EXISTING_ENTITIES>

Completed chapter text:

<CHAPTER_TEXT>
{chapter_text}
</CHAPTER_TEXT>

## Task

Return one JSON object with four top-level keys:
- `new_entities`
- `state_changes`
- `timeline_events`
- `new_aliases`

Output schema:

```json
{
  "new_entities": [],
  "state_changes": [],
  "timeline_events": [],
  "new_aliases": []
}
```

## Rules

- Use `verified` confidence only. This pass operates on completed generated chapter text.
- Follow wiki maintenance rules strictly: extract only facts explicit in chapter text.
- Do not invent slugs for existing entities. Use only slugs supplied in `existing_entities`.
- Use exact singular wiki types: `character`, `location`, `plot_thread`, `event`, `theme`, `world_rule`, `relationship`, `item`, `faction`.
- Prefer updates to existing entities over creating duplicates.
- Aliases are additive only.

## What to return

### `new_entities`
Objects for newly introduced entities:

```json
{
  "name": "Nova Station",
  "type": "location",
  "aliases": [],
  "description": "A refueling station where the crew regroups after the ambush.",
  "confidence": "verified",
  "frontmatter": {
    "region": "Outer Belt"
  }
}
```

### `state_changes`
Objects for existing pages that need updates. Each must include `slug`. Optional keys:
- `frontmatter`: object of updated metadata
- `merge_body`: concise factual prose to append
- `body`: full replacement body when absolutely necessary

Example:

```json
{
  "slug": "mira-vale",
  "frontmatter": {
    "status": "alive"
  },
  "merge_body": "[Ch.4, verified] Mira publicly defects from the fleet and commits to the civilian convoy."
}
```

### `timeline_events`
Objects with:
- `time`
- `description`
- `chapter`

### `new_aliases`
Objects with:
- `slug`
- `aliases`

## Constraints mirroring wiki maintenance skill

- Never downgrade a higher-confidence fact.
- Treat direct chapter statements as authoritative.
- Record plot thread progression as updates, not duplicate creates, when an existing thread already matches.
- Use provenance inline in merge text when practical, such as `[Ch.{chapter_number}, verified]`.
- Keep descriptions factual and compact.

Return only valid JSON. No markdown fences. No commentary.