# lindenmayer.core

The foundation library for Lindenmayer: NIP-01 events, Lindenmayer's custom
event kinds, a minimum-contract relay client, and the verification helpers
that let any consumer trust the signed log without trusting a relay.

Design inputs, in authority order: `docs/DESIGN.md` (§1 layering, §4
extraction pipeline, §6 principles), then the relay-integration research
(`docs/research/relay-integration/`). The per-kind wire specs live in
`docs/kinds/` and are readable without any Lindenmayer context.

## Modules

| Module | Role |
|---|---|
| `event` | NIP-01 events: canonical id, BIP-340 signing/verification. The trust root — everything else consumes events through it. |
| `keys` | secp256k1 keypairs and Schnorr primitives (coincurve/libsecp256k1). The only module that touches raw key material. |
| `kinds` | Typed, validating models for the eight Lindenmayer kinds (42010/42020/42030/42040/42041/42050 history; 38110/38150 addressable). |
| `relay` | Relay client. Minimum contract: NIP-01 + NIP-29 + NIP-42 — connect, auth, publish, subscribe, query — and nothing more. |
| `verify` | The security boundary (DESIGN.md §6.5): attestation validation, approval counting, read-time revocation filtering, extraction-time labeling. |
| `config` | Relay URL, key-material resolution, per-deployment capability attestations. TOML + env only — no new storage systems (§6.2). |

## Security posture

**Verify from the signed log alone.** Relay-side enforcement is an
optimization, never an assumption. Every consumer verifies events
(`Event.verify()`), validates attestations, and counts approvals itself via
the `verify` module. A deployment on Buzz gets enforcement as a bonus; a
deployment on a plain NIP-29 relay loses no *integrity*, only convenience.

**Capabilities are attested, not inferred.** Relay behaviors the protocol
does not guarantee — above all NIP-29 private-group *read* gating — must be
explicitly attested per deployment in config (`CAP_PRIVATE_READ_GATING`).
The relay client refuses to treat a channel as private until the deployment
attests enforcement: fail loud, never degrade silently.

**Privacy is a wire-format property.** Run accounting publishes one rolled-up
event per run — never per step; ephemeral workers author no events and
surface only in their persistent parent's subgraph digest. The API is shaped
so the private thing is the easy thing: there is no per-step publish surface
to misuse.

**Owner attestation is NIP-OA, reused as-is.** Lindenmayer mints no kind for
it — NIP-OA is an `auth` *tag* attachable to any event. The upstream schema
is restated in `docs/kinds/nip-oa-attestation.md` so draft churn cannot
retroactively change what historical attestations meant.

## Acceptable degradation (plain NIP-29 relay vs Buzz)

Per the relay-integration research (aggregate, recommendation 3), the
following degradations are accepted and documented rather than papered over:

- **Merge-gate enforcement is not this library's concern.** Approval
  request/verdict events (42040/42041) are signed records; *enforcement* of
  approval-gated merges is a bridge/process concern layered above them
  (Buzz's `buzz-protect` where present, process discipline elsewhere). The
  signed chain is complete either way — what varies is whether anything
  mechanically blocks a merge that ignores it.
- **Revocation has latency under bridge-refusal + reader-filtering.** Without
  relay-side identity enforcement, revoking a key means: the bridge refuses
  to publish for revoked keys (stops new activity at the source), and readers
  filter by attestation validity at query time (`verify` module — bounds
  trust in stored history). This reproduces Buzz's outcome with higher
  latency and procedural rather than structural guarantees. That latency
  window is real; consumers that care must apply read-time filtering — the
  library ships it, but cannot make a relay un-serve stale events.
- **Human surfaces are pure UX.** The packaged surfaces (desktop app,
  directory, huddles) are conveniences; any NIP-29 client can perform the
  same functions against the same events. Nothing recorded depends on them.

What does *not* degrade: everything Lindenmayer records — lifecycle history,
run accounting, digests, approval chains, template versions, attestations —
stores, verifies, and stays queryable on any NIP-01+29+42 relay.

## Key handling

Secrets resolve at runtime from an env var or a `chmod 600` key file
(`CoreConfig.load_keypair`); they never appear in config files, logs, or
reprs. Signing happens only in `keys` (libsecp256k1 via coincurve).
