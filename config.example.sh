#!/bin/bash
# AI Story Writer - Example Configuration Script
# Copy this file to config.sh and modify the settings below

# Required: Path to your story prompt file
PROMPT_FILE="Prompts/MyStory.txt"

# Optional: Custom output filename (without extension)
OUTPUT_NAME=""

# =============================================================================
# MODEL CONFIGURATION
# =============================================================================

# Outline Generation Models
INITIAL_OUTLINE_MODEL="ollama://huihui_ai/magistral-abliterated:24b"
CHAPTER_OUTLINE_MODEL="ollama://huihui_ai/magistral-abliterated:24b"

# Chapter Generation Models
CHAPTER_S1_MODEL="ollama://huihui_ai/magistral-abliterated:24b"  # Plot
CHAPTER_S2_MODEL="ollama://huihui_ai/magistral-abliterated:24b"  # Character development
CHAPTER_S3_MODEL="ollama://huihui_ai/magistral-abliterated:24b"  # Dialogue
CHAPTER_S4_MODEL="ollama://huihui_ai/magistral-abliterated:24b"  # Final correction

# Revision and Quality Models
CHAPTER_REVISION_MODEL="ollama://huihui_ai/magistral-abliterated:24b"
REVISION_MODEL="ollama://huihui_ai/magistral-abliterated:24b"
EVAL_MODEL="ollama://huihui_ai/qwen2.5-coder-abliterate:7b"

# Information and Processing Models
INFO_MODEL="ollama://huihui_ai/qwen2.5-coder-abliterate:7b"
SCRUB_MODEL="ollama://huihui_ai/qwen2.5-coder-abliterate:7b"
CHECKER_MODEL="ollama://huihui_ai/deepseek-r1-abliterated:8b"

# Translation Models
TRANSLATOR_MODEL="ollama://huihui_ai/magistral-abliterated:24b"

# =============================================================================
# GENERATION SETTINGS
# =============================================================================

# Random seed for reproducible results
SEED=12

# Revision settings
OUTLINE_MIN_REVISIONS=0
OUTLINE_MAX_REVISIONS=3
CHAPTER_MIN_REVISIONS=0
CHAPTER_MAX_REVISIONS=3

# Feature flags (set to "true" to enable, "false" to disable)
NO_CHAPTER_REVISION="false"
NO_SCRUB_CHAPTERS="false"
EXPAND_OUTLINE="true"
ENABLE_FINAL_EDIT_PASS="false"
SCENE_GENERATION_PIPELINE="true"
DEBUG="false"

# Translation settings
TRANSLATE_LANGUAGE=""
TRANSLATE_PROMPT_LANGUAGE=""

# =============================================================================
# BUILD COMMAND
# =============================================================================

# Build the command with all settings
CMD="python src/main.py -Prompt $PROMPT_FILE"

# Add output name if specified
if [ ! -z "$OUTPUT_NAME" ]; then
    CMD="$CMD -Output $OUTPUT_NAME"
fi

# Add model configurations
CMD="$CMD -InitialOutlineModel \"$INITIAL_OUTLINE_MODEL\""
CMD="$CMD -ChapterOutlineModel \"$CHAPTER_OUTLINE_MODEL\""
CMD="$CMD -ChapterS1Model \"$CHAPTER_S1_MODEL\""
CMD="$CMD -ChapterS2Model \"$CHAPTER_S2_MODEL\""
CMD="$CMD -ChapterS3Model \"$CHAPTER_S3_MODEL\""
CMD="$CMD -ChapterS4Model \"$CHAPTER_S4_MODEL\""
CMD="$CMD -ChapterRevisionModel \"$CHAPTER_REVISION_MODEL\""
CMD="$CMD -RevisionModel \"$REVISION_MODEL\""
CMD="$CMD -EvalModel \"$EVAL_MODEL\""
CMD="$CMD -InfoModel \"$INFO_MODEL\""
CMD="$CMD -ScrubModel \"$SCRUB_MODEL\""
CMD="$CMD -CheckerModel \"$CHECKER_MODEL\""
CMD="$CMD -TranslatorModel \"$TRANSLATOR_MODEL\""

# Add generation settings
CMD="$CMD -Seed $SEED"
CMD="$CMD -OutlineMinRevisions $OUTLINE_MIN_REVISIONS"
CMD="$CMD -OutlineMaxRevisions $OUTLINE_MAX_REVISIONS"
CMD="$CMD -ChapterMinRevisions $CHAPTER_MIN_REVISIONS"
CMD="$CMD -ChapterMaxRevisions $CHAPTER_MAX_REVISIONS"

# Add feature flags
if [ "$NO_CHAPTER_REVISION" = "true" ]; then
    CMD="$CMD -NoChapterRevision"
fi

if [ "$NO_SCRUB_CHAPTERS" = "true" ]; then
    CMD="$CMD -NoScrubChapters"
fi

if [ "$EXPAND_OUTLINE" = "true" ]; then
    CMD="$CMD -ExpandOutline"
fi

if [ "$ENABLE_FINAL_EDIT_PASS" = "true" ]; then
    CMD="$CMD -EnableFinalEditPass"
fi

if [ "$SCENE_GENERATION_PIPELINE" = "true" ]; then
    CMD="$CMD -SceneGenerationPipeline"
fi

if [ "$DEBUG" = "true" ]; then
    CMD="$CMD -Debug"
fi

# Add translation settings
if [ ! -z "$TRANSLATE_LANGUAGE" ]; then
    CMD="$CMD -Translate \"$TRANSLATE_LANGUAGE\""
fi

if [ ! -z "$TRANSLATE_PROMPT_LANGUAGE" ]; then
    CMD="$CMD -TranslatePrompt \"$TRANSLATE_PROMPT_LANGUAGE\""
fi

# =============================================================================
# EXECUTION
# =============================================================================

echo "AI Story Writer Configuration"
echo "============================="
echo "Prompt file: $PROMPT_FILE"
echo "Output name: ${OUTPUT_NAME:-auto-generated}"
echo "Seed: $SEED"
echo "Debug mode: $DEBUG"
echo ""
echo "Executing command:"
echo "$CMD"
echo ""

# Execute the command
eval $CMD 