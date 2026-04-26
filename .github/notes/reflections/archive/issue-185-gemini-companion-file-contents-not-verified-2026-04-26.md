---
date: "2026-04-26"
issue: 185
pr: 198
category: agent
targets:
  - ".github/agents/synthesizing-reviewer.agent.md"
  - ".github/agents/orchestrator-v3.agent.md"
severity: minor
status: archived
---

## Companion-file "not updated" claims require reading file contents, not just verifying existence

### Finding

During PR #198, Gemini raised a Critical finding that the pipeline skill companion file was not updated to reflect the two new pipeline phases. The file had in fact already been updated. Gemini reasoned structurally ("new pipeline phases were added, therefore the SKILL.md should be updated") without reading the file's contents to confirm the update was absent.

### Observation

The existing guidance in `orchestrator-v3.agent.md` (Phase D ★☆☆ Singular triage) tells the Orchestrator to verify that a cited companion file "actually exists on disk (`ls path/to/file`)" before acting on the finding. This guards against fabricated file paths (e.g., issue #132 — GPT cited a non-existent `narrative-arc/SKILL.md`), but does not guard against the symmetric error: the file exists and was already updated, but the reviewer never read it. A reviewer making a structural inference ("this type of change always requires updating file X") can plausibly return a Critical finding for a file that needs no change.

The Synthesizing Reviewer's Step 2 filters similarly cover existence fabrication but not content-verification omission.

### Suggested Improvement

**`synthesizing-reviewer.agent.md` Step 2** — add a new false-positive filter immediately after the "Structural existence claims filter":

> **"Companion file not updated" claims filter:** If a reviewer asserts that a companion file (e.g., a SKILL.md, shared process file, pipeline phase registry) "was not updated" or "needs to be updated" to reflect this PR's changes, verify the file's actual contents before treating the finding as valid. Run `grep -n "concept"` or `read_file` on the target to confirm the expected update is genuinely absent. A reviewer may assert the file requires updating based on structural reasoning without reading it — if the file already contains the expected update, the finding is a false positive regardless of how many models raise it. (Source: issue #185, PR #198 — Gemini raised Critical finding that pipeline skill was not updated; the file was already updated.)

**`orchestrator-v3.agent.md` Phase D ★☆☆** — extend the companion file sentence to cover content verification, not just existence:

Current: `verify the file actually exists on disk (ls path/to/file) before acting on the finding`

Extend to: `verify (a) the file actually exists on disk (ls path/to/file) and (b) read it to confirm the expected update is genuinely absent — a file that exists and is already updated is not a valid finding`

### Action Taken

Applied: added "Companion file not updated" claims filter to `synthesizing-reviewer.agent.md` Step 2; extended the ★☆☆ companion file sentence in `orchestrator-v3.agent.md` Phase D.
