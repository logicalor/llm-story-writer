---
date: "2026-04-27"
issue: 211
pr: 217
category: instruction
targets:
  - ".github/notes/gotchas.md"
  - ".github/agents/coder.agent.md"
  - ".github/agents/_shared/review-checklist.md"
severity: minor
status: archived
---

## OpenAI SDK 2.x type casts required for mypy compatibility

### Finding

PR #217 (issue #211) restored mypy baseline for the OpenAI async provider by adding explicit `cast()` calls for six OpenAI SDK 2.x return types that mypy could not infer:

- `cast(AsyncOpenAI, client)` — base client instantiation
- `cast(AsyncStream[ChatCompletionChunk], stream)` — streaming response
- `cast(ChatCompletion, response)` — non-streaming response
- `cast(str, choice.delta.content)` — chunk content extraction
- `cast(str, choice.message.content)` — message content extraction
- `cast(str, choice.finish_reason)` — finish reason extraction

The OpenAI SDK 2.x uses heavy generics and union return types (`ChatCompletion | AsyncStream[ChatCompletionChunk]`) that mypy cannot narrow without explicit casts or runtime `isinstance()` guards. The codebase uses `if stream:` branching, but mypy does not narrow unions on boolean flags.

### Observation

This is a recurring pattern whenever the project integrates a new typed Python SDK with complex generics. Two anti-patterns were avoided:

1. **`# type: ignore` suppression** — would silence the error but remove all type safety for that line, allowing future regressions to pass undetected.
2. **Runtime `isinstance()` guards** — would add unnecessary overhead and code clutter for types that are already contractually guaranteed by the SDK.

Explicit `cast(TargetType, expr)` is the correct middle ground: it documents the developer's intent, preserves type safety for downstream usage, and does not affect runtime behavior. However, `cast()` is idiomatic only when the type is *contractually* guaranteed (e.g., by the SDK's documented return semantics or by prior branching logic). It must not be used to paper over genuine type uncertainty.

### Suggested Improvement

1. **coder.agent.md Code Patterns** — add "Typed SDK integration: `cast()` vs `isinstance()` vs `# type: ignore`" pattern documenting when each is appropriate.
2. **review-checklist.md Phase 2 General** — add a checkbox prompting reviewers to verify that `# type: ignore` comments have a documented rationale and that `cast()` is preferred for contractually guaranteed types.
3. **gotchas.md** — add an entry documenting the OpenAI SDK 2.x cast pattern as a reference for future SDK integrations.

### Action Taken

Applied:
- Added gotcha entry to `.github/notes/gotchas.md` under "Python Patterns" documenting the `cast()` pattern for typed SDK integration.
- Added "Typed SDK integration" Code Pattern to `.github/agents/coder.agent.md`.
- Added review checklist item to `.github/agents/_shared/review-checklist.md` Phase 2 General.
