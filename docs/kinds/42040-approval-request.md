# Kind 42040: Approval Request

## Overview

**Kind Number:** 42040  
**Range:** Regular (append-only history)  
**Status:** Draft  

An approval request from a node's `requires_approval` step to its parent (approver). One event per request. Paired with kind 42041 (Approval Verdict) to form a request/response chain that preserves reject→revise→re-request→approve threading for DESIGN.md §4's preference-pair extraction.

## Range Semantics

This kind is in the **420xx** block (≥40000), which per NIP-01 defaults to append-only **regular** events: every request and subsequent rejection/approval is stored. This is correct for audit trails — you need the full chain of requests and verdicts, not just the latest answer.

## Design Note

This is **not** Buzz's kind 46011 (merge approval). That kind gates git merges at the Buzz-relay layer. Our `requires_approval` is Fractal-native approval of step execution, which is a distinct concept. A parent approves a child's step before it proceeds; this has no necessary relationship to git merges at all. Two separate kinds keep the concerns orthogonal.

## Tag Table

| Tag | Meaning | Required? | Format |
|-----|---------|-----------|--------|
| `branch` | Requesting node's branch | yes | string |
| `run` | The gated step's run id | yes | string |
| `iter` | The gated step's iteration | yes | string |
| `step` | The step identifier | yes | string |
| `p` | Approver's pubkey (parent node) | yes | 64-char lowercase hex |

## Content JSON Schema

```json
{
  "step_name": "<string>",
  "summary": "<string>"
}
```

Both fields are required:
- `step_name`: the step's name from `steps/NN-NAME.md`
- `summary`: what this step would do (motivating the request)

## Worked Example

```json
{
  "kind": 42040,
  "tags": [
    ["branch", "main.core.kinds"],
    ["run", "run-001"],
    ["iter", "2"],
    ["step", "03-REVIEW"],
    ["p", "0e4702b8331d23cf835aeb1d1e0640403b1812709ab10eb1250f688cc6ce183f"]
  ],
  "content": "{\"step_name\":\"REVIEW\",\"summary\":\"Code review required before proceeding with deployment\"}",
  "created_at": 1721761204,
  "pubkey": "3f0ff4ce8fa9b8006d754e26e73b8562711f264efc45ec4a751ba735d6221513",
  "id": "5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d",
  "sig": null
}
```

## NIP-AM/NIP-AO Correspondence

Aligns with **NIP-AO (Agent Observability)** — approval requests model the same control-flow gating concept as AO's `cancel_turn` control frame (choosing whether execution continues), though at a different scope (Fractal node step vs. Buzz agent turn) and with different payload semantics.

**Field correspondence:**
- `branch` ↔ agent identifier context
- `run`, `iter`, `step` ↔ AO execution context
- `p` (approver) ↔ new relative to AO (no direct correspondence)
- `step_name`, `summary` → new; AO has no built-in "what is this decision about" rationale field

The verdict (kind 42041) is what actually decides execution continuation — this request is the *query*.
