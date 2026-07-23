# Lindenmayer

This project is called **Lindenmayer**.

Lindenmayer is a control plane that lets humans govern subgraphs of Fractal agent
trees (plasma-ai/fractal) through Buzz (block/buzz), Block's Nostr-based workspace —
turning agent work into a versioned, evaluated, human-owned workforce. Fractal and
Buzz are external platforms this repo integrates; their code does not live here.

Lindenmayer is a Python host application built on Fractal's extension surfaces
(observability hooks, SQLite/CLI read surfaces, radio/signal steering). It never
patches or forks Fractal, and it adds no capabilities to Fractal nodes — it makes
existing Fractal primitives durable, identified, and observable through Buzz.

True to the name, Lindenmayer's development is managed by a Fractal tree. The tree
doubles as the project's first user: the demo observes the tree that builds it, and
the tree's own telemetry is the demo data.

## Design principles

- Aggregates flow up, details stay in the subgraph (privacy is a default, not a
  feature).
- No new storage systems — the signed event log is the history; source-of-truth
  data stays in Fractal's SQLite and the signed event log on the Lindenmayer
  relay (Buzz is the human surface, not the core-log carrier), with parquet
  snapshot exports in `data/` for local review via duckdb.

## Repo notes

- `tree/` contains the versioned contracts of the Fractal tree that manages this
  project's development (the handrolled root context and each agent node's
  NODE.md). Runtime state stays in gitignored `.fractal/` and `.worktrees/`.
- `docs/DESIGN.md` is the platform design manifest, owned by the
  `platform-architect` node — changes to key components are routed through it
  for review (see `tree/platform-architect/NODE.md`).
- `transcripts/` contains the raw Claude Code session logs of this project's
  development, synced automatically by a hook. This is an intentional public record.
