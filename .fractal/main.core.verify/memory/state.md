---
name: state
desc: Current state of verify.py build — design decided, implementation not yet started.
tags: []
sources: []
created: 2026-07-23T16:01:19Z
updated: 2026-07-23T16:01:19Z
---

# state

## Status

Design is fully decided (see plan file referenced below); no code written
yet. `src/lindenmayer/core/verify.py` and `tests/test_verify.py` do not
exist on disk. Next iteration's EXECUTE should write both files directly
from the design below without re-reading the spec sources — they're
already digested here.

Plan file with full design rationale:
`.fractal/main.core.verify/plans/2026-07-23T15:58:30.417Z-12.1-verify_module.md`
(this is the plans dir, not the wiki — read it directly, no wikilink).

## Design summary (ready to implement)

**`validate_attestation(event) -> AttestationResult`**
- `AttestationOutcome` enum: `VALID`, `ABSENT` (no auth tag), `INVALID`
  (tag present but fails any check).
- Order: `event.verify()` first (else `INVALID`/`invalid_event`) → count
  tags named `auth` directly from `event.tags` (0 → `ABSENT`; >=2 →
  `INVALID`/`duplicate_auth_tag`) → must have exactly 3 values after the
  tag name (4 elements total) → hex validate owner (64 lowercase) and sig
  (128 lowercase) → self-attestation (owner == event.pubkey) → STRICT
  conditions grammar → BIP-340 verify via `keys.schnorr_verify` over
  `sha256("nostr:agent-auth:" + event.pubkey + ":" + conditions)` → each
  clause evaluated against the event (AND) → `VALID`.
- Conditions grammar: `""` is valid (no clauses). Otherwise split on `&`;
  any empty segment (leading/trailing/double `&`) rejects. Each clause
  must fullmatch `^(kind=|created_at<|created_at>)(0|[1-9][0-9]*)$`
  (rejects unicode digits and leading zeros that `str.isdigit()` would
  miss). Range: kind 0-65535, created_at 0-4294967295 — reject out of
  range. Do not reorder/dedupe/normalize the conditions string — the raw
  string is what's signed.

**`count_approvals(request, events) -> ApprovalCounts`** (NamedTuple:
`approve_count`, `reject_count`, `per_approver: dict[pubkey, "approve"|"reject"]`)
- Verdict schema decision (undocumented upstream — no `docs/kinds/` on
  this branch yet): valid verdict candidate = kind==42041, `event.verify()`
  true, has an `e` tag whose value equals `request.id`, and `content` is
  exactly `"approve"` or `"reject"` (anything else excluded, not counted
  either way). **Must radio main.core (priority 5, design note) about this
  assumption before finishing** — not yet sent as of this write.
- Per-approver: latest verdict wins by `(created_at desc, id asc as
  tiebreak)`.
- `is_approved(request, events, threshold, required_approvers=None)`:
  filters `per_approver` to `required_approvers` if given, counts
  approves among the (filtered) set, compares to threshold.

**`attestation_state(event, revoked_owners=frozenset(), revoked_agents=frozenset()) -> AttestationState`**
- `INVALID_EVENT` if `event.verify()` fails.
- Else run `validate_attestation`:
  - `ABSENT` outcome → if `event.pubkey in revoked_agents`: `REVOKED`
    (deliberate extension — agent-key revocation applies even without an
    auth tag, so the reader-side trust bound actually bounds the key, not
    just the attestation claim; document this reasoning in the
    docstring) else `UNATTESTED`.
  - `VALID` outcome → if owner in `revoked_owners` or `event.pubkey in
    revoked_agents`: `REVOKED` else `ATTESTED`.
  - `INVALID` outcome → `INVALID_ATTESTATION`, carrying the reason string
    from `validate_attestation`.

**`filter_attested(events, revoked_owners=frozenset(), revoked_agents=frozenset())`**
- Keep events whose `attestation_state` is `ATTESTED` or `UNATTESTED`;
  drop `INVALID_EVENT`, `INVALID_ATTESTATION`, `REVOKED`.
- Docstring must state the latency caveat: a plain relay still serves
  stale/revoked events post-hoc; this filter is the reader-side bound on
  trusting them, not relay enforcement (degradation.md §2).

## Test vectors on hand

- `tests/vectors/nip_oa_signed_event.json` already exists (committed by
  the `event` module's tests) — the NIP-OA "Signed Event Example". Reuse
  it for the end-to-end ATTESTED test; don't recreate it.
- NIP-OA "Test Vectors" section (owner_secret=...0001, agent_secret=...0002)
  and "Invalid Test Vectors" (6 cases) are transcribed into the plan file
  in full — copy from there, not from re-reading the NIP-OA.md cache.

## Budget note

PLAN step ran long on research (spec + DESIGN.md + interface reading +
degradation.md), tripping the $2.0/iter cap mid-step. Total node budget
is healthy ($2.9491 of $5.0 remaining) — this was a per-iteration cap
trip, not a run-ending one. EXECUTE next iteration should write both
files in one pass using the design above with no further research needed.
