# main.demo -- Evergreen Context

**Mission:** Build Lindenmayer -- a control plane for governing Fractal agent subgraphs through Buzz.
**Phase:** bootstrap
**Governance mode:** veto

## Non-negotiables

- Never patch or fork Fractal; integrate only through its extension surfaces.
- Aggregates flow up, details stay in the subgraph.
- No new storage systems: the signed event log is the history.

## Situational state (live, from the signed log)

- **Current state:** `completed` (run run-1, iter 3)
- **Spend:** $1.23 shadow cost of $25.00 cap
- **Subgraph:** 1 children (0 active, 1 completed, 0 exited, 0 stuck-flagged); subtree spend $1.23 shadow cost
- **Pending approval gates:** 1
  - `deploy` (deploy): ship to prod
- **Recent lifecycle:**
  - completed (run run-1)
  - started (run run-1)

## Model policy (live assignment)

- **node_a default:** sonnet
- **Step pins:**
  - REVIEW: opus

## Pointers

- docs/DESIGN.md
- tree/root/CONTEXT.md
