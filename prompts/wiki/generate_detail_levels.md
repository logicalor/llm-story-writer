# Generate Wiki Detail Levels

You are generating compact wiki summaries for one entity.

Entity JSON:

```json
{entity}
```

## Task

Return one JSON object with exactly these keys:

```json
{
  "l1": "...",
  "l2": "...",
  "l3": "..."
}
```

## Targets

- `l1`: about 30 tokens
- `l2`: about 150 tokens
- `l3`: about 500 tokens

## Style

- Terse factual prose
- No bullet lists
- No markdown formatting
- No speculation beyond supplied entity data
- Preserve established confidence and current state from the entity JSON

## Guidance

- `l1`: one sentence, essential identity or role
- `l2`: short paragraph covering identity, current state, and narrative role
- `l3`: fuller paragraph covering background, current state, relationships, and significance when present in the entity JSON

## Example

Input entity:

```json
{
  "name": "Captain Elara Voss",
  "type": "character",
  "description": "Commander of the northern garrison who now leads a reluctant resistance.",
  "aliases": ["Captain Voss"],
  "confidence": "verified",
  "frontmatter": {
    "role": "protagonist",
    "status": "alive"
  }
}
```

Example output:

```json
{
  "l1": "Captain Elara Voss is the northern garrison commander who becomes a reluctant resistance leader.",
  "l2": "Captain Elara Voss commands the northern garrison and carries the burden of leading a resistance she never wanted. She is alive, respected, and increasingly central to the conflict. Her role in the story is to translate military authority into fragile political leadership.",
  "l3": "Captain Elara Voss is the commander of the northern garrison and a central protagonist whose authority emerges from discipline, endurance, and reluctant moral clarity. She remains alive and active, and the entity record frames her as a resistance leader rather than a detached officer. Her narrative significance comes from the way she links military command, civilian survival, and the broader political struggle. The summary should stay grounded in the supplied entity JSON and avoid inventing history or traits that are not explicitly present there."
}
```

Return only valid JSON. No markdown fences. No commentary.