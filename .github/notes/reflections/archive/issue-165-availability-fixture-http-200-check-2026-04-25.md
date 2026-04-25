---
date: "2026-04-25"
issue: 165
pr: 176
category: agent
targets:
  - ".github/agents/test-writer.agent.md"
severity: minor
status: archived
---

## Availability fixtures must verify HTTP 200, not just no-exception

### Finding

PR #176 defined a custom `require_lm_studio` autouse fixture that only caught connection
exceptions (httpx.ConnectError, etc.) to decide whether to skip. All three models flagged this
unanimously as U-W-01. One concrete consequence is that a server returning HTTP 500 or 401 is
incorrectly treated as "available" and the test proceeds rather than skipping.

The suite-standard `llm_available` fixture in `tests/integration/conftest.py` already handles
both connectivity and HTTP 200 verification, and the review-checklist already mandates using it.
However, there is no guidance in test-writer.agent.md on what a *correctly implemented* live-test
skip fixture must check — so custom fixtures written from scratch (e.g. in a new conftest.py for
a different test subdirectory) are likely to repeat this error.

### Observation

The check for HTTP 200 is the second line of defence that properly distinguishes "server is
reachable" from "server is operational and ready to accept inference requests". Skipping on
any non-200 response avoids wasting test execution time on a partially-started server, CI
environments with boot latency, or proxies returning auth challenges.

### Suggested Improvement

Add a named block to `test-writer.agent.md` covering the requirement for availability fixtures
to check:
1. No connection exception (server reachable)
2. HTTP 200 status (server operational)

And explicitly state: prefer the suite-standard `llm_available` fixture from
`tests/integration/conftest.py`; only implement a new availability fixture when the standard one
does not apply (e.g. a different service type), and if so, always verify HTTP 200 as well as
connectivity.

### Action Taken

Applied: added "Live-test availability fixtures" named block to the Write Tests section of
`.github/agents/test-writer.agent.md`.
