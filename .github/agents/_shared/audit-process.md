# Shared Audit Process

> Common methodology for all auditor agents. **Read this file first** before starting any audit.

## Prerequisites

### Repository Identity

Before any `github/*` call, read `.github/notes/repo.md` for `OWNER` and `REPO`. If missing, run `git remote get-url origin` to derive them.

---

## Audit Phases

Work through each phase in order. Use `todo` to track progress.

### Phase 1 — Establish the Plan

Build the "should" state by reading in order:

1. `docs/planning/prd-nhw-panel.md` — product requirements, full scope
2. `docs/planning/roadmap.md` — phased delivery plan, current phase
3. `docs/planning/**/tasks*.md` — task lists (`completed/` = done, phase directories = active)
4. `docs/planning/adr/*.md` — architecture decisions (binding constraints)
5. `docs/planning/module-dependency-map.md` — module boundaries
6. `docs/planning/role-permission-matrix.md` — RBAC structure
7. `.github/notes/` — `README.md`, `architecture.md`, `domain.md`, `patterns.md`, `gotchas.md`, `deferred.md`

Synthesise: _"The project should be at Phase X, with A, B, C complete, following decisions D, E, F."_

### Phase 2 — Assess Development Progress

Determine the "is" state:

1. `git log --oneline -50` — recent trajectory and velocity
2. `github/search_issues` — closed issues (last 60 days), map to task breakdowns
3. Open issues/PRs — work in progress, blockers
4. `git branch -a --no-merged main | head -20` — stale branches
5. `git status` — uncommitted work

Produce a **Progress Map** for each task: Done / In Progress / Not Started / Unplanned.

### Phase 3 — Code Quality Audit

#### 3a. Linting & Formatting

Run the project's lint and type-check commands (see `copilot-instructions.md` for project-specific commands).

Failures = **Critical** findings.

#### 3b. Test Suite

Run the project's test suite (see `copilot-instructions.md` for the test command).

Record: total tests, pass/fail, execution time. Failures = **Critical**.

#### 3c. Test Coverage

1. List source modules/files
2. List test files
3. Cross-reference — flag untested source modules
4. Verify tests follow project conventions

#### 3d. Convention Compliance

Spot-check against `.github/instructions/` and `.github/copilot-instructions.md`:

- Code follows the project's architecture and style conventions
- Naming conventions are consistent
- No hardcoded configuration values that should be environment variables

#### 3e. Security Quick-Scan

```bash
grep -rn "password\|secret\|api_key\|token" . --include="*.*" | grep -v vendor | grep -v node_modules | grep -v '.example' | grep -v '.git/' | head -20
```

- No real credentials in committed files
- Sensitive configuration uses environment variables

### Phase 4 — Architecture Audit

Review the project's architecture against any ADRs and documented conventions:

- Module boundaries and dependency rules
- Design patterns and architectural constraints
- Separation of concerns

### Phase 5 — Schema / Data Audit

If the project has a database:

1. Check migration status
2. Verify schema matches models/entities
3. Verify relationships are backed by proper constraints
4. Check for missing indexes on query columns

### Phase 6 — Build & Deployment Audit

1. Build process succeeds without errors
2. Dependencies are up to date (check for outdated packages)
3. No known security vulnerabilities in dependencies
4. Deployment configuration is correct

### Phase 7 — Documentation Audit

1. README.md reflects current state
2. Planning docs reflect actual progress
3. ADRs cover all implemented architectural changes
4. `.github/notes/` files are current
5. Spot-check PHPDoc/JSDoc in key files

---

## Output Format

### Audit Summary

2–3 sentences: overall health, plan alignment, most significant finding.

### Development Stage

| Phase | Status | Completion |
| --- | --- | --- |
| Phase 1 — Foundation | [Done/In Progress/Not Started] | X/Y tasks |
| ... | ... | ... |

### Progress Map

```
[✓] Task — issue #N (closed)
[~] Task — issue #N (open, PR #M)
[ ] Task — not started
[?] Unplanned: description
```

### Findings

Group by severity:

**Critical** (blocks progress or breaks functionality):

```
[C-01] Title
Category: Code Quality | Architecture | Schema | Build | Tests | Documentation
Detail: What was found
Expected: What the plan/convention says
Impact: Why this matters
```

**Warning** (deviates from plan/convention, not breaking) — same format as Critical.

**Info** (observations, suggestions) — same format but with `Suggestion:` instead of `Impact:`.

### Deviations from Plan

For each divergence from PRD, ADRs, or task breakdowns:

- What the plan says
- What the code does
- Whether the deviation is intentional (should it be a new ADR?)

### Risk Assessment

- Technical risks (fragile areas, missing tests, schema issues)
- Process risks (stale branches, unplanned work, documentation drift)
- Dependency risks (outdated packages, breaking changes)

### Recommended Actions

Prioritised list ordered by impact:

```
1. [C-01] Fix failing tests before any new work
2. [W-03] Create ADR for the tenancy scope change
3. [I-02] Consider adding integration tests for ...
```
