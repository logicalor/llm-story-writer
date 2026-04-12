---
description: Autonomously select the most pertinent open GitHub issue and drive it through the full GitHub-auditable feature-based workflow.
agent: Orchestrator V3
tools: [read, web/githubRepo, 'github/*']
---

# Work on the Most Pertinent Issue

Autonomously identify the highest-priority open GitHub issue and drive it through the full GitHub-auditable feature-based workflow — no task selection required from the user.

## Step 1 — Select the Most Pertinent Issue

1. Read [.github/notes/repo.md](../../.github/notes/repo.md) for `OWNER` and `REPO`.
2. Fetch all open issues using `#tool:github/list_issues` (exclude pull requests).
3. For each issue, evaluate:
    - **Labels**: `bug` > `feature` > `enhancement` > unlabelled
    - **Age**: older issues rank higher if not blocked
    - **Comments / activity**: higher engagement signals importance
    - **Dependencies**: skip any issue whose description or comments indicate it is blocked by another open issue
    - **Scope**: prefer issues that appear self-contained and actionable (avoid epics that require breaking down)
4. Produce a short internal ranking (you do not need to show this to the user) and select the single most pertinent issue.
5. Present your selection to the user:

    ```
    Selected issue #N — "{title}"

    Rationale: <one sentence explaining why this issue was chosen>

    Labels: ... | Opened: ... | Comments: ...

    Summary:
    <two or three sentence description of what needs to be done>
    ```

## Step 2 — Continue with Normal Orchestrator Workflow

The issue is already located — **skip the Orchestrator's Step 1 (issue creation/search)**. Proceed directly from **Step 2 (Create Feature Branch)** of the standard Orchestrator workflow: create the branch, plan, implement, write verification tests, create the PR, run the review cycle, and document.

Refer to the [Orchestrator agent instructions](../agents/orchestrator-v3.agent.md) for the full workflow details.
