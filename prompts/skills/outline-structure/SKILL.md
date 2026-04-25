# Outline Structure Skill

Reference for all data formats, schemas, and conventions used in the outline generation pipeline. Use this skill when building, validating, or extending outline-related tools and agents.

---

## Outline JSON Structure

The outline is an array of chapter entries. Each chapter contains a scenes array with structured scene definitions.

```json
[
  {
    "chapter_number": 1,
    "chapter_title": "The Awakening",
    "chapter_synopsis": "Brief summary of the chapter's events and purpose in the narrative arc.",
    "scenes": [
      {
        "scene_number": 1,
        "scene_title": "A Knock at Dawn",
        "scene_summary": "Brief summary of what happens in the scene.",
        "key_characters": ["character-slug-1", "character-slug-2"],
        "key_locations": ["location-slug-1"]
      }
    ]
  }
]
```

### Chapter Entry Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `chapter_number` | integer | yes | Sequential chapter number (1-based) |
| `chapter_title` | string | yes | Descriptive chapter title |
| `chapter_synopsis` | string | yes | Summary of chapter events, purpose, and contribution to narrative arc |
| `scenes` | array | yes | Ordered list of scene entries for this chapter |

### Scene Entry Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `scene_number` | integer | yes | Sequential scene number within the chapter (1-based) |
| `scene_title` | string | yes | Descriptive scene title |
| `scene_summary` | string | yes | Summary of scene action, conflict, and outcome |
| `key_characters` | string[] | yes | Character slugs involved in the scene |
| `key_locations` | string[] | yes | Location slugs where the scene takes place |

---

## Story Analysis Chunk Schema

The prompt analysis phase produces 8 independent analysis chunks. Each chunk examines one dimension of the story prompt.

| Category | Slug | Focus |
|----------|------|-------|
| Core Story Foundation | `core_story_foundation` | Premise, central question, genre, scope, time span |
| Character Foundation | `character_foundation` | Protagonists, antagonists, supporting cast, arcs, relationships |
| Setting Foundation | `setting_foundation` | World, geography, culture, technology level, atmosphere |
| Conflict & Stakes | `conflict_stakes` | Central conflict, personal stakes, escalation trajectory |
| Plot Structure | `plot_structure` | Act structure, turning points, climax, resolution |
| Theme & Message | `theme_message` | Thematic threads, moral questions, subtext |
| Tone & Style | `tone_style` | Narrative voice, POV, prose style, pacing rhythm |
| World Rules & Logic | `world_rules_logic` | Magic systems, technology rules, societal constraints, internal consistency |

Each chunk is saved as an independent savepoint (`analysis_chunk_{category}`) and later combined into the unified story elements.

---

## Story Elements Format

The `generate-elements` operation combines all 8 analysis chunks into a single `story_elements` savepoint. This unified document serves as the foundation for outline generation.

Structure:

```json
{
  "core_story_foundation": { "...": "analysis results" },
  "character_foundation": { "...": "analysis results" },
  "setting_foundation": { "...": "analysis results" },
  "conflict_stakes": { "...": "analysis results" },
  "plot_structure": { "...": "analysis results" },
  "theme_message": { "...": "analysis results" },
  "tone_style": { "...": "analysis results" },
  "world_rules_logic": { "...": "analysis results" }
}
```

---

## Savepoint Naming Conventions

The outline pipeline uses the following savepoint names. Each is created automatically by the corresponding tool operation.

| Savepoint Name | Created By | Description |
|----------------|------------|-------------|
| `understand_prompt` | `analyze-prompt` | Initial prompt comprehension |
| `analysis_chunk_{category}` | `analyze-prompt` | One per analysis category (8 total) |
| `story_start_date` | `analyze-prompt` | Extracted narrative start date |
| `base_context` | `analyze-prompt` | Extracted base context for generation |
| `story_elements` | `generate-elements` | Unified analysis from all 8 chunks |
| `outline_complete` | `generate-outline` | Full outline (non-chunked generation) |
| `outline_chunk_{start}_{end}` | `expand-chapter` | Chunked outline segment (e.g., `outline_chunk_1_10`) |
| `continuity_{start}_{end}` | `expand-chapter` | Continuity summary after chunk (e.g., `continuity_1_10`) |
| `critique_results_iteration_{N}` | `run-critics` | Critic scores for iteration N |
| `outline_refined_{N}` | `refine` | Refined outline after iteration N |

---

## Quality Criteria

### Outline Critique Threshold

- **Default threshold:** 87 (configurable via `outline_quality`)
- **Per-criterion floor:** 75 — any individual criterion scoring below 75 triggers refinement regardless of aggregate score

### Critic Types

The critique system employs 6 specialised critics:

| Critic | Focus |
|--------|-------|
| Structure | Plot arc coherence, act balance, pacing distribution |
| Character | Arc completeness, motivation consistency, growth trajectory |
| Continuity | Timeline consistency, cause-effect chains, foreshadowing |
| Stakes | Escalation trajectory, tension curves, resolution setup |
| Originality | Cliché avoidance, fresh angles, subverted expectations |
| Completeness | Scene coverage, missing plot threads, unresolved setups |

---

## Config Reference

Outline-related keys from `config.yml` under the `generation` section:

| Key | Default | Used By | Description |
|-----|---------|---------|-------------|
| `outline_quality` | 87 | `outline-planner` | Aggregate quality threshold for outline acceptance |
| `outline_min_revisions` | 0 | `outline-planner` | Minimum revision iterations before accepting |
| `outline_max_revisions` | 3 | `story-orchestrator` | Maximum revision iterations allowed |
| `enable_outline_critique` | false | `outline-planner` | Whether to run the critique/refinement loop |
| `outline_critique_iterations` | 3 | `outline-planner` | Maximum critique-refine cycles |
| `use_chunked_outline_generation` | true | `outline-planner` | Generate outline in chunks vs. all at once |
| `outline_chunk_size` | 10 | `outline-planner` | Chapters per chunk (when chunked generation enabled) |
| `wanted_chapters` | 25 | `story-orchestrator` | Target number of chapters in the outline |
| `expand_outline` | true | `story-orchestrator` | Whether to expand chapter outlines with scene breakdowns |