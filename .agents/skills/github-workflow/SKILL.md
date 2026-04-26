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
9. Use the `reflection` skill when the task exposed agent-system friction or changed workflow instructions.
10. Review the diff.
11. Commit, push, and open or update the PR.

## Reflection Checkpoints

Use the `reflection` skill during GitHub workflow tasks when you notice a reusable workflow gotcha, stale instruction, unclear tool mapping, or agent/skill behavior that should be remembered.

Skill availability is determined from the current workspace. If `.agents/skills/reflection/SKILL.md` exists locally, use it even when the file is new on the current branch or absent from `origin/development`. Do not skip reflection because a skill or instruction file has not merged to the remote base branch yet.

Near the end of a task, check whether active notes exist in `.github/notes/reflections/`. Apply minor instruction fixes, propose major workflow changes, and archive processed notes according to the reflection skill.

## Codex Delegation

Codex subagents are optional and follow Codex rules: spawn them only when the user explicitly permits subagents, delegation, or parallel agent work. When permitted, use bounded roles:

- `worker`: implementation in a disjoint file set.
- `explorer`: focused codebase question.
- local main agent: git operations, final integration, verification, and user communication.

Do not mimic Copilot's automatic nested agent dispatch when Codex policy does not allow it.

## Copilot Subagent Touchpoints

Translate Orchestrator V3 handoffs into Codex-native workflow pieces:

| Copilot touchpoint | Codex coverage |
| --- | --- |
| `Researcher` | Use `project-memory`, local `rg`/file reads, Chroma queries, and optional `explorer` subagents only when the user explicitly permits delegation. |
| `Coder` | Implement locally by default; use `worker` subagents only with explicit delegation permission and disjoint file ownership. Main Codex owns integration. |
| `Test Writer` | Use the `test-verification` skill. Write or update tests locally by default; use a `worker` only when explicitly permitted. |
| `Documenter` | Use the `documentation-maintenance` skill. For documentation-only tasks, Codex may make the documentation change directly. |
| `Reviewer (Claude/GPT/Gemini)` | Use the `code-review` skill for local review. Do not attempt Copilot's three-model review fanout unless the user explicitly asks for parallel agents or multi-agent review. |
| `Synthesizing Reviewer` | Use `code-review` synthesis rules when raw review reports exist. Otherwise perform a single local maintainer review. |
| `Auditor` / `Synthesizing Auditor` | Use the `synthesized-audit` skill for repository healthchecks. It replaces Copilot's multi-model audit fanout with sequential Architect, Maintainer, and Product Documenter persona passes over shared evidence. |
| `PR Reviewer` / Copilot automated review | After a PR exists, inspect GitHub review comments or checks with GitHub plugin tools or `gh`; address actionable feedback through this workflow. |
| `Browser` | For browser automation or UI verification, use available local browser/test tooling when present. If no browser automation tool is available, run the closest local verification and report the limitation. |
| `Reflection` | Use the `reflection` skill to record, apply, propose, archive, and index workflow improvements. |
| `Deploy` | If deployment monitoring is requested or relevant after merge, inspect GitHub checks, Actions logs, deployment status, or configured production endpoints. Do not start a hotfix without a new workflow pass. |

Main Codex always retains ownership of GitHub operations, local git state, final verification, committing, pushing, PR updates, and user-facing status.

## Tool Mapping

Read `references/tool-mapping.md` before using GitHub, Chroma, Tavily, or Context7 from this workflow.

## Output

When done, report:

- issue and branch
- files changed
- verification run and result
- PR link or why no PR was created
- reflection notes recorded, applied, proposed, or skipped
- any residual risk or blocked step
