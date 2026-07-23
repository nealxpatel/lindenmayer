# Kind 42041: Approval Verdict

## Overview

**Kind Number:** 42041  
**Range:** Regular (append-only history)  
**Status:** Draft  

An approval decision from a parent node in response to a kind 42040 (Approval Request). One event per verdict. Paired with kind 42040 to form a request/response chain that preserves reject→revise→re-request→approve threading. Append-only semantics (not replaceable) ensure chains stay complete and auditable.

## Range Semantics

This kind is in the **420xx** block (≥40000), which per NIP-01 defaults to append-only **regular** events: every verdict is stored immutably. This is correct for decision chains — you need the full record of rejections and approvals, not just the final answer. A single replaceable "approval status" event would overwrite that chain; append-only regular events preserve it.

## Tag Table

| Tag | Meaning | Required? | Format |
|-----|---------|-----------|--------|
| `e` | The Approval Request event id being answered | yes | 64-char lowercase hex |
| `verdict` | The decision: `approve` or `reject` | yes | string |

## Content JSON Schema

```json
{
  "rationale": "<string, optional free text explaining the decision>"
}
```

The `rationale` field is optional but recommended. It provides human-readable context for the decision.

## Worked Example

```json
{
  "kind": 42041,
  "tags": [
    ["e", "5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d"],
    ["verdict", "approve"]
  ],
  "content": "{\"rationale\":\"Changes look good, approved for deployment\"}",
  "created_at": 1721761205,
  "pubkey": "0e4702b8331d23cf835aeb1d1e0640403b1812709ab10eb1250f688cc6ce183f",
  "id": "6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e",
  "sig": null
}
```

Note: The verdict is published by the approver (parent node), so the pubkey differs from the request publisher's key.

## Threading and Rejection Chains

Because verdicts are append-only (kind 42041) events that `e`-tag the request (kind 42040), not replaceable snapshots:

- A rejected verdict does not erase the request
- The child can revise and re-issue the request (another kind 42040)
- The parent can approve the new request (another kind 42041)
- The full chain (reject→revise→approve) is preserved and queryable

This is exactly the shape DESIGN.md §4 needs for extracting preference pairs: "what did the system change between rejection and approval?"

## NIP-AM/NIP-AO Correspondence

Aligns with **NIP-AO (Agent Observability)** — verdicts model the same execution-gating decision as AO's `cancel_turn` control frame (whether execution continues), but at Fractal's node/step scope rather than Buzz's agent/turn scope.

**Field correspondence:**
- `e` (references request) → new relative to AO (threading at the control-flow level)
- `verdict` ↔ AO control frame decision semantics (continue or halt)
- `rationale` → new; AO has no built-in decision rationale field

If NIP-AO evolves, new verdicts should resync this correspondence.
