# Recap Sanitizer Improvements

This document describes the improvements made to the recap sanitizer and how to use them.

## Overview

The recap sanitizer is responsible for formatting and organizing story recap data into a consistent structure. The original version had issues with:
- Complex 5-section time-based formatting that confused the model
- Inconsistent date/time formatting
- No clear examples or validation rules
- Long processing times due to complex template structure

## Improvements Made

### 1. Simplified Template Structure with Progressive Compaction
- **Before**: 5 different time sections (Deep History, A Year to 6 Months Ago, A While Ago, Recently, Current)
- **After**: 3 logical sections with progressive compaction (Historical Context, Recent Events, Current Chapter)
- **Benefit**: Reduces cognitive overhead, improves consistency, and automatically compacts older events

### 2. Clear Examples and Rules
- Added concrete input/output examples
- Included specific formatting rules
- Added validation checklist for the model
- **Benefit**: Model has clear guidance on expected output

### 3. Better Date Handling
- Consistent date format: "YYYY-MM-DD HH:MM to YYYY-MM-DD HH:MM"
- Fallback format for missing times: "YYYY-MM-DD to YYYY-MM-DD"
- Logical grouping of events by time periods
- **Benefit**: Eliminates date formatting confusion

### 4. Progressive Compaction
- **Historical Context**: Events > 1 week ago compressed to 1-2 sentences
- **Recent Events**: Events 1 week to 1 day ago in brief bullet format
- **Current Chapter**: Last 24 hours in full detailed format
- **Benefit**: Maintains important information while reducing length and complexity

### 5. Deduplication Rules
- Remove duplicate events
- Merge similar events that happen close together
- Keep the most detailed version of each event
- **Benefit**: Cleaner, more organized recaps

## Files Added/Modified

### New Files
- `src/application/strategies/prompts/outline-chapter/chapter_outline_recap_sanitizer_v2.md` - Improved sanitizer prompt
- `toggle_recap_sanitizer.py` - Utility script to switch between versions
- `RECAP_SANITIZER_IMPROVEMENTS.md` - This documentation

### Modified Files
- `src/config/settings.py` - Added `use_improved_recap_sanitizer` feature flag
- `src/application/strategies/outline_chapter_strategy.py` - Added conditional prompt selection
- `config.md` - Added feature flag configuration

## Usage

### Switching Between Versions

Use the toggle script to easily switch between the old and new sanitizer:

```bash
# Switch to improved sanitizer
python toggle_recap_sanitizer.py new

# Switch back to original sanitizer
python toggle_recap_sanitizer.py old

# Check current status
python toggle_recap_sanitizer.py status
```

### Manual Configuration

You can also manually edit `config.md` and set:

```yaml
generation:
  use_improved_recap_sanitizer: true  # or false
```

### Rollback Strategy

The implementation is designed for easy rollback:

1. **Configuration Level**: Simply set `use_improved_recap_sanitizer: false` in `config.md`
2. **Code Level**: The strategy automatically falls back to the original prompt
3. **File Level**: The original `chapter_outline_recap_sanitizer.md` remains unchanged

## Expected Benefits

### Performance
- **Faster Processing**: Simplified template reduces model confusion
- **Better Consistency**: Clear rules reduce formatting errors
- **Reduced Retries**: Examples help model understand expectations
- **Progressive Compaction**: Automatically reduces recap length as story progresses

### Quality
- **Cleaner Output**: Consistent formatting across all recaps
- **Better Organization**: Logical grouping of events with progressive compaction
- **Reduced Duplicates**: Automatic deduplication of events
- **Focused Content**: Older events compressed while maintaining critical information

### Maintainability
- **Clear Examples**: Easy to understand expected output
- **Modular Design**: Easy to switch between versions
- **Documentation**: Clear rules and validation checklist

## Testing

To test the improvements:

1. **Enable the new sanitizer**:
   ```bash
   python toggle_recap_sanitizer.py new
   ```

2. **Run a story generation** and observe:
   - Faster recap processing
   - More consistent formatting
   - Better organized content

3. **Compare outputs** between old and new versions

4. **Rollback if needed**:
   ```bash
   python toggle_recap_sanitizer.py old
   ```

## Future Improvements

Potential enhancements for the next iteration:

1. **Pre-processing Pipeline**: Add date normalization and duplicate detection before sanitization
2. **Validation Layer**: Add post-processing validation to ensure output quality
3. **Caching Strategy**: Cache sanitized recaps to avoid re-processing
4. **Structured Output**: Consider JSON output for easier parsing and validation

## Troubleshooting

### Common Issues

1. **Configuration Not Found**: Ensure `use_improved_recap_sanitizer` is set in `config.md`
2. **Prompt Not Found**: Verify `chapter_outline_recap_sanitizer_v2.md` exists
3. **Formatting Issues**: Check that the model is following the new template structure

### Debug Mode

Enable debug mode to see detailed processing information:

```yaml
generation:
  debug: true
  use_improved_recap_sanitizer: true
```

## Support

If you encounter issues with the improved sanitizer:

1. Check the current status: `python toggle_recap_sanitizer.py status`
2. Try switching back to the original: `python toggle_recap_sanitizer.py old`
3. Review the prompt file: `src/application/strategies/prompts/outline-chapter/chapter_outline_recap_sanitizer_v2.md`
4. Check the logs for detailed error information 