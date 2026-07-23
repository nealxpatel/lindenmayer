"""Read-only SQLite adapter for Fractal's per-tree database.

Tables: nodes, runs, iters, steps, events, messages.
WAL-safe, never writes.
"""


class FractalDBReader:
    """Read-only reader for Fractal's per-tree SQLite DB."""

    def __init__(self, db_path: str):
        """Initialize the reader.

        Args:
            db_path: Path to the .db file
        """
        pass

    def get_nodes(self):
        """Read all nodes from the registry."""
        pass

    def get_runs(self, node: str):
        """Read all runs for a given node."""
        pass

    def get_iters(self, run_id: int):
        """Read all iterations for a given run."""
        pass

    def get_steps(self, iter_id: int):
        """Read all steps for a given iteration."""
        pass

    def get_latest_event(self, node: str) -> dict | None:
        """Query own latest published event for a node."""
        pass
