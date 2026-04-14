---
date: "2026-04-14"
issue: 14
pr: 56
category: agent
targets:
  - ".github/agents/_shared/review-checklist.md"
severity: minor
status: archived
---

## Import placement inside loop/function bodies — recurring minor style issue

### Finding

During issue #14 (Build wiki-update Tool), `import re` appeared inside both a loop body and a function body rather than at module level. The Synthesized Review flagged this as a suggestion. This is a style issue — Python caches imports so there's no functional bug, but it violates the project's import conventions (stdlib → third-party → local, at module level).

### Observation

The review checklist Phase 2 (Code Review) → General includes "Import ordering follows project conventions" but doesn't explicitly call out import *placement* (module-level vs. function/loop scope). The existing check focuses on ordering within the import block, not whether imports have drifted into function bodies.

This is a minor clarification — the existing checklist item implicitly covers it, but making it explicit would help reviewers catch it faster and help the Coder avoid it.

### Suggested Improvement

Amend the existing Phase 2 → General checklist item from:

```markdown
- [ ] Import ordering follows project conventions
```

to:

```markdown
- [ ] Import ordering and placement follows project conventions — imports at module level, not inside functions or loops
```

### Action Taken

Applied: clarified import placement in review-checklist.md Phase 2 General section.
