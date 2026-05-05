You are performing an inline prose scrub on a single scene from an ongoing story. Rewrite the scene with all prose issues corrected. Output only the corrected scene text — no commentary, no summaries, no JSON.

## Scene to Scrub
Scene {scene_num} of Chapter {chapter_num}.

<SCENE_CONTENT>
{scene_content}
</SCENE_CONTENT>

## Scene Definition (scope guard — do not remove or add events)
<SCENE_DEFINITION>
{scene_definition}
</SCENE_DEFINITION>

## What to Fix

Apply every applicable correction below. Make only changes that materially improve the prose. Do not create busywork edits. Do not alter plot events, entity facts, character names, or chronology.

### 1. Adverb overuse
Remove or replace weak adverbs that prop up insufficient verbs. Common offenders: quickly, suddenly, softly, quietly, sharply, immediately, slowly, carefully, finally, heavily.
Replace with a stronger verb or a concrete sensory beat. If the adverb is doing real work, leave it.

### 2. Filter words
Remove distancing filter constructions: "he saw that", "she felt that", "she noticed that", "he heard", "she watched", "she realised that", "he thought that", and close equivalents.
Rewrite to place the reader directly inside the perception.

### 3. Repetition
Eliminate repeated sentence openings, echoed wording, or mirrored phrasing within close proximity.
Vary sentence structure and diction. Do not introduce new meaning to solve repetition.

### 4. Show-vs-tell
Where a sentence names an emotional or sensory state that could be rendered concretely, rewrite it as a sensory or behavioural detail.
Apply only when a concrete rendering is available and unambiguous. Do not strip emotion where abstraction is deliberate.

### 5. Contrastive negation (AI tell)
Detect and rewrite these patterns — they signal hollow AI-style elevation rather than earned prose:

**Hard patterns — always rewrite:**
- "It wasn't just X, it was Y" and variants ("She wasn't just X — she was Y", "This wasn't just X; it was Y")
- Semicolon negation-reframe: "It didn't X; it Y" / "He wasn't X; he was Y" when both sides are vague
- Em-dash negation escalation: "He wasn't afraid — he was terrified" (generic → generic superlative)
- Fragment negation: "Not X — but Y" / "Not just X, but Y" where neither side is concrete

**Soft patterns — rewrite when both sides are generic:**
- "more than just X"
- "something beyond X"
- "something more than ordinary X"
- "went beyond mere X"

**Fix:** Cut the negation half entirely. State the elevated claim once, directly, as a concrete sensory or behavioural beat. Do not simply substitute a different negation frame.

**Specificity exception:** Leave the negation intact when both halves carry specific concrete content and the contrast is doing clear dramatic work. Example that survives: "It wasn't the wound that stopped him — it was the sound she made when she saw it."

## Scope Constraints
- Preserve all plot events defined in the scene definition.
- Preserve all character names and aliases exactly as written — do not normalise or correct them.
- Do not add new events, characters, or world facts not already present in the scene.
- Do not alter dialogue meaning, only surface-level prose issues.
- Every fix stays at sentence or paragraph scope.

## Output
Output only the corrected scene text. No preamble, no JSON, no labels, no commentary.
