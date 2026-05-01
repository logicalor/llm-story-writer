# Workflow Gap Report — Restore Pipeline Sub-Steps

**Date:** 2026-05-02
**Source:** Audit during planning round; PRD at [`docs/planning/restore-pipeline-substeps/prd.md`](../../../docs/planning/restore-pipeline-substeps/prd.md).

Catalogue of prompts on disk under `prompts/` (excluding deprecated `prompts/agents/`) that the post-ADR-007 Python-native orchestrator no longer invokes, or invokes with required template variables stubbed empty. Drives Tasks 1–12 in [`docs/planning/restore-pipeline-substeps/tasks.md`](../../../docs/planning/restore-pipeline-substeps/tasks.md).

## Findings by area

### 1. Outline foundation (unblocks everything)
- `extract_base_context.md` — uninvoked. `{base_context}` stubbed empty in every downstream call.
- `extract_story_start_date.md` — uninvoked. Recap timing degrades to relative.
- `outline/create_elements.md` — uninvoked. `{story_elements}` stubbed empty.

### 2. Outline structure
- `outline/create_skeleton.md`, `outline/expand_chapter_detail.md`, `outline/strip_elements.md` — uninvoked. Single-shot `create_direct` runs instead.
- `outline/create_chunk.md`, `outline/analyze_continuity.md`, `outline/analyze_enrichment.md` — uninvoked. `use_chunked_outline_generation` flag dead.
- `multistep/outline/*` (9 files) — uninvoked.

### 3. Outline metadata
- `outline/create_title.md`, `outline/create_summary.md`, `outline/create_tags.md` — uninvoked. State has no title/tags.

### 4. Outline critique + arc
- `outline_review/*.md` (6 critics) — only callable via `tools/critique_runner.py` CLI; not in pipeline. `enable_outline_critique` flag dead.
- `outline_arc/arc_distribution.md`, `promise_payoff.md`, `arc_synthesis.md` — `StoryPlannerAgent` calls `arc_assessment_direct` with all three inputs empty.

### 5. Character + setting depth
- `characters/create_summary.md`, `create_abridged.md` + 7 chunk prompts — uninvoked.
- `settings/create_summary.md`, `create_abridged.md` + 6 chunk prompts — uninvoked.
- `characters/extract_from_chapter.md`, `analyze_changes.md`, `update.md` (and setting equivalents) — uninvoked. Sheets do not evolve.

### 6. Wiki bootstrap
- `wiki/extract_from_outline.md` (helper exists in `tools/wiki_extract.py`) — never called.
- `wiki/extract_from_sheet.md` — never called. Wiki empty until `WikiMaintainerAgent` runs after chapter 1.

### 7. Recap
- `extract_chapter_events.md`, all `recap/*.md` — uninvoked. `previous_chapter_recap` is just the next chapter's outline blurb.
- `use_improved_recap_sanitizer`, `use_multi_stage_recap_sanitizer` flags dead.

### 8. Chapter generation
- `multistep/scene/create_content_first/middle/final.md` + `understand_*` — uninvoked. `ChapterWriterAgent` calls only generic `scenes/create_content`.
- `chapters/create_outline_summary.md`, `create_title.md`, `generate_handoff.md`, `extract_list*.md`, `multistep/chapter/*`, `story_state/*` — uninvoked; need per-prompt decision (invoke or retire).

### 9. Chapter review
- `consistency_check_direct` is invoked but with `outline=""` — see Task 3.
- `chapter_review/chapter-pacing.md`, `chapter-character-consistency.md`, `character-voice-consistency.md`, `commercial-fiction-editor.md` — only callable via critique CLI; not in chapter loop.

### 10. Final edit
- `final_edit/prose_scrub.md`, `voice_consistency_pass.md` — uninvoked. `enable_scrubbing` flag dead.

### 11. Dead `GenerationSettings` flags
`enable_outline_critique`, `outline_critique_iterations`, `enable_scrubbing`, `use_chunked_outline_generation`, `outline_chunk_size`, `use_improved_recap_sanitizer`, `use_multi_stage_recap_sanitizer`, `outline_min_revisions`, `outline_max_revisions`, `chapter_min_revisions`, `chapter_max_revisions`, `enable_chapter_revisions`, `outline_quality`, `chapter_quality`. All to be wired or removed in Task 12.

## Architectural constraint
ADR 007 retired the `application/strategies/outline_chapter/` strategy. New work must live under `src/presentation/agents/` and may reference legacy code only as documentation — no imports. ADR 009 forbids re-introducing OpenCode tools into the pipeline path.
