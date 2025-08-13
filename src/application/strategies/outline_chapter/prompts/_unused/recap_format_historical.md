# Historical Events Formatter

## Task
Format historical events (events with `format: "historical"`) into a markdown section. These are events that happened more than 7 days ago and should be presented in a condensed, summary format.

## Input
You will receive a JSON array of events that have already been classified as historical (`format: "historical"`).

## Output Format
```markdown
### Historical Context
**YYYY-MM-DD to YYYY-MM-DD**: Brief summary of event
- Additional details if needed

**YYYY-MM-DD to YYYY-MM-DD**: Brief summary of another event
- Additional details if needed
```

## Formatting Rules

### 1. Date Formatting
- Use "YYYY-MM-DD to YYYY-MM-DD" format for date ranges
- If start and end dates are the same, use single date: "YYYY-MM-DD"

### 2. Content Style
- **Condensed summaries**: Focus on key plot points and outcomes
- **Essential details only**: What happened and why it matters to the story
- **Brief character development**: Major changes or realizations
- **Key locations**: Only mention if significant to the plot

### 3. Structure
- Start with "### Historical Context" header
- Each event gets its own paragraph with date and summary
- Use bullet points for additional details only if necessary
- Keep it concise - historical events should be background context

## Example

### Input:
```json
[
  {
    "date_start": "2023-09-01",
    "date_end": "2023-09-05",
    "summary": "Amy's family moves to new town and settles in.",
    "key_events": ["Family relocates", "Amy starts new school"],
    "character_development": ["Amy adjusts to new environment"],
    "locations": ["New town", "New school"],
    "compacted": true,
    "format": "historical"
  }
]
```

### Expected Output:
```markdown
### Historical Context
**2023-09-01 to 2023-09-05**: Amy's family moves to new town and settles in.
```

## Processing Instructions
1. Extract date_start and date_end for each event
2. Use the summary as the main description
3. Add bullet points only if key_events, character_development, or locations add critical context
4. Keep descriptions brief and focused on plot progression

<HISTORICAL_EVENTS>
{historical_events_json}
</HISTORICAL_EVENTS>
