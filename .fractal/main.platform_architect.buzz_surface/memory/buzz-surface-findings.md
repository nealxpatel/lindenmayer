---
name: buzz-surface-findings
title: Buzz Surface Research — Final Findings
desc: ...
created: 2026-07-23T23:35:30Z
updated: 2026-07-23T23:41:27Z
---

# Buzz Surface Research — Final Findings

## Deliverable
✅ `docs/research/evergreen/buzz-surface.md` — committed, 398 lines, complete research with all findings and mappings.

## Research Delivered

### Buzz Primitives
- NIP-29 groups: lifecycle kinds (9007, 9008, 9021, 9022, 9009) + state events (39000-39003)
- Channels: typed (Stream, Forum, Dm, Workflow); visibility (Open, Private); nip29_group_id binding
- DMs: kinds 41010 (open), 41011 (add), 41012 (hide)
- Messages: KIND_STREAM_MESSAGE (9), STREAM_MESSAGE_V2 (40002), TEXT_NOTE (1)
- Agent surfaces: KIND_AGENT_PROFILE (10100) for directory; KIND_AGENT_ENGRAM (30174) for encrypted memory

### Ingest Constraints
- Timestamp: MAX_TIMESTAMP_DRIFT_SECS = 900 (±15 min, hard-reject on ingest)
- Accepted kinds: ~40 total, exhaustive match in required_scope_for_kind()
- Message kinds (1, 9, 40002, 30023): MessagesWrite scope
- Channel ops: ChannelsWrite (create, join); AdminChannels (delete, admin)
- DM ops: MessagesWrite scope

### Identity: NIP-OA
- Mechanism: auth tag ["auth", owner_pubkey, conditions_json, bip340_sig] on any event
- Ingest: parsed by buzz_sdk::nip_oa::verify_auth_tag(); stored as metadata
- Product surface: "Agent X — owned by [owner]" for valid tags; "no verified owner" if absent
- Revocation: relay-side instant enforcement is Buzz-layer (not Lindenmayer relay)

### Mapping Table
All 8 Lindenmayer core kinds mapped to Buzz cross-post destinations with tags and channel shapes:
- 42010 (lifecycle) → STREAM_MESSAGE / subgraph
- 42020 (telemetry) → STREAM_MESSAGE / subgraph
- 42030 (aggregates) → STREAM_MESSAGE / parent channel (privacy-scoped)
- 42040/42041 (approvals) → STREAM_MESSAGE / approvals inbox
- 42050 (template) → AGENT_PROFILE / directory
- 38150 (pointer) → TBD (architect decision)

### Key Load-Bearing Invariant
Cross-posts carry (source_id, source_timestamp) in tags. Consumer deduplicates by this tuple; same core event in multiple Buzz channels yields one logical record.

### Privacy Boundary
Subgraph channel contains detail; parent/global receive only curated aggregates. Privacy enforced by channel membership topology.

## Architecture Decisions (Not Made)
- Which cross-posts ship v1
- Audience scope for aggregates (42030 private vs. public)
- Approval workflow topology (group consensus vs. federated DM)
- Template pointer (38150) visibility

All documented in deliverable §8; architect chooses.
