# Progressive Compaction Test Examples

This document shows how the improved recap sanitizer handles progressive compaction with different timeline scenarios.

## Test Case 1: Early Story (Chapters 1-3)

### Input Recap:
```
Chapter 1: John arrives at mansion on 2024-01-15 at 2pm, meets Sarah, discovers mysterious letter
Chapter 2: 2024-01-16: Investigate letter, find clues in library, Sarah reveals she's been here before
Chapter 3: 2024-01-17: Explore basement, find hidden passage, Sarah gets nervous
```

### Expected Output:
```markdown
## Recap

### Historical Context
**2024-01-15 to 2024-01-16**: John arrives at the mansion, meets Sarah, and discovers a mysterious letter that leads to investigation and hidden passages.

### Current Chapter
**2024-01-17 10:00 to 2024-01-17 18:00**: Basement exploration and growing tension
- **Key Events**: Exploration of basement, discovery of hidden passage, Sarah's nervous reaction
- **Character Development**: Sarah's anxiety increases, John notices her unusual behavior
- **Locations**: Mansion basement, hidden passage entrance
- **Symbols/Motifs**: Hidden passage as metaphor for secrets, Sarah's nervousness as foreshadowing
```

## Test Case 2: Mid-Story (Chapters 10-15)

### Input Recap:
```
Chapter 1: John arrives at mansion, meets Sarah, discovers letter
Chapter 2: Investigate letter, find clues, Sarah reveals past connection
Chapter 3: Explore basement, find passage, Sarah gets nervous
Chapter 4: Find diary, learn about curse, John worries about Sarah
Chapter 5: Discover secret room with symbols, Sarah recognizes them
Chapter 6: Sarah admits she's family descendant, explains curse
Chapter 7: Decide to break curse, research symbols, find ritual
Chapter 8: Gather materials, Sarah anxious, John reassures her
Chapter 9: Perform ritual, something goes wrong, mansion shakes
Chapter 10: Escape collapsing mansion, Sarah injured, curse broken
Chapter 11: One week later, return to ruins, find survivors
Chapter 12: Help survivors adjust, learn more about curse history
Chapter 13: Sarah's family accepts her, John proposes
Chapter 14: Wedding planning, survivors integrate into community
Chapter 15: Wedding day arrives, ceremony at ruins site
```

### Expected Output:
```markdown
## Recap

### Historical Context
**2024-01-15 to 2024-01-24**: John and Sarah discover a mysterious letter, explore mansion secrets, uncover a family curse, and break it through a dangerous ritual that destroys the mansion but frees trapped family members.

### Recent Events
**2024-01-25 to 2024-02-06**: Return to ruins, discover survivors, help them adjust, and Sarah's family accepts her while John proposes marriage.

### Current Chapter
**2024-02-07 10:00 to 2024-02-07 18:00**: Wedding ceremony at the ruins
- **Key Events**: Wedding ceremony takes place at the ruins site, survivors attend as honored guests
- **Character Development**: Sarah and John's relationship culminates in marriage, survivors find closure
- **Locations**: Mansion ruins, wedding ceremony site
- **Symbols/Motifs**: Ruins as symbol of curse's end and new beginning, wedding as celebration of victory
```

## Test Case 3: Long Story (Chapters 50-55)

### Input Recap:
```
[Previous 49 chapters of complex story development...]
Chapter 50: Final confrontation with antagonist, epic battle
Chapter 51: Victory achieved, but at great cost
Chapter 52: Recovery and healing process begins
Chapter 53: Community rebuilds, new alliances formed
Chapter 54: Peace established, characters find their place
Chapter 55: Epilogue - one year later, showing lasting impact
```

### Expected Output:
```markdown
## Recap

### Historical Context
**Story beginning to Chapter 49**: Complex story involving multiple characters, conflicts, and developments that led to the final confrontation and resolution of the main plot.

### Recent Events
**Chapter 50 to Chapter 54**: Final confrontation and victory, recovery process, community rebuilding, and establishment of lasting peace.

### Current Chapter
**Chapter 55 - One year later**: Epilogue showing lasting impact
- **Key Events**: Epilogue reveals the lasting impact of the story's events on characters and world
- **Character Development**: Characters have grown and found their place in the new world order
- **Locations**: Various locations showing the transformed world
- **Symbols/Motifs**: Epilogue elements that reinforce the story's themes and resolution
```

## Key Benefits of Progressive Compaction

1. **Automatic Length Management**: As stories grow longer, older events are automatically compressed
2. **Focus on Relevance**: Only the most important historical events are retained
3. **Maintains Context**: Critical plot points and character developments are preserved
4. **Reduces Cognitive Load**: Shorter, more focused recaps are easier for the model to process
5. **Scalable**: Works for stories of any length, from short stories to epic novels

## Compaction Rules Summary

- **Historical Context (> 1 week)**: 1-2 sentences maximum, only critical plot points
- **Recent Events (1 week to 1 day)**: Brief bullet points, major developments
- **Current Chapter (24 hours)**: Full detailed format, complete context
- **Priority**: Plot-critical events > Character development > Background details 