---
name: STATUS
desc: Iteration status and progress
tags: [translation, identity, bridge]
sources: []
created: 2026-07-23T19:06:53Z
updated: 2026-07-23T19:06:53Z
---

# Translation Layer & Identity — Iteration 1

## Task
Implement Deliverable 2 (translation functions) and Deliverable 3 (identity + NIP-OA attestation).

### Deliverable 2: Six Translation Functions
- `translate_node_lifecycle(row)` → kind 42010 (status transitions)
- `translate_run_accounting(row, transcript_usage)` → kind 42020 (one per run, never per step)
- `translate_subgraph_digest(row)` → kind 42030 (subgraph summaries)
- `translate_approval_request(row)` → kind 42040 (requires_approval steps)
- `translate_approval_verdict(row)` → kind 42041 (approval outcomes)
- `translate_node_state(row)` → kind 38110 (current node state)

### Deliverable 3: Identity Module
- `load_node_keypair(node_name)` → KeyPair or None
- `check_attestation_valid(pubkey)` → bool
- `refuse_if_revoked(pubkey)` → raises IdentityError if revoked/expired

## Progress
- [x] Read instructions and understand task
- [x] Understand Fractal data sources (rows structure)
- [x] Read kind documentation for wire format details
- [x] Implement translate.py functions (all 6 functions)
- [x] Implement identity.py functions (3 functions)
- [x] Create comprehensive test suite (39 tests total)
- [x] Run tests and verify all pass
- [x] Verify no other test breakage

## Deliverables

### Implementation
- **translate.py**: 6 translation functions mapping Fractal rows to core kind models
  - `translate_node_lifecycle` → kind 42010
  - `translate_run_accounting` → kind 42020 (one per run, never per-step)
  - `translate_subgraph_digest` → kind 42030
  - `translate_approval_request` → kind 42040
  - `translate_approval_verdict` → kind 42041
  - `translate_node_state` → kind 38110

- **identity.py**: 3 identity functions with NIP-OA attestation checking
  - `load_node_keypair`: Load or derive keypair for persistent nodes
  - `check_attestation_valid`: Verify attestation is current and not revoked
  - `refuse_if_revoked`: Fail-safe gate for revoked/expired keys
  - `IdentityError`: Exception for invalid/revoked identities

### Test Suite
- **test_bridge_translate.py**: 21 tests covering all 6 translation functions
  - Golden tests: fixture rows → expected models
  - No-per-step-path: confirms kind 42020 is per-run only
  - Constraint verification: no step-level fields in RunAccounting

- **test_bridge_identity.py**: 18 tests covering identity and attestation
  - Keypair generation: deterministic key derivation
  - Attestation validation: current, non-revoked, non-expired
  - Revoked-key refusal: IdentityError on revoked/expired keys
  - Error handling: proper exception messages

- **Total: 39 tests, all passing**
- Main repo tests unaffected (38 tests still passing)
- test.sh script working correctly

### Completion Status
✅ All Completion Requirements Met
- Deliverable 2: Translation layer fully implemented
- Deliverable 3: Identity module fully implemented  
- All tests passing
- No test breakage
- Code committed: 8e2d3fb

***
