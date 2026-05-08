# Author Persona

> Story-scoped authorial style profile that keeps generative phases aligned to one creative fingerprint.

## Overview

The author persona is the story's creative fingerprint: a compact Markdown document that captures authorial identity, narrative philosophy, prose preferences, dialogue tendencies, pacing habits, thematic priorities, and anti-patterns. The system generates it once per story, stores it at `stories/<name>/persona/persona.md`, and derives phase-specific views from that one canonical file at generation time.

The canonical file is not split into separate persisted variants. Instead, `persona-builder get-view` reads `persona.md` and projects one of four views:

| View | Used By | Pipeline Surface | Purpose |
|------|---------|------------------|---------|
| `outline` | `outline-generator` | Outline expansion and outline refinement during Phase 3 | Identity, narrative philosophy, thematic focus, pacing philosophy, and anti-patterns for outline-level planning |
| `chapter` | `scene-writer` | Chapter and scene generation or revision during the chapter loop | Full seven-section persona body for scene-level drafting |
| `scrubber` | `prose-scrubber` | Prose scrubbing passes | Short style-focused projection for prose texture and dialogue cleanup |
| `editor` | `final-editor` | Final editorial passes | Identity plus prose, dialogue, narrative philosophy, and anti-pattern constraints for late-stage polish |

The outline-level and chapter-level views are wired into implemented tools now. The scrubber and editor views exist as deterministic projections for the prose-quality passes.

## File Location

The canonical persona file lives at `stories/<name>/persona/persona.md`.

This file is the source of truth. The tool reads it when generation-time persona injection happens. No cached per-view files are written beside it.

## Generation Timing

Persona generation happens during Phase 3, the outline phase. The `outline-planner` workflow generates story elements first, then calls `persona-builder generate`, then proceeds into persona-aware outline expansion and refinement.

This placement keeps persona generation close to its source inputs: the outline-analysis chunks and story elements already owned by the outline phase.

## Inspect, Edit, Regenerate

Use the tool to inspect a specific projection:

```bash
persona-builder get-view --name <story> --view outline
persona-builder get-view --name <story> --view chapter
persona-builder get-view --name <story> --view scrubber
persona-builder get-view --name <story> --view editor
```

To edit the persona by hand, open `stories/<name>/persona/persona.md`, change the text, and save the file. Nothing else is required. The runtime reads the file at generation time, so manual edits take effect on the next persona-aware generation call.

To replace it entirely with a fresh generated version:

```bash
persona-builder regenerate --name <story>
```

`regenerate` archives the current persona, then generates a new canonical `persona.md`.

## Hand Override

Hand override is intentionally simple: edit `stories/<name>/persona/persona.md` in place.

- No rebuild step required.
- No derived-view cache to clear.
- No extra sync command required.

If you prefer full manual control, generate once, then keep refining the file yourself.

## Emphasis Delta

The persona itself is static for the story. Per-chapter tonal variation is handled separately through the emphasis delta.

`scene-writer` receives the chapter persona view through `--persona-view chapter`. When emphasis delta is enabled, a short per-chapter tonal hint is also passed through `--emphasis-delta`. That hint is appended to the user message, not merged into the persona file and not injected as a separate system message.

Use this distinction when debugging output:

- Persona controls stable story-level voice.
- Emphasis delta controls chapter-level tonal tilt.

## Configuration

The author-persona system is controlled through three generation settings.

### Disable Persona Entirely

Set the master switch to `false`:

```yaml
generation:
  enable_author_persona: false
```

When disabled, the system skips persona generation and suppresses persona-view injection.

### Disable Emphasis Delta Only

Set the chapter-level tonal hint switch to `false`:

```yaml
generation:
  enable_emphasis_delta: false
```

This leaves the static persona active while removing the extra per-chapter tonal hint.

### Tune Persona Length

The persona generator targets `generation.persona_word_budget`.

- Default: `225`
- Valid range: `100` to `500`

```yaml
generation:
  persona_word_budget: 225
```

Lower values produce tighter personas for smaller-context or smaller-capacity models. Higher values allow a richer style profile when the model and token budget can afford it.

## Analytical-Agent Exclusion

Persona injection is for generative agents only. Analytical agents stay neutral.

The system does not pass persona views into `recap-manager`, `critique-runner`, or `consistency-checker`. This follows ADR 015's exclusion principle: analytical passes should not be skewed toward the author's stylistic preferences. The same principle applies to outline-analysis sub-phases that extract or assess structure rather than generate prose.

## Related

- [ADR 015](../planning/adr/015-author-persona-system.md) — Author persona architecture, view model, and analytical-agent exclusion rationale
- [Story Orchestrator](./story-orchestrator.md) — Pipeline placement and phase order
