---
name: state
desc: Current build status of the three evergreen deliverables and test suite.
created: 2026-07-24T00:41:53Z
updated: 2026-07-24T00:41:53Z
---

# state

All three deliverables from tree/evergreen/NODE.md exist in
`src/lindenmayer/evergreen/`, with the full suite green (270 tests,
`bash scripts/test.sh`).

- `query.py` -- `EvergreenQuery`, a typed read surface over all nine kinds
  (the eight in `core.kinds.constants` plus a locally-defined
  `KIND_COMPACTION = 42060`, since core hasn't allocated a constant for it
  yet). Every method verifies NIP-01 (id+sig) before parsing and drops
  (never raises on) a tampered or malformed event. Addressable kinds
  (38110, 38150) collapse to latest-by-(created_at, id). Approval counting
  delegates entirely to `core.verify.count_approvals`.
- `surface.py` -- `generate_surface()`, composing a human-authored preamble
  (read verbatim from an operator TOML), a situational block derived from
  `EvergreenQuery` only, and a model-policy block that reads each node's
  live `config.json`/`steps/*.md` frontmatter directly (a third source,
  neither the preamble nor the log-derived block). Has its own
  `python -m lindenmayer.evergreen.surface --relay ...` one-command entry.
- `cli.py` -- `lindenmayer-evergreen` (`python -m
  lindenmayer.evergreen.cli`), subcommands `runs`/`cost`/`approvals`/
  `templates`, all reading through `EvergreenQuery`.

Dogfood fixture committed: `tests/fixtures/evergreen/sample_context.md`,
generated from the mock-relay fixture set (`tests/evergreen_helpers.py`),
byte-identical to the golden test's expectation (re-verified after the tag
filter fix below).

## The tag-filter trap (the most important thing here)

NIP-01 defines tag filters as `#<single-letter>` only. A multi-character
key like `#branch` or `#template_name` is NOT in the spec: a real relay
ignores it and returns everything matching the remaining terms. Measured
against the dev relay: a `#branch`-filtered 42010 query and a bare one
returned the identical 12 events across twelve different branches.

So relay-side filtering is never load-bearing here. Every multi-character
tag constraint is enforced client-side in `_to_records` after verification;
only `kinds`/`authors`/`ids`/`#d`/`#e`/`#p` go to the relay, and even `#d`
is re-checked locally (§6 principle 5). Two named regression tests pin
this.

Two mistakes worth not repeating:

- I first "fixed" `tests/relay_mock.py` to match multi-character keys.
  That was backwards -- it made the shared mock more permissive than any
  real relay and would have masked this bug class for every node reusing
  it. Reverted; the mock's single-letter behavior is the faithful one.
- I reported a live-relay run as returning real `main.evergreen` history
  when it was twelve other branches leaking through the ignored filter.
  What caught it: the run numbers in the output (21-27) were inconsistent
  with this node's actual run (37). Corrected on radio (F4155218).
  Ground truth: `main.evergreen` has zero events on that relay.

Registry's `reader.py:72` has the identical defect and does not re-check
client-side, so `get_version_history()` returns every template's versions
labeled as the requested one on a real relay. Not mine to fix; escalated
to the architect with evidence (6D3D3C19).

## Environment

Worktree-local venv on Python 3.13 (`UV_PYTHON=3.13 uv sync --inexact`) --
the shared repo venv is 3.14 and coincurve ships no cp314 wheels. Wired
into `setup.sh`/`test.sh`.

No blockers open. No architect escalation was needed on the two questions
that looked escalation-shaped at planning time (the missing 42060 core
constant, and model-policy sourcing) -- both resolved from the contract
text itself; the one escalation sent was the registry defect above.
