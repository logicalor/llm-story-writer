# Character Voice Skill

Guide for maintaining consistent, distinct character voices across a long-form narrative. In AI-generated fiction, voice drift — where all characters begin sounding like the narrator or each other — is the most common quality failure. This skill provides concrete techniques to prevent it.

---

## Dialogue Patterns

Each character should have identifiable speech patterns that persist across scenes and chapters:

- **Vocabulary level.** A scholar uses precise, technical language. A street vendor uses colloquial, direct language. A child uses simple words and asks questions. These patterns should remain stable.
- **Sentence length.** Some characters speak in clipped fragments. Others construct elaborate, clause-heavy sentences. Match sentence structure to character background and personality.
- **Verbal tics.** Repeated phrases, filler words, or habitual expressions (e.g., "Listen here," "If you follow my meaning," "Ah, well"). Use sparingly — one or two per scene — but consistently.
- **Formality register.** A diplomat speaks formally even in private. A soldier relaxes their register off-duty. A teenager shifts register between parents and friends. Track each character's register pattern.
- **Dialogue as character revelation.** What a character chooses to say — and what they avoid — reveals their priorities, fears, and values. A character who deflects personal questions with humour is revealing something.

---

## Internal Thought

The POV character's internal monologue is a direct expression of their personality:

- **Voice matches the character, not the narrator.** Internal thought should reflect the character's vocabulary, concerns, and worldview. A pragmatic character doesn't wax poetic in their head. A romantic character doesn't think in spreadsheets.
- **Personality traits as guardrails.** Use the character sheet's personality traits and motivations to filter internal observations. A suspicious character notices exits and escape routes. A compassionate character notices people in distress.
- **Current emotional state.** Internal thought reflects the character's emotional state from the wiki's `current_state` field. A grieving character's thoughts keep circling back to their loss. An excited character's thoughts race and jump.
- **Values and worldview.** What a character judges, dismisses, admires, or fears in their internal monologue reveals their core values. These should align with the character sheet and remain consistent.

---

## Behavioral Consistency

Actions must align with established character traits, growth arcs, and current state:

- **Trait-action coherence.** A cowardly character doesn't charge into danger without a compelling, earned reason. A methodical character doesn't act impulsively. When breaking pattern, acknowledge it — the character should notice their own deviation.
- **Growth arc respect.** Reference the character sheet's `growth_arc` field. Early in the arc, the character should exhibit their starting traits. Growth should be gradual and motivated by story events.
- **Current state continuity.** A character who was injured in the previous scene should still be injured. A character who received devastating news should still be processing it. Use the `current_state` field and prior scene events.
- **Habitual behaviours.** Small, repeated actions ground a character: the way they sit, how they handle objects, their response to silence. Establish these early and maintain them.

---

## Character Relationships

Dialogue and interaction patterns must reflect relationship dynamics from wiki pages:

- **Power dynamics.** A subordinate speaks differently to their superior than to their peers. Deference, challenge, formality — these shift based on relative status and respect.
- **Familiarity levels.** Old friends use shorthand, inside jokes, and comfortable silence. New acquaintances are more formal, more careful. Track how long characters have known each other.
- **Unspoken tensions.** Subtext in dialogue and interaction reveals tensions that characters won't address directly. A betrayed character might be excessively polite. Rivals might be overly casual.
- **History-informed reactions.** If characters have a shared history (documented in wiki relationships), their reactions to each other carry that weight. A reunion is different from a first meeting, even when the words are similar.
- **Group dynamics.** Characters behave differently in groups than one-on-one. A character who is bold with one person may be reserved in a crowd. Track these patterns.

---

## Voice Differentiation Techniques

Concrete techniques for ensuring characters don't sound alike:

- **Unique speech patterns.** Give each character at least one distinctive verbal habit: a favourite curse, a tendency to ask rhetorical questions, a habit of finishing others' sentences, or a pattern of understatement.
- **Contrasting formality levels.** In a scene with multiple characters, vary their formality registers. If one character speaks formally, another should speak casually. The contrast makes both more vivid.
- **Culture-specific expressions.** Characters from different cultures, regions, or social classes use different idioms, metaphors, and references. Draw from the character sheet's background and the world-building wiki.
- **Character-specific metaphors.** A sailor uses nautical metaphors. A baker thinks in terms of ingredients and timing. A warrior frames problems as battles. Source domain for metaphors should align with the character's life experience.
- **Silence and avoidance.** What a character refuses to talk about is as distinctive as what they say. Some characters fill silence nervously. Others weaponise it.

---

## Emotional Continuity

Character emotional state must carry between scenes and chapters:

- **No emotional resets.** A character doesn't go from devastated to cheerful between scenes without a reason. Emotional transitions take time and should be visible in the character's behaviour and internal thought.
- **Reference prior scene events.** When a character enters a new scene, their emotional state should reflect what happened in their last appearance. Use prior scene content and the character's `current_state` from the wiki.
- **Emotional undercurrents.** Even when a character is focused on a task, underlying emotions create texture. A character performing routine work while grieving will do it differently — slower, more mistakes, moments of distraction.
- **Emotional response proportionality.** Major events produce major emotional responses. Minor annoyances produce minor ones. Over-reaction or under-reaction should be intentional character traits, not generation artifacts.

---

## Character Growth

Voice should evolve subtly as the character develops through the story:

- **Early-story vs. late-story voice.** A character who starts naive and becomes worldly should shift vocabulary, speech patterns, and internal thought register over the course of the narrative. The shift should be gradual.
- **Pivotal moment effects.** Trauma, revelation, and transformation moments should leave lasting marks on voice. A character who discovers betrayal may become more guarded, more prone to suspicion in internal thought.
- **Growth through dialogue.** As characters grow, their dialogue should reflect it — new confidence, new doubt, new understanding. Returning to identical speech patterns after a growth event undermines the arc.
- **Regression under pressure.** Under extreme stress, characters may revert to earlier speech patterns and behaviours. This is realistic and can be a powerful storytelling tool.

---

## Common Pitfalls

Failure modes to actively avoid during generation:

- **Voice drift.** All characters gradually converge toward a single "default narrator" voice. Prevent by explicitly checking each character's dialogue against their speech pattern profile before finalising.
- **Emotional whiplash.** Characters swing between extreme emotions without transition or justification. Ensure emotional changes are motivated by story events and have visible progression.
- **Out-of-character actions for plot convenience.** A character acts completely against their established personality because the plot requires it. If the plot needs a character to act differently, provide in-story motivation and let the character struggle with the deviation.
- **Over-explaining motivations in dialogue.** Characters explain their feelings and reasoning in perfect, articulate paragraphs. Real people are often inarticulate about their own motivations. Use action and subtext instead.
- **Identical conflict responses.** Every character responds to conflict the same way (usually with wit or stoic calm). Vary responses: anger, withdrawal, deflection, humour, tears, silence, over-compensation.
- **Relationship amnesia.** Characters interact as if they have no history together. Always reference relationship dynamics from prior scenes and wiki relationship entries.
- **Static voice across growth arcs.** A character whose voice is identical in chapter 1 and chapter 25 despite major story events. Track and implement voice evolution deliberately.