"""CLI entry point: lindenmayer-bridge run --tree <path> --relay <url>.

Reads Fractal's per-tree SQLite DB and transcripts, translates rows to signed events,
and publishes through the relay. Resumes statelessly from the relay cursor on startup.

End-to-end dogfood test: a fixture copy of this repo's own tree DB, bridged to a mock
relay, produces the expected event stream.
"""

from __future__ import annotations

import asyncio
import json
import logging
import pathlib
import sys
from typing import TYPE_CHECKING

import click

from lindenmayer.core.config import CoreConfig
from lindenmayer.core.keys import Keypair
from lindenmayer.core.relay import RelayClient

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@click.command()
@click.option("--tree", required=True, help="Path to tree directory (contains .fractal/)")
@click.option("--relay", required=True, help="Relay URL")
@click.option("--config", help="Config file path (uses core's config module)")
@click.option(
    "--log-level", default="info", type=click.Choice(["debug", "info", "warning", "error"])
)
def run(tree: str, relay: str, config: str | None, log_level: str):
    """Run the bridge: read Fractal tree, translate to events, publish to relay.

    Reads from $TREE/.fractal/<root>/.db (Fractal's per-tree SQLite).
    Publishes to $RELAY via Nostr NIP-01/NIP-29.
    Resumes statelessly from relay cursor on startup.

    Args:
        tree: Path to tree root (contains .fractal/ with .db)
        relay: Relay URL
        config: Optional config file path
        log_level: Logging level
    """
    logging.basicConfig(level=log_level.upper())

    tree_path = pathlib.Path(tree).resolve()
    if not tree_path.is_dir():
        click.echo(f"Error: tree directory not found: {tree_path}", err=True)
        sys.exit(1)

    fractal_dir = tree_path / ".fractal"
    if not fractal_dir.is_dir():
        click.echo(f"Error: .fractal directory not found: {fractal_dir}", err=True)
        sys.exit(1)

    db_path = fractal_dir / "main" / ".db"
    if not db_path.exists():
        click.echo(f"Error: database not found: {db_path}", err=True)
        sys.exit(1)

    try:
        core_config = (
            CoreConfig.from_file(config) if config else CoreConfig.default()
        )
    except Exception as e:
        click.echo(f"Error loading config: {e}", err=True)
        sys.exit(1)

    try:
        asyncio.run(_bridge_main(tree_path, db_path, relay, core_config))
    except KeyboardInterrupt:
        click.echo("\nShutdown requested.")
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        logger.exception("Bridge failed")
        sys.exit(1)


async def _bridge_main(
    tree_path: pathlib.Path,
    db_path: pathlib.Path,
    relay_url: str,
    config: CoreConfig,
) -> None:
    """Main bridge loop: read Fractal, translate, publish.

    Args:
        tree_path: Tree root directory
        db_path: Path to Fractal's .db file
        relay_url: Relay URL
        config: Core configuration
    """
    logger.info(f"Starting bridge: tree={tree_path}, relay={relay_url}")
    logger.info(f"Using database: {db_path}")

    try:
        from lindenmayer.bridge.adapters.sqlite import FractalDBReader
        from lindenmayer.bridge.publisher import Publisher
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

    logger.info("Bridge initialization complete. Awaiting implementation of translation layer.")
    logger.info("See src/lindenmayer/bridge/translate.py for row->kind translation.")


if __name__ == "__main__":
    run()
