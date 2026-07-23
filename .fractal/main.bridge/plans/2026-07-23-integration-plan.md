# Integration Plan

**Date:** 2026-07-23
**Run/Iter:** 1.1
**Status:** Draft (awaiting children completion)

## Overview

Once main.bridge.adapters and main.bridge.translate complete their work, integrate the four deliverables (adapters, translation, identity, publisher) to build the complete bridge implementation.

## Integration Steps

### 1. Verify Child Deliverables

- [ ] **main.bridge.adapters** completed:
  - [ ] FractalDBReader (SQLite adapter) fully implemented and tested
  - [ ] TranscriptUsageHarvester (transcript adapter) fully implemented and tested
  - [ ] All adapter fixture tests passing

- [ ] **main.bridge.translate** completed:
  - [ ] translate.py (all 6 translation functions) implemented
  - [ ] identity.py (attestation checking, revoked-key refusal) implemented
  - [ ] Golden tests passing (fixture rows → signed events)
  - [ ] No-per-step-path test passing
  - [ ] Revoked-key refusal test passing

### 2. Merge Child Branches

```bash
git merge --no-ff main.bridge.adapters
git merge --no-ff main.bridge.translate
```

Wire up module imports in publisher.py and cli.py to use child implementations.

### 3. Complete Remaining Implementation

- [ ] Publisher.resume_from_relay: implement DB schema query to handle Fractal-specific DB layout
- [ ] Publisher publish loop: integrate with translate layer to convert Fractal rows to events
- [ ] CLI: complete the async main loop to read Fractal DB, harvest transcripts, translate, publish
- [ ] E2E dogfood test: fixture tree DB → mock relay → expected event stream

### 4. Run Full Test Suite

```bash
bash /Users/nealpatel/Code/l-system/.worktrees/main.bridge/.fractal/main.bridge/scripts/test.sh
```

Acceptance criteria:
- All adapter fixture tests pass
- All golden tests pass
- No-per-step-path test passes
- Revoked-key refusal test passes
- Idempotent-replay tests pass
- E2E dogfood test passes

### 5. Finalize and Commit

- [ ] Merge resolution and final integration commit
- [ ] Update memory with findings
- [ ] Promote learnings to shared wiki
- [ ] `fractal node finish --reason="Bridge complete: all deliverables integrated and tested"`

## Known Challenges

- Matching Fractal DB schema (adapter must handle all edge cases)
- Replay determinism (ensure source timestamps never change)
- Translation of all status transitions and approval flows
- E2E test setup (mock relay event ordering and filtering)

## Design Constraints

- No new storage systems (relay is the cursor)
- Only persistent nodes author events
- Privacy is wire-format (aggregates-up by default)
- Attestation validity is verifiable by any relay
