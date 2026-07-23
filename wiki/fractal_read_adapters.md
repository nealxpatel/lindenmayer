---
name: fractal_read_adapters
desc: Read-only adapters for accessing Fractal's SQLite database and transcript files.
tags: [adapters, sqlite, transcripts, read-only]
sources: []
created: 2026-07-23T19:06:51Z
updated: 2026-07-23T19:10:27Z
---

# fractal_read_adapters

Two read-only adapters for accessing Fractal runtime data:

## FractalDBReader

Read-only reader for Fractal's per-tree SQLite database.

### Import
```python
from lindenmayer.bridge.adapters.sqlite import FractalDBReader
```

### API

**`__init__(db_path: str)`**
- Initialize with path to `.db` file
- Opens database in read-only mode (WAL-safe)

**`get_nodes() -> list[dict]`**
- All nodes from the registry
- Fields: node_id, node, title, status, max_cost, max_depth, max_children, max_descendants, created_at

**`get_runs(node: str) -> list[dict]`**
- All runs for a given node
- Fields: run_id, node, parent_run_id, agent, max_cost, status, exit_code, metadata, started_at, ended_at

**`get_iters(run_id: int) -> list[dict]`**
- All iterations for a given run
- Fields: iter_id, node, run_id, iter, agent, model, session, status, exit_code, metadata, started_at, ended_at

**`get_steps(iter_id: int) -> list[dict]`**
- All steps for a given iteration
- Fields: step_id, node, iter_id, run_id, step, step_name, agent, model, session, status, exit_code, cost, approved, metadata, started_at, ended_at

**`get_latest_event(node: str) -> dict | None`**
- Latest event for a node, or None if no events exist
- Fields: event_id, node, step_id, iter_id, run_id, event, actor, status, exit_code, metadata, created_at

### Example
```python
reader = FractalDBReader("/path/to/tree.db")
nodes = reader.get_nodes()
for node in nodes:
    runs = reader.get_runs(node["node"])
    for run in runs:
        iters = reader.get_iters(run["run_id"])
```

## TranscriptUsageHarvester

Extract per-request token usage from agent session transcripts (JSONL format).

### Import
```python
from lindenmayer.bridge.adapters.transcripts import TranscriptUsageHarvester
```

### API

**`__init__(transcript_path: str)`**
- Initialize with path to `.jsonl` transcript file

**`iter_requests() -> Iterator[dict]`**
- Yield individual request cost records
- Each record has: model (string), input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens (all ints)
- Only processes "cost" type events; ignores conversational structure

**`get_total_usage() -> dict`**
- Aggregated usage across all requests
- Returns dict with keys: input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens (all ints)

### Design Notes

- **Append-only**: Only reads per-request usage fields written at response time; survives compaction
- **Conversational-agnostic**: Never parses message structure, only cost events
- **Isolated module**: Changes to compaction design ripple through exactly one place

### Example
```python
harvester = TranscriptUsageHarvester("/path/to/transcript.jsonl")

# Per-request usage
for request in harvester.iter_requests():
    print(f"{request['model']}: {request['input_tokens']} input, {request['output_tokens']} output")

# Aggregated usage
total = harvester.get_total_usage()
print(f"Total: {total['input_tokens']} input tokens")
```

***
