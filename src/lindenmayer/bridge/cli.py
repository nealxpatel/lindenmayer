"""CLI entry point: lindenmayer-bridge run --tree <path> --relay <url>.

Reads Fractal's per-tree SQLite DB and transcripts, translates rows to signed events,
and publishes through the relay. Resumes statelessly from the relay cursor on startup.

End-to-end dogfood test: a fixture copy of this repo's own tree DB, bridged to a mock
relay, produces the expected event stream.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import pathlib
import sys
from datetime import datetime
from typing import TYPE_CHECKING

from lindenmayer.core.config import CoreConfig
from lindenmayer.core.keys import Keypair
from lindenmayer.core.relay import RelayClient

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def _epoch(iso_ts: str) -> int:
    """Source timestamp (ISO-8601 from Fractal rows) -> unix seconds."""
    return int(datetime.fromisoformat(iso_ts.replace("Z", "+00:00")).timestamp())


def run(args: argparse.Namespace) -> None:
    """Run the bridge: read Fractal tree, translate to events, publish to relay.

    Reads from $TREE/.fractal/<root>/.db (Fractal's per-tree SQLite).
    Publishes to $RELAY via Nostr NIP-01/NIP-29.
    Resumes statelessly from relay cursor on startup.

    Args:
        args: Parsed command-line arguments
    """
    logging.basicConfig(level=args.log_level.upper())

    tree_path = pathlib.Path(args.tree).resolve()
    if not tree_path.is_dir():
        print(f"Error: tree directory not found: {tree_path}", file=sys.stderr)
        sys.exit(1)

    fractal_dir = tree_path / ".fractal"
    if not fractal_dir.is_dir():
        print(f"Error: .fractal directory not found: {fractal_dir}", file=sys.stderr)
        sys.exit(1)

    db_path = fractal_dir / "main" / ".db"
    if not db_path.exists():
        print(f"Error: database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    try:
        core_config = (
            CoreConfig.from_toml(args.config) if args.config else CoreConfig(relay_url=args.relay)
        )
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        asyncio.run(_bridge_main(tree_path, db_path, args.relay, core_config, args.once))
    except KeyboardInterrupt:
        print("\nShutdown requested.", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        logger.exception("Bridge failed")
        sys.exit(1)


async def _bridge_main(
    tree_path: pathlib.Path,
    db_path: pathlib.Path,
    relay_url: str,
    config: CoreConfig,
    once: bool = False,
) -> None:
    """Main bridge loop: read Fractal, translate, publish.

    Args:
        tree_path: Tree root directory
        db_path: Path to Fractal's .db file
        relay_url: Relay URL
        config: Core configuration
        once: If True, run once and exit; if False, watch for changes
    """
    logger.info(f"Starting bridge: tree={tree_path}, relay={relay_url}")
    logger.info(f"Using database: {db_path}")

    try:
        from lindenmayer.bridge.adapters.sqlite import FractalDBReader
        from lindenmayer.bridge.identity import load_node_keypair, refuse_if_revoked
        from lindenmayer.bridge.publisher import Publisher
        from lindenmayer.bridge.translate import (
            translate_node_lifecycle,
            translate_run_accounting,
        )
    except ImportError as e:
        logger.error(f"Failed to import bridge modules: {e}")
        raise

    try:
        db_reader = FractalDBReader(str(db_path))
    except Exception as e:
        logger.error(f"Failed to open Fractal database: {e}")
        raise

    nodes = db_reader.get_nodes()
    logger.info(f"Loaded {len(nodes) if nodes else 0} nodes from database")

    # Connect to relay and set up publisher
    relay_client = RelayClient(relay_url, Keypair.from_hex("00" * 32), config)
    await relay_client.connect()

    try:
        events = []

        # Use reader's joined view for node lifecycle events
        for lifecycle_row in db_reader.get_node_lifecycle_rows():
            node_name = lifecycle_row["node"]
            keypair = load_node_keypair(node_name)
            if keypair is None:
                logger.debug(f"Node {node_name} is ephemeral, skipping")
                continue

            try:
                refuse_if_revoked(keypair.public_key_hex)
            except Exception as e:
                logger.warning(f"Node {node_name} attestation check failed: {e}")
                continue

            # Translate node lifecycle using actual reader output
            lifecycle = translate_node_lifecycle(lifecycle_row)
            if lifecycle is not None:
                event = lifecycle.to_event(
                    pubkey=keypair.public_key_hex,
                    created_at=_epoch(lifecycle_row["created_at"]),
                )
                events.append(keypair.sign_event(event))
                logger.debug(f"Translated lifecycle for {node_name} (run {lifecycle_row['run']})")

        # Translate run accounting
        for node_row in sorted(nodes, key=lambda r: r["node"]):
            node_name = node_row["node"]
            keypair = load_node_keypair(node_name)
            if keypair is None:
                continue

            for run_row in sorted(db_reader.get_runs(node_name), key=lambda r: r["run_id"]):
                if not run_row["ended_at"]:
                    continue  # active runs have no rollup yet

                accounting = translate_run_accounting(
                    {
                        "node": run_row["node"],
                        "run": str(run_row["run_id"]),
                        "status": run_row["status"],
                        "started_at": run_row["started_at"],
                        "ended_at": run_row["ended_at"],
                    },
                    transcript_usage={},
                )
                if accounting is not None:
                    event = accounting.to_event(
                        pubkey=keypair.public_key_hex,
                        created_at=_epoch(run_row["ended_at"]),
                    )
                    events.append(keypair.sign_event(event))
                    logger.debug(f"Translated accounting for run {run_row['run_id']}")

        logger.info(f"Translated {len(events)} events")

        # Publish events
        publisher = Publisher(relay_client, Keypair.from_hex("00" * 32))
        await publisher.resume_from_relay()
        await publisher.publish_events(events)

        logger.info("Bridge run complete")

        if not once:
            # Watch mode (not implemented yet)
            logger.info("Watching for changes (not yet implemented)")

    finally:
        await relay_client.close()


def main():
    parser = argparse.ArgumentParser(
        description="Run the bridge: read Fractal tree, translate to events, publish to relay."
    )
    parser.add_argument("--tree", required=True, help="Path to tree directory (contains .fractal/)")
    parser.add_argument("--relay", required=True, help="Relay URL")
    parser.add_argument("--config", help="Config file path (uses core's config module)")
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Logging level",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        default=False,
        help="Run once and exit (single-pass mode)",
    )

    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
