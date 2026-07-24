"""``lindenmayer-evergreen`` -- the "query own history" capability in full.

Usage::

    lindenmayer-evergreen --relay ws://localhost:8080 runs <branch>
    lindenmayer-evergreen --relay ws://localhost:8080 cost <branch>
    lindenmayer-evergreen --relay ws://localhost:8080 approvals <branch>
    lindenmayer-evergreen --relay ws://localhost:8080 templates <branch>

Every subcommand reads from the signed log only (via
``lindenmayer.evergreen.query.EvergreenQuery``) -- no write path, no local
index. All dollar figures are shadow cost (DESIGN.md §6), labeled as such in
every subcommand's output.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from lindenmayer.core.config import CoreConfig
from lindenmayer.core.keys import Keypair
from lindenmayer.core.relay import RelayClient
from lindenmayer.evergreen.query import EvergreenQuery

__all__ = ["main"]


def _create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lindenmayer-evergreen",
        description="Query a Lindenmayer node's own history from the signed log (read-only).",
    )
    parser.add_argument("--relay", required=True, help="Relay URL (ws:// or wss://)")
    parser.add_argument("--author", help="Scope to one signing pubkey (default: all authors)")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    runs_parser = subparsers.add_parser("runs", help="A node's runs over time")
    runs_parser.add_argument("branch", help="Node branch name")

    cost_parser = subparsers.add_parser("cost", help="Cost/token rollups (shadow cost)")
    cost_parser.add_argument("branch", help="Node branch name")

    approvals_parser = subparsers.add_parser("approvals", help="Approval traces (42040/42041)")
    approvals_parser.add_argument("branch", help="Node branch name")

    templates_parser = subparsers.add_parser(
        "templates", help="Template-version -> instance linkage for a branch's runs"
    )
    templates_parser.add_argument("branch", help="Node branch name")

    return parser


async def _cmd_runs(args: argparse.Namespace, query: EvergreenQuery) -> int:
    records = await query.run_accounting(branch=args.branch, author=args.author)
    if not records:
        print(f"No runs found for {args.branch}")
        return 0
    print(f"Runs for {args.branch} ({len(records)} total):")
    for record in sorted(records, key=lambda r: r.created_at):
        m = record.model
        print(
            f"  {m.run}: {m.exit_status}, {m.iter_count} iters, "
            f"${m.cost_shadow_usd:.4f} shadow cost, {m.duration_s:.1f}s"
        )
    return 0


async def _cmd_cost(args: argparse.Namespace, query: EvergreenQuery) -> int:
    records = await query.run_accounting(branch=args.branch, author=args.author)
    if not records:
        print(f"No cost data found for {args.branch}")
        return 0
    total = sum(r.model.cost_shadow_usd for r in records)
    total_iters = sum(r.model.iter_count for r in records)
    print(f"Cost rollup for {args.branch} (all figures are shadow cost, DESIGN.md §6):")
    for record in sorted(records, key=lambda r: r.created_at):
        m = record.model
        print(f"  {m.run}: ${m.cost_shadow_usd:.4f} shadow cost over {m.iter_count} iters")
    print(f"  TOTAL: ${total:.4f} shadow cost over {total_iters} iters across {len(records)} run(s)")
    return 0


async def _cmd_approvals(args: argparse.Namespace, query: EvergreenQuery) -> int:
    records = await query.approval_requests(branch=args.branch, author=args.author)
    if not records:
        print(f"No approval requests found for {args.branch}")
        return 0
    print(f"Approval trace for {args.branch} ({len(records)} request(s)):")
    for record in sorted(records, key=lambda r: r.created_at):
        m = record.model
        counts = await query.approval_status(record.event_id)
        if counts.approve_count == 0 and counts.reject_count == 0:
            verdict = "pending"
        elif counts.approve_count > counts.reject_count:
            verdict = f"approved ({counts.approve_count} approve, {counts.reject_count} reject)"
        else:
            verdict = f"rejected ({counts.approve_count} approve, {counts.reject_count} reject)"
        print(f"  [{m.step}] {m.step_name}: {m.summary!r} -- {verdict}")
    return 0


async def _cmd_templates(args: argparse.Namespace, query: EvergreenQuery) -> int:
    records = await query.run_accounting(branch=args.branch, author=args.author)
    linked = [r for r in records if r.model.template is not None]
    if not linked:
        print(f"No template-linked runs found for {args.branch}")
        return 0
    print(f"Template-version -> instance linkage for {args.branch}:")
    for record in sorted(linked, key=lambda r: r.created_at):
        template_id = record.model.template
        version = await query.template_version_by_id(template_id)
        if version is None:
            print(f"  {record.model.run}: template event {template_id} (not found or unverified)")
            continue
        v = version.model
        label = f"{v.template_name} v{v.version} @ {v.git_ref or '?'}"
        print(f"  {record.model.run}: {label}")
    return 0


_COMMANDS = {
    "runs": _cmd_runs,
    "cost": _cmd_cost,
    "approvals": _cmd_approvals,
    "templates": _cmd_templates,
}


async def main_async(args: argparse.Namespace) -> int:
    if not args.command:
        return 1
    handler = _COMMANDS.get(args.command)
    if handler is None:
        print(f"unknown command: {args.command}", file=sys.stderr)
        return 1
    try:
        config = CoreConfig(relay_url=args.relay)
        keypair = Keypair.generate()  # read-only client identity; signs nothing
        async with RelayClient(args.relay, keypair, config) as client:
            query = EvergreenQuery(client)
            return await handler(args, query)
    except Exception as e:  # noqa: BLE001 -- CLI boundary: report, don't traceback
        print(f"error: {e}", file=sys.stderr)
        return 1


def main() -> None:
    """Entry point (also reachable as ``python -m lindenmayer.evergreen.cli``)."""
    parser = _create_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)
    sys.exit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
