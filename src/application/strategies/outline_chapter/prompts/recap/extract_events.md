# Recap Event Extraction - Stage 1

You are an event extraction specialist. Your job is to extract and normalize events from chapter content.

## Input
You will receive:
1. **Chapter Content**: The current chapter's content that needs to be processed
2. **Chapter Number**: The current chapter number for context

## Task
Extract all events from the chapter content and normalize them into a structured format.

**CRITICAL**: Focus on extracting events from the Chapter Content only.

## Output Format
Output a JSON array of events with the following structure:

```json
[
  {
    "summary": "Brief description of the event",
    "type": "event_type",
    "key_events": ["List", "of", "key", "events"],
    "character_development": ["List", "of", "character", "changes"],
    "locations": ["List", "of", "locations"],
    "symbols_motifs": ["List", "of", "symbols", "or", "motifs"],
    "importance": "high|medium|low"
  }
]
```

## Event Types
Use these standard event types to categorize each event:
- **arrival**: Character arrives at a location
- **departure**: Character leaves a location
- **conversation**: Dialogue or discussion between characters
- **discovery**: Finding or learning something new
- **action/activity**: Physical actions or activities
- **routine**: Daily activities, meals, normal tasks
- **tragedy**: Accidents, sudden negative events
- **medical**: Treatment, examinations, health-related
- **emotional**: Processing feelings, reactions, internal states
- **ceremony**: Formal events, rituals, celebrations
- **travel**: Moving between locations
- **investigation**: Searching, exploring, examining
- **conflict**: Arguments, fights, confrontations
- **revelation**: Important information being revealed

## Processing Rules

### 1. Event Extraction
- **Extract from Chapter Content**: Focus on the current chapter's narrative
- Extract each distinct event or narrative moment as separate entries
- **NEVER combine events from different narrative moments** - each distinct event should have separate entries
- Preserve chronological order from the input
- **PRESERVE ALL EVENTS** - do not drop or lose any events from the chapter content

### 2. Importance Assessment
- **High**: Major plot points, character revelations, critical discoveries
- **Medium**: Character development, relationship changes, plot progression
- **Low**: Background details, minor events, descriptive information

### 3. Deduplication Rules
- Remove only exact duplicates with identical content
- **DO NOT merge events with different content**
- Keep the most detailed version only when events are truly identical

## Example

### Input:
```
<CHAPTER_CONTENT>
Chapter 3: The Investigation Deepens

Sarah and John continued their exploration of the mansion. In the library, they discovered an old diary that revealed the mansion's dark history. Sarah's hands trembled as she read about the previous owners' mysterious disappearances.

Later that evening, around 8 PM, they heard strange noises coming from the basement. John insisted on investigating, but Sarah was reluctant, remembering the diary's warnings.
</CHAPTER_CONTENT>
```

### Example Output:
```json
[
  {
    "summary": "Library exploration reveals mansion's dark history",
    "type": "discovery",
    "key_events": ["explore library", "discover old diary", "learn about mysterious disappearances"],
    "character_development": ["Sarah's anxiety increases", "both characters gain knowledge of danger"],
    "locations": ["library"],
    "symbols_motifs": ["diary as source of truth", "mansion's dark history"],
    "importance": "high"
  },
  {
    "summary": "Strange noises from basement create tension",
    "type": "discovery",
    "key_events": ["hear strange noises from basement", "John wants to investigate", "Sarah is reluctant"],
    "character_development": ["John shows bravery", "Sarah shows caution based on diary warnings"],
    "locations": ["basement area"],
    "symbols_motifs": ["basement as source of danger", "warnings from the past"],
    "importance": "medium"
  }
]
```

## Your Task

Extract and normalize all events from the provided chapter content.

<CHAPTER_CONTENT>
{chapter_content}
</CHAPTER_CONTENT>

<CHAPTER_NUMBER>
{chapter_num}
</CHAPTER_NUMBER>

**CRITICAL REMINDERS:**
- **PRESERVE ALL EVENTS** - Every event from the chapter content must appear in the output
- **SEPARATE DISTINCT EVENTS** - Each distinct narrative moment should be a separate entry
- **NO EVENT MERGING** - Never combine events with different content
- **Focus on content extraction** - Do not worry about dates, timing, or previous recap (that's handled later)
- **Extract only from current chapter** - Previous recap integration happens in the timing step

## Processing Steps

1. **Read Chapter Content** - Extract all events from the current chapter
2. **Categorize events** - Assign appropriate event types
3. **Assess importance** - Rate each event's significance
4. **Remove exact duplicates** - Keep most detailed version
5. **Output JSON array** - Include all extracted events

**IMPORTANT**: 
- Output only valid JSON array. No explanations or additional text.
- Extract events sequentially from the chapter content, maintaining the narrative flow
- **Do not assign dates or times** - focus purely on event content and structure
- **Do not integrate with previous recap** - that's handled in the next pipeline step 