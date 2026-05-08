# Patterns

## Analytical-agent exclusion from persona injection

Never pass `--persona-view` or inject a persona `system_message` into analytical agents (`recap-manager`, `critique-runner`, `consistency-checker`, `outline-critic`). These agents require neutral, unbiased evaluation. Persona injection skews analytical output toward the author's stylistic preferences, compromising correctness. See ADR 015; empirical basis: Kim et al. (2025) arXiv:2408.08631.

## Persona view selection by pipeline phase

Use the `outline` view for outline-level agents (`outline-generator` `expand-chapter`, `outline-generator` `refine`). Use the `chapter` view for scene-level generation (`scene-writer` `generate`, `scene-writer` `revise`). Use the `scrubber` view for prose scrubbing passes (`prose-scrubber`). Use the `editor` view for final editorial passes (`final-editor`). Never use the `chapter` full view at the outline level; it adds noise without benefit.
