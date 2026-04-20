---
date: "2026-04-21"
issue: 111
pr: 112
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## New concrete method added without updating abstract interface

### Finding

During PR #112, a method was added to `FilesystemSavepointRepository` (the concrete
implementation) without adding the corresponding abstract method to `SavepointRepository` (the
ABC). The concrete class remained fully functional, but the abstract interface was now
incomplete: other concrete implementations of `SavepointRepository` would not be required to
implement the method, and type-checkers would not flag missing implementations in mocks or
alternative backends.

### Observation

When working on a concrete class that implements an abstract base class, the Coder's attention
is naturally on making the concrete class work correctly. The abstract interface is upstream and
often feels "done" — it just needs to be updated to stay in sync.

The omission is not caught by:
- **ruff** — concrete class is complete; no lint errors
- **mypy** — the concrete class implements all ABC methods; no type errors
- **pytest** — tests call through the concrete class; no `TypeError` from missing abstract methods

It is caught only when someone creates a second implementation (e.g. an in-memory mock) and
mypy flags the missing method — or, as in this case, during code review.

### Suggested Improvement

Add a sub-bullet to Coder Rule 7 in `.github/agents/coder.agent.md`:

> When adding a method to a **concrete class that implements an abstract base class (ABC)** —
> check whether the method belongs on the ABC as well. If it is part of the public contract
> (callable by other layers or needed by alternative implementations), add the abstract method
> to the ABC. Omissions are not caught by ruff or mypy when only one concrete implementation
> exists.

### Action Taken

Applied: added sub-bullet to Coder Rule 7 (before returning, sweep for ABC completeness).
Embedded this reflection into the `reflections` ChromaDB collection.
