---
name: memory
desc: Relay leaf status and delivered design notes for src/lindenmayer/core/relay.py.
tags: []
sources: []
created: 2026-07-23T15:52:09Z
updated: 2026-07-23T16:02:15Z
---

# memory

***

`RelayClient` in `src/lindenmayer/core/relay.py` implements the full minimum
contract: connect/publish/query/subscribe over `websockets`, NIP-42
auth-challenge with retry-after-auth on `OK`/`CLOSED` `auth-required:`
rejections, NIP-29 `h`-tag group scoping (filters get `#h`; publish validates
an already-signed event's `h` tag rather than mutating it), fail-loud
`PrivateCapabilityError` gating behind `CoreConfig.has_capability
(CAP_PRIVATE_READ_GATING)`, and bounded reconnect with resubscribe of live
`subscribe()` calls (no persistent queue — documented in the module
docstring). Inbound events are dropped and counted (`dropped_invalid`) unless
`Event.verify()` passes.

Tests: `tests/relay_mock.py` (in-process mock relay) + `tests/test_relay.py`
(12 tests) cover publish/OK round-trip and rejection, query-until-EOSE, live
subscribe, the NIP-42 auth flow (including retry-after-auth for both publish
and query), invalid-signature drop, `h`-tag scoping, and private-gating
refusal/success. Full project suite passes (64 tests).

Status: implementation and tests complete this iteration; committing and
finishing.
