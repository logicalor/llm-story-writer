# Recent Events Formatter

## Task
Format recent events (events with `format: "recent"`) into a markdown section. These are events that happened 1-7 days ago and should include moderate detail to provide context for current events.

## Input
You will receive a JSON array of events that have already been classified as recent (`format: "recent"`).

## Output Format
```markdown
### Recent Events
**YYYY-MM-DD HH:MM to YYYY-MM-DD HH:MM**: Event summary
- **Key Events**: Important actions or occurrences
- **Character Development**: Changes in character state or relationships
- **Locations**: Where the events took place
- **Symbols/Motifs**: Recurring themes or elements (if present)

**YYYY-MM-DD HH:MM to YYYY-MM-DD HH:MM**: Another event summary
- **Key Events**: Important actions or occurrences
- **Character Development**: Changes in character state or relationships
- **Locations**: Where the events took place
```

## Formatting Rules

### 1. Date Formatting
- Use "YYYY-MM-DD HH:MM to YYYY-MM-DD HH:MM" format with specific times
- Preserve exact times from the input data

### 2. Content Style
- **Moderate detail**: More than historical but less than current events
- **Focus on relevance**: How these events connect to or set up current events
- **Character relationships**: Changes in dynamics between characters
- **Plot development**: Key story progression points

### 3. Structure
- Start with "### Recent Events" header
- Each event gets its own paragraph with date/time and summary
- Use bullet points for structured details:
  - **Key Events**: Required - main actions
  - **Character Development**: Required - character changes
  - **Locations**: Required - where it happened
  - **Symbols/Motifs**: Optional - only if present and relevant

## Example

### Input:
```json
[
  {
    "date_start": "2023-09-14 15:30",
    "date_end": "2023-09-14 17:00",
    "summary": "Amy meets her foster family for the first time.",
    "key_events": ["Introduction to foster parents", "Tour of new home"],
    "character_development": ["Amy feels nervous but hopeful"],
    "locations": ["Foster family home"],
    "symbols_motifs": ["New bedroom as symbol of fresh start"],
    "compacted": true,
    "format": "recent"
  }
]
```

### Expected Output:
```markdown
### Recent Events
**2023-09-14 15:30 to 2023-09-14 17:00**: Amy meets her foster family for the first time.
- **Key Events**: Introduction to foster parents, tour of new home
- **Character Development**: Amy feels nervous but hopeful
- **Locations**: Foster family home
- **Symbols/Motifs**: New bedroom as symbol of fresh start
```

## Processing Instructions
1. Extract date_start and date_end with times for each event
2. Use the summary as the main description
3. Format key_events, character_development, and locations as bullet points
4. Include symbols_motifs only if present in the data
5. Maintain moderate detail level - enough context without overwhelming detail

<RECENT_EVENTS>
{recent_events_json}
</RECENT_EVENTS>
