---
description: Pick an outstanding task from a planning document and drive it through the full GitHub-auditable feature-based workflow.
agent: Orchestrator V3
tools:
    - web/githubRepo
    - github/*
---

# Work on a Task

Pick up a task from a planning document and drive it through the full GitHub-auditable feature-based workflow.

## Step 1 — Choose a Task

1. List every task file under `docs/planning/` (check `docs/planning/**/tasks*.md` including subdirectories like `completed/` and active phase directories).
2. For each file, scan its tasks and note their **status** (completed vs outstanding) based on the acceptance criteria checkboxes.
3. Present a numbered summary to the user showing **only outstanding tasks** grouped by planning document. Include the task number, title, type (frontend/backend), estimated scope, and dependency status (ready vs blocked). Example format:

    ```
    ## completed/tiptap-content-builder/tasks.md
    1. Task 3 — Slash command extension and popup menu (frontend, medium) — READY
    2. Task 5 — Block menu (frontend, small) — BLOCKED by Task 4
    ...

    ## phase-2-operations-mvp/tasks.md
    3. Task 12 — Announcement CRUD (full-stack, large) — READY
    ...
    ```

4. Ask the user: **"Which task would you like me to work on?"**
5. Wait for the user's selection before proceeding.

## Step 2 — Find or Create the GitHub Issue

Once the user selects a task:

1. Read [.github/notes/repo.md](../../.github/notes/repo.md) for `OWNER` and `REPO`.
2. Search open GitHub issues for keywords matching the selected task title using `#tool:github/search_issues`.
    - If a matching issue exists, confirm with the user and use it.
    - If no match, create a new issue with `#tool:github/issue_write`
        - **Title**: Concise description derived from the task title
        - **Body**: Full task description, acceptance criteria (copied from the planning doc), dependency references, and a link back to the planning document
        - **Labels**: `feature` or `bug` as appropriate
3. Record the issue number.

## Step 3 — Create a Branch (locally)

> **IMPORTANT**: All branch creation, file editing, committing, and pushing MUST happen locally via git CLI commands in the terminal. NEVER use GitHub API tools (`github/create_branch`, `github/create_or_update_file`, `github/push_files`) to create branches or modify files remotely.

1. Ensure the local repo is up to date and create the branch from `development`:

    ```bash
    git checkout development && git pull origin development
    git checkout -b {branch-name}
    ```

    - Features: `feat/issue-N-short-description`
    - Bug fixes: `fix/issue-N-short-description`

2. Push the branch to set up tracking:
    ```bash
    git push -u origin {branch-name}
    ```
3. Record the branch name.

## Step 4 — Continue with Normal Orchestrator Workflow

With the issue and branch established, proceed with the standard Orchestrator workflow from **Step 3 (Plan)** onward — research, implement, write verification tests, commit, create PR, verify, and document.

All code changes, commits, and pushes must be performed locally via the terminal. GitHub API tools should only be used for issue tracking, PR creation, and code review — never for file or branch operations.

## ⛔ CRITICAL PROHIBITIONS

**NEVER violate these rules:**

1. **Never use `--no-verify` with git commit** — Pre-commit hooks must ALWAYS run.

2. **Never mark tests as skipped** — Tests must pass or fail. Skipped tests provide false confidence.

Refer to the [Orchestrator agent instructions](../agents/orchestrator-v3.agent.md) for the full workflow details.
