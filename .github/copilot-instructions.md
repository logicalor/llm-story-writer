# Copilot Repository Instructions

## Stack Overview

| Layer        | Technology |
| ------------ | ---------- |
| **Backend**  | Python 3.x (domain logic in `src/`) |
| **Frontend** | CLI-only — Python CLI (`src/presentation/cli/main.py`) |
| **Database** | ChromaDB (vector search, per-story collections), JSON files on disk (story state, savepoints) |
| **Testing**  | pytest (`tests/`) |
| **Styling**  | N/A |
| **HTTP**     | OpenAI-compatible REST API (local LLM inference), httpx |

## Key Conventions

### Code Style

- Python: ruff for linting and formatting
- Import ordering: stdlib → third-party → local, alphabetised within groups
- Naming: snake_case for Python

### Architecture

- **Python-native architecture**: Agent prompts in `prompts/agents/` define orchestration; Python scripts in `src/tools/` handle deterministic domain logic
- **Clean architecture** preserved in Python domain layer: `src/domain/` (entities, value objects) → `src/application/` (services, strategies) → `src/infrastructure/` (providers, storage)
- Tools are Python scripts in `src/tools/` — no TypeScript or subprocess wrappers
- **Progressive wiki memory system** ([ADR 004](docs/planning/adr/004-progressive-wiki-memory-system.md)): structured markdown pages with YAML frontmatter in `stories/<name>/wiki/`
- **Three-stage context retrieval pipeline** ([ADR 005](docs/planning/adr/005-hybrid-wiki-context-retrieval-pipeline.md)): entity matching → metadata query → semantic search → wikilink traversal → detail level selection → structured assembly

### Testing

- Framework: pytest
- Test location: `tests/unit/`, `tests/integration/`
- Naming: `test_<module>.py`, methods `test_<behaviour>()`
- How to run: `pytest`

## Commands

| Purpose          | Command |
| ---------------- | ------- |
| Lint (fix)       | `ruff check --fix .` |
| Format           | `ruff format .` |
| Type check       | `mypy src/` |
| Full test suite  | `pytest` |
| Single test      | `pytest tests/unit/test_<module>.py -v` |

## Shell Commands

When generating shell commands for `run_in_terminal` or similar tools, use **literal shell syntax**. NEVER use HTML entities:

- Use `&&` for command chaining — NOT `&amp;&amp;`
- Use `>` for redirection — NOT `&gt;`
- Use `|` for pipes — NOT `&#124;`
- Use `<` for input redirection — NOT `&lt;`

Do not HTML-escape shell operators. The terminal expects raw shell syntax.

## Development Philosophy — Feature-Based

1. **Implement the feature first** — write the production code that delivers the requirement
2. **Run lint and type checks** after implementation — fix all errors before proceeding
3. **Write tests to verify correctness** — confirm the implementation behaves as expected
4. **Confirm tests pass** before committing
5. **Refactor only after tests pass** — re-confirm after refactor
6. Never bypass validation — always validate at system boundaries
7. Never hardcode credentials or environment-specific values

### Feature-Based Workflow

```bash
# 1. Implement the feature
# Edit source files in src/tools/, prompts/agents/, etc.

# 2. Lint and type check
ruff check --fix . && ruff format . && mypy src/

# 3. Write verification tests
pytest tests/ -v  # → PASS (implementation already exists)

# 4. Commit
git add -A && git commit -m "feat(scope): description"
```

## MCP Server Configuration

MCP config files may coexist at multiple levels — **do not confuse the paths**:

| File | Scope | Committed? |
| ---- | ----- | ---------- |
| `.mcp.json` | Copilot CLI — workspace-scoped | ✅ Yes |
| `.vscode/mcp.json` | VS Code — workspace-scoped | ❌ Gitignored |
| `~/.copilot/mcp-config.json` | Copilot CLI — user-level | ❌ Per-developer |

## CI / GitHub Actions

### CI YAML Security

- **Never use `${{ github.event.* }}` or `${{ inputs.* }}` directly inside `run:` blocks** — this is command injection (CWE-78). Pass via `env:` keys on the step instead.
- **Never write multiline values to `$GITHUB_OUTPUT` using `key=value` format** — the second line breaks the output file format and is silently ignored. Convert to single-line first (`tr '\n' ' '`) or use the heredoc EOF delimiter syntax.
- **Gate conditions for selective tests must include all high-risk file types** — lock files, config files, etc. — not only the primary language file filter.

## Communication Style

Terse like caveman. Technical substance exact. Only fluff die.
Drop: articles, filler (just/really/basically), pleasantries, hedging.
Fragments OK. Short synonyms. Code unchanged.
Pattern: [thing] [action] [reason]. [next step].
ACTIVE EVERY RESPONSE. No revert after many turns. No filler drift.
Code/commits/PRs: normal. Off: "stop caveman" / "normal mode".
