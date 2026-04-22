# Review Checklist — Shared Protocol

> Shared Phase 2–7 review checklist for agents performing code reviews, both local (diff-based) and PR-based (GitHub API). Used by `code-review-process.md` and `pr-review-process.md`.

---

## Review Phases

### Phase 2 — Code Review

Review each changed source file systematically:

#### General

- [ ] Code follows project conventions defined in `.github/copilot-instructions.md`
- [ ] Naming conventions are consistent with the codebase
- [ ] No overly complex functions — decompose if needed
- [ ] No code duplication — extract shared logic where appropriate
- [ ] Import ordering and placement follows project conventions — imports at module level, not inside functions or loops
- [ ] **API signature changes** — if a function, method, or constructor signature changed (parameter added/removed/renamed), grep the workspace for callers: `grep -rn 'ClassName\|function_name' . --include='*.py' --include='*.ts'`; include root-level scripts (`test_*.py`, `demo_*.py`, `migrate_*.py`) — these call `src/` APIs directly and are not in the diff because they were not updated (broken callers never appear in the changed-file list)

#### Architecture

- [ ] Separation of concerns — business logic not in controllers/handlers
- [ ] Proper use of dependency injection where applicable
- [ ] No tight coupling between unrelated modules
- [ ] Follows the project's architectural patterns (see ADRs if any)

#### Data Access

- [ ] Input validation — all user input validated at system boundaries
- [ ] Proper error handling — no swallowed exceptions
- [ ] Database queries are parameterized (no raw user input in queries)
- [ ] Missing indexes on foreign keys and frequently queried columns
- [ ] Migrations have proper rollback support
- [ ] **Batch/composite operations** — if a function wraps multiple state-changing operations, verify: (1) pre-flight snapshot or backup is taken before the batch starts, (2) failures mid-batch trigger rollback or at minimum leave state consistent, (3) a final sync/consistency check runs after the batch completes

#### Agent Instructions

- [ ] **Tool call contracts** — for any new or modified agent instruction file that includes tool invocations, verify each call against the tool source before accepting: (a) operation names match the Python CLI dispatch (grep `src/tools/*.py` for valid operation values), (b) parameter key names match the Zod field names in the TS wrapper (`.opencode/tools/*.ts`) — mismatched keys pass Zod silently; (c) any omitted parameter is confirmed safe — check the tool's default value and verify it produces correct behaviour in this context (e.g. `mode` defaults to `"outline"` in `critique-runner`; a chapter-context agent that omits `mode` will evaluate the wrong artifact type without erroring); (d) any TS parameter marked `.optional()` that is omitted for a specific operation — verify in the Python source that the field is genuinely optional for the active `operation`; Python tools use conditional validation (`if args.operation == "revise" and not args.scene_num: sys.exit(2)`) that the Zod schema cannot represent; `.optional()` reflects TS schema permissiveness only; (e) any parameter passed to the tool is verified to be consumed by the Python backend for the active operation — TS wrappers may accept parameters via Zod that the Python CLI never reads in certain operation branches; passing an accepted-but-ignored parameter produces silently incorrect results; verify by checking `argparse.add_argument` declarations and the operation dispatch branch in `src/tools/*.py`

---

### Phase 3 — Frontend Review (if applicable)

Review each changed frontend file systematically:

- [ ] Follows the project's component conventions
- [ ] Proper typing — no `any` types (TypeScript projects)
- [ ] Accessibility — ARIA attributes where needed
- [ ] No hardcoded URLs — use routing helpers
- [ ] Error states handled in forms and async operations
- [ ] Loading/processing states shown during async operations

---

### Phase 4 — Security Review

Check for common security issues:

- [ ] **Authorization** — every action checks permissions
- [ ] **Input validation** — all user input validated
- [ ] **SQL injection** — parameterized queries, no raw SQL with user input
- [ ] **XSS** — no rendering of untrusted HTML content
- [ ] **CSRF** — protection in place for state-changing operations
- [ ] **Mass assignment** — only expected fields are writable
- [ ] **File uploads** — validated type, size, stored securely
- [ ] **Sensitive data** — no credentials, API keys in code
- [ ] **Access control** — proper scoping for multi-user/multi-tenant systems

---

### Phase 5 — Testing Review

Check test coverage:

- [ ] **New features** — have corresponding tests
- [ ] **Test conventions** — follow project testing patterns (see `copilot-instructions.md`)
- [ ] **Edge cases** — error paths tested
- [ ] **No skipped tests** — all tests run
- [ ] **Assertions** — meaningful assertions, not just absence of errors

---

### Phase 6 — Performance Review

Check for performance issues:

- [ ] **N+1 queries** — eager loading or batch queries where applicable
- [ ] **Database indexes** — on foreign keys and query columns
- [ ] **Caching** — appropriate for expensive operations
- [ ] **Asset size** — no large unnecessary imports
- [ ] **Pagination** — for large result sets

---

### Phase 7 — Documentation Review

Check documentation:

- [ ] **Docblocks** — public methods documented
- [ ] **README** — updated for new features
- [ ] **ADRs** — architectural changes recorded
- [ ] **Inline comments** — for complex logic
- [ ] **Table/prose parity** — if a new entry (agent, subagent, tool, command) is added to a reference table, verify a corresponding prose subsection (`###`) exists for it in the same document; a table row without a prose section leaves the registry asymmetric and the feature doc incomplete
- [ ] **Code matches docs** — if documentation describes a behavior (validation, fallback, default), verify the implementation actually provides it; a mismatch means the documented contract is a false promise
- [ ] **Code example drift** — if this PR changes the semantics of an API method, removes a method, or makes a field immutable, grep docs (`.github/skills/`, `docs/`, `.github/notes/`) for code examples that use the old pattern; examples using removed or changed methods silently become misleading
- [ ] **Role/taxonomy renames** — if a role or taxonomy name was changed in prose (e.g. a role table), grep the same file for old names in embedded code examples, comments, and annotation blocks; stale names in examples are equally misleading
- [ ] **File paths and links** — verify all file paths, directory tree diagrams, and relative links in documentation exist on disk and resolve correctly from the doc's location
- [ ] **Orchestrator-subagent companion sync** — if this PR adds or removes a subagent dispatch in the orchestrator, verify `story-pipeline/SKILL.md` is updated: (1) the subagent count in the overview sentence ("The pipeline uses N subagents"), (2) the reference table row, and (3) the constraint sentence ("These are the only N subagents the orchestrator may dispatch"); a stale constraint sentence is an authoritative false statement that blocks dispatch of the new agent
