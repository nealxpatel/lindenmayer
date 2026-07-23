---
name: status
desc: What stands in the kinds deliverable and what remains to build.
created: 2026-07-23T15:59:46Z
updated: 2026-07-23T15:59:46Z
---

# status

## Stands (committed code, smoke-tested)

`src/lindenmayer/core/kinds/` is complete: constants.py (single-source kind
numbers 42010/42020/42030/42040/42041/42050/38110/38150), base.py
(KindModel with to_event/from_event, KindValidationError), models.py (all
eight models per event-kinds.md §2), registry.py (KIND_REGISTRY +
parse_event). Round-trip and reject paths verified by hand; pytest suite
NOT yet written. Privacy constraints honored: no per-step model, no
per-worker identity, cost fields are cost_shadow_usd.

## Key facts already researched (don't re-read the NIPs)

- NIP-AM (buzz 06e3d82): kind 44200, encrypted per-turn metrics. Vocab:
  costUsd, inputTokens, outputTokens, totalTokens, model, stopReason,
  sessionId, turnSeq, harness, timestamp. NO duration field — spec §3's
  "cost, duration, model" overlap guess is wrong on duration; record that
  correction in the 42020 doc. cost_shadow_usd ↔ costUsd (both advisory
  estimates; renamed to carry the shadow label per DESIGN §6).
- NIP-AO (buzz 06e3d82): kind 24200 ephemeral encrypted observer frames;
  frame kinds turn_started/session_resolved ↔ our 42010 lifecycle;
  cancel_turn control ↔ approval-gate territory for 42040/42041 notes.
- NIP-OA (buzz 06e3d82): an `auth` TAG (4 elements: owner-pubkey-hex,
  conditions, sig-hex), NOT an event kind — corrects event-kinds.md §1.7
  "presumed addressable". Preimage `nostr:agent-auth:<agent-pubkey>:<conditions>`,
  SHA256, BIP-340. Conditions grammar: kind=<dec> / created_at<t / created_at>t,
  &-joined, no whitespace, canonical decimals, no self-attestation, exactly
  one auth tag. Test vectors live in the cached NIP-OA.md §Test Vectors.

## Delivered (completed)

All nine `docs/kinds/` files per §4 convention:
- 42010-node-lifecycle.md, 38110-node-state-pointer.md, 42020-run-accounting.md
- 42030-subgraph-digest.md, 42040-approval-request.md, 42041-approval-verdict.md
- 42050-template-version.md, 38150-template-pointer.md, nip-oa-attestation.md

All eight models + registry/dispatcher in `src/lindenmayer/core/kinds/`:
- constants.py (single-source kind numbers)
- base.py (KindModel, KindValidationError, to_event/from_event)
- models.py (all eight models per event-kinds.md §2)
- registry.py (KIND_REGISTRY, parse_event dispatcher)
- __init__.py (exports)

Comprehensive test suite (`tests/test_kinds.py`, 718 lines):
- Round-trip conversion (model → Event → model) for all kinds
- Rejection cases: wrong kind, missing tags, malformed content
- Addressable kinds carry 'd' tag assertions
- All worked examples from docs validated through registry
- 144 tests total (38 kinds-specific + inherited test coverage)

Test status: ✅ PASSING (144 tests in bash scripts/test.sh)
