# Evergreen design pass — research aggregate

Aggregate for the evergreen-component design pass (root directive 7803C28A).
Three research children ran narrow contracts in parallel; this file carries
the findings that mattered and the architect's rulings on them. Full detail
stays in each study, and the resulting platform truth lives in `DESIGN.md` —
§1 (Buzz cross-post rules), §3 (template registration, model policy), §5.1
(evergreen v1), §5.2 (session continuity), and the decision log.

Child studies, each owned by its node:

- `compaction.md` — compaction observability, harvester boundary, task
  anchors, Nostr derived-view prior art (`main.platform_architect.compaction`).
- `inventory.md` — requirements inventory from `tree/root/CONTEXT.md`,
  classified by data source, mapped to §5's four capabilities
  (`main.platform_architect.evergreen_inv`).
- `buzz-surface.md` — Buzz primitives, ingest constraints, identity, per-kind
  cross-post mapping (`main.platform_architect.buzz_surface`).

## 1. Compaction-to-task mapping — §8 closed

**What the research established.** Per-request usage records survive a
compaction; conversational records do not. Fractal's `iters` table carries the
Claude Code `session` UUID, so a session id resolves to iter → run → step.
Nostr's own idiom for "this event is derived from that one" is a tag marker,
NIP-10-style. Three candidate shapes were weighed: a distinct compaction
event, tags on the existing 42010 lifecycle event, and a git-tracked doc-only
convention.

**Where the study was wrong.** It reported that "no compaction record exists
today" and built its recommendation around asking Claude Code to add one.
Architect verification against this tree's own 36 transcripts found the
opposite: the harness **already writes** an append-only `system` record
carrying a `compactMetadata` object — `trigger`, `preTokens`, `postTokens`,
`durationMs`, `cumulativeDroppedTokens`, and preserved-segment identifiers —
alongside a `user` record flagged `isCompactSummary`. The premise was false,
and the upstream dependency it implied never needed incurring.

**Ruling.** The distinct-event shape is adopted: kind **42060**, task
coordinates in tags, an `e` tag with a `summary-of` marker pointing at the
step's own lifecycle event, metrics and a summary hash in content. The
doc-only variant was rejected on privacy and discoverability; the
tags-on-42010 variant on retrofit and contract pollution.

**Detection reads the marker.** `preTokens`/`postTokens` are exactly the
metrics 42060 reports, so no inference is required and no upstream change is
requested. Had the premise held, the recommendation would still have been
rejected — the rule that governs the buzz kind-allowlist contribution applies
equally here: a parallel track may be endorsed, but *no design surface may
depend on its acceptance*. As it happens the question is moot.

**The fallback, and a measured correction to it.** For transcripts lacking a
marker, total prompt size across a session grows and drops sharply at a
compaction. The usable form is **three-term** — `input_tokens` +
`cache_read_input_tokens` + `cache_creation_input_tokens`. The two-term form
(dropping cache creation) tracks *cache turnover* rather than context: as the
prompt cache expires and refills, `cache_read` collapses to near zero while
`cache_creation` absorbs the prompt, and the series shows a large false drop.
Measured over this tree's four largest sessions, the two-term form fired 4–6
times per session; the three-term form fired twice in total, in exactly the
two sessions carrying a `compactMetadata` marker — a 1:1 match.

Each 42060 event records which signal produced it in a `detection` tag —
`harness-marker` (attested) or `usage-discontinuity` (inferred) — so readers
grade the claim instead of trusting it (§6.5).

**Privacy, and a harvester-boundary extension.** Content carries metrics and a
summary *hash*, never summary text; the pointer resolves to the node's own step
event, so a child's compaction stays in its subgraph and only digests roll up
(§6.1). This matters more than it first appears: the harness writes the compact
summary *body* into the transcript, and `compactMetadata` itself carries
preserved-message UUID lists. The bridge adapter's boundary is therefore
extended to permit append-only structured metadata records while still barring
conversational structure — and the summary body specifically.

**Open, carried forward:** `core` re-runs the block/buzz collision check
before writing `docs/kinds/42060-*.md`. Nearest Buzz neighbour was 42000
@ 06e3d82, so 42060 is expected clear, but the check belongs to core.

## 2. Evergreen v1 — the read plane

**What the research established.** The handrolled prototype decomposes into 28
discrete requirements: **16 relay-derivable**, 7 fractal-derivable, 4
human-authored, 1 mixed. The relay is live with real tree history. Of the
relay-derivable 16, essentially none has a query surface: the bridge's reads
are embedded in publisher logic, and the registry reader covers template
metadata only. The fractal-derivable 7 are the opposite case — every one of
them already has a working Fractal CLI surface.

**Ruling: v1 is the read plane; Fractal's CLI remains the write plane.** v1
ships a query surface over the signed log plus a generator/maintainer of the
standing context surface, and no write path.

That asymmetry in the inventory is the whole argument. Every write-side "gap"
it names — radio-send UI, signal API, live-edit UI, node-spawn bridge — is a
wrapper around a Fractal capability that already works; wrapping adds a second
control path with no new capability, and an orchestration layer over the spawn
API drifts straight at §6.3. "Signal routing is Fractal CLI only" is the
boundary holding, not a defect. Meanwhile the read side is where the need is
real and nothing exists.

The v1 line through §5's four capabilities, and what stays out, is recorded in
`DESIGN.md` §5.1. v1 holds no local index — it reconstructs on demand,
extending relay-as-cursor and relay-as-registry to **relay-as-context**.

**An incidental finding worth keeping.** The inventory recorded the tree's
model policy as a requirement and captured it as "Orchestrator:Fable,
Review:Fable, Development:Haiku" — already stale by the time it was written,
in the same way the manifest body was. Two independent surfaces restating the
same tunable parameter both went stale. Hence the §3 rule: surfaces that
display the model policy read the live assignment rather than restate it, and
this is precisely the kind of requirement the generator exists to serve.

## 3. Buzz human surface v1

**What the research established.** Buzz's relay accepts a finite, exhaustively
matched kind set that excludes every Lindenmayer custom kind, and hard-rejects
any `created_at` beyond ±15 minutes — both re-verified at `daeaf7c`, matching
the findings that demoted Buzz from core-log carrier to human surface. NIP-OA
`auth` tags are parsed and verified on ingest but not relay-enforced; absence
degrades to "no verified owner" rather than rejection. Channel topology is
NIP-29 groups with membership as the gate.

**Ruling.** The v1 cross-post set is fixed in `DESIGN.md` §1: 42010 and 42020
into the subgraph channel as stream messages, 42040/42041 into an
approvals-inbox group, 42030 into the parent channel, and 38150 not surfaced.
Three corrections were applied to the study's recommendations.

**Rejected: 42050 → `KIND_AGENT_PROFILE` (10100).** Two independent grounds.
A template is the improvable asset (§3), not a node identity (§2), so
publishing versions as agent profiles conflates two distinct concepts. And
10100 is user-owned and globally scoped "like kind:0" — replaceable — so each
new version would clobber its predecessor, destroying exactly the diffable
version history §3 exists to guarantee. If templates ever surface in Buzz it
is as a stream message in a registry channel, and replaceability gets verified
first.

**Corrected: tag shape.** The proposed mapping embedded a JSON object as a tag
element (`["l", "lindenmayer:42010", {…}]`). NIP-01 tag elements are strings.
Flattened to `["e", "<source_id>", "", "lindenmayer-source"]` plus
`["source_kind", …]` and `["source_created_at", …]`, which also makes the
established dedup-by-reference rule concrete on the wire.

**Added: the audience invariant.** *A cross-post may never widen the audience
of its source event.* Channel membership is the only access gate, so posting a
subgraph event into a parent channel is a privacy widening; 42030 is the sole
kind eligible for the parent channel because it *is* the upward aggregate.
This resolves the study's open question about marking a radio aggregate's
privacy scope — structurally, rather than by inventing a scope tag.

**Added: forward-only.** Buzz gets no historical backfill. The drift gate
makes it infeasible and re-issuing old events with fresh timestamps would
misrepresent history; history lives on the Lindenmayer relay. This closes the
study's open question on archival cross-posting.

## What remains open

- **Kind 42060 collision check** — `core`'s to run before the registry entry
  is written (above).
- **Buzz agent-directory indexing** — how the directory filters and paginates
  is product-layer, and nothing in v1 depends on it.
- **Evals pillar** (§8) — untouched by this pass by design; the compaction
  ruling was kept deliberately clear of scores, verdicts, and quality labels.
- **Retention defaults, relay selection, history-grant mechanics** (§8) —
  out of scope for this pass, unchanged.
