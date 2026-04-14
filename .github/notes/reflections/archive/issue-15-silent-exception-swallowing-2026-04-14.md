---
date: "2026-04-14"
issue: 15
pr: 54
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: active
---

## Bare except-pass blocks swallow errors silently — missing observability

### Finding

During issue #15 (Build wiki-snapshot Tool), three `except Exception: pass` blocks in the retrieval tier functions silently swallowed all errors. The Synthesized Review flagged this as a Warning. The intent was "graceful degradation" — if one retrieval tier fails, fall through to the next. The implementation achieved degradation but without any logging or diagnostic output, making failures invisible during debugging.

### Observation

This is a common pattern when implementing fault-tolerant pipelines: the developer correctly identifies that failures should not be fatal, but implements the non-fatal path as silent suppression rather than logged-and-continued. The fix is straightforward — `except Exception as e: print(f"...: {e}", file=sys.stderr)` — but the Coder doesn't have a rule requiring observability in exception handlers.

However, adding a specific rule about exception logging would be over-prescriptive. The existing Coder Rule 7 (dead code sweep) and the pending semantic verification rule (issue #10) together should catch bare `except: pass` as a code smell during the pre-handoff review. A bare `pass` in an exception handler is effectively dead code from an observability perspective.

### Suggested Improvement

No new rule needed. This is a code quality pattern that the Synthesized Review catches reliably. Recording as a data point. If this recurs in two or more future issues, consider adding a sub-bullet to Rule 9 about observability in exception handlers at system boundaries.

### Action Taken

No action needed — review system catches this. Recorded for pattern tracking.
