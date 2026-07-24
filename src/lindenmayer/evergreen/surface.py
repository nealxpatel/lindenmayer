"""Context-surface generator: emits the ``CONTEXT.md``-shaped standing surface.

A composite of three independently-sourced pieces (tree/evergreen/NODE.md
deliverable 2; conditions 1 and 2, evergreen countersign):

- A human-authored **preamble** (mission, phase, non-negotiables, governance
  mode, pointers), read verbatim from an operator-owned TOML file. These are
  decisions, not derived facts, so they are never generated.
- A generated **situational block**, derived from ``EvergreenQuery``
  (deliverable 1) ONLY -- never from Fractal's SQLite directly. SQLite holds
  exactly the step-level detail the wire format excludes; anything committed,
  exported, or cross-posted from this module must carry no more than the
  signed log already does (DESIGN.md §5.1, §6.1).
- A **model-policy** block that reads the LIVE assignment -- a third,
  distinct source: each node's own tracked seed files (``config.json``'s
  ``model`` field, and ``model:`` frontmatter pins in ``steps/*.md``) --
  never the SQLite telemetry DB and never a relay query. This is deliberately
  not derived from deliverable 1: it is neither the human-authored preamble
  nor the log-derived situational block, and restating the tier assignment
  as prose (as two prior surfaces did) is exactly what §3 forbids.

No local index: every call re-queries the relay and re-reads the preamble
and model-policy sources fresh (DESIGN.md §6.2).

One-command live invocation, the moment a relay endpoint is supplied
(this is an operator follow-up -- the mock-relay fixture set gates
completion, per condition 3, evergreen countersign; a live run is never
required to demonstrate the generator working)::

    python -m lindenmayer.evergreen.surface \\
        --relay ws://localhost:7100 --branch main.evergreen \\
        --preamble path/to/preamble.toml --node-dir path/to/.fractal/main.evergreen
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

from lindenmayer.core.config import CoreConfig
from lindenmayer.core.keys import Keypair
from lindenmayer.core.relay import RelayClient
from lindenmayer.evergreen.query import EvergreenQuery

__all__ = [
    "ModelPolicy",
    "Preamble",
    "generate_surface",
    "read_model_policy",
    "read_preamble",
]


# -- preamble: human-authored, read verbatim --------------------------------


@dataclass(frozen=True, slots=True)
class Preamble:
    """The human-authored standing context -- never generated."""

    mission: str
    phase: str
    non_negotiables: list[str]
    governance_mode: str
    pointers: list[str]


def read_preamble(path: str | Path) -> Preamble:
    """Read the operator-authored preamble from a TOML file."""
    data = tomllib.loads(Path(path).read_text())
    return Preamble(
        mission=data["mission"],
        phase=data["phase"],
        non_negotiables=list(data.get("non_negotiables", [])),
        governance_mode=data.get("governance_mode", "veto"),
        pointers=list(data.get("pointers", [])),
    )


# -- model policy: live assignment, never a restated tier table -------------


@dataclass(frozen=True, slots=True)
class ModelPolicy:
    """The live model assignment for one node: its default model plus any
    per-step pins (e.g. REVIEW pinned to opus via step frontmatter)."""

    node: str
    default_model: str | None
    step_pins: dict[str, str]


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Minimal ``---\\nkey: value\\n---`` frontmatter reader.

    No YAML dependency -- a new runtime dependency is an automatic architect
    consultation (NODE.md), and every value used here (``model: opus``) is a
    bare scalar, so a line-oriented ``key: value`` split is sufficient.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    out: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def read_model_policy(node_dir: str | Path) -> ModelPolicy:
    """Read the live model assignment for a Fractal node from its own
    tracked seed files: ``config.json``'s ``model`` field (the node's
    default) and each ``steps/*.md`` file's frontmatter ``model:`` override
    (a per-step pin). These are Fractal's own extension-surface files, not
    the SQLite telemetry DB and not a relay query (module docstring).
    """
    node_dir = Path(node_dir)
    default_model = None
    config_path = node_dir / "config.json"
    if config_path.is_file():
        default_model = json.loads(config_path.read_text()).get("model")
    step_pins: dict[str, str] = {}
    steps_dir = node_dir / "steps"
    if steps_dir.is_dir():
        for step_file in sorted(steps_dir.glob("*.md")):
            model = _parse_frontmatter(step_file.read_text()).get("model")
            if model:
                step_name = step_file.stem.split("-", 1)[-1]  # "03-REVIEW" -> "REVIEW"
                step_pins[step_name] = model
    return ModelPolicy(node=node_dir.name, default_model=default_model, step_pins=step_pins)


# -- situational block: derived from EvergreenQuery only --------------------


async def _situational_block(query: EvergreenQuery, branch: str) -> str:
    lines = ["## Situational state (live, from the signed log)", ""]

    pointer = await query.node_state_pointer(branch)
    if pointer is not None:
        p = pointer.model
        lines.append(f"- **Current state:** `{p.status}` (run {p.run}, iter {p.iter})")
        lines.append(
            f"- **Spend:** ${p.cost_shadow_usd:.2f} shadow cost of ${p.cost_cap_usd:.2f} cap"
        )
    else:
        lines.append("- **Current state:** unknown (no kind-38110 pointer published yet)")

    digests = await query.subgraph_digest(branch=branch)
    if digests:
        d = max(digests, key=lambda r: r.created_at).model
        lines.append(
            f"- **Subgraph:** {d.child_count} children ({d.active} active, {d.completed} "
            f"completed, {d.exited} exited, {d.stuck_flagged} stuck-flagged); subtree spend "
            f"${d.subtree_cost_shadow_usd:.2f} shadow cost"
        )
    else:
        lines.append("- **Subgraph:** no digest published yet")

    pending = await query.pending_approvals(branch=branch)
    if pending:
        lines.append(f"- **Pending approval gates:** {len(pending)}")
        for record in pending:
            r = record.model
            lines.append(f"  - `{r.step}` ({r.step_name}): {r.summary}")
    else:
        lines.append("- **Pending approval gates:** none")

    lifecycle = await query.node_lifecycle(branch=branch)
    if lifecycle:
        recent = sorted(lifecycle, key=lambda r: r.created_at, reverse=True)[:5]
        lines.append("- **Recent lifecycle:**")
        for record in recent:
            lines.append(f"  - {record.model.status} (run {record.model.run})")
    else:
        lines.append("- **Recent lifecycle:** no events published yet")

    return "\n".join(lines)


def _model_policy_block(policy: ModelPolicy) -> str:
    lines = ["## Model policy (live assignment)", ""]
    lines.append(f"- **{policy.node} default:** {policy.default_model or 'unset'}")
    if policy.step_pins:
        lines.append("- **Step pins:**")
        for step, model in sorted(policy.step_pins.items()):
            lines.append(f"  - {step}: {model}")
    else:
        lines.append("- **Step pins:** none")
    return "\n".join(lines)


# -- composite ---------------------------------------------------------------


async def generate_surface(
    query: EvergreenQuery,
    *,
    branch: str,
    preamble: Preamble,
    model_policy: ModelPolicy,
) -> str:
    """Compose the full ``CONTEXT.md``-shaped surface for ``branch``.

    Human-authored preamble + generated situational block (deliverable 1
    only) + live model-policy block. No local index: every call re-derives
    from a fresh query and fresh file reads.
    """
    situational = await _situational_block(query, branch)
    parts = [
        f"# {branch} -- Evergreen Context",
        "",
        f"**Mission:** {preamble.mission}",
        f"**Phase:** {preamble.phase}",
        f"**Governance mode:** {preamble.governance_mode}",
        "",
        "## Non-negotiables",
        "",
        *(f"- {item}" for item in preamble.non_negotiables),
        "",
        situational,
        "",
        _model_policy_block(model_policy),
        "",
        "## Pointers",
        "",
        *(f"- {p}" for p in preamble.pointers),
        "",
    ]
    return "\n".join(parts)


# -- one-command live invocation ---------------------------------------------


def _create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lindenmayer-evergreen-surface",
        description="Generate the CONTEXT.md-shaped standing surface for one branch.",
    )
    parser.add_argument("--relay", required=True, help="Relay URL (ws:// or wss://)")
    parser.add_argument("--branch", required=True, help="Node branch name")
    parser.add_argument("--preamble", required=True, help="Path to the operator-authored preamble TOML")
    parser.add_argument("--node-dir", required=True, help="Path to the node's .fractal/<branch> directory")
    parser.add_argument("--author", help="Scope the situational query to one signing pubkey")
    return parser


async def _main_async(args: argparse.Namespace) -> int:
    try:
        preamble = read_preamble(args.preamble)
        model_policy = read_model_policy(args.node_dir)
        config = CoreConfig(relay_url=args.relay)
        keypair = Keypair.generate()  # read-only client identity; signs nothing
        async with RelayClient(args.relay, keypair, config) as client:
            query = EvergreenQuery(client)
            surface = await generate_surface(
                query, branch=args.branch, preamble=preamble, model_policy=model_policy
            )
        print(surface)
        return 0
    except Exception as e:  # noqa: BLE001 -- CLI boundary: report, don't traceback
        print(f"error: {e}", file=sys.stderr)
        return 1


def main() -> None:
    """Entry point (also reachable as ``python -m lindenmayer.evergreen.surface``)."""
    args = _create_parser().parse_args()
    sys.exit(asyncio.run(_main_async(args)))


if __name__ == "__main__":
    main()
