---
name: state
desc: Current work state and progress
tags: []
sources: []
created: 2026-07-23T21:40:00Z
updated: 2026-07-23T23:37:23Z
---

# state

## Task
Build evergreen requirements inventory by decomposing tree/root/CONTEXT.md into discrete requirements that the evergreen surface must generate/maintain.

## Deliverable
`docs/research/evergreen/inventory.md` with:
1. Requirements table (requirement | CONTEXT.md source | classification | existing surface | gap)
2. Per-capability gap list for four sec-5 capabilities

## CONTEXT.md Sections to Decompose
- Why this file exists (design principle)
- Standing context (mission, phase, non-negotiables)
- How the root steers (radio/live steering/approvals/budgets) — **primary steering surface**
- Model policy (role → model tiers)
- Merge hygiene (git checks)
- Consultation covenant (architect veto/review gate)
- Pointers (references to key docs)

## Four sec-5 Capabilities to Map
1. Commission trees on the fly
2. Steer subgraphs (radio, signals, live contract edits)
3. Review approvals
4. Query own history

## Data Sources
- **relay-derivable**: Lindenmayer relay (ws://localhost:7100), kinds in docs/kinds/
- **fractal-derivable**: Fractal SQLite / CLI (bridge/sqlite.py, bridge/cli.py, registry/cli.py, registry/reader.py)
- **human-authored**: standing context, governance parameters, model policy

## Existing Surfaces to Check
- bridge CLI: src/lindenmayer/bridge/cli.py
- registry CLI/reader: src/lindenmayer/registry/cli.py, reader.py
- SQLite adapter: src/lindenmayer/bridge/adapters/sqlite.py
- Relay connectivity: ws://localhost:7100 (read-only test)

## Key References
- DESIGN.md §1 (bridge/Nostr layers), §5 (evergreen), §6.1 (privacy), §6.2 (no new storage)
- docs/kinds/ — event taxonomy (8 custom kinds + NIP-OA)
- tree/root/CONTEXT.md — prototype to decompose
- relay-integration research: docs/research/relay-integration/README.md

## Progress
- PLAN complete
- EXECUTE complete: inventory.md written with full requirements table (28 requirements), source classification, existing-surface survey, per-capability gap analysis
- COMMIT ready
