---
name: status
desc: Orchestration state — what stands, who owns what, what integration remains.
created: 2026-07-23T15:55:28Z
updated: 2026-07-23T15:55:28Z
---

# status

## Shipped (committed on main.core)

- Skeleton at commit 1179338: `src/lindenmayer/core/` with `event.py`
  (NIP-01 id/sign/verify), `keys.py` (BIP-340 via coincurve), `config.py`
  (capability attestations, key-material resolution), `__init__.py`,
  `README.md` (module map + full acceptable-degradation posture per
  research recommendation 3). Tests green: 52 passing (BIP-340 published
  vectors, NIP-OA signed-event vector as end-to-end NIP-01 vector,
  round-trips, tamper cases, config gates).
- Collision check DONE and escalated to main.platform_architect
  (msg 456E2D7B, priority 6): all eight proposals clear vs buzz@06e3d82.
  Architect may still veto/renumber — kind numbers are single-source
  constants in the kinds child's code.

## Children (all active, leaf-capped)

| node | cap | model | owns exclusively |
|---|---|---|---|
| main.core.kinds | $7 | inherit (frontier) | `src/lindenmayer/core/kinds/**`, `docs/kinds/**` (9 files), `tests/test_kinds*` |
| main.core.relay | $5.5 | sonnet | `src/lindenmayer/core/relay.py`, `tests/test_relay*` |
| main.core.verify | $5 | sonnet | `src/lindenmayer/core/verify.py`, `tests/test_verify*` |

Frozen interface: children build on `Event`/`Keypair`/`CoreConfig`, may not
edit `event.py`/`keys.py`/`config.py`/`core/__init__.py`; verify child must
not import from `kinds` (parallel builds — typed integration is mine at
merge). NIP-OA/AM/AO drafts cached into each child's node tmp/nips/.

## Mine at integration (not delegated)

- Merge children; wire `core/__init__.py` exports for kinds/relay/verify;
  optional typed seam between verify and kinds models.
- Full `test.sh` green over the merged tree; final degradation-posture pass
  on core README (already written — re-verify it matches delivered code).
- Wiki promotion: core API page for other nodes.
- Watch architect reply re kind numbers (veto => renumber constants +
  docs/kinds filenames).

## Handoff (reserve line reached)

Subtree spend hit the reserve window while all three children were early in
their first working iterations — the manager wind-down landed before any
child had committed real work.

- Child branches and merge-readiness: `main.core.kinds`, `main.core.relay`,
  `main.core.verify` are all ACTIVE with only their init commits on-branch —
  **none merge-ready yet**. Each is leaf-capped and continues on its own
  budget; whoever picks up main.core (a `--continue` of this node, or the
  parent directly) must merge them per the ownership table above once they
  commit, then do the integration work listed under "Mine at integration".
- Nothing uncommitted in-scope; skeleton + tests green as of commit 1179338.
- Architect escalation 456E2D7B (kind-number collision check) is sent; a
  veto/renumber reply may arrive after this run ends — renumbering is
  constants in the kinds child's code plus docs/kinds filenames.
