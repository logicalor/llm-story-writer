# Character Prompts

This directory contains all prompts related to character management in the outline-chapter strategy.

## Prompt Files

### Core Character Operations

- **`create.md`** - Generates a comprehensive character sheet from story elements
- **`create_abridged.md`** - Creates a concise character summary suitable for prompt injection
- **`update.md`** - Updates character sheets based on new information from chapters

### Character Extraction

- **`extract_names.md`** - Extracts character names from story text or outlines
- **`extract_from_chapter.md`** - Extracts character names specifically from chapter content

### Character Analysis

- **`analyze_changes.md`** - Analyzes how characters have changed over time (currently unused)

## Workflow

1. **Character Creation**: Use `create.md` to generate initial character sheets
2. **Abridged Summary**: Use `create_abridged.md` to create concise versions for context injection
3. **Character Extraction**: Use `extract_from_chapter.md` to identify characters in new chapters
4. **Sheet Updates**: Use `update.md` to keep character sheets current with story developments

## Usage

These prompts are used by the `CharacterManager` class to:
- Generate character sheets during story initialization
- Create abridged summaries for efficient prompt injection
- Extract character information from new chapter content
- Update character sheets as the story progresses

## Naming Convention

All prompts use concise, descriptive names that clearly indicate their function:
- `create` - Creates new content
- `update` - Updates existing content
- `extract` - Extracts information from content
- `analyze` - Analyzes content for insights
