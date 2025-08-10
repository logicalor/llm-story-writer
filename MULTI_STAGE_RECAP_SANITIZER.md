# Multi-Stage Recap Sanitizer Pipeline

This document describes the advanced multi-stage recap sanitizer pipeline that provides better reliability, debugging, and progressive compaction.

## Overview

The multi-stage pipeline breaks down the recap sanitization process into three specialized stages, each with a focused responsibility:

1. **Stage 1: Event Extraction** - Extract and normalize events from input recaps
2. **Stage 2: Event Compaction** - Apply progressive compaction based on age and importance
3. **Stage 3: Output Formatting** - Format compacted events into final markdown structure

## Pipeline Architecture

```
Input Recaps → Stage 1 → Stage 2 → Stage 3 → Final Output
                ↓         ↓         ↓
            Extract   Compact   Format
            Events    Events    Output
```

### Stage 1: Event Extraction (`recap_extract_events.md`)

**Purpose**: Extract and normalize events from messy recap data

**Input**: Raw recap text from previous and latest chapters
**Output**: JSON array of normalized events with structured data

**Key Features**:
- Date normalization to consistent format
- Event deduplication and merging
- Importance assessment (high/medium/low)
- Structured JSON output for easy processing

**Example Output**:
```json
[
  {
    "date_start": "2024-01-15 14:00",
    "date_end": "2024-01-15 23:59",
    "summary": "John arrives at mansion and discovers mysterious letter",
    "key_events": ["John arrives at mansion", "meets Sarah", "discovers mysterious letter"],
    "character_development": ["John and Sarah establish initial relationship"],
    "locations": ["mansion entrance", "various rooms"],
    "symbols_motifs": ["mysterious letter as plot catalyst"],
    "importance": "high",
    "source": "previous"
  }
]
```

### Stage 2: Event Compaction (`recap_compact_events.md`)

**Purpose**: Apply progressive compaction based on event age and importance

**Input**: JSON array of normalized events from Stage 1
**Output**: JSON array of compacted events with appropriate format

**Compaction Rules**:
- **Current Chapter** (Last 24 hours): Full detail format
- **Recent Events** (1 day to 1 week ago): Brief bullet format
- **Historical Context** (More than 1 week ago): Single sentence summary

**Example Output**:
```json
[
  {
    "date_start": "2024-01-15",
    "date_end": "2024-01-16",
    "summary": "John arrives at mansion, meets Sarah, discovers mysterious letter, and investigates it to find clues about Sarah's past connection to the mansion.",
    "compacted": true,
    "format": "historical"
  },
  {
    "date_start": "2024-01-17 00:00",
    "date_end": "2024-01-17 23:59",
    "summary": "Basement exploration reveals hidden passage and Sarah's anxiety",
    "key_events": ["explore basement", "find hidden passage", "Sarah gets nervous"],
    "character_development": ["Sarah's anxiety increases", "John notices unusual behavior"],
    "locations": ["basement", "hidden passage"],
    "symbols_motifs": ["hidden passage as metaphor for secrets"],
    "compacted": false,
    "format": "current"
  }
]
```

### Stage 3: Output Formatting (`recap_format_output.md`)

**Purpose**: Format compacted events into final markdown structure

**Input**: JSON array of compacted events from Stage 2
**Output**: Final markdown recap with proper structure

**Formatting Rules**:
- Group events by format type (historical, recent, current)
- Apply appropriate date formatting for each section
- Generate proper markdown structure
- Handle empty sections gracefully

## Benefits of Multi-Stage Approach

### 1. **Better Error Handling**
- Each stage can fail independently
- Automatic fallback to single-stage if multi-stage fails
- Detailed logging for debugging each stage

### 2. **Improved Reliability**
- Focused responsibilities reduce cognitive load on each model
- Structured JSON intermediate formats prevent formatting errors
- Validation at each stage ensures data quality

### 3. **Enhanced Debugging**
- Clear separation of concerns makes issues easier to identify
- Intermediate outputs can be inspected and validated
- Stage-specific error messages for better troubleshooting

### 4. **More Accurate Compaction**
- Dedicated compaction stage with focused rules
- Better date handling and age calculations
- Importance-based filtering for optimal content preservation

### 5. **Scalability**
- Each stage can be optimized independently
- Easy to add new stages or modify existing ones
- Can use different models for different stages if needed

## Usage

### Configuration

Enable multi-stage processing in `config.md`:

```yaml
generation:
  use_improved_recap_sanitizer: true
  use_multi_stage_recap_sanitizer: true
```

### Toggle Script

Use the toggle script to switch between modes:

```bash
# Switch to multi-stage pipeline
python toggle_recap_sanitizer.py multi

# Switch to improved single-stage
python toggle_recap_sanitizer.py new

# Switch to original sanitizer
python toggle_recap_sanitizer.py old

# Check current status
python toggle_recap_sanitizer.py status
```

### Debug Mode

Enable debug mode to see detailed stage-by-stage processing:

```yaml
generation:
  debug: true
  use_improved_recap_sanitizer: true
  use_multi_stage_recap_sanitizer: true
```

This will log:
- Stage 1: Event extraction progress
- Stage 2: Compaction decisions and results
- Stage 3: Formatting process
- Any fallbacks to single-stage processing

## Fallback Strategy

The multi-stage pipeline includes robust fallback mechanisms:

1. **Stage Failure**: If any stage fails, automatically falls back to single-stage processing
2. **JSON Parsing Errors**: Validates JSON output at each stage
3. **Empty Results**: Handles cases where stages produce no output
4. **Model Errors**: Graceful degradation if model calls fail

## Performance Considerations

### Speed
- **Multi-stage**: Slightly slower due to 3 model calls, but more reliable
- **Single-stage**: Faster but may have more formatting errors
- **Original**: Fastest but most prone to confusion and errors

### Quality
- **Multi-stage**: Highest quality with progressive compaction
- **Single-stage**: Good quality with improved prompts
- **Original**: Basic quality with complex template

### Memory Usage
- **Multi-stage**: Higher memory due to intermediate JSON storage
- **Single-stage**: Moderate memory usage
- **Original**: Lowest memory usage

## Troubleshooting

### Common Issues

1. **Stage 1 Fails**: Check input recap format and date parsing
2. **Stage 2 Fails**: Verify JSON output from Stage 1
3. **Stage 3 Fails**: Check compacted events format from Stage 2
4. **Fallback Triggered**: Review logs to identify which stage failed

### Debug Commands

```bash
# Check current configuration
python toggle_recap_sanitizer.py status

# Enable debug mode in config.md
generation:
  debug: true

# Test with a simple recap to isolate issues
```

### Log Analysis

Look for these log messages:
- `"Recap sanitizer: Starting Stage 1 - Event extraction"`
- `"Recap sanitizer: Starting Stage 2 - Event compaction"`
- `"Recap sanitizer: Starting Stage 3 - Output formatting"`
- `"Multi-stage recap sanitizer failed, falling back to single-stage"`

## Future Enhancements

Potential improvements for the multi-stage pipeline:

1. **Validation Stage**: Add JSON schema validation between stages
2. **Caching**: Cache intermediate results for repeated processing
3. **Parallel Processing**: Run independent stages in parallel where possible
4. **Model Selection**: Use different models optimized for each stage
5. **Metrics Collection**: Track performance and quality metrics per stage 