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

## Remains

1. docs/kinds/ — all NINE files (none written). Use §4 convention; generate
   worked examples via the code (Event.build with fixed pubkey/created_at)
   so ids are canonical-valid. nip-oa-attestation.md = restatement pinned to
   buzz 06e3d82.
2. tests/test_kinds.py — accept/reject per kind + harness extracting each
   doc's ```json example and parsing through registry (skip/special-case
   nip-oa doc: validate via Event.from_dict + auth tag shape).
3. Run scripts/test.sh green, outbox, then node finish.
