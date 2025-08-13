# Setting Prompts

This directory contains all prompts related to setting management in the outline-chapter strategy.

## Prompt Files

### Core Setting Operations

- **`create.md`** - Generates a comprehensive setting sheet from story elements
- **`create_abridged.md`** - Creates a concise setting summary suitable for prompt injection
- **`update.md`** - Updates setting sheets based on new information from chapters

### Setting Extraction

- **`extract_names.md`** - Extracts setting names from story text or outlines
- **`extract_from_chapter.md`** - Extracts setting names specifically from chapter content

## Workflow

1. **Setting Creation**: Use `create.md` to generate initial setting sheets
2. **Abridged Summary**: Use `create_abridged.md` to create concise versions for context injection
3. **Setting Extraction**: Use `extract_from_chapter.md` to identify settings in new chapters
4. **Sheet Updates**: Use `update.md` to keep setting sheets current with story developments

## Usage

These prompts are used by the `SettingManager` class to:
- Generate setting sheets during story initialization
- Create abridged summaries for efficient prompt injection
- Extract setting information from new chapter content
- Update setting sheets as the story progresses

## Naming Convention

All prompts use concise, descriptive names that clearly indicate their function:
- `create` - Creates new content
- `update` - Updates existing content
- `extract` - Extracts information from content
