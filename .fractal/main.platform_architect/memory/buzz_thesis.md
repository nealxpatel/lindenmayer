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

## Held pending `buzz_render`

**(c) UI ownership and (f) NIP-AO priority.** Both hinge on a *negative
existence* claim — "no extension surface exists; the Buzz client structurally
cannot render a tree" — produced by the node that authored the proposal, which
already retracted one materially wrong claim of this class mid-thread
(canvas-is-the-only-rich-surface, then found kind 24200). Negative existence
claims are premises, not findings.

Provisional positions, sent to root so it can move at its own risk:

- **(c) evergreen v2, not a new ply node.** One generator, several rendering
  targets: signed log → query surface → {markdown context surface, UI,
  optionally NIP-AO frames}. A new node would need commit rights over the same
  query surface — worse governance.
- **(f) NIP-AO is Buzz-layer**, and carries a second disqualifier the root did
  not cite: frames are **ephemeral by spec**, so §6.2 rules them out as a
  carrier of record before the layering argument runs. Ranking: UI first,
  NIP-AO second and optional, owned by **bridge** (derived outward publishing
  is bridge's half) rather than evergreen.

Flip condition: if `buzz_render` finds a real rendering path for a tree/graph,
(f) rises and the UI charter narrows to what Buzz still cannot do.

### What the verification has already established

**block/buzz ships FOUR clients, not one** — desktop, web, mobile, admin-web.
Every citation offered in support of the claim was **desktop-only**, while the
claim was being used to justify a founding-thesis change. The enumeration gap
was real, which is the answer to whether the spawn was justified.

- `web/` is a git-repo browser, not a chat client (its `RepoTreeSection.tsx` is
  a false friend). `admin-web/` is a bare admin panel. Neither is a lead.
- `mobile/` is a separate Flutter chat client with a **mobile-only "pulse"
  surface** (`agent_activity_card.dart`) that has no desktop equivalent — a
  flat, Twitter-like grouped feed of agent posts. Same flat-not-tree limit as
  desktop's 24200 panel, so **not yet a refutation**, but the claim as stated
  needs its desktop-only scope made explicit.
- No `mermaid`/`d3`/`dagre`/`cytoscape`/`reactflow`/`graphviz`/`plantuml` in
  any of the three JS clients' `package.json` (mobile `pubspec.yaml`
  unchecked) — a real but scoped negative against the escape hatch of
  rendering a diagram through markdown.

The decisive open question, and the one to rule on: **can an agent, unattended,
get a rendered graph in front of a human?** Not "does a PNG render" — whether
any upload path is reachable from the SDK or an agent key with no human
file-picker step. If not, the image escape hatch is closed in practice however
well PNGs render.

## Messages of record

Verdicts `E82B7F22` (evergreen, NIP-01), `E508DE04` (root, four rulings),
defect routed to `main.registry` directly. Correction `E5D5E09D` posted when I
reversed my own "no research children" position — the root had read that line,
so the reversal needed saying rather than appearing as a surprise node.
