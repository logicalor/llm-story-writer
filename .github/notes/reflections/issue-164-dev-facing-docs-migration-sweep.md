---
date: "2026-04-25"
issue: 164
pr: 175
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## `.github/copilot-instructions.md` absent from high-risk surface list; developer-facing docs missed in migration sweep

### Finding

PR #175 removed the `.opencode/` directory as part of a Node.js/OpenCode artefact cleanup. After the initial Coder pass, three high-visibility files still contained stale OpenCode references: `README.md`, `AGENTS.md`, and `.github/copilot-instructions.md`. All three were explicitly listed in the issue's acceptance criteria. The review cycle caught them before merge.

`AGENTS.md` is already in the "When relocating files" sub-bullet's high-risk surface list. `README.md` is covered by "root-level READMEs" in the rule preamble. `.github/copilot-instructions.md` is not mentioned anywhere in Rule 6.

### Observation

`.github/copilot-instructions.md` is injected into every VS Code Copilot context and is arguably a higher-impact surface than `AGENTS.md` itself (the rule currently says `AGENTS.md` is "injected into every Copilot context via `copilot-instructions.md`" — so `copilot-instructions.md` is the upstream authority). Stale technology references here affect every agent dispatch in the workspace.

The broader pattern: migration tasks (removing an entire directory or technology stack) tend to leave stale references in the most visible onboarding files precisely because those files describe the project at a high level, not at a code level, and are not proactively swept by import-level grep patterns.

### Suggested Improvement

In the "When relocating files" sub-bullet of Rule 6:
1. Update surface `(a)` to name `.github/copilot-instructions.md` alongside `AGENTS.md`.
2. Add a note about migration tasks explicitly checking high-visibility developer-facing files.

This also consolidates the source attribution with the issue #158 finding (which already applied the `AGENTS.md` and `.github/notes/` entires) by appending the issue #164 source to that sub-bullet.

### Action Taken

Applied: updated surface `(a)` in the "When relocating files" sub-bullet of Rule 6 in `.github/agents/coder.agent.md` to include `.github/copilot-instructions.md`; updated source attribution.
