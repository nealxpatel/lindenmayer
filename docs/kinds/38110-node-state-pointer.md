# Kind 38110: Node State Pointer

## Overview

**Kind Number:** 38110  
**Range:** Addressable (latest per pubkey+kind+d)  
**Status:** Draft  

Latest-known snapshot of a node's current state. One per node, overwritten on every meaningful state change, so a dashboard resolves "current state of node X" in a single addressable-kind query instead of replaying the full history from kind 42010 events.

## Range Semantics

This kind is in the **381xx** block (30000–39999), which per NIP-01 is **addressable** / parameterized-replaceable: a plain relay automatically collapses each (pubkey, kind, `d`-tag) stream to keep only the latest event. This is the correct semantics for "current status" — you want O(1) lookups of "what is the state *right now*," not historical chains.

Contrast with kind 42010 (Node Lifecycle), which uses the 420xx regular range to preserve the full history.

## Tag Table

| Tag | Meaning | Required? | Format |
|-----|---------|-----------|--------|
| `d` | Branch name (the addressable key) | yes | string |
| `status` | Current status | yes | string |
| `run` | Current run.iter label | yes | string |
| `iter` | Current iteration number / label | yes | string |

## Content JSON Schema

```json
{
  "cost_shadow_usd": <number>,
  "cost_cap_usd": <number>,
  "last_lifecycle_event": "<64-char lowercase hex event id>"
}
```

All three fields are required in the content. `cost_shadow_usd` is the shadow cost (advisory estimate), `cost_cap_usd` is the remaining budget, and `last_lifecycle_event` cross-references the most recent kind 42010 event for full audit trail.

## Worked Example

```json
{
  "kind": 38110,
  "tags": [
    ["d", "main.core.kinds"],
    ["status", "active"],
    ["run", "run-001"],
    ["iter", "1"]
  ],
  "content": "{\"cost_shadow_usd\":0.15,\"cost_cap_usd\":2.5,\"last_lifecycle_event\":\"9f8e7d6c5b4a39281716151413121110090807060504030201000000000000000\"}",
  "created_at": 1721761201,
  "pubkey": "3f0ff4ce8fa9b8006d754e26e73b8562711f264efc45ec4a751ba735d6221513",
  "id": "2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a",
  "sig": null
}
```

## Invariant

This pointer is a convenience read-index over the history of kind 42010 events, not a second source of truth. It is always reconstructable by taking the latest 42010 event per branch. Losing this pointer (e.g., on a relay that doesn't support addressable collapse) degrades to "replay history," never data loss.
