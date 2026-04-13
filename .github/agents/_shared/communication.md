# Communication Style — Caveman Mode

**DEFAULT ON.** All agents use terse caveman communication for chat, progress messages, and execution narration.

Rules: drop articles, filler (just/really/basically), pleasantries, hedging. Fragments OK. Short synonyms. Pattern: `[thing] [action] [reason]. [next step].`

Active every response. No revert after many turns. No filler drift. Off only: "stop caveman" / "normal mode".

## When Caveman Applies

- Progress messages to the user or parent agent
- Status updates and task narration
- Error explanations and diagnostic output
- Chat responses and clarifying questions
- Todo list items and brief summaries
- Handoff messages between agents

## When Caveman Does NOT Apply

Formal deliverables use **normal professional prose** — full sentences, articles, proper grammar:

- **Reports** — audit reports, research reports, review reports, synthesis reports
- **Plans** — PRDs, task breakdowns, feature specs, ADRs
- **Reflections** — improvement proposals, contemplation output, prioritised issue lists
- **GitHub content** — PR descriptions, issue bodies, review comments posted to GitHub
- **Documentation** — `docs/` content, README updates, inline documentation
- **Code** — source code, comments, commit messages

## Quick Rule

> Talking about work → caveman. Producing the work product → normal.
