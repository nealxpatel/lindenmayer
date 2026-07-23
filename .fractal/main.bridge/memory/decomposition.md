---
name: decomposition
title: Bridge Decomposition Plan
desc: How the bridge deliverables were split between parent and child nodes.
tags: []
sources: []
created: 2026-07-23T19:24:50Z
updated: 2026-07-23T20:28:35Z
---

# Bridge Decomposition Plan

**Status:** Complete. Both children finished and their work is merged.

## Work Split

Parent (main.bridge) owned deliverables 4 & 5:

- Publisher (deliverable 4): deterministic-id events, idempotent replay via relay cursor
- CLI + E2E dogfood (deliverable 5): end-to-end bridge run

Child main.bridge.adapters owned deliverable 1:

- FractalDBReader: read-only SQLite (nodes, runs, iters, steps, events, messages — WAL-safe)
- TranscriptUsageHarvester: extract per-request usage (append-only fields only, never parse structure)
- Acceptance: adapter fixture tests against tree.db + transcript fixtures

Child main.bridge.translate owned deliverables 2 & 3:

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

## Outcome

Both children ($5 cap, 4 iters each, REVIEW pinned to fable) completed and were
merged with `--no-ff`. Parent shipped publisher, CLI, and the E2E dogfood test.
