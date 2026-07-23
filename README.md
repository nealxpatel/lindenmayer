# Lindenmayer

**A control plane for governing agent workforces — humans steering subgraphs of
[Fractal](https://github.com/plasma-ai/fractal) agent trees through
[Buzz](https://github.com/block/buzz), with every action a signed event.**

## Why

Autonomous agent trees can already do real work. What they lack is what makes a
workforce *ownable*: durable identity, versioned roles, evaluated performance,
and human governance with an audit trail. Lindenmayer adds exactly that layer —
and nothing else — on top of two platforms it never forks:

- **Fractal** (Plasma AI) provides the workforce: hierarchical agent loops in
  git worktrees, with budgets, approvals, and full accounting in SQLite.
- **Buzz** (Block) provides the workspace: a self-hostable Nostr relay where
  humans and agents are peers with cryptographic identity, and every message,
  approval, and git event is a signed event in one log.

Lindenmayer is a Python host application built on Fractal's extension surfaces
(observability hooks, SQLite/CLI read surfaces, radio steering). It adds no
capabilities to Fractal nodes — it makes existing Fractal primitives durable,
identified, and observable as signed Nostr events.

## Design principles

1. **Privacy-preserving defaults.** Aggregates flow up; details stay in the
   subgraph. No arbitrary search of histories — access follows the graph.
   Enforced structurally: the wire format publishes one rolled-up event per
   run, and ephemeral workers author no events at all.
2. **No new storage systems.** The signed event log *is* the history.
   Source-of-truth data stays in Fractal's SQLite and the relay; parquet
   exports in `data/` are snapshots for local review, never truth.
3. **Never patch or fork the platforms.** Integration only through documented
   extension surfaces.
4. **Explicit, traceable governance.** Design review is veto-by-default;
   disagreements resolve as recorded conversation, never silent override.
   Every design decision in this repo traces to a logged directive.
5. **Relay enforcement is an optimization, never an assumption.** The core
   targets plain Nostr (NIP-01 + NIP-29 + NIP-42); Buzz-specific behavior is
   a layer on top. Clients verify from the signed log alone — attestation
   chains, approval counts, revocation — so the history outlives any one
   relay implementation.

Because provenance is signed and versioned, the event log doubles as a
labeled training corpus: approval events are labels, rejection→revision→
acceptance chains are preference pairs, and consent to train on history is
itself a signed, revocable, expiring event. See `docs/DESIGN.md` §4.

## This repo governs itself

True to the name, Lindenmayer's development is managed by a Fractal tree, and
that tree is the project's first user: the demo observes the tree that builds
it, and the tree's own telemetry is the demo data.

- `docs/DESIGN.md` — the platform manifest, owned by the tree's
  `platform-architect` node; changes route through its inbox and its
  rejection is a veto. The decision log is the project's history.
- `tree/` — the versioned contracts of the governing tree (root context and
  per-node task contracts).
- `transcripts/` — raw session logs of every agent that built this repo,
  published deliberately as telemetry (a per-subgraph choice; the platform
  default is private).
- All dollar figures anywhere in this repo are **shadow costs**: ground-truth
  token counts priced at public API rates while execution runs on a
  subscription. Real caps, notional dollars.

## Layout

| Path | What it is |
|---|---|
| `docs/DESIGN.md` | Platform design manifest + decision log |
| `docs/platforms.md` | Fractal & Buzz platform research reference |
| `docs/research/` | Research subgraph output (aggregates up top) |
| `tree/` | Governing tree's versioned node contracts |
| `src/lindenmayer/` | The host application (first ply in progress) |
| `transcripts/` | Published session telemetry |
| `wiki/` | Shared knowledge base maintained by the tree's nodes |
| `data/` | Parquet snapshot exports (duckdb-friendly, never truth) |

## Status

Early and deliberate: the governance loop is live and proven (directive →
review → veto-standing verdict → scoped commit → merge gate), the relay
integration research is done, and the first feature node (`core`: event
kinds, relay client, verification) is commissioned. Follow the decision log
in `docs/DESIGN.md` — it is the changelog that matters.
