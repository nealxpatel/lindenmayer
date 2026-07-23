# NODE.md — core

- **branch:** `main.core`
- **parent:** `main` (root / user node)
- **scope:** `src`, `tests`, `docs/kinds`
- **role:** first ply, foundation. Event kinds, relay client, config — merges
  first; the rest of the ply builds against its contracts (DESIGN.md §7).

## Instructions

You are the **core** node for Lindenmayer: you build the foundation library
that every other component consumes. Your design inputs, in authority order:
`docs/DESIGN.md` (especially §1 layering, §6 principles, §4
extraction-pipeline requirements), then the relay-integration research
(`docs/research/relay-integration/` — the README aggregate is your interface;
event-kinds.md and degradation.md are your detail).

Deliverables, in `src/lindenmayer/core/`:

1. **Event model.** NIP-01 events: canonical id computation, secp256k1
   Schnorr signing and verification. This is the trust root of the entire
   platform — test it against published NIP-01 vectors.
2. **Kind registry.** Typed models with validation for the eight custom
   kinds proposed by the research — append-only history: 42010 node
   lifecycle, 42020 run accounting, 42030 subgraph digest, 42040/42041
   approval request/verdict, 42050 template version; addressable: 38110 node
   state, 38150 template pointer — plus NIP-OA attestation events reused
   as-is (no Lindenmayer kind minted; the upstream schema is restated in
   `docs/kinds/nip-oa-attestation.md` per event-kinds.md §1.7, so draft
   churn cannot invalidate historical attestation semantics — pull
   `docs/nips/OA.md`, `AM.md`, and `AO.md` from block/buzz before writing
   those entries). Each custom kind is self-documented into
   `docs/kinds/` per the convention in event-kinds.md §4, so any Nostr
   client can interpret it without Lindenmayer context.
3. **Relay client.** The minimum relay contract is NIP-01 + NIP-29 + NIP-42
   and NOTHING more (connect, auth, publish, subscribe, query). NIP-34,
   Blossom, and Buzz custom relay behavior are additive capabilities, never
   baseline. Private-group read gating is a per-deployment capability that
   must be verified, not inferred: the client refuses to treat a channel as
   private until the deployment attests enforcement (fail loud).
4. **Verification module — the §6.5 security boundary.** Attestation-chain
   validation, approval counting, read-time revocation filtering. Relay
   enforcement is an optimization, never an assumption: these helpers are
   how every consumer verifies from the signed log alone. Include an
   attestation-state labeling helper for the future extraction pipeline
   (§4 requires corpus rows labeled at extraction time).
5. **Config.** Relay URL, key material handling, per-deployment capability
   attestations. No new storage systems (§6.2).
6. **Kind-number collision check.** The proposed numbers are unregistered
   proposals (DESIGN.md §8). Check them against Buzz's current allocations
   (`buzz-core/src/kind.rs`, 40000–49999 range) and escalate the result to
   `main.platform_architect` (priority 6) — resolving the open question is
   the architect's call, not yours.

Constraints:

- Python ≥3.12, uv-managed. Minimal, well-maintained dependencies; justify
  every new runtime dep in a plan before adding it.
- Privacy is a wire-format property: one rolled-up accounting event per run,
  never per step; ephemeral workers author no events. The library must make
  the private thing the easy thing — no API that tempts a caller into
  per-step publishing.
- Design questions and key-component changes route to
  `main.platform_architect` (priority 6); its rejection is a veto. Never
  edit `docs/DESIGN.md` — it is outside your scope and owned by the
  architect.
- All dollar figures are shadow cost; the binding constraint is subscription
  rate windows — pace children accordingly.

## Completion Requirements

- All six deliverables exist and `bash $NODE_DIR/scripts/test.sh` passes,
  covering at minimum: NIP-01 id/sign/verify round-trips against published
  vectors; kind schema validation (accept/reject cases per kind);
  verification-module cases (valid, expired, and revoked attestation chains;
  approval-count edges); relay client exercised against a mock or local
  relay.
- `docs/kinds/` documents all eight custom kinds plus the NIP-OA restatement
  (nine files) per the event-kinds.md §4 convention.
- Library documentation states the acceptable-degradation posture (research
  aggregate, recommendation 3): merge-gate enforcement is a bridge/process
  concern layered above the signed approval events; revocation latency under
  bridge-refusal + reader-filtering is documented, not hidden; human
  surfaces are pure UX with any NIP-29 client as substitute.
- The collision-check escalation is sent to the architect (priority 6).
  (Acknowledgment is the architect's commitment, not your gate — a reply
  requirement would strand a done node `exited` if the architect isn't
  running.)
- Progress posted to your outbox; `fractal node finish` in the iteration the
  requirements hold.
