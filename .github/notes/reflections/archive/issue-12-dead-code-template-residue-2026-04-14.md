---
date: "2026-04-14"
issue: 12
pr: 48
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Dead code from template-copying persists despite Rule 7

### Finding

During issue #12 (Build scene-writer Tool), the Coder copied the outline-generator as a template and left behind: (1) `_call_llm_messages()` — a function defined but never called by any scene-writer operation, and (2) a dead `scenes` list variable in the assemble-chapter loop. Both caught by the Synthesized Review (U-W-01, unanimous).

### Observation

This is the third occurrence of dead code slipping through after Rule 7 was expanded to include dead code sweeps (issue #9):

| Issue | Dead Code | Rule 7 status |
| ----- | --------- | ------------- |
| #9 | `_call_llm_json()` in `_llm.py` | Pre-expansion (prompted the rule change) |
| #10 | None flagged | Rule 7 working |
| #12 | `_call_llm_messages()`, dead `scenes` variable | Rule 7 not applied |

The Rule 7 text is clear: "sweep newly created or heavily modified files for dead code — unused functions, unreachable branches, abandoned helpers — especially in shared modules where iterative development leaves artifacts." The issue is intermittent compliance, not insufficient rule text.

Template-copying is a specific trigger: when the Coder uses an existing tool as a starting template, functions from the template that aren't needed by the new tool persist as dead code. This is distinct from iterative development artifacts (abandoned approaches within the current task).

### Suggested Improvement

No rule text change. The rule is clear and comprehensive. Adding more sub-clauses to a rule that's already intermittently applied won't improve compliance. The pending semantic verification rule (issue #10 proposal) would catch these as part of data-flow tracing — a function defined but never called is immediately visible when tracing operation flows.

### Action Taken

No action needed — observation recorded. Pattern reinforces the case for the pending semantic verification rule (issue #10).
