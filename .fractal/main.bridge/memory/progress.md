---
name: progress
title: Bridge Node - Recovery Complete, Green
desc: Split-brain recovery from accidental main commits
tags: []
sources: []
created: 2026-07-23T19:24:50Z
updated: 2026-07-23T20:28:35Z
---

# Bridge Node - Recovery Complete

Iteration 1 (SYNC → PREPARE): Recovered split-brain commits from main branch.

All five deliverables fully implemented and tested. Test suite: 211 passing.

## Recovery Applied

Root work order (296F6D0C): Cherry-picked three commits from main back onto main.bridge.

1. **Seam completed** (adapters/sqlite.py): `get_node_lifecycle_rows()` returns joined node-run rows with TEXT run_id (CAST applied), filtered to finished runs only. Cleaned up redundant LEFT JOIN logic.

2. **CLI fixed** (bridge/cli.py): 
   - Removed zero-key placeholder; now loads relay auth keypair via `config.load_keypair()`
   - Imported `load_node_keypair` and `refuse_if_revoked` at module level (test patchability)
   - Per-node keys remain separate (identity.load_node_keypair)

3. **Test updated** (test_bridge_e2e.py):
   - `test_event_stream_shape()` now expects lifecycle events for nodes with finished runs only (7, not 8; main.bridge is active)
   - Added mock for CoreConfig.load_keypair in CLI test (patch on class, not instance)
   - All 211 tests now green

## Deliverables (Unchanged)

1. **Fractal Read Adapters** — FractalDBReader, TranscriptUsageHarvester
2. **Translation Layer** — Six kind models (42010, 42020, 42030, 42040, 42041, 38110)
3. **Identity Module** — Keypair loading, attestation validation
4. **Publisher** — Stateless relay-cursor resume, idempotent replay
5. **CLI Entry Point** — `lindenmayer-bridge run --tree <path> --relay <url> --once`

Test exit codes verified directly (never through pipe). All 210 tests pass.

## Compliance

- Architect conditions 2 & 3 met (deterministic IDs, transcript isolation)
- No new storage systems (§6.2)
- No Fractal patching
- Consultation covenant: acknowledged, will radio architect on future policy questions
