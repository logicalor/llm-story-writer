# Task Breakdown: Author Persona System

> Implements [PRD](./prd.md)

**Date:** 2026-05-08

## Tasks

### Task 1: Add ADR for author persona architecture

**Type:** documentation
**Estimated scope:** small
**Dependencies:** none

**Description:**

Record the architectural decision: a static, story-scoped author persona document with deterministically-derived agent-specific views, injected as `system_message` on every generative LLM call. This is non-trivial because it establishes a new layer in the prompt architecture that is parallel to (not part of) the wiki, and it constrains where personas may and may not be applied.

**Acceptance Criteria:**

- [ ] `docs/planning/adr/015-author-persona-system.md` exists with full ADR template
- [ ] ADR documents the static-vs-dynamic decision with reference to research findings
- [ ] ADR documents the four agent-specific views and the rationale for excluding analytical agents
- [ ] ADR is linked from the PRD and from `.github/notes/architecture.md`

**Key Files:**

- `docs/planning/adr/015-author-persona-system.md` — new ADR
- `.github/notes/architecture.md` — add link reference

---

### Task 2: Persona document schema and generation prompt template

**Type:** backend
**Estimated scope:** small
**Dependencies:** Task 1

**Description:**

Define the canonical persona Markdown structure (frontmatter fields and the five trait sections) and author the generation prompt template that converts the existing analysis chunks (`core_story_foundation`, `tone_style`, `theme_message`, `story_elements`) into a persona document. The prompt must produce second-person prose, target a configurable word budget (default 225, range 100–500), and include the structured anti-pattern bullets.

**Acceptance Criteria:**

- [ ] `prompts/persona/generate.md` exists with template variables for `core_story_foundation`, `tone_style`, `theme_message`, `story_elements`, `word_budget`
- [ ] Template instructs the LLM to produce a YAML frontmatter block and five named trait sections plus anti-patterns
- [ ] Template includes a `{{ word_budget }}` substitution that drives the target length instruction in the prompt body
- [ ] Schema is documented in a header comment block in the template
- [ ] Schema example output is included in the template prompt to anchor the LLM
- [ ] Test: `prompt-loader --prompt-id persona/generate --variables '{"word_budget": 225, ...}'` renders without error

**Key Files:**

- `prompts/persona/generate.md` — new generation prompt template
- `prompts/persona/_schema.md` — schema reference (optional documentation file)

---

### Task 3: `persona-builder` Python tool — `generate` operation

**Type:** backend
**Estimated scope:** medium
**Dependencies:** Task 2

**Description:**

Create the `persona-builder` CLI tool implementing the `generate` operation. The tool reads the four required savepoints (`core_story_foundation`, `tone_style`, `theme_message`, `story_elements`), renders `prompts/persona/generate.md` with the configured `word_budget`, calls the LLM, validates the returned document has the required frontmatter and section headings, and writes it to `stories/<name>/persona/persona.md`. On success it also writes a savepoint pointer (`step: "persona"`) recording the file path.

The tool follows the existing tool patterns (`outline_generator.py`, `scene_writer.py`): `argparse` CLI, `_success`/`_error` JSON output, savepoint integration via `FilesystemSavepointRepository`.

**Acceptance Criteria:**

- [ ] `src/tools/persona_builder.py` exists with `generate` operation
- [ ] CLI accepts `--name <story>`, optional `--model <model-id>`, optional `--word-budget <int>` arguments
- [ ] `--word-budget` defaults to 225 when omitted; clamped to range 100–500
- [ ] Reads required savepoints; reports a clear error if any are missing
- [ ] Renders the generation prompt and calls the LLM via `_llm.generate_text`
- [ ] Validates returned document parses as Markdown with YAML frontmatter and required section headings; on validation failure, writes the raw response to `persona/.last-failed.md` and reports a structured error
- [ ] Writes successful output to `stories/<name>/persona/persona.md`
- [ ] Saves savepoint `persona` containing the relative file path and a generation timestamp
- [ ] Output is JSON to stdout: `{status, operation, data: {persona_path, savepoint_step, word_count}}`

**Key Files:**

- `src/tools/persona_builder.py` — new tool
- `tests/unit/test_persona_builder.py` — new test module

---

### Task 4: `persona-builder` `get-view` operation with derivation logic

**Type:** backend
**Estimated scope:** medium
**Dependencies:** Task 3

**Description:**

Add the `get-view` operation that reads `stories/<name>/persona/persona.md` and returns one of four agent-specific projections (`outline`, `chapter`, `scrubber`, `editor`) as plain text on stdout, suitable for direct use as a `system_message` parameter.

Derivation rules (per PRD § Agent Views):

- `outline` → identity paragraph, narrative philosophy, thematic sensibility, pacing philosophy, anti-patterns
- `chapter` → full document (all sections)
- `scrubber` → identity paragraph (one-sentence form), prose texture, dialogue style, anti-patterns
- `editor` → identity paragraph, prose texture, dialogue style, narrative philosophy, anti-patterns

Views are derived at read time (not stored as separate files). If the persona file does not exist, the tool exits with status 0 and empty stdout — callers must treat empty output as "no persona available" and skip system-message injection. This graceful-degradation contract is critical for the configuration kill-switch and for legacy stories.

**Acceptance Criteria:**

- [ ] `persona-builder get-view --name <story> --view <view-name>` returns the projection on stdout
- [ ] `--view chapter` returns the full document body (without YAML frontmatter)
- [ ] `--view outline`, `scrubber`, `editor` return only the sections specified in the PRD
- [ ] Missing persona file → exit 0, empty stdout, no error message on stderr
- [ ] Invalid view name → exit 1, structured JSON error on stdout
- [ ] Output is plain text (not JSON) — designed for direct use as `system_message`
- [ ] Unit tests cover all four view types and the missing-persona case

**Key Files:**

- `src/tools/persona_builder.py` — add `get-view` operation
- `tests/unit/test_persona_builder.py` — extend tests

---

### Task 5: `persona-builder` `regenerate` operation with history archiving

**Type:** backend
**Estimated scope:** small
**Dependencies:** Task 3

**Description:**

Add the `regenerate` operation. Behaviour: if `persona.md` exists, copy it to `persona/history/persona-YYYYMMDD-HHMMSS.md` (timestamped) before invoking the same generation logic as `generate`. This allows the user to retry persona generation while keeping audit history.

**Acceptance Criteria:**

- [ ] `persona-builder regenerate --name <story>` archives the existing persona before regenerating
- [ ] Archive directory `stories/<name>/persona/history/` is created if missing
- [ ] Archive filename uses UTC timestamp `persona-YYYYMMDD-HHMMSS.md`
- [ ] Calling `regenerate` when no persona exists is equivalent to `generate` (no error)
- [ ] Unit test verifies archive file is created with correct content

**Key Files:**

- `src/tools/persona_builder.py` — add `regenerate` operation
- `tests/unit/test_persona_builder.py` — extend tests

---

### Task 6: Plumb `system_message` and emphasis delta through `outline-generator` and `scene-writer`

**Type:** backend
**Estimated scope:** medium
**Dependencies:** Task 4

**Description:**

The `_call_llm` helper in `outline_generator.py` and the equivalent in `scene_writer.py` currently call `_llm.generate_text(prompt, model=model)` without a `system_message`. Modify both to accept and forward an optional `system_message` parameter. Add a `--persona-view <view-name>` CLI argument to operations that perform generative work; when present, the tool reads the view via `persona-builder get-view` (subprocess call) and passes it as `system_message`.

Additionally, add an optional `--emphasis-delta <text>` CLI argument to chapter-level and scene-level generative operations. When present, the delta text is appended to the user prompt under a clearly-labelled section (e.g., `\n\n## Chapter Emphasis\n\n<delta text>`) so the model sees a chapter-local tonal hint alongside the static persona system message. Empty/missing delta produces identical behaviour to current code.

Operations that gain `--persona-view` and `--emphasis-delta`:

- `outline-generator`: `expand-chapter`, `refine-chapter`, any operation that produces chapter-level prose-relevant text
- `scene-writer`: `generate`, `revise`

Operations that do **not** gain them:

- `outline-generator`: `analyze-prompt`, `generate-elements` (analytical / structural)
- `scene-writer`: `parse-definitions`, `assemble-chapter`, `scrub-analyze`, `voice-analyze` (analytical)

**Acceptance Criteria:**

- [ ] `_call_llm` and `_call_llm_messages` in both tools accept optional `system_message` parameter
- [ ] Empty/missing system_message produces identical behaviour to current code (no system message sent)
- [ ] `--persona-view <view>` and `--emphasis-delta <text>` arguments added to specified operations only
- [ ] When `--persona-view` is provided, the tool subprocess-invokes `persona-builder get-view` and uses the result
- [ ] When `--emphasis-delta` is provided, the delta text is appended to the user prompt under a labelled section
- [ ] Empty stdout from `persona-builder get-view` is treated as "no persona" — tool proceeds without system_message
- [ ] Empty/missing `--emphasis-delta` produces identical behaviour to current code
- [ ] `LLM_DEBUG_LOG` records show the system_message in the messages array when persona is active, and the delta text within the user message when active
- [ ] Existing tests still pass (no `--persona-view` and no `--emphasis-delta` provided ⇒ no behaviour change)
- [ ] New tests verify system_message and delta forwarding

**Key Files:**

- `src/tools/outline_generator.py` — modify `_call_llm`, `_call_llm_messages`, add CLI arguments to relevant operations
- `src/tools/scene_writer.py` — same modifications
- `tests/unit/test_outline_generator.py` — extend
- `tests/unit/test_scene_writer.py` — extend (if it exists; otherwise add minimal coverage)

---

### Task 7: Configuration flags and graceful-degradation contract

**Type:** backend
**Estimated scope:** small
**Dependencies:** Task 6

**Description:**

Add four new fields under `generation` in the configuration schema:

- `enable_author_persona: bool` (default `true`) — master kill switch
- `persona_model: str | null` (default `null`, falls back to `creative_model`) — model override for persona generation
- `persona_word_budget: int` (default `225`, valid range 100–500) — target document length
- `enable_emphasis_delta: bool` (default `true`) — per-chapter tonal delta on top of the static persona

When `enable_author_persona` is `false`, the orchestrator must not invoke the persona-generation phase, and downstream agents must not pass `--persona-view` to their tool calls. When the flag is `true` but the persona file does not exist (legacy story), agents must continue gracefully — `persona-builder get-view` already returns empty stdout in that case (Task 4), so the contract holds end-to-end.

When `enable_emphasis_delta` is `false`, the chapter-writer agent must not pass `--emphasis-delta` to its tool calls, regardless of the static persona's status.

**Acceptance Criteria:**

- [ ] `config.example.yml` documents all four new fields with comments explaining valid ranges and defaults
- [ ] `GenerationSettings` (Python dataclass) exposes `enable_author_persona: bool`, `persona_model: str | None`, `persona_word_budget: int`, `enable_emphasis_delta: bool`
- [ ] Config loader validates `persona_word_budget` in range 100–500 (clamps or errors on out-of-range)
- [ ] Existing stories without personas continue to generate successfully with the flags enabled (graceful degradation verified by integration smoke test)
- [ ] `enable_author_persona: false` produces zero `system_message` injections across all tool calls (verified via `LLM_DEBUG_LOG` inspection in test)
- [ ] `enable_emphasis_delta: false` produces zero `--emphasis-delta` invocations (verified via debug log)

**Key Files:**

- `config.example.yml` — document new fields
- `src/domain/value_objects/generation_settings.py` (or equivalent) — add fields
- `src/config/config_loader.py` (or equivalent) — parse and validate new fields
- `tests/unit/test_config_loader.py` — extend if exists

---

### Task 8: Update agent prompts to dispatch persona-builder, forward views, and emit emphasis deltas

**Type:** backend (agent prompts)
**Estimated scope:** medium
**Dependencies:** Task 7

**Description:**

Update the affected agent prompt files to invoke `persona-builder`, forward the appropriate view to their tool calls, and (for chapter-writer) derive and forward the per-chapter emphasis delta.

- **`prompts/agents/story-orchestrator.md`**: no direct persona invocation — the orchestrator dispatches `outline-planner`, which owns persona generation. Document that the persona phase is owned by outline-planner so future contributors do not move it.
- **`prompts/agents/outline-planner.md`**: add a workflow step (after `generate-elements`) that calls `persona-builder generate` with the configured `word_budget`. Skip the call when `config.generation.enable_author_persona` is false. For outline-expansion operations, pass `--persona-view outline`.
- **`prompts/agents/chapter-writer.md`**: per-scene generation calls pass `--persona-view chapter` to `scene-writer generate` and `scene-writer revise`. Additionally, derive a short emphasis-delta string from the current chapter's outline metadata (chapter tone label, beat, or arc position — e.g., `"climax: maximum tension, short sentences, sensory overload"`) and pass it as `--emphasis-delta`. Skip the delta when `config.generation.enable_emphasis_delta` is false.
- **`prompts/agents/prose-scrubber.md`**: `scene-writer revise` calls pass `--persona-view scrubber`. No emphasis delta (scrubbing is local prose work, not narrative shaping).
- **`prompts/agents/final-editor.md`**: `scene-writer revise` calls pass `--persona-view editor`. No emphasis delta.
- **`prompts/agents/consistency-checker.md`**: explicitly document that this agent does **not** use a persona view or emphasis delta (defensive — prevents future contributors from adding one inappropriately).

**Acceptance Criteria:**

- [ ] All six agent prompt files updated as specified
- [ ] Each updated agent prompt explicitly states which persona view (if any) it uses and why
- [ ] `outline-planner.md` documents the persona generation step and word-budget config wiring
- [ ] `chapter-writer.md` documents how the emphasis delta is derived from chapter outline metadata
- [ ] `consistency-checker.md` includes a one-sentence rationale for not using a persona view (cite Kim et al.)
- [ ] Outline-planner's persona generation step has explicit skip-on-config-false behaviour
- [ ] Chapter-writer's emphasis delta has explicit skip-on-config-false behaviour
- [ ] Manual smoke run: an end-to-end story generation completes successfully with persona and delta enabled

**Key Files:**

- `prompts/agents/story-orchestrator.md`
- `prompts/agents/outline-planner.md`
- `prompts/agents/chapter-writer.md`
- `prompts/agents/prose-scrubber.md`
- `prompts/agents/final-editor.md`
- `prompts/agents/consistency-checker.md`

---

### Task 9: Integration test — full persona injection path

**Type:** backend (integration test)
**Estimated scope:** small
**Dependencies:** Task 8

**Description:**

Add an integration test that exercises the full persona path with a stub LLM: persona generation → view derivation → `system_message` injection in `outline-generator` and `scene-writer` tool calls → emphasis delta forwarded by chapter-writer. The test mocks `_llm.generate_text` (or sets `LLM_DEBUG_LOG` and inspects the JSONL output) to assert that the system_message contains expected persona-view markers (e.g., the identity paragraph) on appropriate calls and is absent on calls that should not receive it (recap-manager, critique-runner, scrub-analyze, voice-analyze), and that the emphasis-delta text appears in the user message body for chapter-writer scene generation calls.

**Acceptance Criteria:**

- [ ] `tests/integration/test_persona_injection.py` exists
- [ ] Test verifies persona file is generated under `stories/<test-name>/persona/persona.md`
- [ ] Test verifies generated persona word count is within ±20% of `persona_word_budget`
- [ ] Test verifies `outline-generator expand-chapter --persona-view outline` injects the outline view as system_message
- [ ] Test verifies `scene-writer generate --persona-view chapter --emphasis-delta "<text>"` injects both the persona view as system_message and the delta text in the user message
- [ ] Test verifies `recap-manager` and `critique-runner` calls do **not** include persona content in system_message
- [ ] Test verifies `enable_author_persona: false` ⇒ zero system_message injections
- [ ] Test verifies `enable_emphasis_delta: false` ⇒ zero `--emphasis-delta` invocations even when persona is enabled

**Key Files:**

- `tests/integration/test_persona_injection.py` — new test module

---

### Task 10: Update documentation and project notes

**Type:** documentation
**Estimated scope:** small
**Dependencies:** Tasks 1–9 complete

**Description:**

Document the feature for end users and developers.

- Add a `docs/features/author-persona.md` user-facing feature page describing what the persona is, how to inspect/edit/regenerate it, how the per-chapter emphasis delta works, and how to disable both via config.
- Update `docs/manual.md` (or equivalent) to mention the new pipeline phase.
- Update `.github/notes/architecture.md` with the new persona phase, the `persona-builder` tool entry in the tools table, and a link to the ADR.
- Add a brief note to `.github/notes/patterns.md` (or `gotchas.md`) about the rule "never apply persona to analytical agents."

**Acceptance Criteria:**

- [ ] `docs/features/author-persona.md` exists with installation, configuration, inspection, and emphasis-delta guidance
- [ ] `.github/notes/architecture.md` lists `persona-builder` in the tools table and documents the new pipeline phase
- [ ] `.github/notes/patterns.md` (create if absent) records the analytical-agent exclusion rule
- [ ] User-facing docs explicitly cover: how to disable persona, how to disable emphasis delta independently, how to tune `persona_word_budget`, how to regenerate, where the file lives, what to edit if you want to override the LLM-generated persona

**Key Files:**

- `docs/features/author-persona.md`
- `docs/manual.md`
- `.github/notes/architecture.md`
- `.github/notes/patterns.md`

---

## Task Ordering Summary

```
1 (ADR) ──► 2 (schema + prompt) ──► 3 (generate) ──► 4 (get-view) ──► 6 (system_message plumbing) ──► 7 (config) ──► 8 (agent prompts) ──► 9 (integration test) ──► 10 (docs)
                                          │
                                          └─► 5 (regenerate)
```

Tasks 5 and 6 can be parallelised after Task 4 completes. Tasks 1–10 are otherwise sequential.

## Effort Summary

- **Small tasks** (1, 2, 5, 7, 9, 10): 6 tasks
- **Medium tasks** (3, 4, 6, 8): 4 tasks
- **Large tasks**: none

Each task is sized for one Orchestrator dispatch (issue → branch → implement → verify → PR).
