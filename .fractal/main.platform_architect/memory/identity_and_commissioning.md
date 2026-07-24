---
name: identity_and_commissioning
desc: The competing-assertion rule and the identity/version/grant/commissioning rulings it settled.
created: 2026-07-24T01:52:39Z
updated: 2026-07-24T01:52:39Z
---

# identity_and_commissioning

Two root directives (`35718844` identity × version + commissioning;
`2A25343E` revocation defect + intake + @mention) ruled as one pass. Verdicts
`AAB14416` and `E4DC729B`. Eight decision-log rows.

## The rule that came out of it — carry this forward

**A new signed record is safe exactly when Fractal holds no competing
assertion of the same proposition.** DESIGN.md §6.5 corollary; working form on
the shared wiki page `platform_boundaries`.

It settles approvals (barred), radio/signal/kill wrappers (barred), commission
authorization (permitted), and inbound @mention (permitted) — and the fact
that it does *not* rule the same way on all four is what makes it a rule
rather than a rationalization for what I already wanted.

Two clean-ups it forces on my own past reasoning:

- Publishing a signed event is never *itself* the violation. I had written
  §5.1 so that "no write path" could be read as "evergreen never signs
  anything," which would have barred safe work. The split governs the
  **Fractal control plane, not the log**.
- "It wraps a CLI" is never *itself* decisive. It is usually a symptom. Ask
  what proposition the record asserts.

The line that keeps approvals barred while letting commissioning through:
**authorization-without-execution is coherent; approval-without-release is
not.**

## What was ruled

- **Identity role-scoped, trust version-scoped.** One npub per role across
  runs and revisions; revision keeps identity, fork mints a new one; the
  42050 inherit `e`-tag is design ancestry, never reputation transfer.
  Adoption is explicit and event-recorded, never automatic on publish.
- **10100 profile = derived pointer only.** Resolvable coordinates (`a` tag
  to 38150 + adopted 42050 id), never a transcribed version string — the same
  stale-restatement failure §3 records against the tier table. Adoption chain
  wins on disagreement.
- **§1 revocation defect fixed.** Subgraphs attest to a durable org/seat key;
  a human's evergreen node holds a revocable *grant*; succession moves grants,
  not capabilities.
- **Grants unified**: kind 42080 + 42081 revocation, one kind with a `scope`
  tag, three uses.
- **Commissioning approved minus the spawn**: kind 42070 commission covers
  everything through the work order; `fractal node init` stays operator-run;
  the instance's 42010 carries a `commission` reference.
- **Intake absorbed into evergreen**; **@mention veto lifted** with four
  specified conditions.
- **Vocabulary**: Fractal (platform) / tree-subgraph (running instance) /
  **capability** (template + role identity + version-scoped track record).

## Two method notes worth keeping

**The abstraction test.** The root offered "one primitive doing three jobs" as
evidence the grant abstraction was right. Reuse is evidence of *economy*, not
correctness — a shared shape proves nothing. The test that does work is shared
**revocation semantics**: same revoker (as a rule, not as an identity), same
blast radius, same expiry. The three uses passed, so the answer was the same;
the grounds were not. Had the *revoker* differed, they would be distinct kinds
however alike they looked.

**Verifying beat assuming, again, and cheaply.** The root asserted NIP-OA
"models 'this agent belongs to this person', full stop" and inferred we needed
our own kind. Reading `docs/kinds/nip-oa-attestation.md` showed the owner field
is just a *pubkey* — the draft nowhere requires it be a person — so an org key
substitutes with no spec change. Half the request dissolved; the other half
(the grant) was a kind we already owed ourselves. One file read.

The same read produced the argument for the durable owner key that the root
had not found: NIP-OA has **no revocation primitive at all** (conditions are
only `kind=` and `created_at` bounds; attestations are never revoked, only
superseded), so person-attestation would force reissuing every attestation in
a subgraph on every departure. Attesting to the org means the attestation
never changes on succession — the spec's weakest property stops mattering.

## Standing constraints respected

`tree/` untouched (contract consequences go out as proposals); `docs/kinds/`
entry *files* are `core`'s to write — I allocate numbers and set conditions,
and `core` re-runs the block/buzz collision check first. Decision-log rows
cite requesting message UUIDs, never line numbers.

## Honest limits recorded rather than implied

Nothing enforces a management grant today — Fractal does not read the log, so
a grant is a governance fact of decision-log standing until commissioning
gives it a consumer. Two new §8 open questions came out of ruling rather than
being papered over: **org/seat key custody** (succession is specified at the
grant layer, unspecified at the key layer, and a lost org key strands every
capability attested to it) and **commission conformance** (drift is visible
by construction but nothing checks it).
