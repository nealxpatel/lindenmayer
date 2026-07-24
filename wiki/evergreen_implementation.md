---
name: evergreen_implementation
desc: The read plane -- a typed query surface over the signed log, the context-surface generator, and the history CLI.
tags: [evergreen, nostr, read-plane, context]
sources: [docs/DESIGN.md, tree/evergreen/NODE.md, docs/research/evergreen/README.md]
created: 2026-07-24T00:41:53Z
updated: 2026-07-24T00:41:53Z
---

# evergreen_implementation

Evergreen is the surface a human governs their subgraph from. Per
DESIGN.md §5.1, **v1 is the read plane**: Fractal's own CLI remains the
write plane, and evergreen ships no radio-send UI, signal API, live-edit UI,
or node-spawn bridge. Three deliverables, all in
`src/lindenmayer/evergreen/`.

## 1. Query library (`query.py`)

`EvergreenQuery` wraps core's `RelayClient` -- no new client, no local
index. Every call is a fresh relay round trip (relay-as-context, §6.2,
extending the bridge's relay-as-cursor and the registry's
relay-as-registry).

Covers all nine published kinds: 42010 lifecycle, 42020 run accounting,
42030 subgraph digest, 42040/42041 approvals, 42050 template version,
38110 node state pointer, 38150 template pointer, 42060 compaction.

| Method | Kind | Returns |
|---|---|---|
| `node_lifecycle(branch=)` | 42010 | `list[Record[NodeLifecycle]]` |
| `node_state_pointer(branch)` | 38110 | `Record[NodeStatePointer] \| None` |
| `run_accounting(branch=)` | 42020 | `list[Record[RunAccounting]]` |
| `subgraph_digest(branch=)` | 42030 | `list[Record[SubgraphDigest]]` |
| `approval_requests(branch=)` | 42040 | `list[Record[ApprovalRequest]]` |
| `approval_status(request_id)` | 42041 | `ApprovalCounts` |
| `pending_approvals(branch=)` | 42040+42041 | requests with no verdict |
| `template_versions(template_name=)` | 42050 | `list[Record[TemplateVersion]]` |
| `template_version_by_id(id)` | 42050 | one version, for linkage joins |
| `template_pointer(template_name)` | 38150 | `Record[TemplatePointer] \| None` |
| `compactions(branch=)` | 42060 | `list[Compaction]` |

`Record[T]` carries the parsed kind model plus the event metadata the model
itself omits (`event_id`, `pubkey`, `created_at`) -- needed to resolve
pointers and order history.

Design notes worth reusing:

- **Verify, then drop.** Every event is `Event.verify()`-checked (NIP-01 id
  + signature) before parsing; a tampered, unsigned, or structurally
  malformed event is silently dropped, never surfaced (§6.5). This is the
  drop-don't-raise posture of core's `filter_attested`, chosen over the
  registry reader's raise-on-failure style deliberately: a read-plane
  dashboard should degrade by omission rather than crash on one bad event.
- **Tag constraints are client-side.** See `relay_query_patterns` -- this
  is the single most important thing to get right when adding a query.
- **Approval counting is core's.** `approval_status` delegates entirely to
  `core.verify.count_approvals`; the reject→revise→approve resolution rule
  is not reimplemented.
- **42060 has no core constant yet.** `KIND_COMPACTION = 42060` is a local
  literal with a comment pointing at the open collision check
  (`docs/research/evergreen/README.md`). DESIGN.md §5.2 already ratifies
  the number and shape; only core's paperwork is pending. Evergreen reads
  this kind only -- the bridge's transcript adapter is the sole emitter.
  `Compaction` carries metrics and the summary **hash**; the summary body
  is never read (§6.1).

## 2. Context-surface generator (`surface.py`)

`generate_surface()` emits the `CONTEXT.md`-shaped standing surface as a
composite of **three independently-sourced pieces**. Keeping them distinct
is the whole design:

1. **Human-authored preamble** -- mission, phase, non-negotiables,
   governance mode, pointers. Read verbatim from an operator-owned TOML
   (`read_preamble`). These are decisions, not derived facts, so they are
   never generated.
2. **Generated situational block** -- live state and spend (38110), subgraph
   aggregates (42030), pending approval gates (42040 minus 42041), recent
   lifecycle (42010). Derived from the query library **only, never from
   Fractal's SQLite**: SQLite holds exactly the step-level detail the wire
   format excludes, so reading it would make any committed or cross-posted
   surface a §6.1 leak. Anything published is built from log-derived fields
   alone.
3. **Model-policy block** -- reads the **live assignment** via
   `read_model_policy(node_dir)`: the node's `config.json` `model` field
   plus `model:` frontmatter pins in `steps/*.md`. This is a third source,
   neither the preamble nor the log: Fractal's own tracked seed files, not
   the telemetry DB and not a relay query. It never restates the tiers as
   prose -- two independent surfaces did that and both went stale, which is
   why §3 forbids it.

One-command invocation, once a relay endpoint exists:

```bash
python -m lindenmayer.evergreen.surface \
    --relay ws://localhost:7100 --branch main.evergreen \
    --preamble preamble.toml --node-dir .fractal/main.evergreen
```

## 3. History CLI (`cli.py`)

`lindenmayer-evergreen`, stdlib argparse only (a new runtime dependency
would be an architect consultation). Subcommands, all `--relay`-scoped:

- `runs <branch>` -- the node's runs over time, from 42020
- `cost <branch>` -- cost rollups, every figure labeled **shadow cost** (§6)
- `approvals <branch>` -- approval traces from 42040/42041, resolved or pending
- `templates <branch>` -- template-version → instance linkage (42020's
  `template` tag joined to its 42050 version event)

## Testing

270 tests pass. Evergreen-specific coverage:

- `tests/evergreen_helpers.py` -- one deterministic signed fixture subgraph
  (fixed keypair, fixed `created_at`, no wall clock) covering all nine
  kinds. Shared by all three test modules so the fixture shape is defined
  once.
- `tests/test_evergreen_query.py` -- per-kind round trips, addressable
  latest-wins, **tampered-event rejection** at both the relay-client
  boundary and evergreen's own re-verification layer, plus two regression
  tests pinning client-side tag scoping.
- `tests/test_evergreen_surface.py` -- golden (fixture events → exact
  expected surface) plus a test that changes the live model assignment and
  asserts the rendered block follows it.
- `tests/test_evergreen_cli.py` -- **the argument path itself under test**:
  each subcommand is invoked as a real subprocess
  (`python -m lindenmayer.evergreen.cli ...`) against a live mock relay,
  plus argparse error paths (missing required arg → exit 2, no subcommand →
  help). Two prior nodes shipped CLIs whose argument path no test executed
  and both broke on first live use; this is the guard.
- `tests/fixtures/evergreen/sample_context.md` -- the committed dogfood
  output, generated end to end against the mock relay fixture set.

## Live-relay status

No node can gate completion on live relay data (see `node_operations`).
Demonstrations run against the mock fixture set; the live run is an
operator follow-up. As measured during this build, the dev relay carried
lifecycle events for `main.core`, `main.bridge`, `main.registry`,
`main.platform_architect` and others, but **none for `main.evergreen`** --
the bridge has not published this branch. The generator itself works
against it; there is simply nothing published to show.
