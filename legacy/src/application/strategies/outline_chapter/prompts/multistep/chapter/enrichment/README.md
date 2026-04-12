# Multistep Chapter Enrichment Workflow

This directory contains prompts for the 7-step multistep workflow used in `_generate_single_chapter_synopsis`.

## Workflow Overview

The chapter synopsis generation follows a progressive understanding approach:

### Step 1: Understand Storyline
- **Prompt**: `understand_storyline.md`
- **Purpose**: Analyze story elements to understand core storyline and narrative foundation
- **Input**: `{story_elements}`
- **Focus**: Main plot, central conflict, themes, narrative direction, story characteristics

### Step 2: Understand Base Context
- **Prompt**: `understand_base_context.md`
- **Purpose**: Analyze base context to understand foundational setting and background
- **Input**: `{base_context}`
- **Focus**: Setting, world-building, historical background, foundational details

### Step 3: Understand Combined Outline
- **Prompt**: `understand_outline.md`
- **Purpose**: Analyze combined outline to understand overall story structure and flow
- **Input**: `{outline}`
- **Focus**: Story arc, chapter progression, pacing, plot points, story threads

### Step 4: Understand Characters
- **Prompt**: `understand_characters.md`
- **Purpose**: Analyze character summaries to understand key characters and their roles
- **Input**: `{character_summaries}`
- **Focus**: Main characters, motivations, relationships, character arcs, personalities

### Step 5: Understand Settings
- **Prompt**: `understand_settings.md`
- **Purpose**: Analyze setting summaries to understand key locations and environments
- **Input**: `{setting_summaries}`
- **Focus**: Main locations, atmosphere, story influence, setting relationships, mood

### Step 6: Understand Previous Chapter (Conditional)
- **Prompt**: `understand_previous_chapter.md`
- **Purpose**: Analyze previous chapter synopsis for continuity and progression
- **Input**: `{previous_chapter}`
- **Focus**: Key events, character actions, plot progression, continuity elements
- **Note**: Only runs if `chapter_num > 1` and `previous_chapter` exists

### Step 7: Generate Chapter Synopsis
- **Prompt**: `chapters/create_synopsis` (existing prompt)
- **Purpose**: Generate the final chapter synopsis using all accumulated understanding
- **Input**: All previous context plus chapter-specific details
- **Focus**: Final synopsis generation with full context

## Benefits

- **Progressive Understanding**: Each step builds upon previous understanding
- **Contextual Richness**: Final synopsis benefits from comprehensive context analysis
- **Consistency**: Structured approach ensures consistent quality across chapters
- **Debugging**: Individual step savepoints enable better troubleshooting
- **Reusability**: Conversation history can be saved and analyzed

## Usage

This workflow is automatically used when calling `_generate_single_chapter_synopsis` with the `use_chunked_outline_generation` setting enabled.
