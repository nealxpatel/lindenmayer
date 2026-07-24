---
name: node_operations
desc: Repo-specific fractal operating quirks every node hits (scope, transcripts, spawning).
created: 2026-07-23T13:28:12Z
updated: 2026-07-23T13:28:12Z
---

# node_operations

Operating facts specific to this repo that differ from stock fractal
behavior. Any node committing or spawning here will hit these.

## Transcripts vs scope

A hook syncs the live session transcript to `transcripts/<session>.jsonl`
(untracked). For any node with a scope set, this file is out of scope and
`fractal commit` rejects it. Commit it deliberately with
`fractal commit --ignore-scope "<msg>"` (still lints) rather than leaving it
to the loop's `(auto)` force-commit backstop — transcripts are an
intentional public record for this tree (see `docs/DESIGN.md` §7).

## `.fractal/` ignore rules (changed on main)

The repo's `.gitignore` no longer blanket-ignores `.fractal/` — the entry
was dropped on main (commit 9e32acb) because it broke `fractal commit` for
every scoped node: fractal's staging names the node's own
`.fractal/<branch>` dir as an explicit literal pathspec, and git hard-errors
on an explicitly-named ignored path. Runtime-state exclusion is fractal's
own `.git/info/exclude` mechanism, which is narrower. Consequences:

- Scoped `fractal commit` works without `--force` again; stop routing
  around it.
- `.fractal/` may appear as untracked in `git status` — that is expected,
  not drift. Nothing under `.fractal/` is tracked on any branch.
- Versioned node contracts still live in `tree/` (see CLAUDE.md); a child's
  NODE.md/memory/plans are edited on disk in the child's worktree, and
  merge-up carries only project files.

## rtk filters merge commits from `git log`

The rtk proxy (which transparently wraps git commands) drops merge commits
from `git log` output — after a PREPARE merge, HEAD can look stale or your
merge commits invisible. Not data loss: verify with
`rtk proxy git log --first-parent --oneline` (raw, unfiltered) or
`git rev-parse HEAD` before concluding a merge didn't land.

## A relay may be running, but no node can discover which one

**Corrected — an earlier version of this page said no relay is reachable from
inside a node run. That was wrong.** A dev relay does answer on
`ws://localhost:7100`; `nc -z localhost 7100` succeeds from inside a node run,
and `docs/research/evergreen/inventory.md` records that relay holding 12 node
identities with live 42010/42020 events. Do not repeat the reachability claim.

The real problem is **discovery and reproducibility**, and it still bites:

- No deployment artifact exists — no `deploy/`, no compose file, no deployment
  TOML — so the endpoint is operator ambient state, not something the repo
  tells a node.
- The only relay default recorded in code, `registry/cli.py:35`, is
  `ws://localhost:8080` — **a port nothing is listening on**. A node that
  trusts the one default in the tree reaches nothing, and fails with a
  connection error that reads like the relay being down.
- `bridge/cli.py:210` makes `--relay` required, and `CoreConfig.relay_url` has
  no default (`src/lindenmayer/core/config.py`). Those are the correct
  shapes: failing loudly beats a default aimed at a closed port.

Relay selection and deployment remains an open design question
(`docs/DESIGN.md` §8), which now gates on reproducibility rather than
reachability. Closing it means a checked-in deployment plus one endpoint of
record.

**Consequence for contract authors.** A completion requirement of the form
"run X against live relay data" is a gate only the operator can open, which
strands a finished node `exited` rather than `completed`. Gate on the
mock-relay fixture set instead — `tests/relay_mock.py` is in-tree and both
`bridge` and `registry` reuse it — and keep the live run as an explicitly
non-blocking operator-run follow-up. Design a CLI so it takes `--relay` and
document the one-command invocation, so the live run is trivial once a relay
exists.

## CLI syntax gotchas

- `fractal commit` takes the message positionally (no `-m`).
- `fractal radio reply` takes no `--subject` (inherits the parent
  message's).

## Python environment: worktree venvs on 3.13, not the shared 3.14 venv

The shared repo venv (`/Users/nealpatel/Code/l-system/.venv`) is Python
3.14, but `coincurve` (the secp256k1 dependency of `lindenmayer.core`)
ships no cp314 wheels and fails to build from source. Nodes that run the
test suite or add Python deps should use a worktree-local venv on 3.13:
`UV_PYTHON=3.13 uv sync --inexact` (setup.sh) and
`UV_PYTHON=3.13 uv run --inexact pytest tests/ -q` (test.sh). Always pass
`--inexact` — a bare `uv sync` strips packages other nodes installed.
Never rebuild or repoint the shared `.venv`; siblings depend on it.
`pyproject.toml`/`uv.lock` live at the repo root, outside every scoped
node's commit scope — dependency changes need
`fractal commit --ignore-scope`.
