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

## CLI syntax gotchas

- `fractal commit` takes the message positionally (no `-m`).
- `fractal radio reply` takes no `--subject` (inherits the parent
  message's).
