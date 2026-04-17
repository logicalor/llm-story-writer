---
date: "2026-04-18"
issue: 90
pr: 97
category: agent
targets:
  - ".github/agents/coder.agent.md"
  - ".github/agents/orchestrator-v3.agent.md"
severity: minor
status: archived
archived_at: "archive/issue-90-ruff-scope-inflation-gpt-false-positive-2026-04-18.md"
---

## Ruff scope inflation recurrence (repo-wide format command) + GPT diff-whitespace false positive

### Finding

**Finding 1 — Ruff scope inflation (fifth recurrence)**

During issue #90 (PR #97), the Coder ran `ruff format .` repo-wide rather than limiting the
formatter to the specific files modified by the task. This formatted unrelated files, inflating the
diff with non-functional changes. The Orchestrator caught the scope inflation and reverted the
unrelated formatting changes before committing.

Coder Rule 8 already requires flagging this situation on handoff, but does not address the root
cause: the Coder chooses to run formatters repo-wide instead of on specific modified files. This
is the fifth scope-inflation variant observed (issues #5, #16, #21, #25, #90).

**Finding 2 — GPT reviewer false positive from diff whitespace misread**

During the PR #97 synthesized review, the GPT reviewer claimed a syntax error in the changed
file. The Synthesizing Reviewer correctly identified this as a false positive caused by the GPT
reviewer misreading the diff — leading `+`/`-` diff markers and indentation whitespace were
interpreted as code characters. The actual file was syntactically valid (all 303 unit tests pass).

### Observation

**On Finding 1:** Rule 8 addresses the symptom (flag scope-inflated commits on handoff) but not
the cause. A specific sub-bullet prescribing scope-limited formatter commands (`ruff format
path/to/file.py` rather than `ruff format .`) gives the Coder a concrete, mechanically-checkable
rule that prevents the problem rather than detecting it after the fact. The Orchestrator's revert
step is remediation; the correct fix is prevention at the Coder level.

**On Finding 2:** This is a distinct failure mode from the prior transcription error (issue #27,
PR #87). In that case the Orchestrator introduced a false positive by reconstructing code from
memory instead of reading the file verbatim. Here the review package was assembled correctly —
the GPT reviewer misread the diff whitespace when evaluating it. Diff output includes leading
`+`/`-` characters and indentation shifts that can cause reviewers to mistake whitespace as
syntactic characters (e.g., reading `+    )` as a syntax error on an otherwise correct line). The
Synthesizing Reviewer's role as final synthesizer and false-positive filter worked correctly here.

The Phase D triage guidance already says singular findings "may be a false positive, fix only if
clearly valid." The synthesis should explicitly note that syntax-error claims on modified files
deserve direct file verification before being actioned — misread diff whitespace is a well-known
reviewer failure mode.

### Suggested Improvement

**Improvement 1 (minor) — Coder Rule 8: prescribe scope-limited formatter commands**

Add a sub-bullet to Coder Rule 8:

```markdown
   - **Scope-limited commands:** Run formatters and linters only on the files you have modified,
     not repo-wide. Use `ruff format path/to/file.py` (or specific directory) rather than
     `ruff format .`. Repo-wide runs silently format unrelated files, inflating the diff with
     non-functional changes.
```

**Improvement 2 (minor) — Orchestrator Phase D triage: note diff-whitespace false positives**

Add a sentence to the singular finding guidance in Phase D triage:

```markdown
    - **★☆☆ Singular** → evaluate individually — may be a false positive, fix only if clearly
      valid. If the claim is a syntax error on a modified file, verify by re-reading the actual
      file — diff whitespace (leading `+`/`-` markers, indentation shifts) is a known source of
      reviewer misreads that do not appear in the real file.
```

### Action Taken

Applied both minor improvements:
1. Added scope-limited commands sub-bullet to Coder Rule 8 in `.github/agents/coder.agent.md`.
2. Added diff-whitespace false-positive note to Orchestrator Phase D triage singular-finding guidance in `.github/agents/orchestrator-v3.agent.md`.
