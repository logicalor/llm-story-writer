# Savepoint Structure Update

## Overview

Updated the savepoint references in the character and setting managers to use a more organized directory structure instead of flat naming conventions.

## Changes Made

### Character Manager (`character_manager.py`)

**Before:**
- `character_sheet_{character_name.lower().replace(' ', '_')}`

**After:**
- `characters/{character_name}/sheet`

**Updated Methods:**
- `generate_single_character_sheet()` - savepoint_id
- `fetch_character_sheets_for_chapter()` - sheet_key
- `update_character_sheets()` - sheet_key and savepoint_id

### Setting Manager (`setting_manager.py`)

**Before:**
- `setting_sheet_{setting_name.lower().replace(' ', '_')}`

**After:**
- `settings/{setting_name}/sheet`

**Updated Methods:**
- `generate_single_setting_sheet()` - savepoint_id
- `fetch_setting_sheets_for_chapter()` - sheet_key
- `update_setting_sheets()` - sheet_key and savepoint_id

## New Directory Structure

```
characters/
├── {character_name}/
│   ├── sheet              # Full character sheet
│   └── sheet-abridged     # Abridged character summary
│
settings/
├── {setting_name}/
│   ├── sheet              # Full setting sheet
│   └── sheet-abridged     # Abridged setting summary
```

## Benefits

1. **Better Organization**: Related files are grouped in logical directories
2. **Cleaner Naming**: No more complex string replacements with underscores
3. **Easier Navigation**: Clear hierarchy for savepoint management
4. **Consistent Structure**: Both characters and settings follow the same pattern
5. **Scalability**: Easier to add new file types within each directory

## Compatibility

- **Abridged summaries**: Already using the new structure (`characters/{name}/sheet-abridged`, `settings/{name}/sheet-abridged`)
- **Existing savepoints**: Will need to be migrated or regenerated
- **Test files**: Unchanged (only production code was updated)

## Files Modified

- `src/application/strategies/outline_chapter/character_manager.py`
- `src/application/strategies/outline_chapter/setting_manager.py`

## Verification

All modified files compile without syntax errors:
- ✅ `character_manager.py`
- ✅ `setting_manager.py`

## Migration Notes

When running the system with existing savepoints:
1. **New characters/settings**: Will be created in the new directory structure
2. **Existing characters/settings**: May not be found until regenerated
3. **Abridged summaries**: Already using the new structure, so they should work

## Future Considerations

- Consider adding a migration utility to move existing savepoints
- Add validation to ensure savepoint paths are properly formatted
- Consider adding subdirectories for different types of character/setting data
- Add logging for savepoint path creation and access
