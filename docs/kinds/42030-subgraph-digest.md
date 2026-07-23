# Kind 42030: Subgraph Digest

## Overview

**Kind Number:** 42030  
**Range:** Regular (append-only history)  
**Status:** Draft  

Periodic aggregate published by a persistent node about its own subtree. This event makes DESIGN.md §5's claim true in practice: "aggregates-up is structurally enforced by one-hop subscription" — nodes publish aggregate digests so parents see rolled-up health metrics without seeing individual child details.

## Range Semantics

This kind is in the **420xx** block (≥40000), which per NIP-01 defaults to append-only **regular** events: every digest is stored, history is never collapsed. This is correct for audit trails — you want to see how the subtree evolved over time, not just the latest snapshot.

## Tag Table

| Tag | Meaning | Required? | Format |
|-----|---------|-----------|--------|
| `branch` | The publishing (persistent) node's branch | yes | string |
| `period_start` | ISO 8601 start of the period this digest covers | yes | ISO 8601 timestamp |
| `period_end` | ISO 8601 end of the period this digest covers | yes | ISO 8601 timestamp |

## Content JSON Schema

```json
{
  "child_count": <integer, >= 0>,
  "active": <integer, >= 0>,
  "exited": <integer, >= 0>,
  "completed": <integer, >= 0>,
  "stuck_flagged": <integer, >= 0>,
  "subtree_cost_shadow_usd": <number, >= 0>
}
```

All six fields are required:
- `child_count`: total number of children spawned by this node
- `active`: number currently in active state
- `exited`: number exited on budget
- `completed`: number completed successfully
- `stuck_flagged`: number flagged as stuck
- `subtree_cost_shadow_usd`: rolled-up shadow cost across the entire subtree

## Worked Example

```json
{
  "kind": 42030,
  "tags": [
    ["branch", "main.core.kinds"],
    ["period_start", "2026-07-23T00:00:00Z"],
    ["period_end", "2026-07-23T01:00:00Z"]
  ],
  "content": "{\"child_count\":2,\"active\":1,\"exited\":1,\"completed\":0,\"stuck_flagged\":0,\"subtree_cost_shadow_usd\":1.23}",
  "created_at": 1721761203,
  "pubkey": "3f0ff4ce8fa9b8006d754e26e73b8562711f264efc45ec4a751ba735d6221513",
  "id": "4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c",
  "sig": null
}
```

## Privacy Enforcement

Per DESIGN.md §6, this digest contains **no per-child breakdown by name or content**. A parent sees aggregate health (how many children, how many in each state, total cost) but not "child foo is in state bar" or per-child metrics.

When a parent needs more detail, it must ask (via radio message), not read it off the wire by default. This keeps subgraph details private while still making parent visibility possible at the aggregate level.

Ephemeral workers (who have no npub) do not publish their own lifecycle events (kind 42010) directly. Instead, their existence surfaces only in their persistent parent's digest counts (e.g., contributing to `child_count` and `active`).
