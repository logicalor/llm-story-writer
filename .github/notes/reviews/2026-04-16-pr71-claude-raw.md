# Code Review Report — PR #71

**Branch:** `feat/issue-69-compaction-plugin-behavioral-tests`
**Reviewer:** Claude Opus 4.6
**Date:** 2026-04-16

---

## Review Summary

This PR adds a Node.js/Vitest behavioral test harness for the compaction plugin, introducing unit tests for five exported utility functions and integration tests for the `assembleContext` pipeline. The implementation is clean, tests are well-structured with good edge case coverage, and the export block is properly isolated. Two warnings relate to non-reproducible dependency specifiers and missing documentation updates for the new test harness.

**Files Reviewed:** 8
**Findings:** 0 Critical, 2 Warning, 3 Suggestion

---

## Findings

### Critical Findings

None.

### Warning Findings

```
[W-01] Non-reproducible dependency version specifiers
Category: Correctness
Severity: Warning
File: package.json
Lines: 8-9
Description: Both devDependencies use "latest" as the version specifier.
  While the committed package-lock.json pins exact versions (typescript 6.0.2,
  vitest 4.1.4), any developer running `npm install` after deleting or
  regenerating the lockfile will resolve to whatever version is current at that
  time. This makes builds non-reproducible across environments and risks
  breaking changes silently entering the project.
Suggestion: Pin to the exact major versions currently resolved:
  "typescript": "^6.0.0",
  "vitest": "^4.1.0"
  This allows patch/minor updates while preventing unexpected major version
  jumps.
```

```
[W-02] Feature documentation not updated for new test harness
Category: Documentation
Severity: Warning
File: docs/features/compaction-plugin.md
Lines: 170-185
Description: The "Testing" section at the bottom of the compaction plugin
  feature doc describes only the Python structural verification tests
  (pytest). This PR introduces a complete Node.js behavioral test suite using
  Vitest, but the documentation does not mention it. Developers looking at the
  feature docs will not discover the `npm test` command or the behavioral test
  coverage.
Suggestion: Add a subsection under "Testing" for the behavioral tests:

  ### Behavioral Tests

  The plugin's core functions are tested with Vitest (Node.js). Unit tests
  cover `parseFrontmatter`, `unquote`, `estimateTokens`, `isWithinBase`, and
  `getCurrentPosition`. Integration tests verify `assembleContext` against
  real filesystem state.

  ```bash
  npm test
  ```

  Test files: `.opencode/plugins/__tests__/story-compaction.test.ts` (unit),
  `.opencode/plugins/__tests__/story-compaction.integration.test.ts` (integration).
```

### Suggestions

```
[S-01] Missing trailing newline in .gitignore
Category: Style
Severity: Suggestion
File: .gitignore
Lines: 181
Description: The file does not end with a newline character (POSIX
  convention). This was pre-existing but the diff perpetuates it. Many tools
  and diff viewers produce cleaner output when files end with a newline.
Suggestion: Add a trailing newline after the last line (`node_modules/`).
```

```
[S-02] Long single-line string literals in integration test
Category: Style
Severity: Suggestion
File: .opencode/plugins/__tests__/story-compaction.integration.test.ts
Lines: 37-45
Description: The wiki file content strings (e.g., the writeFileSync calls
  for alice.md, main-quest.md, chapter-1.md) are very long single-line
  strings that exceed typical line-length limits. While this works correctly,
  it reduces readability.
Suggestion: Consider using template literals with actual newlines, or
  breaking these into multi-line strings. Example:

  writeFileSync(
    join(wikiDir, "characters", "alice.md"),
    [
      "---",
      "title: Alice",
      "role: protagonist",
      "detail_levels:",
      "  L1: A brave adventurer",
      "---",
      "Full character bio here.",
    ].join("\n"),
  );
```

```
[S-03] Export block placement could use architectural note
Category: Style
Severity: Suggestion
File: .opencode/plugins/story-compaction.ts
Lines: 523-533
Description: The named exports are placed between the assembleContext
  function and the plugin API interfaces/default export. The comment
  "Named exports for testing" makes the intent clear, which is good.
  However, there is no note explaining that these exports are safe alongside
  the default export — a future maintainer might worry about side effects on
  the OpenCode plugin loader.
Suggestion: Consider extending the comment to note that OpenCode loads only
  the default export, so named exports do not affect runtime behaviour:

  // --- Named exports for testing ---
  // OpenCode loads this file via the default export only.
  // Named exports are used by the Vitest test suite and have no runtime effect.
```

---

## Phase Checklist Summary

### Phase 1 — Structural Review

- [x] **Commit message** — `feat(testing): add Node.js behavioral test harness for compaction plugin (#69)` — clear, follows convention, references issue
- [x] **Branch name** — `feat/issue-69-compaction-plugin-behavioral-tests` — follows convention
- [x] **Scope** — ~390 lines of content changes (excluding lockfile), reasonable
- [x] **No unrelated changes** — all changes directly support the test harness
- [x] **No numbered step list gaps** — N/A (no step lists in changed files)
- [x] **No file relocations** — N/A
- [x] **No sibling orphaning** — N/A
- [x] **No stale prose counts** — N/A
- [x] **No tools array changes** — N/A
- [x] **No model-variant sync needed** — N/A
- [x] **No section heading drift** — N/A
- [x] **No YAML frontmatter removal** — N/A
- [x] **No agent model field changes** — N/A
- [x] **Shell snippet safety** — N/A (no shell snippets in changed files)

### Phase 2 — Code Review

- [x] Code follows project conventions (TypeScript camelCase, proper imports)
- [x] Naming consistent with codebase
- [x] No overly complex functions
- [x] No code duplication
- [x] Import ordering correct (Node.js builtins → vitest → local)
- [x] Proper separation of concerns — exports are isolated, tests are separate files
- [x] No tight coupling — tests use public API only
- [x] Error handling appropriate — `assembleContext` returns null on failures, tests verify this

### Phase 3 — Frontend Review

N/A — no frontend changes.

### Phase 4 — Security Review

- [x] Path traversal — `isWithinBase` is properly tested including `../` traversal case
- [x] Temp directory usage — `mkdtempSync` in integration tests is secure
- [x] No credentials or API keys in code
- [x] No user input handling (test-only code)
- [x] `rmSync` cleanup in `afterEach` is properly scoped to test-created temp dirs

### Phase 5 — Testing Review

- [x] New test files cover all exported functions
- [x] Test conventions followed (describe/it blocks, clear test names)
- [x] Edge cases tested: empty strings, missing data, invalid JSON, path traversal, missing frontmatter, empty chapters
- [x] No skipped tests
- [x] Assertions are meaningful — checking specific values, not just truthiness
- [x] Integration tests properly clean up temp directories
- [x] Both happy path and error paths covered

### Phase 6 — Performance Review

- [x] No performance concerns — test files only
- [x] Integration tests use temp directories (no persistent side effects)

### Phase 7 — Documentation Review

- [ ] Feature docs not updated for new test harness — see [W-02]
- [x] No ADR needed (testing addition, not architectural change)
- [x] Code comments present where needed (export block comment)

---

## Overall Assessment

The PR is well-implemented and close to merge-ready. The test coverage is thorough, hitting both unit and integration levels with good edge case variety. The export mechanism is clean and non-invasive to the plugin's runtime behaviour.

Two items should be addressed before merge: the `"latest"` version specifiers in `package.json` should be pinned to version ranges for build reproducibility [W-01], and the feature documentation should be updated to mention the new behavioral test suite and the `npm test` command [W-02]. Neither is a blocking issue, but both reduce maintainability if left unresolved.

No security, correctness, or performance concerns were identified.
