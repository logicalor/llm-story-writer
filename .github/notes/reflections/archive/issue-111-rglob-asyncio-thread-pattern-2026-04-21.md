---
date: "2026-04-21"
issue: 111
pr: 112
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: archived
---

## `asyncio.to_thread(path.rglob, pattern)` passes an unevaluated generator

### Finding

During PR #112, the codebase contained `asyncio.to_thread(path.rglob, pattern)`. This does not
offload filesystem I/O to a worker thread. `path.rglob(pattern)` returns a **generator** (a lazy
iterator); `asyncio.to_thread` calls it with no arguments, receives the generator object, and
immediately returns it to the event loop. The filesystem traversal still happens on the event
loop thread when the generator is iterated.

The correct pattern is to wrap rglob in a lambda that forces materialisation:

```python
files = await asyncio.to_thread(lambda: list(path.rglob(pattern)))
```

The `lambda` wrapping ensures the generator is both created **and** fully consumed (materialised
into a list) inside the worker thread. Without the lambda, the I/O latency lands on the event
loop regardless of the `to_thread` call.

### Observation

This is a subtle async/threading footgun. `asyncio.to_thread(fn, *args)` calls `fn(*args)` in a
thread — it works correctly when `fn` is a blocking function that **returns a value** directly.
It silently fails when `fn` returns a lazy iterator (generator, `map`, etc.) because the work
happens lazily, later, on the thread that eventually iterates the object — which is typically the
event loop thread.

The pattern is particularly likely to appear with `Path.rglob`, `Path.glob`, `os.scandir`,
`csv.reader`, and other file-system or I/O APIs that return generators or iterators rather than
fully-evaluated sequences.

### Suggested Improvement

Add gotcha #008 to `.github/notes/gotchas.md`.

### Action Taken

Applied: added gotcha #008 to `.github/notes/gotchas.md`.
Embedded this reflection into the `reflections` ChromaDB collection.
