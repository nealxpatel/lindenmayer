---
name: technical_notes
desc: Environment, dependency, and upstream-source facts that bite if forgotten.
created: 2026-07-23T15:55:28Z
updated: 2026-07-23T15:55:28Z
---

# technical_notes

## Python / deps

- coincurve has NO cp314 wheels; the shared repo `.venv` is Python 3.14 and
  must stay untouched for siblings. This worktree (and each child) uses a
  worktree-local `.venv` on Python 3.13: `UV_PYTHON=3.13 uv sync --inexact`
  in setup.sh; `UV_PYTHON=3.13 uv run --inexact pytest tests/ -q` in
  test.sh. `--inexact` avoids stripping siblings' packages.
- coincurve `sign_schnorr` only signs 32-byte messages — BIP-340 vectors
  15–18 (variable-length msgs) are excluded from the SIGN test (still in the
  VERIFY test). Nostr only signs 32-byte ids, so no functional gap.
- Runtime deps (justified in plan core_foundation): coincurve, pydantic v2,
  websockets. Dev: pytest, pytest-asyncio.

## Scope / commit mechanics

- `pyproject.toml` and `uv.lock` live at repo root — OUT of my scope
  (src/tests/docs/kinds). Dep changes need
  `fractal commit --ignore-scope "..."`. Same for synced transcripts.

## Upstream (block/buzz) facts

- kind.rs real path: `crates/buzz-core/src/kind.rs` (DESIGN.md §8 cites
  `buzz-core/src/kind.rs` — stale). Checked at commit 06e3d82.
- Buzz 40000–49999 allocations at that commit: 40001–40008, 40099, 40100,
  40901–40902, 41001, 41010–41012, 42000, 43001–43006, 44100/44101/44200,
  45001–45003, 46001–46031, 48001/48100–48106, 49001. Nothing in 381xx.
  All eight Lindenmayer proposals clear.
- NIP-OA is an `auth` TAG (four elements, preimage
  `nostr:agent-auth:<agent-pubkey>:<conditions>`, BIP-340), NOT an event
  kind — corrects event-kinds.md §1.7's "presumed addressable". NIP-AM =
  kind 44200 per-turn metrics; NIP-AO = kind 24200 ephemeral frames.
- Sparse clone lives in node tmp/buzz (scratch — refetch if gone); NIP
  drafts copied into each child's node tmp/nips/.

## Test vectors in repo

- `tests/vectors/bip340_vectors.csv` — verbatim bitcoin/bips bip-0340.
- `tests/vectors/nip_oa_signed_event.json` — verbatim NIP-OA signed-event
  example; independent-implementation NIP-01 id+sig vector.
