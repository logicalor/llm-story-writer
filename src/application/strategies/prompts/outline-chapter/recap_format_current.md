# Current Events Formatter

## Task
Format current events (events with `format: "current"`) into a markdown section. These are events that happened today (0 days ago) and should include full detail as they are most relevant to the immediate story context.

## Input
You will receive a JSON array of events that have already been classified as current (`format: "current"`).

## Output Format
```markdown
### Current Events
**YYYY-MM-DD HH:MM to YYYY-MM-DD HH:MM**: Detailed event summary
- **Key Events**: Specific actions, dialogue, and occurrences
- **Character Development**: Detailed changes in character state, emotions, or relationships
- **Locations**: Specific places and environmental details
- **Symbols/Motifs**: Recurring themes, metaphors, or symbolic elements

**YYYY-MM-DD HH:MM to YYYY-MM-DD HH:MM**: Another detailed event summary
- **Key Events**: Specific actions, dialogue, and occurrences
- **Character Development**: Detailed changes in character state, emotions, or relationships
- **Locations**: Specific places and environmental details
- **Symbols/Motifs**: Recurring themes, metaphors, or symbolic elements
```

## Formatting Rules

### 1. Date Formatting
- Use "YYYY-MM-DD HH:MM to YYYY-MM-DD HH:MM" format with specific times
- Preserve exact times from the input data

### 2. Content Style
- **Full detail**: Maximum detail level for immediate story context
- **Specific actions**: Include dialogue, specific behaviors, and reactions
- **Emotional depth**: Character feelings, motivations, and internal states
- **Environmental details**: Setting descriptions that matter to the scene
- **Plot significance**: How events advance or complicate the story

### 3. Structure
- Start with "### Current Events" header
- Each event gets its own paragraph with date/time and detailed summary
- Use bullet points for structured details:
  - **Key Events**: Required - specific actions and dialogue
  - **Character Development**: Required - detailed emotional/psychological changes
  - **Locations**: Required - specific places and environmental context
  - **Symbols/Motifs**: Required - thematic elements and their significance

## Example

### Input:
```json
[
  {
    "date_start": "2023-09-15 06:00",
    "date_end": "2023-09-15 07:00",
    "summary": "House fire; Amy escapes and loses parents.",
    "key_events": ["Fire at home; Amy safely exits with help"],
    "character_development": ["Amy's life shatters, losing her parents in the fire"],
    "locations": ["Family home", "outside burning house"],
    "symbols_motifs": ["Fire as destruction; carrying out of parents symbolizes loss"],
    "compacted": false,
    "format": "current"
  }
]
```

### Expected Output:
```markdown
### Current Events
**2023-09-15 06:00 to 2023-09-15 07:00**: House fire; Amy escapes and loses parents.
- **Key Events**: Fire at home; Amy safely exits with help
- **Character Development**: Amy's life shatters, losing her parents in the fire
- **Locations**: Family home, outside burning house
- **Symbols/Motifs**: Fire as destruction; carrying out of parents symbolizes loss
```

## Processing Instructions
1. Extract date_start and date_end with times for each event
2. Use the summary as the main description
3. Format all available details as bullet points
4. Include all structured information: key_events, character_development, locations, symbols_motifs
5. Maintain maximum detail level - these events are most important to current story context

<CURRENT_EVENTS>
{current_events_json}
</CURRENT_EVENTS>
