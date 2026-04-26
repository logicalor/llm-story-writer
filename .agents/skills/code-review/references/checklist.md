# Review Checklist

## Code

- Validate all external inputs at boundaries.
- Preserve clean architecture dependency direction.
- Avoid ad hoc string parsing where a structured parser exists.
- Do not call CLI `cmd_*` functions from application code if they can `sys.exit()`.
- Preserve exception causes when wrapping errors.
- Check savepoint resume paths perform required state writes.

## Tests

- Tests should assert meaningful values, not only counts.
- CLI validation tests should assert exit code and stderr fragment.
- LLM JSON parsing should test invalid JSON, non-dict roots, null sections, and mixed list items when relevant.
- When disk writes are added, existing tests must patch base paths.
- New test files should cover production-used subjects, not orphaned helpers.

## Docs And Instructions

- Sweep for stale references after renames, deletions, or architecture changes.
- Verify markdown links resolve.
- Keep summary tables synchronized with body text.
- Keep numbered workflow steps contiguous.
- Update `AGENTS.md`, `.github/copilot-instructions.md`, `docs/manual.md`, and `docs/tools.md` when architecture terms change.

## Agent And Skill Files

- Tool names must match actual Codex or project tools.
- Copilot-only tool names must not be presented as Codex-callable.
- Avoid stale `.opencode` and TypeScript wrapper references in Python-native workflow docs unless discussing historical context.
- When a skill references a detailed file, ensure that file exists.

## False Positive Filters

- Ignore `.vscode/` findings for committed-secret review if the file is gitignored and not in the diff.
- Treat out-of-diff violations as follow-up issues unless the PR relies on that behavior.
- Verify "companion file not updated" claims by reading the companion file.
- Verify annotation-like comments exist in actual files before treating them as source defects.
