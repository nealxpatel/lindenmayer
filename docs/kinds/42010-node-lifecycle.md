# Kind 42010: Node Lifecycle Event

## Overview

**Kind Number:** 42010  
**Range:** Regular (append-only history)  
**Status:** Draft  

One event per node status transition. Emitted by the persistent node's own Nostr key. This provides an immutable, timestamped record of a node's state changes within a run, enabling historical reconstruction of node behavior.

## Range Semantics

This kind is in the **420xx** block (≥40000), which per NIP-01 defaults to append-only **regular** events on any compliant relay: every event is stored immutably, history is never collapsed. This is the correct semantics for state transitions — you need the full chain, not just the latest status.

Contrast with kind 38110 (Node State Pointer), which uses the 381xx addressable range to collapse to latest-only for "current status" snapshots.

## Tag Table

| Tag | Meaning | Required? | Format |
|-----|---------|-----------|--------|
| `branch` | Dotted Fractal branch name of the node | yes | string |
| `status` | New status (`active`, `paused`, `completed`, `exited`, `stopped`) | yes | string |
| `run` | Run id this transition occurred within | yes | string |
| `p` | Parent node's pubkey, if parent is a persistent (keyed) node | no | 64-char lowercase hex |
| `e` | Previous lifecycle event id for this node (chains history) | no | 64-char lowercase hex |

## Content JSON Schema

```json
{
  "reason": "<string, optional free text (e.g. 'budget exhausted', 'user kill')>"
}
```

The `reason` field is optional but recommended. It provides human-readable context for why the transition occurred. Content is kept minimal; all queryable state lives in the tags.

## Worked Example

```json
{
  "kind": 42010,
  "tags": [
    ["branch", "main.core.kinds"],
    ["status", "active"],
    ["run", "run-001"],
    ["p", "0e4702b8331d23cf835aeb1d1e0640403b1812709ab10eb1250f688cc6ce183f"],
    ["e", "abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234"]
  ],
  "content": "{\"reason\":\"Initial startup\"}",
  "created_at": 1721761200,
  "pubkey": "3f0ff4ce8fa9b8006d754e26e73b8562711f264efc45ec4a751ba735d6221513",
  "id": "9f8e7d6c5b4a39281716151413121110090807060504030201000000000000000",
  "sig": null
}
```

**Note:** The `sig` field is `null` here because this is an unsigned example. In practice, events would be signed per NIP-01.

## NIP-AM/NIP-AO Correspondence

Aligns with **NIP-AO (Agent Observability)** `session_started` / `session_resolved` frames. Our lifecycle events (`active` / `completed` / `exited`) map to AO's frame kinds at Fractal's node granularity rather than per-turn. The `status` tag (our state machine) and NIP-AO's frame kinds cover the same conceptual ground — a stateful system going through identifiable phases — but at different temporal grains and with different payloads.

**Field correspondence:**
- `branch` ↔ agent identifier context
- `status` ↔ AO frame kind implied state
- `run` ↔ session/execution context
- `reason` (free text) → new relative to AO (no direct correspondence)
