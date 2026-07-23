---
name: relay_integration
desc: Relay-integration research program — children, contracts, synthesis plan.
created: 2026-07-23T13:26:19Z
updated: 2026-07-23T13:26:19Z
---

# relay_integration

## Program — COMPLETE

Root directive 5CD20B25 (now unsaved — both items closed): Nostr-first
layering review (approved, DESIGN.md §1 rewritten, §2 aligned, decision-log
row added, verdict replied as 21FC51ED) plus relay-integration research
(delivered: both children merged, aggregate README.md written and posted to
outbox as F6486011).

## Children (both sonnet leaves, $6 cap, 4 iters, scope docs/)

- `main.platform_architect.kinds` → owns
  `docs/research/relay-integration/event-kinds.md`. Telemetry→NIP mapping,
  custom-kind sketches (tag schemas, replaceable vs append-only), NIP-AM/AO
  alignment, kind-documentation convention.
- `main.platform_architect.degradation` → owns
  `docs/research/relay-integration/degradation.md`. Works/degrades/Buzz-only
  matrix on a plain NIP-29 relay, identity without NIP-OA enforcement,
  plain-relay privacy, minimum relay contract recommendation.

Both fork commit e390f32 (contains the adopted layering — they research
against current truth). Their completion gates on their own committed
deliverable + a priority-3 outbox note; they self-finish, no parent sign-off
gate.

## Synthesis — delivered

`docs/research/relay-integration/README.md` aggregates both studies:
mostly-standard taxonomy (8 custom kinds in 420xx/381xx blocks, NIP-OA
as-is), privacy in the wire format (per-run rollups, ephemeral workers only
in parent digests), min relay contract NIP-01/29/42, private-group read
gating verified per deployment (fail loud), revocation via bridge-refusal +
reader-filtering. Posted to outbox (F6486011). Degradation child completed;
kinds child delivered and finishing. Tooling issue (.gitignore '.fractal/'
vs fractal's exclude design breaking fractal commit) verified and escalated
to root as C06265E8.

## Operational facts

Promoted to the shared wiki: see the project wiki page `node_operations`
(transcript --ignore-scope convention, gitignored `.fractal/` and its
spawn/baseline-commit consequences, CLI syntax gotchas).
