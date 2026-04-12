# AGENTS.md — llm-story-writer

## Project

**Name:** llm-story-writer
**Purpose:** AI-powered long-form story generation system

## Architecture

This project uses a **hybrid agent-tool architecture**. OpenCode agents handle orchestration and human interaction; Python scripts (wrapped as OpenCode tools) handle deterministic domain logic.

### Clean Architecture Layers

```
src/domain/       → Entities, value objects (core business rules)
src/application/  → Services, strategies (use cases)
src/infrastructure/ → Providers, storage (external adapters)
```

Each layer depends only on the layers above it. Domain has no external dependencies.

### Tools

Tools are **TypeScript wrappers** in `.opencode/tools/` that call **Python scripts** in `src/tools/` via subprocess. The TypeScript layer handles argument parsing and OpenCode integration; the Python layer contains the actual logic.

### Storage

- Stories are stored in `stories/<name>/` directories with JSON state files
- Prompt templates are in `src/infrastructure/prompts/` (131 Markdown templates)
- ChromaDB vector collections provide semantic search per story

### Model Configuration

Local LLM inference via **Ollama**. Multiple model roles can be configured for different tasks (generation, analysis, embedding).

## Conventions

- **Python:** `snake_case` naming, `ruff` for linting/formatting, `pytest` for testing
- **TypeScript:** `camelCase` naming, ESLint for `.opencode/tools/` wrappers
- **Import order:** stdlib → third-party → local, alphabetised within groups
- **Testing:** `tests/unit/`, `tests/integration/`; name files `test_<module>.py`, methods `test_<behaviour>()`

## Commands

| Purpose        | Command                        |
| -------------- | ------------------------------ |
| Lint (fix)     | `ruff check --fix .`           |
| Format         | `ruff format .`                |
| Type check     | `mypy src/`                    |
| Full tests     | `pytest`                       |
| Single test    | `pytest tests/unit/test_<module>.py -v` |

## Important Rules

- **NEVER modify files under `legacy/`** — that directory is a frozen archive of the original codebase, kept for reference only.
- Never hardcode credentials or environment-specific values.
- Always validate at system boundaries.
- Run lint and type checks after every change.
