---
date: "2026-04-13"
issue: 3
pr: 32
category: agent
targets:
  - ".github/agents/reflection.agent.md"
severity: minor
status: archived
---

## Reflection agent leaves stale active notes after archiving

### Finding

After the issue #30 reflection was processed and archived to `.github/notes/reflections/archive/issue-30-2026-04-13.md`, the original `issue-30.md` was left in the active reflections directory. The file was marked `status: archived` in its frontmatter but not removed from the active directory. This was discovered during the issue #3 collation.

### Observation

The Reflection agent's archival process should move notes from `reflections/` to `reflections/archive/` — copy then delete the original. The "append-only — never delete reflection notes, only archive them" constraint means notes should not be destroyed, but once a note exists in the archive, the active copy is a stale duplicate and should be removed.

The likely root cause is that the Reflection agent (or Orchestrator) copied the note to the archive but did not delete the active copy, possibly because the "never delete" constraint was interpreted too broadly. Alternatively, the archival happened but the deletion was not committed.

### Suggested Improvement

Clarify in the Reflection agent instructions that "archive" means **move** (copy to archive, then delete the active copy), and that the "never delete" constraint applies to the archive — not to active copies after successful archival.

### Action Taken

Applied: Clarified Reflection agent constraint #3 in `.github/agents/reflection.agent.md` to explicitly state "archive" means move (copy + delete active copy). Stale `issue-30.md` needs manual removal from active directory.
