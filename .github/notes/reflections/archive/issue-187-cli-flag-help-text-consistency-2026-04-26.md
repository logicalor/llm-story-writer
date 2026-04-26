---
date: "2026-04-26"
issue: 187
pr: 200
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## CLI flag help text must match actual backend semantics and be consistent across subcommands

### Finding

During issue #187/PR #200, the TUI `--savepoint` flag's `help=` string read "resume from" but the backend only validates against the supplied savepoint ID — it always uses the latest savepoint for the actual resume. The same flag existed on both the `tui` and `resume` subcommands with semantically identical behaviour, but different help text strings.

### Observation

`argparse` `help=` strings are user-facing documentation. A help string that overstates the flag's role misleads users and reviewers alike. When the same flag (same name, same semantics) appears on multiple subcommands, divergent help text creates confusion about whether the flag behaves differently per subcommand. This is a correctness issue, not a style issue — it misrepresents what the code actually does.

### Suggested Improvement

Add a rule to `coder.agent.md` under Rule 7 (sweep/dead-code/accuracy checks): when implementing or modifying a CLI flag that appears on multiple subcommands, verify (a) the help text accurately reflects what the backend does — not what developers intended — and (b) shared-semantics flags carry identical or explicitly differentiated help text across all subcommands.

### Action Taken

Applied: Added a sub-bullet to Rule 7 in `coder.agent.md` covering CLI help-text accuracy and cross-subcommand consistency.
