# Recap Prompts

This directory contains prompts for the recap generation and processing pipeline in the outline-chapter strategy.

## Prompt Functions

### Core Recap Generation
- **`extract_events.md`** - Extracts events from chapter content into structured JSON format
- **`assign_event_timing.md`** - Assigns temporal context and timing to extracted events
- **`enrich_event_details.md`** - Adds character development, location, and symbolic details to events
- **`format_json.md`** - Formats enriched events into final JSON recap output with metadata

### Event Processing
- **`compact_events.md`** - Applies progressive compaction to events based on importance and recency
- **`outline.md`** - Generates chapter outlines with recap context

**Note**: Event filtering by age is now handled programmatically in the `RecapManager` class for better performance and reliability.

### Sanitization & Validation
- **`sanitize.md`** - Enhanced sanitization with progressive compaction and timeline organization

## Workflow

1. **Extract Events** → `extract_events.md` (Chapter content → JSON events)
2. **Assign Timing** → `assign_event_timing.md` (Add temporal context)
3. **Enrich Details** → `enrich_event_details.md` (Add character, location, symbolic details)
4. **Format Output** → `format_json.md` (Final JSON recap structure)
5. **Sanitize** → `sanitize.md` (Consistency and compaction)
6. **Filter Events** → Programmatic filtering (Remove aged events based on importance)

## JSON Structure

All prompts output consistent JSON format with:
- Event arrays with dates, summaries, and metadata
- Character development tracking
- Location and symbolic motif information
- Progressive compaction based on recency and importance
- Timeline organization for easy consumption

## Usage

These prompts are used by the `RecapManager` class to:
- Generate recaps during chapter creation
- Process and sanitize existing recaps
- Maintain consistency across the story timeline
- Provide context for subsequent chapter generation
