Review the proposed chapter scene decomposition for clear structural problems only.

## Inputs

You will receive:
- `{scene_array_json}`: JSON array of scene objects for one chapter
- `{chapter_synopsis}`: synopsis the scenes are supposed to cover
- `{known_character_slugs}`: comma-separated wiki character slugs, may be empty
- `{known_location_slugs}`: comma-separated wiki location slugs, may be empty

## Goal

Find only concrete decomposition problems that would make scene drafting weaker or inconsistent.

Be conservative:
- Flag only clear structural violations
- Do not flag stylistic preferences
- Do not ask for richer prose, more atmosphere, or different wording
- Do not invent missing facts unless the synopsis clearly requires them
- If evidence is ambiguous, do not flag it

## Checks

Review the scene array against the synopsis for these issue types:

### Overlap Pairs

Flag pairs of scenes that cover the same beat, same confrontation, same reveal, same transition, or the same chunk of chapter timeline.

Use this when two scenes materially overlap instead of advancing to a new part of the chapter.

Output format:

```json
"overlap_pairs": [[0, 1, "both cover the opening confrontation"]]
```

### Missing POV

Flag a scene when the synopsis clearly requires a viewpoint anchor or focal character, but the decomposition omits that character or makes the scene's viewpoint unclear.

Use zero-based scene indexes.

Output format:

```json
"missing_pov": [{"scene_index": 2, "character": "Elena"}]
```

### Duplicate Setting

Flag adjacent or near-adjacent scenes that appear to duplicate the same setting without a meaningful progression in chapter time, purpose, or situation.

Do not flag repeated settings when the synopsis clearly calls for multiple distinct beats in the same place.

Output format:

```json
"duplicate_setting": [[1, 2, "Throne Room"]]
```

### Continuity Break

Flag a scene when its opening state clearly contradicts where the prior scene leaves the chapter, or when the sequence breaks synopsis continuity.

Output format:

```json
"continuity_break": [{"scene_index": 3, "reason": "Scene 3 opens with Amy at the cafe but scene 2 ends with her leaving for the airport"}]
```

## Wiki Hints

Known character slugs: {known_character_slugs}

Known location slugs: {known_location_slugs}

Use these only as weak continuity hints. Do not require exact slug usage in the scene JSON. Their purpose is to help detect obvious missing or duplicated references when the synopsis clearly points to known characters or locations.

## Chapter Synopsis

{chapter_synopsis}

## Scene Array JSON

```json
{scene_array_json}
```

## Output Rules

Return a single JSON object only.

Allowed keys:
- `overlap_pairs`
- `missing_pov`
- `duplicate_setting`
- `continuity_break`
- `summary`

Rules:
- Omit any key with no findings
- If there are no clear issues, return exactly `{}`
- `summary` should be one short line describing overall severity only when at least one issue exists
- Do not return markdown fences
- Do not return prose before or after the JSON object

## Example

```json
{
  "overlap_pairs": [[0, 1, "both cover the opening confrontation"]],
  "missing_pov": [{"scene_index": 2, "character": "Elena"}],
  "duplicate_setting": [[1, 2, "Throne Room"]],
  "continuity_break": [
    {
      "scene_index": 3,
      "reason": "Scene 3 opens with Amy at the cafe but scene 2 ends with her leaving for the airport"
    }
  ],
  "summary": "Several clear structural overlaps and continuity problems found."
}
```