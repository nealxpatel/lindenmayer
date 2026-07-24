---
name: platform_boundaries
desc: What a Lindenmayer node may build — the competing-assertion test for new signed records and wrappers.
tags: []
sources: []
created: 2026-07-24T01:52:08Z
updated: 2026-07-24T01:52:08Z
---

# platform_boundaries

Every node eventually proposes something that touches the Fractal boundary: a
new event kind, a UI action, a convenience wrapper. This page is the test to
apply before escalating, so proposals arrive already filtered. The canonical
statement is DESIGN.md §6.5; this is the working form.

## The competing-assertion rule

> A new signed record is safe **exactly when Fractal holds no competing
> assertion of the same proposition.**

Where Fractal already asserts the proposition, a second record can diverge from
the one that actually governs execution, and something has to reconcile them —
a second control path, which the never-patch-or-fork principle forbids. Where
Fractal asserts nothing, the signed record is the only record, and divergence
is impossible because there is nothing to diverge from.

| Proposal | Fractal's competing assertion | Ruling |
|---|---|---|
| Approval verdict released back into the gate | gate state: approved or not | barred |
| radio-send / signal / kill wrappers | the message, the signal, the kill | barred |
| Commission authorization (kind 42070) | none — Fractal has no concept of authorization | permitted |
| Inbound Buzz @mention → radio message | none — the mention originates outside Fractal | permitted |

## Two things that are *not* the test

**Publishing a signed event is never itself the violation.** Bridge and
registry publish; so may any node with something to assert. "It writes to the
log" is not an objection.

**"It wraps a CLI" is never itself decisive.** It is usually a symptom of the
real problem rather than the problem. Ask what proposition the new record
asserts, and whether Fractal already answers that question.

The test is the **proposition**, not the medium.

## The shape that distinguishes a safe record

Two records are safe together when they assert *different* propositions about
the same subject, with an explicit link between them:

- Fractal's registry records what **runs**; a commission records what was
  **authorized**. Where they differ, the difference is a *finding with a
  reader* — an instance running outside its commission — not a silent
  divergence with nobody to adjudicate it.
- A Buzz mention is the **origin**; the radio message it produces is the
  **effect**. One authoritative record, one explicit reference.

Contrast the failing case: a signed approval verdict and Fractal's gate state
both answer "is this work approved?" — so they can disagree, and one of them is
lying. The general form: **authorization-without-execution is a coherent
state; approval-without-release is not.**

## Read/write, stated correctly

The evergreen read/write split governs the **Fractal control plane, not the
log**. A node may publish; it may not drive Fractal. Reading "no write path" as
"never signs anything" is the common misreading and it bars work that is
actually safe.

## Where enforcement actually lives

Nothing in Fractal reads the signed log. A grant, a commission, or any other
governance record is a *fact of record*, not a gate — real, verifiable, and not
self-enforcing. Say so plainly in any design that relies on one; a record
described as if it enforces something it cannot is worse than an absent
record.
