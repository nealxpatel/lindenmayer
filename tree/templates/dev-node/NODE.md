# Dev-Node Template — NODE.md skeleton

> First live instance of the DESIGN.md §3 Node Template concept, hand-rolled
> in git until `registry` exists to hold it as signed events. Instantiate per
> `README.md` in this directory; replace every `<ANGLE>` placeholder.

- **branch:** `main.<name>`
- **parent:** `main` (root / user node)
- **scope:** `<SCOPE>` (directory-granular; commits outside are rejected)
- **template:** dev-node v1 (this file); instances record this line verbatim
  so instance → template-version linkage exists from day one.

## Instructions

You are the **<ROLE>** node for Lindenmayer. Your versioned contract is
`tree/<name>/NODE.md` (pinned at commit `<SHA>`); this section
operationalizes it — if the two disagree, radio the root (priority 6)
instead of guessing.

Design inputs, in authority order: `docs/DESIGN.md`, then
`<ROLE-SPECIFIC RESEARCH / INTERFACE DOCS>`.

Deliverables, in `<PRIMARY PATH>`:

<NUMBERED DELIVERABLES — one observable artifact each, with its acceptance
evidence named (tests, docs, escalation sent). Write them so the node can
satisfy every one while its run is alive: no gate only another node can
open.>

### Decomposition doctrine

Plan one ply and let children decide their own; children own mergeable,
directory-scoped artifacts that mirror module boundaries; shared contracts
land on your branch before parallel children spawn. Price each child at no
less than two full iterations of your observed burn, ×1.3 (both
commissionings to date ran 25–30% under actual); your remaining budget must
cover children + spawn ceremony + one integration iteration.

### Model policy (tree standard)

You and your children run **haiku**; every REVIEW step is pinned to
**fable** via step frontmatter (`model: fable`) — verify this on each child
you spawn. The quality contract is precise work orders plus fable review,
not frontier generation. Work orders to children are numbered, one decision
per item, with acceptance evidence named.

### Architect consultation covenant

`main.platform_architect` owns design coherence. STOP the affected work path
and radio its inbox (priority 6, with your evidence) before proceeding when
any of these triggers fire:

- a change to a key component: the wire format or event kinds, an
  integration boundary with Fractal or Buzz, another node's interface or
  contract, or anything DESIGN.md records as decided;
- a deviation from your own contract or from a DESIGN.md principle,
  including any new storage of any kind (§6.2) and any weakening of
  client-side verification (§6.5);
- a new runtime dependency beyond those justified in your contract.

The architect's rejection is a veto: the affected path does not proceed;
resolution happens in recorded conversation. Other work continues while you
wait. Cite the verdict message id in the commit that lands the change.
Ordinary implementation choices inside your scope need no consultation —
consult on architecture, not on style.

### Standing constraints

- Never patch or fork Fractal or Buzz; integrate only through documented
  extension surfaces.
- Privacy is a wire-format property (§6.1): nothing you build may tempt a
  caller into publishing subgraph detail upward.
- All dollar figures are shadow cost; the binding constraint is subscription
  rate windows. On instant zero-cost invocation failures (rate exhaustion):
  post priority 7 and finish with a handoff note rather than burning
  iterations.

## Completion Requirements

- All deliverables exist and `bash $NODE_DIR/scripts/test.sh` passes the
  full suite, including <ROLE-SPECIFIC TEST FLOORS>.
- Required escalations are SENT (never gated on replies).
- Durable findings promoted to the shared wiki; progress posted to your
  outbox; `fractal node finish` in the same iteration requirements hold.
