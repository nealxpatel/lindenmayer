"""CLI entry point for the bridge: lindenmayer-bridge run --tree <path> --relay <url>.

End-to-end dogfood test: a fixture copy of this repo's own tree DB, bridged to a mock
relay, produces the expected event stream.

Acceptance: an end-to-end dogfood test demonstrating the full flow.
"""

import click
from lindenmayer.core.config import Config


@click.command()
@click.option("--tree", required=True, help="Path to tree directory (contains .fractal/)")
@click.option("--relay", required=True, help="Relay URL")
@click.option("--config", help="Config file path (uses core's config module)")
def run(tree: str, relay: str, config: str | None):
    """Run the bridge: read Fractal tree, translate to events, publish to relay.

    Args:
        tree: Path to tree root (contains .fractal/ with .db)
        relay: Relay URL
        config: Optional config file path
    """
    pass


if __name__ == "__main__":
    run()
