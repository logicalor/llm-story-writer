# Unused Prompts

This directory contains prompt files that were identified as unused in the outline-chapter strategy codebase.

## Analysis Summary

- **Total prompts analyzed**: 58
- **Used prompts**: 41
- **Unused prompts**: 17 (moved to this directory)

## Unused Prompt Files

### Character and Setting Related
- `analyze_character_changes.md` - Character analysis prompt not used in current implementation
- ~~`generate_character_abridged.md` - Abridged character summary prompt (created but not integrated)~~ **MOVED BACK - NOW INTEGRATED**
- ~~`generate_setting_abridged.md` - Abridged setting summary prompt (created but not integrated)~~ **MOVED BACK - NOW INTEGRATED**

### Outline Generation
- `generate_iterative_chapter_list.md` - Iterative chapter list generation not implemented
- `generate_outline_chunk.md` - Outline chunking functionality not used
- `initial_outline_sanity_check.md` - Sanity check functionality not implemented

### Chapter Outline Variants
- `chapter_outline_recap_v2.md` - Alternative recap version not used

### Recap Format Variants
- `recap_format_current.md` - Current format variant not used
- `recap_format_historical.md` - Historical format variant not used
- `recap_format_output.md` - Output format variant not used
- `recap_format_recent.md` - Recent format variant not used

### Outline Review System
- `outline_review/` - Entire directory of critic-type prompts not used
  - `audiobook-producer.md`
  - `book-club-moderator.md`
  - `commercial-fiction-editor.md`
  - `literary-fiction-reviewer.md`
  - `publishing-acquisitions-editor.md`
  - `subject-expert.md`

## Notes

These prompts were identified as unused through a comprehensive code analysis that searched for:
1. Direct `prompt_id` references in Python code
2. Function names and other references to the prompt functionality

The prompts may have been:
- Created for planned features that weren't implemented
- Replaced by newer versions
- Part of experimental functionality that was abandoned
- Created as alternatives that weren't adopted

## Recent Changes

**2025-08-13**: Moved `generate_character_abridged.md` and `generate_setting_abridged.md` back to main prompts directory and integrated them into the workflow:
- Abridged character summaries are now generated after full character sheets
- Abridged setting summaries are now generated after full setting sheets
- Sheet update logic now uses abridged sheets as fallback when no previous sheets exist
- Added `update_setting_sheet.md` prompt for setting updates

## Restoration

If you need to restore any of these prompts:
1. Move the file back to the main prompts directory
2. Update the code to reference the prompt
3. Test the functionality
4. Remove from this directory once confirmed working

## Last Updated

Analysis performed on: 2025-08-13
Prompt files moved: 17
**Recent update**: Abridged prompts reintegrated into workflow
