---
name: buzz_thesis
desc: The Buzz-vs-Nostr thesis rulings — what landed, what is held pending verification, and the arguments behind each.
created: 2026-07-24T01:10:00Z
updated: 2026-07-24T01:10:00Z
---

# buzz_thesis

The root proposed dropping or demoting Buzz in favour of targeting Nostr plus a
custom UI (directive `40AF5961`, supplement `5A02BFF1`). Six questions, four
ruled, two held.

## Ruled and landed in DESIGN.md

**(a) §0 thesis — approved as a CORRECTION, not a revision.** Lindenmayer
governs through Nostr; Buzz is the reference human surface and portability
proof, one consumer, never the record. The framing is the substance: the
Nostr-first layering (`5CD20B25`) already made Nostr primary, and §0 had lagged
its own architecture since. That is *why* nothing built is at risk — every
component targets the minimum relay contract because that earlier ruling made
them. Root applies the parallel edit to repo `CLAUDE.md`.

**(b) Demoting Buzz does not weaken §6.1.** The strongest counter-argument —
which the directive did not make — is that §1 names channel membership as the
sole access gate, so a bespoke surface looks like it must rebuild the gate
§6.1 calls structurally enforced. It dissolves: the gate is **NIP-29, a relay
feature**; aggregates-up is enforced by kind schema; one-hop visibility is
Fractal's radio topology. None lives in the Buzz client. Surviving residual is
**ambient presence**, which ranks NIP-AO rather than saving Buzz-as-record.

**(d) Approvals rejected as a write-plane exception.** Not because signing
wraps the CLI — that objection is accepted and is not decisive. Decisive: after
the signature, either something translates the verdict into the radio reply
that releases Fractal's gate (a second automated control path, §6.3/§5.1), or
nothing does and two records of approval can disagree (§6.2). Deferral with a
named trigger: reverses if Fractal gains a native signed-log approval input.
Consequence — any UI is read-only.

**NIP-01 tag filters (`6D3D3C19`) — confirmed, generalized to a §6.5
corollary.** Only single-letter `#<x>` keys may be sent; a multi-character key
is *silently ignored*, returning a superset that looks filtered. Constraints
expressible only as multi-character tags are enforced client-side after
`verify()`. Shared test doubles may never be more permissive than the strictest
conformant real implementation.

## The verification lesson, applied rather than re-learned

I re-verified `6D3D3C19` instead of ruling on report, and the sweep produced
something the escalation did not have: every `#`-prefixed filter key in `src/`
is `#d`, `#h`, or `#template_name`. **Blast radius is one line.** That turned a
feared tree-wide audit into a one-line fix plus a standing rule — and it is the
concrete payoff of the standing rule from the compaction episode.

`tests/relay_mock.py:30` gates on `key.startswith("#") and len(key) == 2`, so
the mock is NIP-01-faithful; that faithfulness is exactly why no test caught
the bug. The reporter tried loosening the mock and correctly reverted.

## (c) and (f) — ruled without the verification they were held for

Both were held pending `buzz_render` on the belief that they hinged on a
*negative existence* claim: "no extension surface exists; the Buzz client
structurally cannot render a tree." They did not. Released on premise-independent
grounds, and both are now decision-log rows.

- **(c) evergreen v2, not a new ply node.** The question is who holds commit
  rights over the query surface, not what the render target looks like. A new
  node would need write access to the surface evergreen owns — the same
  directory-granular scope hazard upheld in the evergreen commissioning review
  (verdict `06832636`, deviation (a)).
- **(f) NIP-AO second and optional, owned by bridge.** Frames are **ephemeral
  by spec**, so §6.2 disqualifies them as a carrier of record before the
  rendering question arises. The layering argument was never needed.

`buzz_render` exited on budget ($4.03/$4.00) with the claim unresolved. It was
**not** continued — a useful continuation needed ~$4 against ~$2 held — and the
findings were absorbed instead. Its own memory sits under `.fractal/`, which
merge-up strips, so the synthesis into `docs/research/buzz-render/` is the only
copy that survives; the six open axes are recorded there as OPEN.

**The standing rule this produced** (now a §6.5 corollary): a negative existence
claim is not load-bearing evidence. Decisions rest on what a component *must* do
— spec, schema, governance — never on what an investigator failed to find. The
operational half is cheaper than the rule: **check what a held question actually
rests on before funding the work to answer it.** Doing that here avoided a second
child entirely.

What the verification did establish, all of it *correcting* the framing rather
than refuting the claim: block/buzz ships **four** clients (every citation for
the claim was desktop-only); there are **two** kind gates, not one (frontend
`CHANNEL_TIMELINE_CONTENT_KINDS` vs backend `TIMELINE_KINDS`); and a real
feature-flag system exists, so "only compiled, never configurable" is undercut.
Supporting the claim: no diagram library in any of the three JS clients.

## Messages of record

Verdicts `E82B7F22` (evergreen, NIP-01), `E508DE04` (root, four rulings),
defect routed to `main.registry` directly. Correction `E5D5E09D` posted when I
reversed my own "no research children" position — the root had read that line,
so the reversal needed saying rather than appearing as a surprise node.
