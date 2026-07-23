# Root Node — Evergreen Context

- **branch:** `main`
- **kind:** Fractal user node (`user: true`) — never iterates; holds the tree's
  central SQLite DB and the operator's radio mailbox
- **operator:** Neal (the human)

## Why this file exists

Lindenmayer's core promise is an evergreen context environment for a human
governing a subgraph of agents. That surface does not exist yet, so this first
one is handrolled and maintained by hand. It is both the operating manual for
the root of this tree and the living prototype of the product: whatever this
file needs to be is what Lindenmayer must eventually generate and maintain.

Everything here is *standing* context — durable framing the operator should
have loaded at all times. Session-by-session detail belongs in transcripts,
plans, and the radio log, not here.

## Standing context

- **Mission:** build Lindenmayer — a control plane that lets humans govern
  subgraphs of Fractal agent trees through Buzz, turning agent work into a
  versioned, evaluated, human-owned workforce.
- **Current phase:** bootstrap. Governance structure first (this node, then
  `platform-architect`, then `docs/DESIGN.md`), feature code after.
- **Non-negotiables** (restated from `CLAUDE.md`):
  - Never patch or fork Fractal; integrate only through its extension surfaces
    (observability hooks, SQLite/CLI read surfaces, radio/signal steering).
  - Aggregates flow up, details stay in the subgraph — privacy is a default.
  - No new storage systems: Fractal's SQLite and the Buzz relay are the sources
    of truth; the signed event log is the history; `data/` holds only parquet
    snapshots for local review.

## How the root steers

The root acts through Fractal's operator surfaces, never by editing a child's
worktree directly:

- **Radio** — messages to child inboxes; children's outboxes and one-hop
  auto-subscriptions carry progress back up. Priority conventions: 2–3
  progress, 6 needs-action, 7 lifecycle, 8–10 urgent.
- **Live steering surfaces** — a child's `NODE.md` and `steps/` are re-read
  every iteration and may be edited mid-run.
- **Approval gates** — steps marked `requires_approval` wait for the root's
  explicit approval; `fractal node pending` lists waiters.
- **Budgets and signals** — per-run USD caps and the three-level stop
  escalation (`finish` / `stop` / `kill`).

## Consultation covenant

`docs/DESIGN.md` is the platform manifest and is owned by
`main.platform_architect`. The root honors the same protocol it imposes on
agent nodes:

1. Changes to key components (the design manifest, tree structure, node
   contracts, integration boundaries with Fractal or Buzz) are not made
   unilaterally — a review request goes to the platform-architect's inbox at
   priority 6 first.
2. The architect reviews against the design principles and platform flows and
   replies with a verdict; DESIGN.md changes land only through the architect.
3. New feature thinking starts as a research request to the architect, which
   coordinates the research subgraph and returns organized artifacts.

By default the architect's rejection is a **veto** — a hard signal for the
human to stop and think carefully about the design principle at stake. The
resolution is never a silent override: the root either withdraws the request,
revises it, or adjusts the architect's context (the DESIGN.md principles or
the node contract itself) and re-submits. That adjustment happens as a
conversation on the architect's node, so the node's log carries the full
history of the human's thought process and the clarified ambiguity.

Governance mode is a platform parameter — an important one. `veto` is the
default; softer modes (advisory review, recorded override) are deliberate
per-subgraph choices, not escape hatches.

## Pointers

- `docs/DESIGN.md` — platform design manifest (owner: `main.platform_architect`)
- `docs/platforms.md` — Fractal & Buzz platform research
- `tree/platform-architect/NODE.md` — the architect's task contract
- `transcripts/` — public record of development sessions
