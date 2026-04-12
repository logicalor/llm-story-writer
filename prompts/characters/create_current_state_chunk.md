# Character Current State Chunk Generation

You are tasked with extracting and focusing on the current state of {character_name} from their full character sheet. Create a focused, detailed description of the character's present circumstances, emotional state, and current situation.

## Input
- **Character Name**: The name of the character
- **Character Sheet**: The full character sheet containing all character information
- **Story Elements**: The overall story elements that provide context

## Task
Extract and focus on the character's current state, creating a comprehensive but focused chunk that covers:

### Present Circumstances
- Current location and situation
- Immediate environment and surroundings
- What they are currently doing or involved in
- Recent events that have affected them

### Emotional State
- Current emotional condition and mood
- Recent emotional experiences or changes
- How they are feeling about their situation
- Emotional stability or volatility

### Physical Condition
- Current physical health and well-being
- Any injuries, fatigue, or physical stress
- Physical comfort or discomfort
- Energy levels and physical capabilities

### Mental State
- Current mental clarity and focus
- Stress levels and mental pressure
- Recent thoughts and preoccupations
- Mental energy and cognitive capacity

### Current Relationships
- How their relationships are currently functioning
- Recent changes in relationship dynamics
- Current social support or isolation
- Interpersonal tensions or harmony

### Immediate Concerns
- What is currently worrying or occupying them
- Immediate problems they are facing
- Current priorities and focus areas
- What they need to address right now

## Output Format
**CRITICAL: You MUST wrap your response in <output> tags. This is REQUIRED for proper processing.**

Create a focused, well-structured description of the character's current state that is:
- **Comprehensive**: Covers all major current state aspects
- **Present-Focused**: Emphasizes current situation over past or future
- **Focused**: Stays within the current state domain
- **Readable**: Well-organized and easy to understand
- **Dynamic**: Shows how they are currently affected by circumstances

## Guidelines
- Focus ONLY on current state and circumstances - avoid background or future plans
- Use the character's name throughout for clarity
- Emphasize what is happening now, not what has happened or will happen
- Provide specific details about their current situation
- Ensure consistency with the established character state
- Keep the focus on where they are now, not where they came from or where they're going
- **MANDATORY: Always wrap your complete response in <output> and </output> tags**

## REQUIRED OUTPUT FORMAT
**You MUST use this exact format with <output> tags:**

```xml
<output>
[Character Name]'s Current State

Present Circumstances:
- [Current location and situation]
- [What they are currently involved in]

Emotional Condition:
- [Current mood and emotional state]
- [Recent emotional experiences]

Physical State:
- [Current health and physical condition]
- [Energy levels and capabilities]

Mental State:
- [Current mental clarity and focus]
- [Stress levels and preoccupations]

Current Relationships:
- [How relationships are functioning now]
- [Recent changes in dynamics]

Immediate Concerns:
- [What is currently worrying them]
- [Current priorities and problems]
</output>
```

**IMPORTANT: Your response MUST begin with <output> and end with </output>. Do not include any text outside these tags.**

Remember: This chunk should be focused specifically on current state and circumstances, providing a clear understanding of where this character is right now and how they are currently affected by their situation.
