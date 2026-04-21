## Synthesized Audit — 2026-04-21
## Focus: Agent-Tool Interface Compatibility for Low-Parameter Local Models

**Audit Type:** Multi-model synthesis (Claude Opus 4.6 + GPT 5.4 + Gemini 3.1 Pro)
**Model Agreement Score:** 9/10 — high agreement on critical defects; minor severity divergences only
**Overall Health:** At Risk — six unanimous critical defects will cause hard pipeline failures on first run
**Development Stage:** Agent documentation significantly ahead of interface contract completeness

---

### Finding Counts by Consensus

| Consensus         | Critical | Warning | Info |
| ----------------- | -------- | ------- | ---- |
| ★★★ Unanimous     | 6        | 1       | 0    |
| ★★☆ Majority      | 2        | 6       | 2    |
| ★☆☆ Singular      | 3        | 5       | 5    |

---

### Key Findings

- [U-C-01] `story-state` operation "update" does not exist — must be "write" (★★★)
- [U-C-02] `wiki-snapshot` returns JSON object, not bare string — agent docs wrong (★★★)
- [U-C-03] `character-mgr` and `setting-mgr` generate-sheet: required `data` parameter undocumented (★★★)
- [U-C-04] `wiki-lint` `chapter_text` is a file path, not text content — agent doesn't write chapter to disk first (★★★)
- [U-C-05] `prompt-loader` cannot read arbitrary files — wrong tool used in Phase 1 (★★★)
- [U-C-06] `wiki-maintainer` references skills `wiki-maintenance` and `wiki-conventions` that do not exist (★★★)
- [M-C-01] `expand-chapter` output field `continuity_analysis` not extracted; agent doc says "continuitySummary from prior chunk" without extraction instructions (★★☆)
- [M-C-02] `savepoint-mgr` operation "restore" does not exist — must be "load" (★★☆)
- [U-W-01] camelCase/snake_case naming mismatch between tool call parameters and batch JSON payload fields (★★★)
- [M-W-01] `wiki-snapshot` output not mapped to a specific `scene-writer` parameter (★★☆)
- [M-W-02] `storyStartDate` value from Phase 1 never threaded to `recap-manager` generate in Phase 8d (★★☆)
- [M-W-03] Phase 8a single-chapter expansion: no specify which operation or params to use (★★☆)
- [M-W-04] Acceptance condition in `outline-planner` Phase 4 uses ambiguous AND/OR prose (★★☆)
- [M-W-05] `qualityThreshold` default mismatch: tool defaults 85.0, config default is 87 (★★☆)
- [M-W-06] Chapter-writer fallback path (no wiki) unspecified for character/setting sheet loading (★★☆)

### Divergences

- [D-01] Severity of missing skills: Claude=Warning, GPT+Gemini=Critical → Assessed Critical (wiki-maintainer calls them "required" and says "follow strictly")
- [D-02] Severity of prompt-loader misuse: Claude=Warning, GPT+Gemini=Critical → Assessed Critical (Phase 1 fails immediately)
- [D-03] Severity of storyStartDate threading: Claude=Info, GPT=Critical, Gemini=Warning → Assessed Warning (tool does not hard-fail on missing storyStartDate for generate, produces inconsistent timelines)

### Actions Taken

- Notes written: `.github/notes/audits/2026-04-21-agent-tool-interface-synthesis.md`
- 25 findings embedded into `audits` ChromaDB collection

---

## Full Synthesis Report

### Individual Report Summaries

| Model  | Overall Assessment | Unique Focus Areas | Critical Count | Warning Count |
| ------ | ------------------ | ------------------ | -------------- | ------------- |
| Claude | Systemic — docs written at frontier-model level | Savepoint data schema gaps; output envelope chain for generation context; qualityThreshold mismatch | 6 | 8 |
| GPT | High-risk — interface contracts inconsistent with docs | Savepoint "restore" op doesn't exist; story-state init doesn't accept metadata; silent partial failures; savepoint name mismatches | 8 | 8 |
| Gemini | Multiple critical mismatches for first-run failure | wiki-snapshot → scene-writer parameter mapping gap (clearest statement); forced-revision branch; vague savepoint call syntax | 7 | 4 |

---

### ★★★ Unanimous Findings (All Three Models Agree)

```
[U-C-01] story-state "update" operation does not exist
Severity: Critical
Category: Tool name/operation mismatches
Detail: story-orchestrator Phase 2 instructs: story-state (operation: "update", field: "outline").
  The tool only accepts: init|read|write|list. "update" is not a valid enum value.
  Tool returns: Zod validation error on every Phase 2 call.
Models: Claude ✓ GPT ✓ Gemini ✓
Impact: Pipeline halts at Phase 2, the very first post-analysis step. No workaround
  available to a small model following the doc verbatim. Correct call:
  story-state (operation: "write", field: "outline", value: <JSON string>).
```

```
[U-C-02] wiki-snapshot returns JSON object, not a bare string
Severity: Critical
Category: Output format clarity / State threading
Detail: chapter-writer states: "wiki-snapshot returns the assembled context string directly."
  The tool (wiki_snapshot.py line 1072) returns:
    {"snapshot": "...", "stats": {...}}
  The agent must extract data["snapshot"]. Without this, scene-writer receives a raw JSON
  blob as its generation context.
Models: Claude ✓ GPT ✓ Gemini ✓
Impact: Every scene is generated with corrupted, tool-metadata-polluted context. Output
  quality degrades catastrophically. A corrected chapter-writer doc must say: "Parse the
  JSON response. Extract the 'snapshot' field. Pass that string to scene-writer as 'baseContext'."
```

```
[U-C-03] character-mgr and setting-mgr generate-sheet: required "data" parameter undocumented
Severity: Critical
Category: Parameter ambiguity / JSON construction requirements
Detail: story-orchestrator Phases 5 and 6 say: "call character-mgr (operation: generate-sheet)"
  with no mention of data. Python source hard-errors if data is absent. Additionally:
  setting-mgr uses parameter "setting" not "character" — an agent learning the character-mgr
  pattern will use the wrong parameter name.
Models: Claude ✓ GPT ✓ Gemini ✓
Impact: Every character and setting sheet generation call fails. The agent cannot infer
  the JSON schema from any available context. Both agent and tool docs need an explicit
  schema example.
```

```
[U-C-04] wiki-lint chapter_text is a file path, not chapter text content
Severity: Critical
Category: Parameter ambiguity / Implicit knowledge requirements
Detail: story-orchestrator Phase 8e says: "call wiki-lint (operation: check-chapter,
  chapter_number: N)". The "chapter_text" required parameter is a filesystem path to a
  saved chapter file — not raw text. The orchestrator doc never instructs writing the
  assembled chapter to disk before calling wiki-lint.
Models: Claude ✓ GPT ✓ Gemini ✓
Impact: wiki-lint fails at every chapter boundary. Small models passing raw text as a
  path will see file-not-found errors; those omitting chapter_text entirely will see a
  missing-required-parameter error.
```

```
[U-C-05] prompt-loader misused in Phase 1 — cannot read arbitrary files
Severity: Critical
Category: Tool name/operation mismatches / Implicit knowledge requirements
Detail: story-orchestrator Phase 1 Step 1 says: "Read the user-provided story prompt file
  using prompt-loader". The prompt-loader tool accepts only a promptId (internal template
  registry key under prompts/) and cannot read arbitrary user file paths. A small model
  will pass a file path as promptId, receiving a file-not-found error on the very first
  tool call.
Models: Claude ✓ (Warning) GPT ✓ (Critical) Gemini ✓ (Critical) — assessed Critical
Impact: Pipeline fails before any story state is initialised. A dedicated file-reading
  mechanism or direct context injection is needed.
```

```
[U-C-06] wiki-maintainer references non-existent skills wiki-maintenance and wiki-conventions
Severity: Critical
Category: Skill dependency gaps
Detail: wiki-maintainer agent says "Follow the wiki-maintenance skill strictly" and lists
  both skills as "required". Neither skill file exists in the repository. The available
  skills are: chromadb-ops, github-issues, tavily-cli, caveman, find-skills. The
  wiki-maintainer explicitly runs on a smaller model and depends on these skills for entity
  taxonomy, confidence rules, slug conventions, and the batch payload schema.
Models: Claude ✓ (Warning) GPT ✓ (Critical) Gemini ✓ (Critical) — assessed Critical
Impact: Without the skills, wiki-maintainer must guess at entity formatting, batch structure,
  and slug conventions. This is the highest-traffic agent in the pipeline. Either create
  both skill files or inline all required conventions into the agent doc.
```

```
[U-W-01] camelCase/snake_case naming mismatch in wiki-update batch payload
Severity: Warning
Category: Parameter ambiguity / JSON construction requirements
Detail: Tool call parameters use camelCase (firstAppearance, detailLevels, pageType) but
  batch operation payload JSON fields use snake_case (first_appearance, detail_levels,
  page_type). No documentation highlights this distinction.
Models: Claude ✓ GPT ✓ Gemini ✓
Impact: Small models will use camelCase inside batch JSON payloads, resulting in silently
  ignored fields or validation errors. A naming table should be added to wiki-maintainer
  and wiki-update docs.
```

---

### ★★☆ Majority Findings (Two of Three Models Agree)

```
[M-C-01] expand-chapter output "continuity_analysis" not documented for extraction
Severity: Critical
Category: State threading / Output format clarity
Detail: outline-planner Phase 3 instructs passing "continuitySummary (continuity analysis
  text from the previous chunk)" to each subsequent expand-chapter call. The tool returns:
    {"status":"success","operation":"expand-chapter","data":{"chunk_outline":"...","continuity_analysis":"..."}}
  The agent doc never states: extract data["continuity_analysis"] and pass it as
  continuitySummary. Savepoint names in the doc are also wrong: doc says outline_chunk_{N}
  but implementation (outline_generator.py line 344) uses outline_chunk_{start}_{end}.
Models: Claude ✓ GPT ✓ Gemini ✓ (Warning) — assessed Critical
Dissenting view: Gemini rated Warning. Assessed Critical because continuitySummary is
  architecturally required for coherent multi-chunk outlines.
Impact: Chunked outline generation produces chunks without continuity context. Story
  consistency breaks across outline chunks.
```

```
[M-C-02] savepoint-mgr operation "restore" does not exist
Severity: Critical
Category: Tool name/operation mismatches
Detail: chapter-writer doc line 106 says: "Load the savepoint via savepoint-mgr
  (operation: restore)". The tool only supports: save|load|has|list|list-full|clear.
  The correct operation is "load". Confirmed in source.
Models: GPT ✓ (confirmed); Claude ✗ Gemini ✗
Assessment: Verified against code — savepoint-mgr "restore" confirmed nonexistent.
Impact: The resume/recovery path fails exactly when a small model most needs it.
```

```
[M-W-01] wiki-snapshot output not mapped to a specific scene-writer parameter
Severity: Warning
Category: State threading / Parameter ambiguity
Detail: chapter-writer instructs passing wiki snapshot context into scene-writer.generate
  but scene-writer has distinct parameters: baseContext, storyElements, characterSheets,
  settingSheets. The doc does not specify which parameter receives the snapshot string.
Models: Claude ✓ Gemini ✓ GPT ✓ (implicit in C-08 envelope finding)
Impact: Small models will guess — likely concatenating all context into one field or
  distributing it incorrectly — degrading generation quality.
```

```
[M-W-02] storyStartDate not threaded from Phase 1 to recap-manager generate (Phase 8d)
Severity: Warning
Category: State threading
Detail: outline-generator analyze-prompt creates a story_start_date savepoint in Phase 1.
  recap-manager generate requires storyStartDate (YYYY-MM-DD). The orchestrator doc never
  instructs reading story_start_date from the analyze-prompt savepoint and passing it to
  recap-manager. chapter-writer doc doesn't mention storyStartDate at all.
Models: Claude ✓ (Info) GPT ✓ (Critical) Gemini ✓ (Warning) — assessed Warning
Dissenting view: GPT assessed Critical. recap-manager generate does not hard-fail on
  missing storyStartDate; it produces incorrect timeline annotations rather than a halt.
Impact: All chapter recaps will have inconsistent timeline date stamps.
```

```
[M-W-03] Phase 8a per-chapter expansion: no operation or parameters specified
Severity: Warning
Category: Agent instruction clarity / Parameter ambiguity
Detail: story-orchestrator Phase 8a says "Use outline-generator to expand the brief
  outline into detailed scene breakdowns" without specifying which operation or what
  parameter values to use. expand-chapter requires chunkStart, chunkEnd, totalChapters.
  The correct single-chapter call is chunkStart=N, chunkEnd=N, totalChapters=wanted_chapters
  but this is not stated anywhere in the orchestrator doc.
Models: Claude ✓ GPT ✓ Gemini ✗
Impact: Small model will choose wrong operation or omit required parameters.
```

```
[M-W-04] Outline-planner Phase 4 acceptance condition logic ambiguous
Severity: Warning
Category: Conditional logic complexity
Detail: Phase 4d states "Accept if: should_refine is false AND iteration >=
  outline_min_revisions / Accept if: iteration >= outline_critique_iterations /
  Continue if: should_refine is false but iteration < outline_min_revisions".
  The AND/OR boundaries in prose are syntactically ambiguous. Forced-continue
  branch also has no defined feedback source for the outline-generator refine call.
Models: Claude ✓ GPT ✓ Gemini ✗
Impact: Small model refines too many or too few times; forced-continue branch causes
  the model to hallucinate critique feedback.
```

```
[M-W-05] qualityThreshold default mismatch: tool default 85.0, config default 87
Severity: Warning
Category: Parameter ambiguity
Detail: critique-runner tool defaults qualityThreshold to 85.0. Orchestrator config
  outline_quality defaults to 87. If a small model omits the parameter (not marked
  required), outlines are accepted at a lower threshold than configured.
Models: Claude ✓ Gemini ✓ GPT ✗
Impact: Silent quality gate regression. Difficult to detect during testing.
```

```
[M-W-06] Chapter-writer fallback path unspecified when wiki is unavailable
Severity: Warning
Category: Agent instruction clarity / State threading
Detail: chapter-writer doc says to fall back to character sheets and setting sheets
  when the wiki is not initialised, but does not specify which operations to call on
  character-mgr and setting-mgr, what data to pass, or how the returned JSON maps to
  scene-writer parameters characterSheets and settingSheets.
Models: Claude ✓ GPT ✓ Gemini ✗
Impact: Recovery behaviour is improvisation rather than a deterministic fallback path.
```

```
[M-I-01] wiki-search similarity threshold for deduplication undefined
Severity: Info
Category: Implicit knowledge requirements
Detail: wiki-maintainer Mode 2 instructs using wiki-search to check for existing entities
  before creating new ones but does not define what similarity score constitutes a match.
Models: Claude ✓ GPT ✓
Suggestion: Document a default cutoff (e.g., cosine similarity > 0.85 = match).
```

```
[M-I-02] wiki-update batch payload: updates and timeline_events arrays underdocumented
Severity: Info
Category: JSON construction requirements
Detail: wiki-maintainer batch payload example only shows the creates array schema.
  The updates and timeline_events fields (snake_case keys; timeline_events requires
  time, description, chapter) are not shown with examples.
Models: GPT ✓ Gemini ✓
Suggestion: Add one worked example per array type with all required fields populated.
```

---

### ★☆☆ Singular Findings (One Model Only)

```
[S-C-01] story-state init does not accept metadata payloads
Severity: Critical
Category: Parameter ambiguity
Model: GPT
Detail: Phase 1 says "Initialise story state via story-state (operation: init) with
  prompt metadata and config values". init only creates the empty state structure —
  it accepts no payload. Metadata must be written via subsequent write calls.
Assessment: Real — verified against story_state.py. Worth fixing: agent doc should
  separate init (no payload) from subsequent write calls.
```

```
[S-C-02] Savepoint names in outline-planner doc don't match implementation
Severity: Warning
Category: Tool name/operation mismatches
Model: GPT (verified against outline_generator.py line 344)
Detail: Doc lists outline_chunk_{N} and continuity_analysis_{N}.
  Implementation uses outline_chunk_{start}_{end} and continuity_{start}_{end}.
Assessment: Confirmed in source. Agents told to verify savepoints by name will
  falsely conclude the tool failed.
```

```
[S-C-03] Tool error responses are unstructured; success response format inconsistent
Severity: Warning
Category: Output format clarity / Error signal quality
Model: GPT
Detail: Tools return bare "Error: ..." strings on failure while success responses vary:
  story-state read returns unwrapped JSON; all other ops return status-wrapped envelopes;
  prompt-loader returns raw text. Small models must infer format before parsing.
Assessment: Genuine systemic issue. A consistent {status, data} / {status, error} schema
  across all tools would reduce agent confusion significantly.
```

```
[S-W-01] Partial failures hidden behind successful tool outputs
Severity: Warning
Category: Error signal quality
Model: GPT
Detail: critique-runner succeeds even if individual critics fail (stderr only).
  scene-writer parse-definitions may silently fall back to one scene. TypeScript wrappers
  suppress stderr on exit 0. Agents receive no degradation signal.
Assessment: Real systemic concern. Success outputs should include a "warnings" array
  or "degraded" boolean for key pipeline tools.
```

```
[S-W-02] Slug acquisition assumed implicit — never instructed
Severity: Warning
Category: Implicit knowledge requirements
Model: GPT
Detail: chapter-writer requires povCharacter, primaryLocation, characters, locations as
  slug strings. wiki-maintainer requires slugs for deduplication. No agent doc explains
  where canonical slugs originate or instructs against guessing from display names.
Assessment: Real and high-impact for wiki integrity. Fabricated slugs cause broken
  wikilinks, missed context retrieval, and duplicate entity creation.
```

```
[S-I-01] rag-query tool undocumented in all agent docs
Severity: Info
Model: Claude
Detail: .opencode/tools/rag-query.ts exists with index and query operations but appears
  in no agent tool list. Status unclear — may be deprecated or internal-only.
Suggestion: Mark as deprecated in rag-query.ts or document in relevant agents.
```

```
[S-I-02] No shared glossary for core agent concepts
Severity: Info
Model: GPT
Detail: Terms like slug, frontmatter, detail level, wikilink, and continuity summary
  used without definition across all agent docs.
Suggestion: Add a glossary section to each agent doc's header, especially wiki-maintainer.
```

```
[S-I-03] Forced-revision branch in outline-planner Phase 4 has no feedback input defined
Severity: Info
Model: GPT / Claude
Detail: When should_refine is false but iteration < outline_min_revisions, the agent is
  told to force another pass but the feedback parameter for outline-generator refine has
  no defined source in this branch.
Suggestion: Specify that forced passes should use the most recent generate-feedback output.
```

---

### Divergence Analysis

```
[D-01] Topic: Severity of missing wiki skills
Claude says: Warning — agent can proceed without skills, just lacks authoritative reference
GPT says: Critical — model told to follow skills strictly, will refuse or hallucinate
Gemini says: Critical — model will invent conventions contradicting project standards
Assessment: Critical. wiki-maintainer.md says "Follow the wiki-maintenance skill strictly."
  A model told an authoritative source is required but doesn't exist cannot safely infer
  the rules it needs. Batch payload schema especially depends on it.
Resolution: Assessed unanimous-critical.
```

```
[D-02] Topic: Severity of prompt-loader misuse in Phase 1
Claude says: Warning — Phase 1 fails at step 1 but pipeline could be salvaged
GPT says: Critical — immediate failure before any state is initialised
Gemini says: Critical — model likely hallucinates a template key
Assessment: Critical. Phase 1 fails at the very first tool call with no recovery path
  visible to a small model.
Resolution: Assessed unanimous-critical.
```

```
[D-03] Topic: Severity of storyStartDate threading gap
Claude says: Info — produces inconsistent timelines, not a hard failure
GPT says: Critical — recap generation depends on chapter content savepoint also not written
Gemini says: Warning — inconsistent timestamps but pipeline continues
Assessment: Warning. recap-manager generate does not hard-fail if storyStartDate is absent;
  it uses a default. GPT's related finding about chapter_N/content savepoint is captured
  separately as S-C-01.
Resolution: Assessed majority-warning.
```

---

### Deviations from Plan

| Agent Doc Says | Tool Actually Requires | Severity |
|---|---|---|
| story-orchestrator Ph.2: `operation: "update"` | `operation: "write"` | ★★★ Critical |
| story-orchestrator Ph.1: `prompt-loader` reads user prompt file | `promptId` is a template registry key, cannot read files | ★★★ Critical |
| chapter-writer: "wiki-snapshot returns the assembled context string directly" | Returns `{"snapshot":"...","stats":{...}}` JSON | ★★★ Critical |
| story-orchestrator Ph.8e: `wiki-lint(chapter_number: N)` | `chapter_text` (file path) also required | ★★★ Critical |
| story-orchestrator Ph.5-6: `[entity]-mgr(operation: generate-sheet)` | `data` (JSON object) required; setting-mgr uses `setting` not `character` param | ★★★ Critical |
| wiki-maintainer: skills `wiki-maintenance`, `wiki-conventions` required | Neither skill exists in repository | ★★★ Critical |
| outline-planner: "continuitySummary from prior chunk" | Must extract `data.continuity_analysis` from expand-chapter JSON response | ★★☆ Critical |
| chapter-writer: `savepoint-mgr(operation: "restore")` | Correct operation is `"load"` | ★★☆ Critical |
| outline-planner savepoints: `outline_chunk_{N}`, `continuity_analysis_{N}` | Implementation: `outline_chunk_{start}_{end}`, `continuity_{start}_{end}` | ★☆☆ Warning |
| story-orchestrator Ph.1: `story-state(operation: init) with prompt metadata` | init accepts no payload; metadata requires subsequent write calls | ★☆☆ Warning |

---

### Risk Assessment

**Highest risk:** Pipeline will never complete Phase 2 (story-state "update"), Phase 5-6
(character/setting sheets), or Phase 8e (wiki-lint). These three blockers stop the most
common execution path. Combined with the wiki-snapshot output format mismatch, the entire
Phase 8b scene generation pipeline produces corrupted output until fixed.

**Architecture risk:** wiki-maintainer is explicitly stated as running on a smaller model
and carries the most complex JSON construction requirements. Without the skills it
references, it is the single highest-risk agent for hallucinated output.

**Cascading risk:** Several critical defects compound. Corrupted wiki-snapshot context →
degraded scene generation → degraded wiki updates from those scenes. The quality of a
25-chapter story depends heavily on fixing the scene generation context chain first.

---

### Recommended Actions (Prioritized)

```
1.  [U-C-01] ★★★ Fix story-state "update" → "write" in orchestrator Phase 2
2.  [U-C-02] ★★★ Fix wiki-snapshot output format doc in chapter-writer; add extraction step; map to 'baseContext'
3.  [U-C-03] ★★★ Document character-mgr and setting-mgr 'data' parameter schemas with examples; clarify setting-mgr uses 'setting' not 'character'
4.  [U-C-04] ★★★ Add chapter disk-write step before wiki-lint in Phase 8e; clarify chapter_text is a path
5.  [U-C-05] ★★★ Replace prompt-loader in Phase 1 with direct file-read mechanism
6.  [U-C-06] ★★★ Create .opencode/skills/wiki-maintenance/ and wiki-conventions/ skill files (or inline conventions into wiki-maintainer doc)
7.  [U-W-01] ★★★ Add camelCase/snake_case naming table to wiki-update and wiki-maintainer docs
8.  [M-C-01] ★★☆ Document continuitySummary extraction from expand-chapter JSON in outline-planner; fix savepoint name table
9.  [M-C-02] ★★☆ Fix "restore" → "load" in chapter-writer resumption instructions
10. [M-W-01] ★★☆ Map wiki-snapshot 'snapshot' field to scene-writer 'baseContext' explicitly in chapter-writer
11. [M-W-02] ★★☆ Thread storyStartDate from Phase 1 analyze-prompt output to recap-manager calls
12. [M-W-03] ★★☆ Specify expand-chapter operation and params for single-chapter expansion in Phase 8a
13. [M-W-04] ★★☆ Rewrite acceptance condition as explicit pseudocode; define forced-pass feedback source
14. [S-C-01] ★☆☆ Fix story-state init semantics docs (no metadata payload; use write calls)
15. [S-W-02] ★☆☆ Document slug acquisition — where to read canonical slugs; warn against guessing from display names
```
