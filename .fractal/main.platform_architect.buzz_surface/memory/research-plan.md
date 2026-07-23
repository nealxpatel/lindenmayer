---
name: research-plan
title: Buzz Surface Research Plan
desc: ...
created: 2026-07-23T21:47:00Z
updated: 2026-07-23T23:41:27Z
---

# Buzz Surface Research Plan

## Objective
Ground the Buzz human-surface mapping for the evergreen component by researching:
1. Buzz primitives (NIP-29 channels, groups, membership, identity)
2. Ingest constraints (accepted kinds, timestamp drift)
3. Identity handling (NIP-OA attestation on ingest/surface)
4. Mapping table (Lindenmayer core kinds → Buzz cross-post destinations)

## Source Context
- Lindenmayer kinds (core): 42010 (node lifecycle), 42020 (telemetry), 42030 (radio aggregates), 42040/42041 (approvals), 42050/38150 (templates)
- Buzz repo: ~/Code/buzz @ daeaf7c
- DESIGN.md §1: Two-layer output (Nostr core on Lindenmayer relay + Buzz layer as derived view)
- DESIGN.md §1: Cross-posts are by-reference (core id + source timestamp in tags), deduped on core event id

## Verified Findings So Far
- Buzz ingest MAX_TIMESTAMP_DRIFT_SECS = 900 (±15 min) ✓
- Buzz has exhaustive kind_required_scope_for_kind match (restrictive) ✓
- Buzz accepts ~40 kinds total, including:
  - KIND_TEXT_NOTE (1)
  - KIND_STREAM_MESSAGE (9) 
  - KIND_APPROVAL_GRANT/DENY (46030/46031)
  - KIND_NIP29_* group management
  - KIND_DM_OPEN/ADD_MEMBER/HIDE (0-scoped message commands)
- NIP-29 group kinds (9000-9009, 9021, 9022, 39000-39003)

## Next Steps
1. Read NIP-29 group implementation (channels, membership, invites, moderation)
2. Read NIP-OA attestation format and Buzz handling
3. Study Buzz channel/room model and agent directory
4. Map each Lindenmayer kind to Buzz surface + channel shape + tag structure

## Deliverable
`docs/research/evergreen/buzz-surface.md` with:
- Buzz primitives findings (cited)
- Ingest constraints (cited, re-verified)
- Identity findings (NIP-OA on ingest/surface)
- Full mapping table (all 8 core kinds × Buzz kinds/shapes/tags)
