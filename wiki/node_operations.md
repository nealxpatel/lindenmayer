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

## `.fractal/` is gitignored here

This repo gitignores `.fractal/` (runtime state; versioned node contracts
live in `tree/` instead — see CLAUDE.md). Consequences when spawning:

- `fractal commit --init` in a fresh child worktree fails with "paths
  ignored by .gitignore" because the seed is not committable. This is fine:
  the child's worktree is clean w.r.t. tracked files and starts normally
  without the baseline commit.
- A child's NODE.md/memory/plans therefore never travel through git — edit
  them on disk in the child's worktree; merge-up carries only project
  files.

## CLI syntax gotchas

- `fractal commit` takes the message positionally (no `-m`).
- `fractal radio reply` takes no `--subject` (inherits the parent
  message's).
