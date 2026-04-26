---
name: github-workflow
description: Use when asked to work on a GitHub issue, create or update a PR, address review feedback, publish local changes, run the repository development lifecycle, or coordinate implementation through Codex.
---

# GitHub Workflow

This is the Codex-native replacement for the Copilot Orchestrator workflow. It preserves the repo's GitHub-auditable lifecycle while using Codex tools and local git.

## Core Rules

1. Work locally first. Edit files in the workspace, run verification locally, then commit and push with git.
2. Never use remote file-write APIs to create source changes.
3. Never use `--no-verify`.
4. Never mark tests skipped to get a green suite.
5. Protect user work: inspect `git status --short` before edits and do not revert unrelated changes.
6. Use one issue per implementation session unless the user explicitly asks for planning or triage only.

## Normal Lifecycle

1. Resolve repo identity from `.github/notes/repo.md`.
2. Locate or create one GitHub issue unless the user only asked for read-only status, summary, or review inspection.
3. Create or check out a branch from `development`.
4. Gather memory with the `project-memory` skill.
5. Plan the change and identify files, tests, and risks.
6. Implement locally.
7. Run focused lint, formatting, type checks, and tests.
8. Update docs or notes when behavior, architecture, CLI, or workflows changed.
9. Review the diff.
10. Commit, push, and open or update the PR.

## Codex Delegation

Codex subagents are optional and follow Codex rules: spawn them only when the user explicitly permits subagents, delegation, or parallel agent work. When permitted, use bounded roles:

- `worker`: implementation in a disjoint file set.
- `explorer`: focused codebase question.
- local main agent: git operations, final integration, verification, and user communication.

Do not mimic Copilot's automatic nested agent dispatch when Codex policy does not allow it.

## Tool Mapping

Read `references/tool-mapping.md` before using GitHub, Chroma, Tavily, or Context7 from this workflow.

## Output

When done, report:

- issue and branch
- files changed
- verification run and result
- PR link or why no PR was created
- any residual risk or blocked step
