# Character Prompts

This directory contains all prompts related to character management in the outline-chapter strategy.

## Prompt Files

### Core Character Operations

- **`create.md`** - Generates a comprehensive character sheet from story elements
- **`create_abridged.md`** - Creates a concise character summary suitable for prompt injection
- **`create_summary.md`** - Transforms abridged character sheets into natural language summaries
- **`update.md`** - Updates character sheets based on new information from chapters

### Character Extraction

- **`extract_names.md`** - Extracts character names from story text or outlines
- **`extract_from_chapter.md`** - Extracts character names specifically from chapter content

### Character Analysis

- **`analyze_changes.md`** - Analyzes how characters have changed over time (currently unused)

## Workflow

1. **Character Creation**: Use `create.md` to generate initial character sheets
2. **Abridged Summary**: Use `create_abridged.md` to create concise versions for context injection
3. **Natural Summary**: Use `create_summary.md` to create flowing prose descriptions
4. **Character Extraction**: Use `extract_from_chapter.md` to identify characters in new chapters
5. **Sheet Updates**: Use `update.md` to keep character sheets current with story developments

## Usage

These prompts are used by the `CharacterManager` class to:
- Generate character sheets during story initialization
- Create abridged summaries for efficient prompt injection
- Generate natural language summaries for story context
- Extract character information from new chapter content
- Update character sheets as the story progresses

## New Utility Methods

The `CharacterManager` now includes three new utility methods:

### `generate_character_summary(character_name, settings)`
- Generates a natural language summary from an abridged character sheet
- Returns a flowing prose description suitable for story prompts
- Saves the summary to `characters/{character_name}/summary` savepoint
- Uses the `logical_model` for consistent, coherent summaries

### `get_character_summaries(character_names, settings)`
- Generates summaries for multiple characters
- Returns combined summaries formatted for prompt injection
- Useful for providing character context in writing prompts
- Automatically handles missing characters gracefully

### `get_character_summaries_list(character_names, settings)`
- Generates summaries for multiple characters with horizontal rule separators
- Returns a formatted list with `---` dividers between each character
- Skips characters without abridged summaries automatically
- Perfect for creating visually separated character reference lists
- Output format: `**Character Name**\n\nSummary\n\n---\n\n**Next Character**\n\nSummary`

## Naming Convention

All prompts use concise, descriptive names that clearly indicate their function:
- `create` - Creates new content
- `update` - Updates existing content
- `extract` - Extracts information from content
- `analyze` - Analyzes content for insights
- `summary` - Creates natural language summaries
