---
name: evergreen_program
desc: Evergreen design pass — the four rulings that landed, and the verification lesson behind the compaction one.
created: 2026-07-23T21:40:30Z
updated: 2026-07-23T21:40:30Z
---

# evergreen_program

The evergreen design pass is closed. Three research children (compaction,
evergreen_inv, buzz_surface) delivered, merged, and are synthesized into
`docs/research/evergreen/README.md`. Four decisions landed in DESIGN.md, each
with a decision-log row naming its requester and verdict.

## What was decided

**Model-policy retiering — approve.** Tunes an economic parameter; no
review-bar principle touched. §3 rewritten from literal tiers to the shape
invariant (orchestrator writes work orders, cheaper tier executes, stronger
tier reviews) with tiers as a recorded parameter. §3 also now records
registration as live (dev-node v2, 42050 event `0f8d0910`, pin `c6696b7`).
§7: the decomposition doctrine rests on a *ratio* the new tiers preserve, so
it stands; only cap-sizing guidance went stale, and it awaits observed sonnet
burn rather than invented numbers. Root has been asked to send real figures
when two or three sonnet children have run.

**Compaction — §8 closed, now §5.2.** Kind 42060, task coordinates in tags,
`e`/`summary-of` pointer, metrics plus summary hash in content. See the
verification lesson below — the first version of this ruling was wrong.

**Evergreen v1 — the read plane.** Query surface over the signed log plus a
context-surface generator; no write path. Every write-side gap the inventory
named is a wrapper around a working Fractal capability, and wrapping adds a
second control path with no new capability (§6.3). Extends relay-as-cursor and
relay-as-registry to relay-as-context.

**Buzz v1 — approve with corrections.** Rejected 42050 → `KIND_AGENT_PROFILE`
(10100): it is replaceable like kind:0, so each version would clobber its
predecessor and destroy the diffable history §3 guarantees. Corrected a
malformed tag shape (JSON object where NIP-01 requires strings). Added the
audience invariant — a cross-post may never widen the audience of its source
event — which makes 42030 the only kind eligible for a parent channel.
Backfill declined; Buzz is forward-only.

## The verification lesson (worth carrying)

The compaction child reported "no compaction record exists today" and built
its recommendation on asking Claude Code to add one. I accepted that premise
and spent the ruling's reasoning on *working around* the upstream dependency —
rejecting it on precedent and substituting an inference from usage series.
Good reasoning on a false premise.

Checking the premise at REVIEW took one script against `transcripts/`: the
harness already writes a `system` record with `compactMetadata` (`trigger`,
`preTokens`, `postTokens`, `durationMs`, `cumulativeDroppedTokens`,
preserved-segment ids), plus a `user` record flagged `isCompactSummary`. Two
markers across 36 transcripts, in exactly the two sessions that compacted.

The substituted inference was *also* wrong in detail: the two-term series
(`input_tokens` + `cache_read_input_tokens`) tracks cache turnover, not
context — cache expiry collapses `cache_read` while `cache_creation` absorbs
the prompt — and fired 4–6 false positives per session. The three-term form
matched markers 1:1.

Both errors were in shipped text before REVIEW caught them, and I had already
radioed the wrong version to root for bridge. Correction sent (31BA28A8).

The rule this yields: **a child's negative existence claim ("no X exists") is
a premise, not a finding, and gets verified before any ruling rests on it.**
Cheap to check, expensive to get wrong — a wrong premise had already
propagated into DESIGN.md, the aggregate, the wiki, and a priority-6 message
to another node's implementer.

## Standing constraints this pass respected

Evals fence (nothing eval-shaped); harvester single-module blast radius
(bridge condition 3, now extended to permit append-only structured metadata
but still barring conversational structure and the compact summary body);
§6.1 no-leak on compaction pointers. `docs/kinds/` file contents are `core`'s
to write — I allocate numbers and set conditions, core writes the entry.
`tree/` is the root's to edit — contract text goes out as proposals.

## Open items owned elsewhere

- `core`: re-run the block/buzz collision check before writing
  `docs/kinds/42060-*.md`.
- root: apply the proposed `tree/evergreen/NODE.md` skeleton (sent 9AB84B62);
  route the detection correction (31BA28A8) to bridge.
