---
date: "2026-04-25"
issue: 181
pr: 192
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: active
---

## CLI entry points call sys.exit — use underlying helpers in orchestration code

### Finding

PR #192 wired story assembly into the pipeline orchestrator. The Coder correctly identified that
calling `cmd_assemble()` (the CLI entry point in `story_assembler.py`) from within orchestrator code
would be unsafe. `cmd_assemble()` calls `_error()` on any failure, which calls `sys.exit()` — this
would terminate the entire orchestrator process. The Coder implemented inline assembly directly
inside the orchestrator instead.

In this case inline assembly was also simpler because the orchestrator already held `approved_chapters`
in memory, eliminating the need to read them back from disk.

### Observation

Python CLI tools follow the pattern: thin `cmd_*()` entry point → calls `_error()` / `sys.exit()` on
failure → delegates to underlying helpers. This pattern is safe when the function is invoked as a
subprocess or from `if __name__ == "__main__"`, but it is fatal when called from library or
orchestration code — any error path kills the host process with no exception to catch.

Every `cmd_*()` function in `src/tools/` is an entry point, not a library function. Calling them from
`src/presentation/`, `src/application/`, or tests crosses an architectural boundary. The underlying
helpers (e.g., `_discover_chapter_numbers()`, `_load_chapter_content()`, `_write_output_file()`)
are the correct integration surface.

### Suggested Improvement

Add a Code Pattern entry to `coder.agent.md` under "Code Patterns" with the rule:
- `cmd_*()` CLI entry points terminate on error via `sys.exit()` — safe only as
  `if __name__ == "__main__"` or subprocess entrypoints. When integrating tool logic into
  orchestration or library code, call the underlying `_helper()` functions directly, or refactor
  the shared logic into a helper the entry point delegates to.

### Action Taken

Applied: Added "CLI entry point isolation" code pattern to `coder.agent.md` under "Code Patterns".
