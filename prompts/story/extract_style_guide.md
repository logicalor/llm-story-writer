# Extract Style Guide

You are a story-writing assistant. Read the story prompt below and extract a compact, reusable style guide.

<PROMPT>
{prompt}
</PROMPT>

Extract ONLY prose-style rules — not plot, not character backgrounds, not setting descriptions.

Focus on:
- **Banned words and phrases**: Any words, constructions, or cliches explicitly prohibited
- **POV rules**: Point of view (first/third person, limited/omniscient, whose perspective)
- **Voice and register**: Tone, tense, sentence rhythm, formality level
- **Non-negotiable world rules**: Hard facts about the world that must appear consistently (e.g. "magic is always painful", "no technology above medieval level")
- **Formatting rules**: Chapter length targets, scene break conventions, dialogue formatting

If a category has no rules, omit it entirely.

Format your response as a compact markdown document, ≤300 words total. Use short bullet points. No prose padding.

<EXAMPLE>
## Banned Phrases
- "like a knife through butter"
- "her heart skipped a beat"
- Ellipsis for dramatic pause (use em-dash instead)

## POV
- Deep third-person limited, Emma's perspective only
- No head-hopping within a scene

## Voice
- Present tense throughout
- Short declarative sentences; fragments allowed for effect
- Sardonic register; avoid sentimentality

## World Rules
- Magic requires blood sacrifice; always painful
- No character knows the true name of the antagonist

## Formatting
- Scenes: 500–800 words
- Chapter endings: always on an unresolved beat
</EXAMPLE>

Return only the style guide document. No preamble, no explanation.