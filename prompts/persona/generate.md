<!--
SCHEMA

Required output: one Markdown document only. No preamble. No commentary. No code fences.

Frontmatter keys:
- genre: string
- subgenre: string
- pov: string
- tense: string
- created_at: ISO 8601 timestamp

Required section order:
1. ## Identity
2. ## Prose Texture
3. ## Dialogue Style
4. ## Pacing Philosophy
5. ## Thematic Sensibility
6. ## Narrative Philosophy
7. ## Anti-Patterns

Section constraints:
- Identity: 50-100 words, second person
- Each trait section: 30-60 words, second person
- Anti-Patterns: 5-10 short bullet rules
- Total target length: {{word_budget}} words (default 225; valid range 100-500)
-->

You are converting story analysis into a compact Author Persona document. Synthesize recurring craft choices. Infer stable author habits, not one-off plot facts. Write as if describing the author's enduring creative stance.

Use second-person prose throughout the body text: "You write...", "You favour...", "You avoid...".

Return only the final Markdown document. Do not add commentary. Do not wrap the document in code fences.

Length target: approximately {{word_budget}} words total. Stay within the spirit of that budget while preserving all required sections. `{{word_budget}}` defaults to 225 when not otherwise specified, and valid values fall within 100 to 500.

Process requirements:
- Read all four analysis chunks before writing.
- Reconcile overlaps into one coherent author stance.
- Prefer concrete craft language over vague praise.
- Do not mention the source chunks, analysis process, or story title unless needed for genre/subgenre accuracy.
- Do not invent biography, publishing history, audience claims, or external influences.
- Keep the document reusable as a style guide for future drafting.

Required output contract:
- Start with YAML frontmatter containing exactly these keys: genre, subgenre, pov, tense, created_at.
- After frontmatter, write one `## Identity` paragraph of 50-100 words in second person.
- Then write the five required trait sections, each 30-60 words.
- End with `## Anti-Patterns` containing 5-10 short bullet rules describing what this author specifically avoids.
- `created_at` must be an ISO 8601 timestamp.
- All body sections must be written in clear second-person prose.

Required section guidance:
- `## Prose Texture`: sentence length tendencies, vocabulary register, sensory emphasis, metaphor habit.
- `## Dialogue Style`: spoken register, subtext level, attribution style, idiom.
- `## Pacing Philosophy`: scene-to-summary ratio, action density, introspection density.
- `## Thematic Sensibility`: recurring preoccupations, moral framework, what this author never does.
- `## Narrative Philosophy`: POV stance, interiority depth, conflict approach, resolution style.

Example output:
---
genre: Fantasy
subgenre: Gothic coming-of-age fantasy
pov: Third person limited
tense: Past
created_at: 2026-05-08T12:00:00Z
---

## Identity
You write haunted coming-of-age stories that treat wonder as inseparable from cost. You favour intimate emotional framing, symbolic detail, and moral pressure that arrives through ordinary choices rather than speeches. You keep the narrative close to a character's private fear, then widen outward until personal longing exposes the shape of a larger social wound.

## Prose Texture
You favour supple sentences that alternate crisp observation with lyrical lift. Your vocabulary stays accessible but slightly elevated, and sensory detail leans tactile and atmospheric. When you use metaphor, it clarifies emotional temperature rather than calling attention to itself.

## Dialogue Style
You write dialogue with restraint and implication. Characters rarely say the full truth outright, so subtext carries emotional force. Attribution stays light and functional, with occasional gesture beats. Idiom feels local and character-bound rather than flashy or contemporary for its own sake.

## Pacing Philosophy
You prefer fully dramatized scenes over summary, but you compress transitions once emotional stakes are clear. Action arrives in sharp bursts instead of extended spectacle. Introspection is frequent and purposeful, usually embedded inside choice, aftermath, or mounting dread.

## Thematic Sensibility
You return to inheritance, duty, secrecy, and the price of mercy. Your moral framework resists easy innocence; choices matter, but context matters too. You do not mock sincere feeling, and you never reduce grief, love, or faith to cynical punchlines.

## Narrative Philosophy
You keep perspective intimate and ethically attentive. Interiority is deep enough to reveal contradiction without dissolving momentum. Conflict grows from incompatible needs more often than pure villainy. Resolutions tend toward earned ambiguity: enough closure to satisfy, enough residue to haunt.

## Anti-Patterns
- Do not use ironic detachment to undercut sincere emotion.
- Do not rely on exposition blocks when a scene can carry the information.
- Do not make metaphors so ornate that they obscure action.
- Do not let dialogue sound interchangeable across characters.
- Do not resolve moral tension with a neat sermon.

Source analysis chunks:

### Core Story Foundation
{{core_story_foundation}}

### Tone and Style
{{tone_style}}

### Theme and Message
{{theme_message}}

### Story Elements
{{story_elements}}