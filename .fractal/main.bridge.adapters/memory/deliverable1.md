---
name: deliverable1
desc: Implementation of FractalDBReader and TranscriptUsageHarvester.
tags: [delivered, adapters, sqlite, transcripts]
sources: []
created: 2026-07-23T19:06:51Z
updated: 2026-07-23T19:10:27Z
---

# deliverable1

## Implementation

### FractalDBReader
- **File**: `src/lindenmayer/bridge/adapters/sqlite.py`
- **Methods**:
  - `get_nodes()`: Returns all nodes from the registry
  - `get_runs(node)`: Returns all runs for a given node
  - `get_iters(run_id)`: Returns all iterations for a given run
  - `get_steps(iter_id)`: Returns all steps for a given iteration
  - `get_latest_event(node)`: Returns the latest event for a node or None

- **WAL-safe**: Opens database in read-only mode with URI parameter `?mode=ro`
- **No writes**: All methods are read-only queries
- **Row factory**: Uses sqlite3.Row for dict-like access to columns

### TranscriptUsageHarvester
- **File**: `src/lindenmayer/bridge/adapters/transcripts.py`
- **Methods**:
  - `iter_requests()`: Yields individual cost events with usage fields (model, input_tokens, output_tokens, cache_*_input_tokens)
  - `get_total_usage()`: Returns aggregated usage across all cost events with keys: input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens

- **Read-only**: Only reads JSONL append-only per-request usage fields
- **No conversational parsing**: Ignores conversational structure, only processes "cost" type events
- **Robust to compaction**: Per-request cost events survive compaction

## Testing

### Test Suite
- **File**: `tests/test_adapters.py`
- **Coverage**: 16 tests covering both adapters
- **FractalDBReader tests** (10):
  - Fixture reading and structure validation for nodes, runs, iters, steps, events
  - Edge cases like nonexistent nodes
- **TranscriptUsageHarvester tests** (6):
  - Per-request iteration with both transcript fixtures
  - Aggregated usage calculation
  - Model field verification
  - Return type validation

### Test Execution
- **Command**: `bash /Users/nealpatel/Code/l-system/.worktrees/main.bridge.adapters/.fractal/main.bridge.adapters/scripts/test.sh`
- **Results**: All 16 adapter tests pass
- **Full suite**: All 160 project tests pass (no regressions)

## Fixtures
- `tests/fixtures/tree.db`: Snapshot of project's Fractal tree database with 8 nodes, 20 runs, 38 iterations, 307 steps, 104 events, 76 messages
- `tests/fixtures/transcript-1.jsonl`: Test transcript with 2 cost events (100→50 and 150→75 tokens)
- `tests/fixtures/transcript-2.jsonl`: Test transcript with 2 cost events (200→100 and 250→125 tokens)

## Status
COMPLETED - All acceptance criteria met.
