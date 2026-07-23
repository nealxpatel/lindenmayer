# Kind 42020: Run Accounting Event

## Overview

**Kind Number:** 42020  
**Range:** Regular (append-only history)  
**Status:** Draft  

One rolled-up accounting event per completed run. Deliberately **run-grained, never step-grained**: no per-step fields exist anywhere in this event schema. This enforces privacy at the wire level (aggregates flow up, details stay in the subgraph per DESIGN.md §6). Costs are always shadow cost, never real spend.

## Range Semantics

This kind is in the **420xx** block (≥40000), which per NIP-01 defaults to append-only **regular** events: every event is stored, history is never collapsed. This is correct for accounting records — you need the immutable ledger, not just the latest snapshot.

## Tag Table

| Tag | Meaning | Required? | Format |
|-----|---------|-----------|--------|
| `branch` | Node branch | yes | string |
| `run` | Run id | yes | string |
| `template` | Template version event id that spawned this node | no | 64-char lowercase hex |

## Content JSON Schema

```json
{
  "iter_count": <integer, >= 0>,
  "cost_shadow_usd": <number, >= 0>,
  "duration_s": <number, >= 0>,
  "exit_status": "<string: 'completed', 'exited', or 'killed'>"
}
```

All four fields are required:
- `iter_count`: total iterations completed in this run
- `cost_shadow_usd`: shadow cost (advisory estimate, never real spend)
- `duration_s`: total wall-clock duration in seconds
- `exit_status`: how the run ended

## Worked Example

```json
{
  "kind": 42020,
  "tags": [
    ["branch", "main.core.kinds"],
    ["run", "run-001"],
    ["template", "9f8e7d6c5b4a39281716151413121110090807060504030201000000000000000"]
  ],
  "content": "{\"iter_count\":5,\"cost_shadow_usd\":0.42,\"duration_s\":123.45,\"exit_status\":\"completed\"}",
  "created_at": 1721761202,
  "pubkey": "3f0ff4ce8fa9b8006d754e26e73b8562711f264efc45ec4a751ba735d6221513",
  "id": "3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b",
  "sig": null
}
```

## Privacy Note

Per DESIGN.md §6, this event publishes rolled-up metrics only. Step-level granularity (agent, model, session, per-step cost) stays in Fractal's local SQLite and never leaves the subgraph unless the node explicitly opts into transcript publication. This ensures:
1. Parent visibility is aggregated (cost, duration, status) not detailed (per-step metrics)
2. Ephemeral workers (who have no npub) author zero events
3. Private subgraph state remains private by default

## NIP-AM/NIP-AO Correspondence

Aligns with **NIP-AM (Agent Turn Metrics)** at the run grain instead of per-turn. NIP-AM covers per-turn metrics (tokens, cost, duration, model) for a Buzz agent; our Run Accounting covers the same conceptual ground but at Fractal's run/iteration granularity (a run = one `fractal node start`) because step-level detail is private and stays in Fractal's SQLite.

**Field correspondence** (sync with NIP-AM vocabulary where semantics overlap):
- `cost_shadow_usd` ↔ NIP-AM `costUsd` (both advisory estimates; labeled "shadow" to carry the non-literal caveat)
- `duration_s` ↔ NIP-AM `duration` (wall-clock total)
- No direct correspondence for `iter_count`, `exit_status` — these are Fractal-native concepts
- Note: NIP-AM also covers tokens/model/stopReason, which are step-level details private to the subgraph per §6

If NIP-AM evolves, new Run Accounting events should resync this correspondence so the vocabulary doesn't silently drift.
