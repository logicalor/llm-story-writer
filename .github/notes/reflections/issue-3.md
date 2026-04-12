---
date: "2026-04-13"
issue: 3
pr: 32
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: major
status: active
---

## Coder creates shell injection and path traversal vulnerabilities in first tool implementation

### Finding

During issue #3 (Build prompt-loader Tool), the Coder implemented a TypeScript OpenCode tool wrapper (`.opencode/tools/prompt-loader.ts`) that called a Python script via `execSync`. Two critical security vulnerabilities were introduced:

1. **Shell injection (CWE-78):** The TypeScript wrapper used `execSync(cmd + ' ' + args.join(' '))` to invoke the Python script, passing user-controlled arguments directly into a shell command string. An attacker could inject arbitrary shell commands via crafted prompt names (e.g., `; rm -rf /`).

2. **Path traversal (CWE-22):** The Python tool script (`src/tools/prompt_loader.py`) did not validate that the resolved prompt file path remained within the `prompts/` directory. A request for `../../etc/passwd` would traverse out of the intended directory.

Both vulnerabilities were caught by the Synthesized Review and fixed before merge.

### Observation

This is the **first tool** created following the hybrid architecture pattern (ADR 001: TypeScript wrapper → Python script via subprocess). The security issues are systemic patterns that will recur in every future tool unless addressed:

- **Shell injection via `execSync`** is a well-known antipattern. The safe alternative is `execFileSync` (no shell interpretation) or `spawnSync` with explicit argument arrays. The Coder had no specific guidance about subprocess invocation patterns in TypeScript.
- **Path traversal** is a standard OWASP Top 10 vulnerability. The Coder's instructions reference OWASP generically via `copilot-instructions.md` (`<securityRequirements>`), but there is no actionable rule about validating file paths against a base directory.

The `copilot-instructions.md` `<securityRequirements>` section says "Ensure your code is free from security vulnerabilities outlined in the OWASP Top 10" — but this is too abstract to prevent specific implementation mistakes. The Coder needs concrete, actionable rules for the two most common vulnerability patterns in this architecture:

1. **Subprocess invocation** — every tool wrapper calls a Python script
2. **Path validation** — many tools will resolve user-provided names to file paths

### Suggested Improvement

Add a new **Rule 9** to the Coder agent instructions:

```
9. **Security: subprocess and path handling.**
   - **TypeScript tool wrappers:** Never use `execSync()` or `exec()` with string concatenation for subprocess calls. Use `execFileSync()` or `spawnSync()` with explicit argument arrays — these bypass the shell and prevent command injection (CWE-78).
   - **Python tools with file paths:** When resolving user-provided names to file paths, always validate the resolved absolute path starts with the intended base directory using `resolved.resolve()` and `.is_relative_to(base)`. Reject any path that traverses outside the base (CWE-22).
```

### Action Taken

Proposed for approval — this is a new rule (structural change to the Coder agent).
