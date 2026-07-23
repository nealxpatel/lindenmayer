"""Read-only SQLite adapter for Fractal's per-tree database.

Tables: nodes, runs, iters, steps, events, messages.
WAL-safe, never writes.
"""

import sqlite3
from pathlib import Path


class FractalDBReader:
    """Read-only reader for Fractal's per-tree SQLite DB."""

    def __init__(self, db_path: str):
        """Initialize the reader.

        Args:
            db_path: Path to the .db file
        """
        self.db_path = db_path
        # Set up WAL-safe read mode
        self.conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        """Close the underlying database connection."""
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_nodes(self):
        """Read all nodes from the registry."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT node_id, node, title, status, max_cost, max_depth, max_children, max_descendants, created_at FROM nodes")
        return [dict(row) for row in cursor.fetchall()]

    def get_runs(self, node: str):
        """Read all runs for a given node."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT run_id, node, parent_run_id, agent, max_cost, status, exit_code, metadata, started_at, ended_at FROM runs WHERE node = ?",
            (node,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_node_lifecycle_rows(self):
        """Get node-run joined rows for lifecycle translation.

        Returns one row per persistent node with a finished run.
        Each node's row represents its latest finished run status (a status transition).
        Fields: node, status, run (run_id as TEXT), created_at (from run end).
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                n.node,
                r.status,
                CAST(r.run_id AS TEXT) AS run,
                r.ended_at AS created_at
            FROM nodes n
            INNER JOIN (
                SELECT * FROM runs
                WHERE ended_at IS NOT NULL
                AND run_id = (
                    SELECT MAX(run_id) FROM runs r2
                    WHERE r2.node = runs.node AND r2.ended_at IS NOT NULL
                )
            ) r ON n.node = r.node
            ORDER BY n.node
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_iters(self, run_id: int):
        """Read all iterations for a given run."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT iter_id, node, run_id, iter, agent, model, session, status, exit_code, metadata, started_at, ended_at FROM iters WHERE run_id = ?",
            (run_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_steps(self, iter_id: int):
        """Read all steps for a given iteration."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT step_id, node, iter_id, run_id, step, step_name, agent, model, session, status, exit_code, cost, approved, metadata, started_at, ended_at FROM steps WHERE iter_id = ?",
            (iter_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_latest_event(self, node: str) -> dict | None:
        """Query own latest published event for a node."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT event_id, node, step_id, iter_id, run_id, event, actor, status, exit_code, metadata, created_at FROM events WHERE node = ? ORDER BY created_at DESC LIMIT 1",
            (node,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
