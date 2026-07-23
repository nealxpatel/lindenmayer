---
title: Buzz Surface Research — Final Findings
created: 2026-07-23T23:35:30Z
---

# Buzz Surface Research — Final Findings

## Deliverable Status
✅ `docs/research/evergreen/buzz-surface.md` completed and committed.

## Research Scope Completed

### Buzz Primitives
- NIP-29 groups: lifecycle kinds (9007, 9008, 9021, 9022, 9009) + state events (39000-39003)
- Channels: typed (Stream, Forum, Dm, Workflow) + visible (Open, Private); nip29_group_id binding for Nostr interop
- DMs: kinds 41010 (open), 41011 (add), 41012 (hide) — direct peer/group messages, no group membership gate
- Messages: KIND_STREAM_MESSAGE (9), KIND_STREAM_MESSAGE_V2 (40002) for channels; KIND_TEXT_NOTE (1) for short-form
- Agent surfaces: KIND_AGENT_PROFILE (10100) for agent directory; KIND_AGENT_ENGRAM (30174) for encrypted agent memory

### Ingest Constraints
- Timestamp gate: MAX_TIMESTAMP_DRIFT_SECS = 900 (±15 min), hard-reject on ingest before kind filter
- Accepted kinds: exhaustive match in `required_scope_for_kind()`, ~40 kinds total
- Message-capable kinds: 1, 9, 40002, 30023 (long-form) — all scoped to MessagesWrite
- Group/channel ops: 9007, 9009 scoped ChannelsWrite; admin ops (9000, 9001, 9008) scoped AdminChannels
- DM ops: 41010, 41011, 41012 scoped MessagesWrite

### Identity: NIP-OA
- Mechanism: auth tag structure ["auth", owner_pubkey_hex, conditions_json, bip340_sig_hex] on any event
- Ingest: parsed by buzz_sdk::nip_oa::verify_auth_tag(); stored as metadata, not relay-enforced
- Product surface: "Agent X — owned by [owner]" for valid auth tags; "no verified owner" if absent/invalid
- Revocation: instant relay-side enforcement is Buzz-layer (per DESIGN.md §1), not Lindenmayer relay

### Mapping Table (All 8 Core Kinds)
| Kind | Buzz Kind | Channel | Tags | Status |
|------|-----------|---------|------|--------|
| 42010 (lifecycle) | STREAM_MESSAGE (9) | Subgraph | l:lindenmayer:42010 + source_id + source_created_at | Feasible |
| 42020 (telemetry) | STREAM_MESSAGE (9) / LONG_FORM (30023) | Subgraph | Same tag structure | Feasible |
| 42030 (aggregates) | STREAM_MESSAGE (9) / TEXT_NOTE (1) | Subgraph/parent/global | Same | Feasible (privacy-scoped) |
| 42040/42041 (approvals) | STREAM_MESSAGE (9) in approvals inbox | Approvals NIP-29 group | Same + approval_id | Feasible |
| 42050 (template) | AGENT_PROFILE (10100) / LONG_FORM | Agent directory / registry | Same + template_name + version | Feasible (carry NIP-OA) |
| 38150 (template ptr) | (TBD) | Not surfaced or registry | Not determined | Deferred to architect |
| 38110 (state ptr) | (Not in mapping scope) | Not addressed | — | Out of scope |

## Key Insights

### Dedup Invariant (Load-Bearing)
All cross-posts must carry (source_id, source_created_at) in tags. Consumer deduplicates by this tuple; same core event posted to multiple Buzz channels yields one logical record.

### Privacy Boundary
Subgraph channel (NIP-29 group) contains detail; parent channel/global relay receives only curated aggregates (42030). Privacy enforced by channel membership topology, not post-hoc policy.

### Timestamp Constraints
- ±15 min drift hard-rejects on Buzz ingest.
- Backfill of old Lindenmayer events into Buzz not feasible (Buzz rejects stale created_at).
- Lindenmayer relay accepts historical created_at; Buzz relay does not.

### Node Identity
- Persistent nodes should carry NIP-OA auth tags (owner_pubkey + sig) in events/profiles.
- Ephemeral worker nodes omit attestation; work surfaces via persistent parent's aggregates.
- Attestation is optional for acceptance; absence degrades identity signal, not functionality.

## v1 Recommended Cross-Posts
1. 42010 → STREAM_MESSAGE / subgraph (observability)
2. 42020 → STREAM_MESSAGE / subgraph (cost/latency)
3. 42040/42041 → STREAM_MESSAGE / approvals inbox (governance gate)
4. 42050 → AGENT_PROFILE / directory (publishable asset)

Optional v1+: 42030 (radio aggregates), 38150 (template pointers).

## Arch Decision Points (Not Made)
- Which cross-posts ship in v1
- How to tag/mark private vs. public aggregates (42030 audience scope)
- Whether 38150 surfaces in directory or stays hidden
- Approval workflow topology: approvals inbox (group consensus) vs. DM (federated)

All documented in deliverable §8 (Recommendations); architect chooses.
