# Compaction-to-Task Mapping: Research Findings

## Investigation Conclusions

### 1. Compaction Observability
- Transcripts contain cost events (survive compaction) and conversational records (destroyed by compaction)
- No compaction marker/record type exists today—when compaction occurs, there's no artifact identifying the span
- Adapter anticipates this gap but design not yet in place
- Solution: add "compaction" record type to transcripts with timestamp span and hash

### 2. Harvester Boundary
- TranscriptUsageHarvester (transcripts.py) isolated behind one module—good architecture for extension
- Current: reads only "cost" type events via iter_requests()
- Proposed: add iter_compactions() method reading new "compaction" record type
- Session→(run_id, iter_id, step_id) lookup via manifest enables enrichment inside adapter alone
- All logic stays in one place (constraint b compliance)

### 3. Task Anchors Available
- Fractal DB: run_id, iter_id, step_id as primary identifiers
- iters table carries session UUID (Claude Code session, links to compaction records)
- events table links step_id, iter_id, run_id (task hierarchy preserved)
- Existing kinds (42010/42020/42030) use tags: "branch", "run" (no iter_id or step yet)

### 4. Nostr Idioms for Event References
- NIP-10: `e` tags with optional marker (reply, root, mention, etc.)
- NIP-18: `q` tag for quote reposts
- NIP-51: `e` tags with list-item markers
- Pattern: third field of tag can carry marker string to indicate relationship type
- For compaction: `["e", "<event-id>", "", "summary-of"]` reads cleanly

## Candidate Shapes Analysis

### Candidate A: Compaction Event Kind (kind TBD) ← RECOMMENDED
- New kind in 420xx block (kind TBD by architect)
- Tags: branch, run, iter, step, compaction-session, compaction-span-start, span-end, e tag with "summary-of"
- Content: iter_count, duration_s, context_tokens_compacted, summary_hash
- Strength: traceable, verifiable, linked via e tag, privacy-tight
- Constraint compliance: a (kind TBD), b (adapter-harvested), c (no content leaks)

### Candidate B: Compaction Tags on 42010 Lifecycle Event
- Reuse existing kind 42010, add status="context-compacted" or JSON metadata tag
- No new kind number (constraint a compliant)
- Weakness: retrofitting problem (event immutability), tag pollution
- Fallback if kind allocation deferred

### Candidate C: Compaction Doc-Only Convention
- Versioned manifest in git (e.g., docs/compaction-manifest.md)
- No signed events
- Rejected: not discoverable, privacy leak if repo public, no cryptographic proof

## Architecture Note
- Constraint b is tight: compaction-pointer harvesting must live in transcripts.py alone
- Session manifest mapping (sessionId → (run_id, iter_id, step_id)) should be written by Fractal at step start, persisted in .fractal/
- Bridge code calls adapter methods; adapter handles all transcript parsing

## Privacy Compliance
- All three constraints satisfied by Candidate A
- Compaction events carry only task IDs, timestamps, metrics—no conversational content
- Follows DESIGN.md §6.1: aggregates up, details stay in subgraph
