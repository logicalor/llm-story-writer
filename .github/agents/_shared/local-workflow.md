# Local-First Workflow & Critical Prohibitions

> Shared rules for all agents that create commits or interact with the GitHub API. **Include this file in every agent that performs git operations.**

---

## ⛔ CRITICAL PROHIBITIONS — NON-NEGOTIABLE

**NEVER violate these rules:**

1. **Never use `--no-verify` with git commit** — Pre-commit hooks must ALWAYS run. Bypassing them can introduce bugs, style violations, and security issues.

2. **Never mark tests as skipped** — Tests must pass or fail. Skipped tests provide false confidence.

---

## ⛔ LOCAL-FIRST WORKFLOW — NON-NEGOTIABLE

**All code changes MUST be made locally and synced to the remote branch via `git push`.**

Never use `mcp_github_push_files` or `mcp_github_create_file` to create commits directly on GitHub. These tools bypass:

1. **Pre-commit hooks** — linting, formatting, and type checks
2. **Local verification** — running tests before pushing
3. **Working tree sync** — your local repository won't know about remote-only commits

**Correct workflow:**

1. Edit files locally using `read_file` + `replace_string_in_file` + `create_file`
2. Run verification commands via `run_in_terminal` (lint, type-check, test — see `copilot-instructions.md` for project-specific commands)
3. Commit via `run_in_terminal`: `git add -A && git commit -m "..."`
4. Push via `run_in_terminal`: `git push origin {branch-name}`

**GitHub API tools are ONLY for:**

- Creating/searching issues (`mcp_github_issue_write`, `mcp_github_search_issues`)
- Creating branches (`mcp_github_create_branch`)
- Creating/updating PRs (`mcp_github_create_pull_request`, `mcp_github_update_pull_request`)
- Adding PR comments (`mcp_github_add_issue_comment`, `mcp_github_add_reply_to_pull_request_comment`)

**Never use GitHub API tools to write code files.**

---

## ⛔ STASH SAFETY PROTOCOL — MANDATORY

**After any `git stash pop`, you MUST audit the diff before proceeding.**

Run immediately after stash pop:

```bash
git diff HEAD --stat
```

Scan the output for unexpected changes to **test files**. Specifically:

- Any test file appearing as `modified` must be reviewed line-by-line
- **Security tests must NEVER be removed** unless the plan explicitly calls for it
- Cross-module tests, integration tests, and boundary tests are HIGH RISK — losing them creates silent regressions

**If a test file appears in the diff unexpectedly:**

1. Run `git diff HEAD -- path/to/test/test_file.py` to inspect the change
2. If test methods were removed and the plan does NOT call for removal → STOP
3. Restore the missing tests before proceeding

**Why this matters:** Stash operations can silently re-introduce deletions of test methods. These can pass through the full implementation cycle undetected and only be caught during PR review — requiring retroactive restoration and an extra review cycle.

**The fix takes seconds. Missing it costs cycles and reduces security coverage.**

---

## ℹ️ FEATURE BRANCH CONTAMINATION CHECK

**Before your first commit on a new feature branch, audit `git status --porcelain`.**

When `git checkout {branch}` is run while staged or unstaged changes exist in the working tree,
those changes travel with you to the new branch. This is standard Git behaviour — but it means
pre-existing local modifications (partial experiments, out-of-scope fixes, investigation
artefacts) can silently become part of your feature branch's first commit.

Run immediately after checkout:

```bash
git status --porcelain
```

Review every modified or staged file. For any file unrelated to the current feature:

1. Stash it: `git stash -- path/to/file.ext` — or reset it: `git checkout -- path/to/file.ext`
2. Record it as an out-of-scope observation in your handoff summary.

**Do not commit until `git status --porcelain` shows only in-scope files.**

---

## ℹ️ PRE-COMMIT HOOK OUTPUT TRUNCATION

**If commit tool output is truncated, `✓ Pre-commit checks passed` is the definitive success indicator.**

The pre-commit hook runs linting, formatting, and tests. On large
suites the terminal output can be truncated by the tool before all lines are visible. This is NOT
a failure indicator.

- **If you see `✓ Pre-commit checks passed`** at the end → the commit succeeded. Do not re-commit.
- **If output is truncated with no success banner** → run `git log --oneline -1` to check whether
  the commit was recorded before re-attempting.
- **Never re-run a commit without checking `git log` first** — double commits create noise.

---

## ℹ️ POST-COMMIT VERIFICATION LOOP

After any `git commit`, the pre-commit hook may auto-format files (Prettier, ESLint `--fix`), leaving the working tree dirty.

**Use `git-safe-publish.sh` for all commits** — it handles the add → commit → push → clean-tree loop automatically:

```bash
bash scripts/git-safe-publish.sh "commit message" {branch-name}
```

If you have already committed manually and need to handle a dirty tree:

```bash
git add -A && git commit --amend --no-edit && git push origin {branch-name} --force-with-lease
```

Repeat until `git status` shows `nothing to commit, working tree clean`.
