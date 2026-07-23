# Degradation analysis: Lindenmayer on a plain relay

Scope: what still works, degrades, or disappears if Lindenmayer's Nostr-core
output (DESIGN.md §1) is read by a **plain NIP-29 relay** — a strfry- or
khatru-class relay implementing NIP-01 (wire), NIP-29 (group channels), and
NIP-42 (auth), with no Buzz process attached. Ground truth: `docs/DESIGN.md`
§1/§2/§4/§6, `docs/platforms.md` §2. NIP-29/NIP-42 exact text fetched from
the nostr-protocol/nips repo (cited inline); claims about strfry/khatru's
actual implementation behavior (vs. bare spec text) are reasoned, not
independently verified against their source — flagged where load-bearing.

## Executive summary

Everything Lindenmayer *records* survives a plain relay: core events are
standard-shaped or self-documented custom kinds, so history is never at
risk. What degrades is everything that depends on relay-side **enforcement**
— access gating, revocation, approval-gated merges — because NIP-29 leaves
enforcement of its own `private`/`restricted` flags as relay-implementation
policy, not a spec mandate, and NIP-42 supplies only an auth handshake, not
an authorization model. Concretely: telemetry, provenance, and approval
*records* are fully portable; approval *enforcement*, instant identity
revocation, and the human-facing surfaces are Buzz-only. The one place this
bites hardest is privacy (§3 below): Lindenmayer's aggregates-up default
assumes channel membership is a real access gate, and on a plain relay that
gate is real only if the operator's specific NIP-29 implementation chooses
to enforce the `private` flag server-side — which is common practice, not a
protocol guarantee.

Recommendation in one line: the `core` node should write to NIP-01/29/42 and
assume nothing more; it should treat "does this relay enforce `private`
group reads" as a **relay capability the bridge must probe or declare**, not
an assumption baked into the privacy design — because that single fact is
what silently downgrades "aggregates flow up, details stay in the subgraph"
from a structural guarantee to a courtesy.

## 1. Feature-by-feature degradation matrix

| Flow | Plain NIP-29 relay | Degrades to | Buzz-only |
|---|---|---|---|
| Telemetry publication | Full — standard/custom kinds store and query normally | — | Desktop dashboards, agent directory UI |
| Subgraph→channel mapping & membership gating | Channel exists, membership/roles tracked (kinds 9000–9008, 39000–39002) | Read-gating on `private` groups is relay-policy, not spec-mandated (see §3) | "Branch as room" UX binding, hosted git browsing at the channel URL |
| Approvals | Approval events store, are signed, are queryable/threaded | Enforcement (blocking a merge until approved) is gone — approval becomes a record, not a gate | `buzz-protect` merge enforcement, workflow `request_approval` gates |
| Template registry | Registration events store and version if authored as replaceable/parameterized-replaceable kinds (mechanics open, DESIGN §8) | — | Agent directory browsing/search UI |
| Identity / attestation | Attestation events store and are independently verifiable by any client (signature + NIP-05 lookup) | Revocation becomes a fact in the log, not an access change — readers/bridge must check it themselves (see §2) | Instant relay-side access removal on revocation (NIP-OA enforcement) |
| Provenance / training corpus | Full event log, fully attested, fully queryable | Labeling still works (approval events are self-contained labels); trust in "safe to train on" shifts from relay-guaranteed to pipeline-verified (see §2) | — (this flow was never relay-enforcement-dependent) |
| History-access grants | Grant/revocation events store as signed, expiring, revocable events | Expiry/revocation enforcement is extraction-pipeline responsibility, not relay-enforced (true even on Buzz today — mechanics open, DESIGN §8) | — |
| Human surfaces (Evergreen node's steering/review) | Any NIP-29 client can read/write the channels | Desktop app UX, inbox/agent-directory browsing, huddles are absent | Buzz desktop app, Home feed, Agents directory, huddles |

Reading the matrix: the "Buzz-only" column is almost entirely **experience**
(a UI, a merge gate, an instant-revocation convenience) — DESIGN.md's own
framing in §1 ("losing this layer degrades experience, never history")
holds up under this analysis with one caveat: approval and membership
*enforcement* are not just experience, they're the mechanisms that make
history trustworthy in real time. A plain relay keeps the history
recoverable and auditable after the fact; it does not keep it enforced
while work is happening. That distinction is the throughline of §2 and §3.

### Per-row detail

**Telemetry publication.** No degradation. Standard NIP-01 wire format plus
Lindenmayer's self-documented custom kinds (draft-dependency rule, §1) are
storage-and-query complete on any compliant relay. This is the layering
paying off exactly as designed.

**Subgraph→channel mapping & membership gating.** The mapping itself
(subgraph ↔ NIP-29 `h`-tagged group) is standard and works. Write-side
membership is enforced by any real NIP-29 implementation — moderation
events (kind 9000 `put-user`, 9001 `remove-user`, etc.) are checked against
admin roles in kind 39003 before being honored, and joins are rejected for
non-preauthorized users when a group is `closed`. What's *not* spec-mandated
is read-side gating (the `private` flag) — see §3, this is the crux of the
privacy analysis and is *not* the same fact as write-side moderation
authorization, which is solid.

**Approvals.** DESIGN §1 already separates this correctly: the signed
approval event is core, `buzz-protect` enforcement is Buzz-layer. On a
plain relay, `requires_approval` steps still surface as signed events, and
anyone can read the approval/rejection history. What's gone is the
*gate* — nothing stops a merge from proceeding without a matching approval
event unless something downstream (a bridge-side pre-merge check, or a
human process) enforces it. This is a real capability loss for live
governance, not merely UX: "human governance is explicit and traceable"
(§6.4) is satisfied (traceable), but the veto-by-default mechanism (§6.4)
needs its own enforcement point when Buzz isn't the one blocking the merge.

**Template registry.** Registration-as-signed-events is core and portable
regardless of relay. The open question in DESIGN §8 (kind numbers,
replace semantics, inheritance) is orthogonal to Buzz-dependency — it needs
resolving either way. Nothing here is Buzz-only except the browsing UI.

**Identity/attestation.** See §2 — this is the deepest question in the
brief, treated on its own below.

**Provenance/training corpus.** See §2's training-corpus sub-question.

**History-access grants.** Already designed as signed/revocable/expiring
events independent of relay (DESIGN §4) — this flow was never relying on
Buzz enforcement in the first place; the open mechanics (§8) are the same
open questions on any relay. No new degradation from being Buzz-less; the
existing open-question risk (pipelines must self-enforce expiry) is
identical whether or not Buzz is present.

**Human surfaces.** Full loss of the packaged desktop experience, Home
feed, Agents directory, huddles. Any NIP-29-speaking client (`nak`, Chachi,
0xchat per platforms.md §2.5) can read/write the same channels, so the
Evergreen Node's *functions* (steer, review, query) are never blocked —
only the polished surface for doing them is gone.

## 2. Identity and attestation without NIP-OA enforcement

**Who verifies, and when.** The attestation chain (node keypair ↔
responsible human, per NIP-OA-shaped events) is core: any client can fetch
the attestation event, check the signature, and check whether a
newer/revoking event supersedes it. On a plain relay there is no
relay-side step that removes a revoked node's access — verification moves
entirely to whoever is about to *act* on an event:

- **Client-side read filtering.** A reader (human or downstream pipeline)
  checks attestation validity before trusting an event's provenance. This
  is necessary but not sufficient for anything with a real-time stake
  (e.g. "don't let a revoked node's output influence a live decision"),
  because a slow or absent reader lets stale trust persist.
- **Bridge-side pre-publish checks.** The bridge, as the one component
  that controls what gets published on behalf of a node, is the only
  place that can act *before* an event exists: refuse to sign/relay a new
  event for a node whose attestation has been revoked. This is the
  practical minimum-viable enforcement point, because it requires no
  relay cooperation and closes the gap for new activity (it cannot
  retract what's already stored — nothing on a plain relay can, deletion
  is client-cooperative under NIP-09 at best).

**Minimum viable enforcement story:** bridge refuses to publish for
revoked keys (stops new bad activity at the source, requires only that the
bridge itself stay current on attestation state) **plus** readers filter by
attestation validity at query time (bounds trust in what's already stored,
requires no relay support). Together these reproduce Buzz's outcome
(revoked identity stops mattering) with higher latency (revocation
propagation depends on the bridge's and readers' polling/subscription
cadence, not an instant relay-side cutoff) and weaker guarantees against a
compromised or stale bridge (nothing stops a *different* publishing path
from ignoring revocation — Buzz's guarantee is structural, this
reconstruction is procedural).

**Training-corpus trust model (§4).** DESIGN §4 treats attested, versioned
history as what makes training safe ("unsigned telemetry can be
dashboarded, but only attested, versioned history can be safely trained
on"). Unenforced attestation does not break this — it only moves the
safety check from "the relay already excluded revoked-key events" to "the
extraction pipeline must apply the same attestation-validity filter Buzz
would have applied at read time." A corpus built by an extraction pipeline
that checks attestation validity (and history-grant validity, per §4's
consent mechanism) at extraction time is exactly as safe as one built from
a Buzz-gated feed — the filtering just moved from the relay to the
pipeline. The risk case is a pipeline that *skips* this filter because it
assumes the relay already did it; that assumption is the one thing this
document argues must not be made. Practically: label corpus rows with the
attestation state *at extraction time*, not at event-creation time, since
revocation can postdate the original event.

## 3. Privacy on a plain relay

DESIGN §1 states channel membership is the only access gate; §6.1 requires
that aggregates flow up while details stay in the subgraph. The load-bearing
question is whether "channel membership" is actually enforced by the relay
or only checked by well-behaved clients.

**What the NIP-29 spec text actually says (fetched from
nostr-protocol/nips):** the `private` group-metadata flag means "only
members can read"; the `restricted` flag means "only members can write."
The spec's own language is permissive on read enforcement — relays
"should" honor `private`, but this is not phrased as a mandatory
server-side rejection the way NIP-01 mandates signature verification.
Write-side moderation, by contrast, reads as a real requirement: role
checks against the admin-list kind (39003-class) before honoring
`put-user`/`remove-user`/`edit-metadata` events. **Practical reading**
(reasoned from common strfry/khatru-class implementation practice, not
independently confirmed against their source in this pass): mainstream
NIP-29 relay implementations *do* enforce `private`-flagged read-gating
server-side — filtering `REQ` responses by the requester's NIP-42-
authenticated pubkey against group membership — because that enforcement is
the entire reason the `private` flag exists; a relay that stored it as
inert metadata would make the flag meaningless. Treat this as
high-confidence but implementation-dependent, not a protocol guarantee: a
relay operator could ship "NIP-29 compliant" and only enforce the
mandatory parts (moderation authorization), leaving `private` unenforced.

**What this means concretely:**

- **Holds without Buzz, if the relay enforces `private`:** subgraph
  channels marked `private` are genuinely relay-gated. A non-member
  cannot `REQ` the raw events regardless of client behavior. This is the
  same mechanism Buzz itself uses (NIP-29 native) — Buzz's "membership
  gating" and a well-configured plain relay's are the same enforcement,
  just without Buzz's UI and instant-revocation convenience on top.
- **Does not hold, and degrades to client-side filtering, if the relay
  does not enforce `private`:** any client can `REQ` the channel's raw
  events; "membership" becomes a norm respected by cooperating clients,
  not a wall. This is the failure mode that would silently violate §6.1 —
  aggregates-up would be enforced only by which clients *choose* to
  subscribe one hop, not by an actual boundary. NIP-42 does not close this
  gap on its own: it defines the auth handshake only (challenge/response,
  recency check, relay-URL binding) — it explicitly leaves authorization
  policy (who gets to see what, once authenticated) to the relay's own
  logic. Authenticating a reader tells the relay *who* is asking; it says
  nothing about whether the relay then checks that identity against group
  membership before answering.
- **What genuinely stays in the subgraph, either way:** work that never
  gets published at all (radio's one-hop subscription topology, §5,
  independent of relay choice — a channel's raw traffic literally isn't
  sent to a non-subscribing parent by the messaging layer itself, before
  any relay-level access question even arises). This is a stronger
  guarantee than relay-side group privacy because it doesn't depend on
  relay configuration at all.

**Requirement for the aggregates-up default to genuinely hold on a given
relay:** the relay must (a) support NIP-42 auth so it can identify readers,
and (b) actually enforce `private`/membership checks on `REQ` for groups so
flagged — not just store the flag. Since (b) is relay-implementation
policy rather than a protocol guarantee, Lindenmayer cannot assume it from
"NIP-29 compliant" alone; it is a fact about a *specific* relay deployment
that the bridge should be able to check or that an operator should have to
attest to (see recommendation).

## 4. Recommendation

**Minimum relay contract `core` may assume:** NIP-01 (wire/signing),
NIP-29 (group channels, including its 9000-series moderation and
39000-series metadata kinds), NIP-42 (auth). This is exactly the plain
relay class this document analyzed, and it is sufficient for every core
flow in §1 to store, version, and remain queryable/attestable. Do not
assume NIP-34 git hosting, Blossom media, or any Buzz custom kind's
relay-side behavior as a baseline — those are additive, not required.

**Acceptable degradations (ship without hard-blocking on them):**

- Approval-gated merge *enforcement* — keep the signed event as the
  source of truth; let the merge-gate mechanism be a bridge- or
  process-level concern layered on top, not a relay assumption. Buzz's
  `buzz-protect` is one such mechanism; a plain-relay deployment needs an
  equivalent (even if manual) but does not need Buzz specifically.
- Instant identity revocation — the bridge-refuses-to-publish +
  reader-filters-by-attestation-validity combination (§2) is an acceptable
  default; document its latency/trust gap rather than pretending it
  matches Buzz's instant cutoff.
- Packaged human surfaces (desktop app, Agents directory, Home feed,
  huddles) — treat as pure UX; any NIP-29 client is a valid substitute for
  functionality, never a required dependency for correctness.

**Worth a documented hard dependency on Buzz specifically (not just "some
relay with equivalent features"):** relay-enforced `private`-group read
gating for any channel carrying subgraph detail the design intends to keep
non-aggregate. This is the one degradation that isn't merely cosmetic — if
unenforced, it silently breaks the aggregates-up privacy default (§6.1)
rather than degrading gracefully. The recommendation is not "require Buzz"
per se, but: **the bridge must treat relay-enforced private-group reads as
a capability to verify per deployment, not infer from NIP-29 compliance**
— e.g. a startup/config-time check or an explicit operator attestation of
"this relay enforces `private`" before trusting a channel's privacy
boundary. Buzz satisfies this by construction (NIP-29 native, described as
enforcing membership as the access gate in platforms.md §2.3); a plain
relay may or may not, and the design should fail loud (warn / refuse to
mark a channel private) rather than fail silent when it can't confirm
enforcement.
