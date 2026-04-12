# Character Foundation Chunk Generation

You are tasked with analyzing the story prompt to identify all mentioned characters and, if necessary, create additional characters to support the story's needs. Focus on building a complete character foundation that serves the narrative requirements.

## Input
- **Prompt**: The original story prompt or request
- **Base Context**: Initial context extracted from the prompt
- **Story Elements**: Any existing story elements that have been identified

## Task
Your primary objectives are:

### 1. Extract Mentioned Characters
- Identify ALL characters explicitly mentioned in the prompt
- Extract character names, roles, and any provided details
- Note character relationships and dynamics mentioned
- Capture character goals, motivations, or conflicts stated

### 2. Create Supporting Characters (if needed)
- Analyze what character types would best support the story
- Identify gaps in the character roster that could enhance the narrative
- Create additional characters that serve specific story functions:
  - Antagonists or opposition forces
  - Mentors, guides, or wisdom figures
  - Allies, friends, or family members
  - Foils or contrasting characters
  - Minor characters that add depth and realism

## Character Foundation Elements

### Main Character Roster
- **Extracted Characters**: Characters mentioned in the prompt with their details
- **Created Characters**: Additional characters created to support the story
- **Character Functions**: The role each character plays in the narrative

### Character Relationships and Dynamics
- How characters relate to each other
- Power dynamics and hierarchies
- Alliances and conflicts between characters
- Character group structures and social networks

### Character Goals and Motivations
- What each main character wants
- Driving forces behind character actions
- Character conflicts and tensions
- Character growth objectives

### Character Backgrounds and Contexts
- Basic character origins and backgrounds
- Character social positions and contexts
- Character skills and capabilities
- Character limitations and weaknesses

## Output Format
Create a comprehensive character foundation that clearly distinguishes between extracted and created characters:

```xml
<output>
Character Foundation

Extracted Characters (from prompt):
- [Character name]: [Role/function] - [Brief description of what was mentioned]

Created Characters (to support story):
- [Character name]: [Role/function] - [Brief description and story purpose]

Character Relationships:
- [How characters relate to each other]
- [Power dynamics and alliances]

Character Goals:
- [What each character wants]
- [Driving forces and motivations]

Character Backgrounds:
- [Basic origins and contexts]
- [Skills and limitations]

Development Framework:
- [Character growth paths]
- [Transformation objectives]
</output>
```

## Guidelines
- **Extract First**: Start by thoroughly identifying all characters mentioned in the prompt
- **Analyze Gaps**: Determine what character types would strengthen the story
- **Create Purposefully**: Only add characters that serve clear narrative functions
- **Maintain Balance**: Ensure the character roster supports the story without overwhelming it
- **Focus on Function**: Emphasize how each character serves the story's needs
- **Keep Consistent**: Ensure all characters align with the established story concept

Remember: This chunk should provide a complete character foundation that includes both the characters explicitly mentioned in the prompt and any additional characters needed to create a compelling, well-supported narrative.
