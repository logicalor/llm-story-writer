# Setting Prompts

This directory contains all prompts related to setting management in the outline-chapter strategy.

## Prompt Files

### Core Setting Operations

- **`create.md`** - Generates a comprehensive setting sheet from story elements
- **`create_abridged.md`** - Creates a concise setting summary suitable for prompt injection
- **`create_summary.md`** - Transforms abridged setting sheets into natural language summaries
- **`update.md`** - Updates setting sheets based on new information from chapters

### Setting Extraction

- **`extract_names.md`** - Extracts setting names from story text or outlines
- **`extract_from_chapter.md`** - Extracts setting names specifically from chapter content

## Workflow

1. **Setting Creation**: Use `create.md` to generate initial setting sheets
2. **Abridged Summary**: Use `create_abridged.md` to create concise versions for context injection
3. **Natural Summary**: Use `create_summary.md` to create flowing prose descriptions
4. **Setting Extraction**: Use `extract_from_chapter.md` to identify settings in new chapters
5. **Sheet Updates**: Use `update.md` to keep setting sheets current with story developments

## Usage

These prompts are used by the `SettingManager` class to:
- Generate setting sheets during story initialization
- Create abridged summaries for efficient prompt injection
- Generate natural language summaries for story context
- Extract setting information from new chapter content
- Update setting sheets as the story progresses

## New Utility Methods

The `SettingManager` now includes three new utility methods:

### `generate_setting_summary(setting_name, settings)`
- Generates a natural language summary from an abridged setting sheet
- Returns a flowing prose description suitable for story prompts
- Saves the summary to `settings/{setting_name}/summary` savepoint
- Uses the `logical_model` for consistent, coherent summaries

### `get_setting_summaries(setting_names, settings)`
- Generates summaries for multiple settings
- Returns combined summaries formatted for prompt injection
- Useful for providing setting context in writing prompts
- Automatically handles missing settings gracefully

### `get_setting_summaries_list(setting_names, settings)`
- Generates summaries for multiple settings with horizontal rule separators
- Returns a formatted list with `---` dividers between each setting
- Skips settings without abridged summaries automatically
- Perfect for creating visually separated setting reference lists
- Output format: `**Setting Name**\n\nSummary\n\n---\n\n**Next Setting**\n\nSummary`

## Naming Convention

All prompts use concise, descriptive names that clearly indicate their function:
- `create` - Creates new content
- `update` - Updates existing content
- `extract` - Extracts information from content
- `summary` - Creates natural language summaries
