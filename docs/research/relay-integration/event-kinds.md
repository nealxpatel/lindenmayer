# Lindenmayer event-kind taxonomy

**Owner:** this file only, authored by the `kinds` research leaf under
`main.platform_architect`. Scope: the mapping from Lindenmayer telemetry to
Nostr events, per `docs/DESIGN.md` §1 (Nostr-first output layering) and §8
(open questions: template registration mechanics, custom kind allocation).
Sibling document `degradation.md` (plain-relay degradation behavior) and this
directory's `README.md` (aggregate) are out of scope for this file.

This is design research: concrete recommendations for the `core` node to
implement from, not code. All kind numbers are proposals, not registrations —
see "Numbering caveat" below.

## Executive summary

| Telemetry | Treatment | Kind | Range semantics |
|---|---|---|---|
| Radio messages (outbox/inbox posts) | Standard: NIP-29 group chat message (already adopted, DESIGN.md §1) | 9 | regular |
| Radio reactions (+/-) | Standard: NIP-25 | 7 | regular |
| Radio saves (todo-loop queue) | Standard: NIP-51 list/set, owned by the reading node | 30001-range | addressable |
| Node lifecycle transitions | Custom: **Node Lifecycle Event** | 42010 | regular (append-only) |
| Node current status (dashboard read) | Custom: **Node State Pointer** | 38110 | addressable (`d`=branch) |
| Run/iteration accounting + cost | Custom: **Run Accounting Event** | 42020 | regular (append-only) |
| Radio-derived subtree aggregate | Custom: **Subgraph Digest** | 42030 | regular (append-only) |
| Approval request (`requires_approval` step) | Custom: **Approval Request** | 42040 | regular (append-only) |
| Approval verdict | Custom: **Approval Verdict** | 42041 | regular (append-only, `e`-tags the request) |
| Template registration (new version) | Custom: **Template Version** | 42050 | regular (append-only, one event per version) |
| Template "current version" pointer | Custom: **Template Pointer** | 38150 | addressable (`d`=template name) |
| Owner attestation | Not ours: Buzz draft **NIP-OA**, used as-is (DESIGN.md §1 names it core-usable) | per NIP-OA | presumed addressable — verify upstream |

Eight Lindenmayer custom kinds total, all in two Buzz-adjacent blocks chosen to
avoid its documented allocations (see "Numbering" below): `420xx` for
append-only history, `381xx` for addressable pointers. Everything else rides
standard NIPs already fit for purpose — no shoehorning.

## 1. Telemetry inventory → mapping

The task lists seven telemetry categories the bridge emits. Radio messages
themselves are already resolved by DESIGN.md §1 (NIP-29); reactions/saves are
this document's own extension of that mapping, included for completeness
since they're part of the same radio surface (`fractal radio react/save`,
platforms.md §1.4).

### 1.1 Radio (messages, reactions, saves) — standard NIPs, no custom kind

- **Messages** → NIP-29 kind 9 (group chat message), channel = the node's
  branch-bound room (already adopted). Lindenmayer-specific structure
  (`priority` 0–10, `subject`) rides as extra tags on the same kind-9 event —
  NIP-01 clients ignore unknown tags safely, so this stays standard-NIP-first:
  a plain Nostr client renders it as a chat message; a Lindenmayer-aware
  client additionally sorts by priority. No custom kind needed; the tag
  vocabulary is documented per the convention in §4.
- **Reactions** (`fractal radio react <uuid> +/-`) → NIP-25 kind 7, `content`
  = `+`/`-`, `e` tag = the reacted-to kind-9 event id. Direct fit, no
  extension needed.
- **Saves** (`fractal radio save`, the cross-iteration action queue) → NIP-51
  generic list (kind 30001, `d`=`saved`), owned by the *reading* node's
  pubkey, `e`-tagging saved message ids. Addressable is correct here — "my
  current saved set" is single latest-value state, not history; unsave is a
  list-membership removal, i.e. a new addressable event replacing the old,
  which is exactly parameterized-replaceable semantics.

### 1.2 Node lifecycle — custom kind

Node status transitions (`active`/`paused`/`completed`/`exited`/`stopped`,
platforms.md §1.3) are a state machine with history, emitted only by
**persistent** nodes (DESIGN.md §2 — ephemeral workers stay anonymous inside
their subgraph and never get an npub, so they never author lifecycle events
directly; their existence is visible only via their parent's aggregates, see
§1.4 below).

No standard NIP fits: this isn't a text note (NIP-01), a group message
(NIP-29 — it's not conversational, it's structured state), or a git event
(NIP-34 — a node isn't a git ref). Custom kind required.

### 1.3 Run/iteration/step accounting + cost records — custom kind, aggregated

Fractal's `steps` table (platforms.md §1.4) is per-step granular: agent,
model, session, cost, approved, exit_code, timestamps. Publishing at that
grain would leak subgraph detail upward by default, violating DESIGN.md §6
principle 1 (aggregates flow up, details stay in the subgraph — privacy is a
default). So the mapping is deliberately lossy: **one event per run (or per
iteration where a run spans many), never per step**, carrying rolled-up cost
and duration only. Step-level detail stays in Fractal's local SQLite, exactly
where §6 principle 2 (no new storage systems) says the source of truth
belongs; it only leaves the subgraph if a node explicitly opts into
transcript publication (the per-subgraph parameter DESIGN.md §7 already
covers) — that's a separate concern from this taxonomy.

No standard NIP fits (this is accounting telemetry, not a note/reaction/git
event). Custom kind required.

### 1.4 Radio-derived aggregates — custom kind

This is the mechanism that makes DESIGN.md §5's structural claim literally
true: "the aggregates-up privacy default is structurally enforced by the
one-hop messaging topology" only holds if persistent nodes actually publish
something aggregate-shaped to their own outbox for the parent to see.
Individual radio messages (§1.1) are too fine-grained and conversational for
this; a dashboard consuming a subtree's health needs a periodic rollup: child
count, active/exited/stuck breakdown, rolled-up cost across the subtree,
notable events. This is also where ephemeral-worker existence surfaces
(§1.2) — never as their own lifecycle events, only folded into their
persistent parent's digest counts.

No standard NIP fits. Custom kind required.

### 1.5 Approval requests/verdicts — custom kind, deliberately not NIP-34/Buzz's merge-approval kind

DESIGN.md §1 is explicit: "Fractal `requires_approval` steps surface as
signed approval events (core); enforcement of approval-gated merges via
buzz-protect is Buzz-layer." Two different things are easy to conflate here,
and the taxonomy has to keep them apart:

- **Buzz's kind 46011** (platforms.md §2.3: "merges can require N signed
  approval events, kind 46011") is Buzz's own git-merge-gate mechanism,
  enforced relay-side by `buzz-protect`. That's Buzz-layer per the
  draft-dependency rule — core cannot depend on it, because the dependency
  would be on relay-side *enforcement*, not just schema-on-the-wire.
- **Fractal's `requires_approval` step gate** (a parent approving a child's
  step before it proceeds, platforms.md §1.3) is a distinct, Fractal-native
  concept with no necessary relationship to git merges at all — many
  approval-gated steps never touch a merge. This needs its *own* kind,
  independent of whatever Buzz does with kind 46011.

Two events, not one, because DESIGN.md §4 needs the full chain:
"rejection → revision → acceptance chains, already recorded as threaded
signed events, yield natural preference pairs." A single replaceable
"approval status" event would overwrite that chain; append-only regular
events, verdict `e`-tagging request, preserve it.

No standard NIP fits (NIP-25 reactions are too thin — no rationale field,
no revision threading semantics). Custom kind required.

### 1.6 Template registration/versioning — custom kind, answers DESIGN.md §8

This is explicitly an open question ("Template registration mechanics: kind
numbers, versioning/replace semantics ... template inheritance, and what
exactly an eval attaches to," §8). Recommendation:

- Every registered version is its **own immutable event** (append-only,
  never replaced) — DESIGN.md §3 requires versions to be "diffable"; you
  can't diff against a value a replaceable event already overwrote. A
  template's full version history is the set of all such events sharing a
  `template_name` (`d`-like) tag, ordered by `created_at`.
- **Inheritance** (§8's open sub-question) is a tag on the version event
  pointing at the parent template version's event id (`e` tag, marker
  `inherit`) — makes inheritance chains queryable by any Nostr client via
  ordinary tag filters, no Lindenmayer-specific indexing needed.
- **"What an eval attaches to"** (§8): the anchor is the version event's id.
  This document does not design the evals pillar (explicitly future work per
  §8) but the Template Version kind's `e`-taggability is sufficient anchor
  for whatever eval-result kind that future work defines — noted here so the
  evals design doesn't have to re-derive it.
- A **separate addressable pointer** resolves "what's the current/default
  version of template X" in one query instead of walking full history —
  see §2 for why this needs to be a distinct kind from the version events
  themselves.

### 1.7 Owner attestation — not a Lindenmayer kind at all

DESIGN.md §1 names this explicitly: "Node identity via NIP-OA owner
attestation... the attestation chain is core (verifiable anywhere)... NIP-OA
attestation events qualify [as schema-on-wire]." So Lindenmayer does not mint
its own kind here — it uses NIP-OA's kind directly, because the draft's
event *shape* is exactly what's needed and re-deriving an equivalent custom
kind would just be NIP-OA with extra steps. What Lindenmayer *does* need to
do, per the draft-dependency rule, is restate NIP-OA's schema in its own docs
(§3 below) so a future draft revision can't silently invalidate historical
attestation events' meaning. This document does not have upstream network
access to confirm NIP-OA's current kind number and exact tag set (platforms.md
names the draft but not its kind number) — flagged as a verification item for
whoever implements this: pull `docs/nips/OA.md` from `block/buzz` before
wiring attestation, and paste its current kind number + tag schema into this
project's own restatement (§4's registry).

## 2. Custom-kind design

### 2.0 Placement: why two blocks, not one

Nostr's kind-range semantics (per NIP-01, confirmed against
`nostr-protocol/nips`) are behavioral, not just organizational:

| Range | Behavior |
|---|---|
| 0–9999 (minus the explicit exceptions below) | regular — relay stores every one, immutable history |
| 10000–19999 | replaceable — only the latest per (pubkey, kind) is kept |
| 20000–29999 | ephemeral — never stored at all |
| 30000–39999 | addressable / parameterized-replaceable — latest per (pubkey, kind, `d` tag) is kept |

Any kind number ≥ 40000, including Buzz's whole 40000–49999 custom
convention, falls **outside** every range NIP-01 defines behavior for. Per
NIP-01's own default ("events with a kind other than the specified ranges are
regarded as regular events"), a compliant relay treats everything in
40000–49999 as plain append-only regular storage — Buzz's replaceable-ish
behaviors for its own kinds in that band (if any) would be Buzz-relay-side
convention, not something a plain Nostr relay honors. That matters directly
for this project's portability goal (DESIGN.md §1: "consumable by any
compliant relay/client"):

- **History kinds** (lifecycle transitions, run accounting, digests,
  approval request/verdict, template versions) want exactly this default —
  append-only, immutable, every event kept. They belong in the **420xx**
  block: numerically adjacent to Buzz's own custom convention (signals
  "this is a Lindenmayer application kind" to anyone skimming Buzz's
  40000–49999 docs) while sitting in unclaimed space relative to Buzz's
  documented allocations (43001 job requests, 45001/45003 forum, 46001–46012
  workflow execution including 46011 merge approval, per platforms.md §2.3).
- **Pointer/latest-value kinds** (node current status, template current
  version) genuinely need replace-on-write semantics that only the
  **standard** 30000–39999 addressable range guarantees on *any* relay — a
  plain relay has no idea 4XXXX should behave specially, but every compliant
  relay already knows how to collapse a 3XXXX + `d`-tag stream to latest-only.
  These go in the **381xx** block, clear of Buzz's own addressable kinds
  (30617 git repo announcements, 30000–30009 NIP-51 sets, 30023 long-form,
  39000–39002 NIP-29 group metadata).

This is the concrete resolution of DESIGN.md §8's "reason about replaceable
vs append-only semantics per event type" instruction: the axis that decides
placement isn't "is this Lindenmayer's own concept" (both blocks are), it's
"does a plain relay need to collapse this to one row, or keep every row."

**Numbering caveat.** These are proposed numbers, not registered ones. Buzz
defines "81 kinds... in `buzz-core/src/kind.rs`" (platforms.md §2.3) that this
document did not have access to enumerate exhaustively — before
implementation, the `core` node should diff these eight proposals against
that file (and against any kinds NIP-AM/NIP-AO/other Buzz drafts claim in the
same numeric neighborhood) and shift any collision. The *blocks* (420xx for
history, 381xx for pointers) and the *reasoning* for the split are the
durable part of this recommendation; the exact two- and three-digit suffixes
are cheap to renumber.

### 2.1 Node Lifecycle Event — kind 42010 (regular)

One event per status transition. Emitted by the persistent node's own key.

| Tag | Meaning | Required? |
|---|---|---|
| `d` (no — this is regular, not addressable) | — | — |
| `branch` | dotted Fractal branch name of the node | yes |
| `status` | new status (`active`/`paused`/`completed`/`exited`/`stopped`, etc.) | yes |
| `p` | parent node's pubkey, if the parent is itself a persistent (keyed) node | no — omitted when the parent has no npub |
| `run` | run id this transition occurred within | yes |
| `e` | previous lifecycle event id for this node (chains history without relying on relay-side ordering guarantees) | no, recommended |

Content: `{"reason": "<free text, e.g. budget exhausted / user kill>"}`.
Kept minimal — the tags carry everything queryable.

### 2.2 Node State Pointer — kind 38110 (addressable, `d` = branch name)

Latest-known snapshot, one per node, overwritten on every meaningful state
change so a dashboard resolves "current state of node X" in a single
addressable-kind query instead of replaying history.

| Tag | Meaning | Required? |
|---|---|---|
| `d` | branch name (the addressable key) | yes |
| `status` | current status | yes |
| `run` / `iter` | current run.iter label | yes |

Content: `{"cost_shadow_usd": <number>, "cost_cap_usd": <number>,
"last_lifecycle_event": "<event id, see 2.1>"}`. The pointer is a
convenience read-index over 2.1's history, not a second source of truth —
it's always reconstructable by taking the latest 42010 event per branch, so
losing it (e.g. on a relay that doesn't support addressable collapsing)
degrades to "replay history," never data loss.

### 2.3 Run Accounting Event — kind 42020 (regular)

One per completed run (platforms.md §1.3: a run = one `fractal node start`).
Deliberately excludes step-level rows — see §1.3's privacy reasoning.

| Tag | Meaning | Required? |
|---|---|---|
| `branch` | node branch | yes |
| `run` | run id | yes |
| `template` | template version event id that spawned this node (see §2.6) | no — only when the node was template-spawned |

Content: `{"iter_count": <int>, "cost_shadow_usd": <number>,
"duration_s": <number>, "exit_status": "<completed/exited/killed>"}`. Shadow
cost per DESIGN.md §6's shadow-cost principle — never presented as real
spend; downstream consumers must carry that label through.

### 2.4 Subgraph Digest — kind 42030 (regular)

Periodic, published by a persistent node about its own subtree — the event
that makes §5's "aggregates-up is structurally enforced by one-hop
subscription" claim actually true in practice, not just in topology.

| Tag | Meaning | Required? |
|---|---|---|
| `branch` | the publishing (persistent) node's branch | yes |
| `period_start` / `period_end` | ISO8601 window this digest covers | yes |

Content: `{"child_count": <int>, "active": <int>, "exited": <int>,
"completed": <int>, "stuck_flagged": <int>, "subtree_cost_shadow_usd":
<number>}`. No per-child breakdown by name/content in the default digest —
that would re-leak the detail §6.1 keeps in the subgraph; a parent that needs
more must ask (radio), not read it off the wire by default.

### 2.5 Approval Request / Approval Verdict — kinds 42040 / 42041 (regular)

| Tag (Request, 42040) | Meaning | Required? |
|---|---|---|
| `branch` | requesting node | yes |
| `run` / `iter` / `step` | the gated step's coordinates | yes |
| `p` | approver's pubkey (parent node) | yes |

Request content: `{"step_name": "<from steps/NN-NAME.md>", "summary": "<what
this step would do>"}`.

| Tag (Verdict, 42041) | Meaning | Required? |
|---|---|---|
| `e` | the Approval Request event id being answered | yes |
| `verdict` | `approve` / `reject` | yes |

Verdict content: `{"rationale": "<free text>"}`. Two kinds, not one
replaceable kind, so that reject→revise→re-request→approve chains stay fully
threaded — this is the exact shape DESIGN.md §4 needs for preference-pair
extraction.

### 2.6 Template Version — kind 42050 (regular, one event per version)

| Tag | Meaning | Required? |
|---|---|---|
| `template_name` | the template's stable name (the key pointer events key off) | yes |
| `version` | monotonic version identifier for this template name | yes |
| `e` (marker `inherit`) | parent template version event id, if this version extends another | no |
| `git_ref` | commit/tag in the templates' git history, if template content is git-hosted (system prompts/skills/files/references, DESIGN.md §3) rather than inlined | no |

Content: `{"summary": "<what changed this version>"}`. Kept thin — the
template's actual content (system prompts, skills, files) is not duplicated
into the event; `git_ref` is the pointer to it, keeping this a registry
entry, not a second copy of the artifact (consistent with §6 principle 2, no
new storage systems).

### 2.7 Template Pointer — kind 38150 (addressable, `d` = template name)

| Tag | Meaning | Required? |
|---|---|---|
| `d` | template name (the addressable key) | yes |
| `e` | the current/default Template Version event id | yes |

Content: empty or `{}` — this kind is pure indirection, resolved the same way
as 2.2's Node State Pointer and for the same reason (O(1) "what's current"
instead of walking history).

## 3. NIP-AM/NIP-AO alignment

Buzz's drafts cover overlapping ground at the field-semantics level, not the
event-shape level, so alignment means matching *vocabulary*, not reusing
*kinds*:

- **NIP-AM (Agent Turn Metrics)** covers per-turn metrics for a Buzz agent
  (tokens, cost, duration, model — inferred from name and Buzz's own
  turn/session framing, platforms.md §2.3–2.4). Fractal's Run Accounting
  event (§2.3) covers the same conceptual ground at the run/iteration grain
  rather than per-turn, because Fractal's native unit of "one model
  invocation" is a *step*, not exposed at that grain here (§1.3's privacy
  reasoning). Where field names overlap in meaning — cost, duration, model —
  Run Accounting should use the **same field names NIP-AM uses**, so a
  client that already speaks NIP-AM's vocabulary can read Lindenmayer's
  events without a translation table, even though the kind numbers and
  granularity differ.
- **NIP-AO (Agent Observability)** covers lifecycle/observability events for
  an agent — the natural counterpart to Fractal's own `on_<event>` hook set
  (`on_call`, `on_spawn`, `on_action`, `on_session`, `on_cost`, `on_budget`,
  `on_error`, `on_preflight` — platforms.md §1.5). Node Lifecycle (§2.1) and
  Approval Request/Verdict (§2.5) are Lindenmayer's versions of that same
  observability surface, sourced from Fractal's hooks rather than a Buzz
  agent's own instrumentation.
- **What we restate, concretely.** Per the draft-dependency rule (DESIGN.md
  §1: "the schemas are restated in Lindenmayer's own kind documentation so
  they survive draft churn"), the per-kind registry entries this document's
  §4 proposes for 42010/42020/42040/42041 must each include a short "NIP-AM/AO
  correspondence" note pinning which of our fields is semantically the same
  thing as which NIP-AM/AO field, as of the draft version consulted at
  write-time. If NIP-AM/AO later renames or restructures those fields, our
  historical events don't change meaning — they were never literally NIP-AM/AO
  events, only informed by them — but new events should re-sync the
  correspondence note so the vocabulary doesn't quietly drift apart for no
  reason.
- **This document's limitation.** Web access here was sufficient to confirm
  Nostr's standard kind-range table (nostr-protocol/nips) but did not include
  fetching the actual NIP-AM/NIP-AO draft text from `block/buzz`'s
  `docs/nips/`, so the field-level correspondence above is reasoned from
  platforms.md's descriptions and Fractal's documented hook/accounting
  surfaces, not a line-by-line diff against the drafts. Whoever writes the
  §4 registry entries should pull `docs/nips/AM.md` and `docs/nips/AO.md`
  from the Buzz repo first and correct any mismatch this document guessed at.

## 4. Documentation convention

Recommend a **NIP-style, one-file-per-kind registry**, so a Nostr client
author can implement a reader from this project's docs alone — no Buzz
source, no Lindenmayer source, same posture Nostr's own NIPs repo takes.

Proposed layout (not created by this document — the architect or `core`
owns actually standing it up):

```
docs/research/relay-integration/
├── README.md                  # architect-owned aggregate (out of scope here)
├── event-kinds.md             # this file — the taxonomy + reasoning
├── degradation.md             # sibling — plain-relay degradation behavior
└── kinds/                     # proposed: the actual portable registry
    ├── 42010-node-lifecycle.md
    ├── 38110-node-state-pointer.md
    ├── 42020-run-accounting.md
    ├── 42030-subgraph-digest.md
    ├── 42040-approval-request.md
    ├── 42041-approval-verdict.md
    ├── 42050-template-version.md
    ├── 38150-template-pointer.md
    └── nip-oa-attestation.md  # our restatement of the upstream draft, per §1.7/§3
```

Each `kinds/<kind>.md` should be self-contained in the way a NIP is
self-contained (mirroring `nostr-protocol/nips`' own per-NIP format):
title + kind number + range rationale (history vs pointer, per §2.0) +
status (draft/stable, since these are proposals until `core` implements them)
+ full tag table + content JSON schema + one worked example event +, where
relevant, the NIP-AM/AO correspondence note from §3. That last field is what
makes the draft-dependency rule operational rather than aspirational: it's
the concrete place draft alignment gets written down per kind, not just
asserted once in this overview.

This document (`event-kinds.md`) is the taxonomy and the reasoning behind it;
the `kinds/` registry it proposes is the implementation-grade per-kind spec.
Keeping them separate means this file stays readable as a decision record
even after the registry grows past a skim-able size.
