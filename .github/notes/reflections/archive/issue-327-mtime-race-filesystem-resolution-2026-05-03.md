---
date: "2026-05-03"
issue: 327
pr: 339
category: instruction
targets:
  - ".github/notes/gotchas.md"
  - ".github/agents/skills/test-verification/SKILL.md"
severity: minor
---

## mtime race condition in filesystem fingerprint tests

### Finding

`test_edit_and_retrieve` initially flaked without `_bump_mtime`. Writing a file and immediately
checking `st_mtime` can return the same timestamp when the write and read happen within the same
filesystem clock-resolution window (ext4: 1 s). `refresh_if_stale` uses mtime comparison; equal
mtime means "fresh", so the stale refresh was silently skipped.

### Observation

Any test exercising stale-refresh or fingerprint-change logic must control mtime explicitly via
`os.utime`. Relying on wall-clock progression is non-deterministic across filesystems and CI
environments. The fix is simple and deterministic: advance mtime by 10 s using `os.utime` after
writing the modified content.

### Suggested Improvement

Add gotcha #050 to `gotchas.md` documenting the `_bump_mtime` / `os.utime` pattern.
Add a corresponding assertion bullet to `test-verification/SKILL.md`.

### Action Taken

Applied: Added gotcha #050 to `.github/notes/gotchas.md`. Added assertion bullet to
`.github/agents/skills/test-verification/SKILL.md`.
