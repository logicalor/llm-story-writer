# Scene Writing Skill

Guide for generating high-quality individual scenes within a chapter. This skill covers narrative structure, pacing, transitions, and best practices for AI-driven scene generation using wiki-based context.

---

## Scene Structure

Every scene follows a three-part structure grounded in the scene definition fields:

### Beginning (Hook/Grounding)
- Open with a **hook** — a compelling image, line of dialogue, or sensory detail that draws the reader in.
- **Ground** the reader in the scene's setting (from the `setting` field) and establish the POV character's immediate situation.
- Use the `lead_in_to_next_scene` from the *previous* scene to create continuity. If this is the chapter's first scene, use the chapter-opening hook.

### Middle (Rising Action)
- Develop the scene's central `conflict` through character interaction, internal tension, or environmental pressure.
- Introduce `key_events` progressively — not all at once. Each event should feel earned by the preceding action.
- Weave in `dialogue` beats and `literary_devices` naturally. Dialogue should advance conflict, not just fill space.
- Build toward the scene's turning point.

### End (Turning Point or Transition)
- Deliver a **turning point** — a moment that changes the character's situation, understanding, or emotional state.
- Set up the `ending` as defined in the scene definition.
- Plant the `lead_in_to_next_scene` seed — a question, tension, or momentum that carries the reader forward.

### Scene Definition Fields Reference
- `title` — scene name (used for savepoints and chapter table of contents)
- `description` — brief summary of what happens
- `characters` — who appears in this scene
- `setting` — where and when the scene takes place
- `conflict` — the central tension or problem
- `tone` — emotional register (tense, reflective, humorous, etc.)
- `key_events` — plot-critical events that must occur
- `dialogue` — key dialogue beats or exchanges
- `ending` — how the scene resolves or suspends
- `lead_in_to_next_scene` — transition hook for narrative flow
- `literary_devices` — specific devices to employ (foreshadowing, metaphor, irony, etc.)

---

## Narrative Pacing

### Word Count Targets
- **Default range:** 750–1500 words per scene (configurable in story config).
- Action scenes trend toward the lower end — punchy, high-velocity prose.
- Emotional and introspective scenes trend toward the higher end — room for reflection and nuance.
- Exposition scenes fall in the middle — enough space to establish without dragging.

### Pacing Variation
- Alternate scene pacing within a chapter to create rhythm. A high-tension action scene followed by a quiet character moment creates breathing room.
- Avoid consecutive scenes at the same pace — monotony kills engagement.
- Chapter openings should establish pace quickly. Chapter closings should escalate toward a chapter-ending hook.

### Chapter Rhythm
- Early scenes in a chapter build the situation. Middle scenes escalate. Final scenes deliver the chapter's payoff.
- A typical 4-scene chapter: establish → complicate → escalate → turn.
- A typical 6-scene chapter: hook → develop → complicate → confront → turn → aftermath.

---

## Transitions

### Scene-to-Scene Continuity
- Use the `lead_in_to_next_scene` field from the previous scene definition to bridge into the next scene.
- Transitions can be temporal (time skip), spatial (location change), or perspectival (POV shift).
- Avoid abrupt jumps with no connective tissue — even a single grounding sentence bridges effectively.

### Chapter-Opening Hooks
- The first scene of a chapter should re-orient the reader after the chapter break.
- Ground quickly: who, where, when, what's at stake — within the first two paragraphs.
- If the previous chapter ended on a cliffhanger, address it promptly. Artificial delay frustrates readers.

### Chapter-Closing Momentum
- The final scene of a chapter should leave unresolved tension, a new question, or a revelation.
- Avoid tidy chapter endings that resolve everything — they kill forward momentum.
- The final line of the chapter is disproportionately important. Craft it deliberately.

---

## Point of View

### POV Consistency
- Maintain a single POV within each scene. Do not head-hop between characters mid-scene.
- The POV character is identified from the scene definition's `characters` field (typically the first listed, or explicitly marked).
- All sensory details, observations, and internal thoughts must be filtered through the POV character's perspective.

### POV Character Identification
- Use the scene definition to determine whose perspective drives the scene.
- If the scene definition does not specify a POV character, default to the story's protagonist or the character with the most at stake in the scene.

### Multi-POV Stories
- Different scenes or chapters may use different POV characters.
- When switching POV, establish the new character's voice immediately — readers need quick orientation.
- Maintain distinct voice, priorities, and observational patterns for each POV character (see the character-voice skill).

---

## Show Don't Tell

- **Sensory details over abstract statements.** "His hands trembled" instead of "He was nervous."
- **Dialogue reveals character.** What characters say (and don't say) shows who they are better than narration about their personality.
- **Action reveals personality.** How a character reacts under pressure, the small habits they display, the choices they make — these are characterisation.
- **Emotion through physicality.** Describe the physical manifestations of emotion rather than naming the emotion directly. "Her jaw tightened" rather than "She was angry."
- **Environment reflects mood.** Use setting details to reinforce emotional tone. A ticking clock in a tense scene. Rain in a melancholy scene. But avoid cliché — subvert when possible.

---

## Scene Types

Different scene types call for different generation strategies. Match the `sceneType` parameter used with `wiki-snapshot`:

### Dialogue-Heavy Scenes
- Focus on distinct character voices (speech patterns, vocabulary, rhythm).
- Use dialogue tags sparingly — action beats ("She set down her cup") are stronger than "she said."
- Subtext is critical — what characters avoid saying matters as much as what they say.
- Keep narration between dialogue lines minimal to maintain conversational pace.

### Action Scenes
- Short sentences. Short paragraphs. Rapid pacing.
- Concrete, physical language — describe what the body does, not what the character thinks about doing.
- Limit internal monologue during high-action moments — save reflection for before and after.
- Spatial clarity — the reader should always know where characters are in relation to each other.

### Exposition Scenes
- Weave information into character activity — a character examining a map, discussing history over a meal, discovering a document.
- Avoid info-dumps. Distribute exposition across multiple scenes when possible.
- Use character curiosity as a delivery mechanism — questions feel natural, lectures don't.
- Balance new information with forward plot movement. Every exposition scene should also advance the story.

### Mixed Scenes
- Blend elements naturally. A conversation that escalates into conflict. An exploration scene that delivers exposition through discovery.
- Let the dominant element drive pacing, with secondary elements providing texture.
- Transition between modes smoothly — avoid abrupt shifts from contemplation to action without a trigger.

---

## Context Usage

How to effectively use the wiki snapshot context provided by `wiki-snapshot`:

### Prioritise POV Character Details
- The POV character's personality traits, speech patterns, current emotional state, and active goals should directly influence narration and internal thought.
- Reference specific details from the character's wiki page — appearance, mannerisms, relationships — to maintain consistency.

### Use Setting Details for Atmosphere
- Pull sensory details from the setting's wiki page — architecture, climate, ambient sounds, lighting.
- Ground each scene in its physical environment within the first few paragraphs.
- Use setting to reinforce or contrast the scene's emotional tone.

### Weave in Active Plot Threads
- Reference ongoing plot threads from the wiki snapshot naturally through character dialogue, thoughts, or observations.
- Do not force plot thread references where they don't belong. If a plot thread isn't relevant to the scene, omit it.
- Advance at least one plot thread per scene, even if incrementally.

### Reference World Rules Implicitly
- World-building rules (magic systems, political structures, technology levels) should be embedded in character behaviour and environmental description.
- Characters should act within established rules without explicitly explaining them to the reader.
- When rules are relevant to the scene's conflict, demonstrate them through action rather than exposition.

---

## Quality Indicators

What distinguishes a well-generated scene:

- **Narrative tension.** The scene has stakes — something the POV character wants, fears, or must resolve. Even quiet scenes have undercurrents of tension.
- **Character voice consistency.** The POV character sounds like themselves throughout. Dialogue voices are distinct and recognisable.
- **Sensory grounding.** The reader can see, hear, smell, and feel the scene's environment. At least two senses are engaged in every scene.
- **Forward momentum.** The scene changes something — a relationship, a piece of knowledge, a decision, a situation. Static scenes that return to their starting state waste the reader's time.
- **Thematic resonance.** The scene's events, imagery, or dialogue connect to the story's larger themes, even subtly.
- **Earned emotion.** Emotional moments are built up to, not arrived at arbitrarily. The reader should feel the emotion, not just be told it exists.
- **Satisfying structure.** The scene has a clear beginning, development, and turning point. The reader finishes the scene with a sense of completion and curiosity about what comes next.