---
name: decomposition
title: Bridge Decomposition Plan
desc: ...
tags: []
sources: []
created: 2026-07-23T19:24:50Z
updated: 2026-07-23T19:24:50Z
---

# Bridge Decomposition Plan

**Status:** Spawning children per work order step 2.

## Work Split

Parent (main.bridge): Deliverables 4 & 5
- Publisher (deliverable 4): deterministic-id events, idempotent replay via relay cursor
- CLI + E2E dogfood (deliverable 5): end-to-end bridge run

Child main.bridge.adapters: Deliverable 1
- FractalDBReader: read-only SQLite (nodes, runs, iters, steps, events, messages — WAL-safe)
- TranscriptUsageHarvester: extract per-request usage (append-only fields only, never parse structure)
- Acceptance: adapter fixture tests against tree.db + transcript fixtures

Child main.bridge.translate: Deliverables 2 & 3
- Translation: Fractal rows → kind models (42010/42020/42030/42040/42041/38110)
- Golden tests: fixture rows → expected signed events
- No-per-step-path tests: prove only per-run 42020, never per-step
- Identity: per-node keypairs, NIP-OA attestation, revoked-key refusal
- Acceptance: golden tests + revoked-key refusal tests

## Design Constraints

- Only persistent (identified) nodes author events; ephemeral workers only in digest aggregates
- Event ids deterministic from source timestamps (never wall clock)
- No per-step publication path exists (test proves it)
- Harvester never parses conversational structure, only append-only usage fields
- Identity API surfaces attestation validity check and refusal on revoked keys

## Spawn Ceremony Complete

Children initialized and started:
- main.bridge.adapters (cost cap: $5, max iters: 4)
- main.bridge.translate (cost cap: $5, max iters: 4)
Both running in active state with REVIEW step pinned to fable model (inherited).

Parent proceeding with deliverables 4 & 5:
- Publisher: deterministic-id events via relay cursor
- CLI + E2E: fixture tree DB -> mock relay -> expected event stream
