# Evergreen Requirements Inventory

## Overview

This inventory decomposes the handrolled evergreen prototype at `tree/root/CONTEXT.md` into discrete requirements that the evergreen surface must generate, maintain, or show. Each requirement is classified by data source:

- **relay-derivable**: reconstructable from events on the Lindenmayer relay (ws://localhost:7100)
- **fractal-derivable**: from Fractal's SQLite DB or CLI read surfaces
- **human-authored**: standing governance context no query produces
- **mixed**: requirements combining multiple sources

The inventory then surveys existing query surfaces and maps requirements to the four sec-5 capabilities: commission trees, steer subgraphs, review approvals, and query own history.

---

## Requirements Table

| # | Requirement | CONTEXT.md Source | Classification | Existing Surface | Gap |
|---|---|---|---|---|---|
| 1 | Display project mission | Standing context | human-authored | N/A | Evergreen must serve mission statement from configurable source (currently hardcoded in CONTEXT.md §2) |
| 2 | Display current phase label | Standing context | human-authored | N/A | Evergreen must display phase tag (e.g., "bootstrap") from configurable source; no surface yet |
| 3 | Display non-negotiable constraints | Standing context | human-authored | N/A | Evergreen must render non-negotiables (Fractal-only integration, privacy-default aggregates, no new storage) from manifest; currently hand-maintained |
| 4 | Send messages to child inboxes | How the root steers (§35) | fractal-derivable + relay-derivable | None directly; radio infrastructure exists in Fractal | Evergreen must expose radio send surface; message format/routing is Fractal native but UX surface missing |
| 5 | Display child outbox subscriptions (1-hop) | How the root steers (§35) | relay-derivable | None; radio log lives on relay but no query tool | Need relay filter query: kind=[42020/42030/42040] authors=[child_pubkeys]; subscription topology is 1-hop structural, must reflect in UI |
| 6 | Display progress aggregates from children | How the root steers (§35) | relay-derivable | None; subgraph-digest (kind 42030) events exist on relay | Need query for kind 42030 (subgraph digest); map to run/iter/step chains to show progression |
| 7 | Edit NODE.md / steps/ live mid-run | How the root steers (§43) | fractal-derivable | fractal node CLI only; no REST/UX surface | Evergreen must watch git working tree or Fractal's state for live edits; re-read semantics are Fractal responsibility |
| 8 | Display pending approval gates | How the root steers (§46) | fractal-derivable | `fractal node pending` CLI; no UX surface | Bridge and registry CLIs list templates/nodes; no approval-pending query yet; must query kind 42040 (approval request) on relay |
| 9 | Track per-child USD budgets | How the root steers (§48) | fractal-derivable | Fractal tracks per-run cost; run-accounting events (kind 42020) exist on relay | Evergreen must aggregate kind 42020 events per child per run; visualize vs. budget cap; no surface yet |
| 10 | Track per-child time remaining | How the root steers (§48) | fractal-derivable | `fractal node time remaining` CLI only | Evergreen must compute time-window budget from Fractal config or kind 42010 (node-lifecycle) events; no surface |
| 11 | Signal stop/finish/kill escalation | How the root steers (§48) | fractal-derivable | Fractal CLI: `fractal node stop/finish/kill`; no API surface | Evergreen must provide signal interface; routing is Fractal native (needs bridge connection) |
| 12 | Display model tier policy mapping | Model policy (§50) | human-authored | N/A | Evergreen must render role → model tier binding (Orchestrator:Fable, Review:Fable, Development:Haiku) from manifest |
| 13 | Warn on frontier-model burn | Model policy (§54) | fractal-derivable + human-authored | None; constraint is "observed 2026-07-23" subscription-rate throttle | Evergreen must track frontier-model call rates, display throttle-event count per run |
| 14 | Display merge-commit diffs (regression check) | Merge hygiene (§69) | fractal-derivable | Git CLI only; no Lindenmayer surface | Evergreen must show diff against pre-merge main after every squash merge; flag files outside node's legitimate write surfaces |
| 15 | Lint .fractal seeds on main | Merge hygiene (§72) | fractal-derivable | Git CLI only (`git ls-files \| grep .fractal`) | Evergreen must run post-merge lint; show paths leaked to main; block push if violations found |
| 16 | Display architect review gate status | Consultation covenant (§82) | relay-derivable | None; review happens via radio but no query surface | Evergreen must show pending review requests (prioritized as "6") and verdicts on DESIGN.md changes |
| 17 | Render architect veto protocol | Consultation covenant (§99) | human-authored | N/A | Evergreen must display governance mode (default: veto; softer modes are per-subgraph choices) and show veto as hard-stop signal |
| 18 | Track design decision log entries | Consultation covenant (§97) | relay-derivable | DESIGN.md carries history as comments; no relay surface | Evergreen should link to or display key decision-log entries; decision events not yet kind-defined |
| 19 | Point to key docs (wiki links) | Pointers (§103) | human-authored | N/A | Evergreen must render static pointers: DESIGN.md, platforms.md, platform-architect/NODE.md, transcripts/ |
| 20 | Display node identities (npub, attested) | From DESIGN.md §2 (persistent nodes) | relay-derivable | None; kind 42010 (node-lifecycle) carries pubkey and attestation chain | Evergreen must query kind 42010 by branch name; verify NIP-OA attestation chain; show attestation state |
| 21 | Render template version history | From DESIGN.md §3 (templates) | relay-derivable | Registry CLI: `lindenmayer-registry show <author> <name>`; no Evergreen UI surface | Evergreen must query kind 42050 (template version) + kind 38150 (pointer); map instances to versions |
| 22 | Track run-to-template linkage | From DESIGN.md §3 (instances record template version) | relay-derivable | Kind 42010 (node-lifecycle) carries template_name / version / git_ref tags | Evergreen must parse lifecycle events; show which template version spawned which run |
| 23 | Query approval-verdict events | From DESIGN.md §1, §3 (approval events) | relay-derivable | None; kind 42041 (approval-verdict) events exist on relay but no query | Evergreen must query kind 42041 by run/template; show verdicts (approved/rejected) and reviewer |
| 24 | Display subgraph membership (channel binding) | From DESIGN.md §1 (branch-as-room NIP-29) | relay-derivable | None; group membership is channel-level in relay | Evergreen must show NIP-29 group membership; which children are subscribed to which channels |
| 25 | Query node-lifecycle event stream | From DESIGN.md §3, §4 (tracking runs) | relay-derivable | Kind 42010 (node-lifecycle) events; no Evergreen query surface | Evergreen must query kind 42010 filtered by branch/node; show run start/end/status, model used, cost |
| 26 | Query run-accounting aggregates | From DESIGN.md §1 (telemetry) | relay-derivable | Kind 42020 (run-accounting) events exist; no Evergreen query surface | Evergreen must query kind 42020 by node/run; aggregate cost, token counts; compare to budget cap |
| 27 | Query subgraph-digest aggregates | From DESIGN.md §1 (aggregates flow up) | relay-derivable | Kind 42030 (subgraph-digest) events exist on relay; no query surface | Evergreen must query kind 42030 by subgraph/run; show digest metrics (cost, step count, status roll-up) |
| 28 | Enforce compaction-to-task mapping | From DESIGN.md §5 (evergreen sessions compact) | relay-derivable + human-authored | None; compaction is open question in §8 | Evergreen must maintain or link to compaction events that map summary → run/iter/step; structure not yet defined (kind 420xx TBD) |

---

## Source Classification Summary

- **Relay-derivable (16 reqs)**: Node identities, template history, run accounting, approval verdicts, subgraph digests, radio aggregates, node-lifecycle streams
- **Fractal-derivable (7 reqs)**: Live NODE.md/steps/ edits, pending approval gates, per-child budgets, time-budget computation, signal routing, merge diffs, seed linting
- **Human-authored (4 reqs)**: Mission, phase label, non-negotiables, model policy, governance mode, wiki links
- **Mixed (1 req)**: Compaction-to-task mapping (relay structure TBD + human context)

---

## Existing Query Surfaces Survey

### Bridge CLI (`src/lindenmayer/bridge/cli.py`)
- **Reads from**: Fractal SQLite (.db file) and transcripts
- **Publishes to**: Nostr relay via NIP-01/NIP-29
- **Existing queries**:
  - `get_node_lifecycle_rows()`: Joined view of node runs with timestamps, used to translate kind 42010 events
  - `get_nodes()`: List all node names from database
  - `get_runs(node_name)`: List runs for a specific node; filters by `ended_at` to exclude active runs
- **Gap**: No user-facing query surface; reads are embedded in publisher logic only

### Registry CLI (`src/lindenmayer/registry/cli.py`)
- **Commands available**:
  - `publish <template_dir>`: Publish template version (kind 42050) + pointer (kind 38150)
  - `list <author>`: List templates by author; queries kind 42050, groups by template_name
  - `show <author> <name>`: Show version history for a template; calls `TemplateReader.get_version_history()`
- **Queries**: Relay filters `{"kinds": [42050], "authors": [...]}`; reads template_name, version, git_ref tags
- **Gap**: Read-only for template metadata; no queries for run linkage, approval verdicts, or budget aggregates

### Registry Reader (`src/lindenmayer/registry/reader.py`)
- **Exports**: `TemplateReader` class with `get_version_history(author, name)` async method
- **Used by**: Registry CLI; queries relay for kind 42050 events and parses tags
- **Gap**: No wrapper for node-lifecycle (kind 42010), run-accounting (kind 42020), subgraph-digest (kind 42030), or approval-verdict (kind 42041) queries

### SQLite Adapter (`src/lindenmayer/bridge/adapters/sqlite.py`)
- **Provides**: `FractalDBReader` class to load node/run/step data from Fractal's per-tree .db
- **Used by**: Bridge CLI for translating Fractal rows to events
- **Queries exposed**:
  - `get_nodes()`: All nodes
  - `get_node_lifecycle_rows()`: Node run data with timestamps
  - `get_runs(node_name)`: Per-node run list
- **Gap**: No Evergreen-facing API; queries are translation-focused, not end-user analytics

### Relay Connectivity (Live Test)
- **Status**: Lindenmayer relay at ws://localhost:7100 is running with 12 node identities, 42010 x12, 42020 x27, registered template events
- **Queryable kinds**: 42010, 42020, 42030, 42040, 42041, 42050, 38110, 38150 + NIP-OA attestations
- **Gap**: No standard client interface for Evergreen queries; bridge uses RelayClient but it is not exposed as a read-only query API

---

## Per-Capability Gap Analysis

### 1. Commission Trees on the Fly

**Requirement sources from DESIGN.md §5 & §3**:
- Evergreen user selects a template from registry
- Instantiates a new node with that template
- Records commissioning decision (approval or veto from architect)

**What exists**:
- Registry CLI can list and show template versions (kind 42050 query works)
- Template version history is queryable (TemplateReader)
- Fractal itself spawns nodes; Evergreen would orchestrate the request

**Gaps**:
1. No Evergreen UI for template selection / commissioning workflow
2. No relay query for "templates available for instantiation" — kinds 42050/38150 exist but no curator filter
3. No record of commission decisions — approval events (kind 42040/42041) exist but commissioning-specific schema not defined
4. No bridge connection from Evergreen to Fractal node-spawn API

### 2. Steer Subgraphs (Radio, Signals, Live Edits)

**Requirement sources from DESIGN.md §5 & CONTEXT.md §35–§48**:
- Send radio messages to child inboxes
- Subscribe to child outboxes (1-hop)
- Display progress aggregates
- Edit NODE.md / steps/ live mid-run
- Display pending approval gates
- Send stop/finish/kill signals
- Track budgets and time remaining

**What exists**:
- Fractal radio infrastructure is live; message routing works natively
- Subgraph-digest kind 42030 events carry aggregates from children
- Node-lifecycle kind 42010 and run-accounting kind 42020 exist on relay
- Bridge can translate Fractal runs to events
- Registry/reader can query the relay

**Gaps**:
1. No Evergreen radio send UI (messaging is CLI-only via `fractal radio send`)
2. No Evergreen query for outbox subscriptions (relay events exist; no aggregation surface)
3. No live edit UI for NODE.md/steps/ (Fractal monitors git; Evergreen needs watch bridge)
4. No cost/time aggregation query (raw events exist; no roll-up surface)
5. No pending-approval display (kind 42040 exists; no query filter)
6. Signal routing (`finish`/`stop`/`kill`) is Fractal CLI only; no bridge API

### 3. Review Approvals

**Requirement sources from CONTEXT.md §76–§99 (consultation covenant) & DESIGN.md §1**:
- Display pending design-change review requests
- Show architect veto vs. approval verdicts
- Track decision-log entries
- Enforce governance mode (default: veto)
- Link to key design documents

**What exists**:
- Radio infrastructure carries review requests (priority 6)
- Approval-request kind 42040 and approval-verdict kind 42041 exist on relay
- DESIGN.md exists with decision-log comments
- Architect node (main.platform_architect) holds the review contract

**Gaps**:
1. No Evergreen query for pending review requests (radio is live; no relay event kind for review-requests specifically)
2. No decision-log event kind defined (decisions live as comments in DESIGN.md only)
3. No display of governance-mode parameter (human-authored; must come from manifest/config)
4. No veto enforcement surface (Evergreen could display, but action is human decision + radio reply)
5. No link aggregation from Evergreen to architect's NODE.md or decision history

### 4. Query Own History

**Requirement sources from DESIGN.md §5 & §4 (provenance as training asset)**:
- Query node-lifecycle events (runs, statuses, templates used)
- Query run-accounting aggregates (cost, tokens per run)
- Query approval verdicts (which runs were approved, by whom)
- Query subgraph-digest aggregates (roll-ups per run)
- Trace template version to run linkage
- Query compaction-to-task mapping (open question)

**What exists**:
- Kind 42010 (node-lifecycle) events carry run metadata, template linkage, cost placeholders
- Kind 42020 (run-accounting) events carry token counts and cost aggregates per run
- Kind 42041 (approval-verdict) events link to runs and carry reviewer/verdict
- Kind 42030 (subgraph-digest) events carry roll-up metrics
- Registry reader can list template versions (kind 42050)
- All events are signed and queryable from relay

**Gaps**:
1. No query aggregator for "all runs of node X across time" (raw filters exist; no roll-up)
2. No cost-trend visualization (kind 42020 events exist; no query/render surface)
3. No approval-trace query (kind 42041 exists; no filter by run/template/reviewer)
4. No compaction-to-transcript mapping (open question in DESIGN.md §8; event structure TBD)
5. No consent-grant query (DESIGN.md §4 mentions history-access grants as future; no kind defined)
6. No extraction-pipeline query surface (audit/compliance; future work, §4)

---

## Summary by Component

### Data Availability
- **Relay events**: All four capability domains have event kinds defined (42010, 42020, 42030, 42040, 42041, 42050, 38110, 38150, NIP-OA)
- **Fractal SQLite**: Run metadata, node definitions, step records (readable via bridge adapters; not exposed to Evergreen)
- **Radio infrastructure**: Message routing live and functional; no query surface yet
- **Human context**: Mission, phase, governance mode, model policy are hand-maintained in CONTEXT.md and DESIGN.md

### Surface Readiness
1. **Bridge CLI**: Can translate Fractal → relay events; no user-facing query
2. **Registry CLI/Reader**: Can list and show templates; no integration with node lifecycle or run history
3. **Relay connectivity**: Live and queryable; no Evergreen-facing client library yet
4. **Fractal interfaces**: Radio, signals, node spawn, live edits are all native; no orchestration layer bridges them to Evergreen

### Evergreen-Specific Gaps
1. **No unified query API**: Each surface (bridge, registry, relay, Fractal CLI) requires separate integration
2. **No aggregation layer**: Raw events exist; roll-ups (cost trends, approval traces, run sequences) must be built
3. **No UX surfaces**: All operations are CLI-only or embedded in publisher logic
4. **No governance display**: Veto mode, review gates, architect decisions are not surfaced
5. **No session continuity**: Compaction-to-task mapping is open (DESIGN.md §8); no event kind or schema yet
