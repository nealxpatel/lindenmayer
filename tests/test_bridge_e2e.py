"""End-to-end dogfood test for the bridge.

A fixture copy of THIS repo's own tree DB (tests/fixtures/tree.db, a snapshot of
the Fractal tree that builds Lindenmayer) is bridged to a mock relay and must
produce the expected event stream: one 42010 lifecycle event per node and one
42020 accounting rollup per finished run — never per step or per iteration.

Event ids must be deterministic (content and created_at derive from Fractal
source timestamps, never wall clock), so a full replay after a mid-stream
restart reproduces identical ids with no duplicates and no gaps.
"""

from __future__ import annotations

import pathlib
from datetime import datetime

import pytest

from lindenmayer.bridge.adapters.sqlite import FractalDBReader
from lindenmayer.bridge.publisher import Publisher
from lindenmayer.bridge.translate import (
    translate_node_lifecycle,
    translate_run_accounting,
)
from lindenmayer.core.config import CoreConfig
from lindenmayer.core.keys import Keypair
from lindenmayer.core.kinds import KIND_NODE_LIFECYCLE, KIND_RUN_ACCOUNTING
from lindenmayer.core.relay import RelayClient
from relay_mock import MockRelay

FIXTURE_DB = pathlib.Path(__file__).parent / "fixtures" / "tree.db"

EXAMPLE_SECRET = "0000000000000000000000000000000000000000000000000000000000000001"


def _epoch(iso_ts: str) -> int:
    """Source timestamp (ISO-8601 from Fractal rows) -> unix seconds."""
    return int(datetime.fromisoformat(iso_ts.replace("Z", "+00:00")).timestamp())


def _build_event_stream(keypair: Keypair) -> list:
    """Read the fixture tree DB using actual reader output, translate, and sign events.

    Uses the reader's joined lifecycle view to verify the adapter/translator seam.
    Pure function of the fixture DB and keypair — calling it twice must
    produce byte-identical events (the determinism the dogfood test asserts).
    """
    reader = FractalDBReader(str(FIXTURE_DB))
    events = []

    # Use reader's joined view for node lifecycle events (verifies adapter output shapes)
    for lifecycle_row in reader.get_node_lifecycle_rows():
        lifecycle = translate_node_lifecycle(lifecycle_row)
        assert lifecycle is not None, f"lifecycle translation failed for {lifecycle_row['node']} run {lifecycle_row['run']}"
        event = lifecycle.to_event(
            pubkey=keypair.public_key_hex,
            created_at=_epoch(lifecycle_row["created_at"]),
        )
        events.append(keypair.sign_event(event))

    # Translate run accounting using actual reader output
    for node_row in sorted(reader.get_nodes(), key=lambda r: r["node"]):
        for run_row in sorted(reader.get_runs(node_row["node"]), key=lambda r: r["run_id"]):
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
            assert accounting is not None, f"accounting translation failed for run {run_row['run_id']}"
            event = accounting.to_event(
                pubkey=keypair.public_key_hex,
                created_at=_epoch(run_row["ended_at"]),
            )
            events.append(keypair.sign_event(event))

    return events


@pytest.fixture
def keypair():
    return Keypair.from_hex(EXAMPLE_SECRET)


def test_fixture_db_is_own_tree():
    """The dogfood fixture really is a snapshot of this repo's own tree."""
    reader = FractalDBReader(str(FIXTURE_DB))
    branches = {row["node"] for row in reader.get_nodes()}
    assert "main.bridge" in branches
    assert "main.core" in branches


def test_event_stream_shape(keypair):
    """The translated stream has one 42010 per node and one 42020 per finished run."""
    reader = FractalDBReader(str(FIXTURE_DB))
    nodes = reader.get_nodes()
    finished_runs = [
        r for n in nodes for r in reader.get_runs(n["node"]) if r["ended_at"]
    ]

    events = _build_event_stream(keypair)
    kinds = [e.kind for e in events]
    assert kinds.count(KIND_NODE_LIFECYCLE) == len(nodes)
    assert kinds.count(KIND_RUN_ACCOUNTING) == len(finished_runs)
    assert set(kinds) == {KIND_NODE_LIFECYCLE, KIND_RUN_ACCOUNTING}
    # No per-step or per-iteration events exist anywhere in the stream.
    assert len(events) == len(nodes) + len(finished_runs)


def test_event_ids_deterministic(keypair):
    """Rebuilding the stream from the same source rows reproduces identical ids."""
    ids_first = [e.id for e in _build_event_stream(keypair)]
    ids_second = [e.id for e in _build_event_stream(keypair)]
    assert ids_first == ids_second


def test_created_at_from_source_rows(keypair):
    """created_at comes from Fractal source timestamps, never wall clock."""
    reader = FractalDBReader(str(FIXTURE_DB))
    source_ts = {
        _epoch(row["created_at"]) for row in reader.get_nodes()
    } | {
        _epoch(r["ended_at"])
        for n in reader.get_nodes()
        for r in reader.get_runs(n["node"])
        if r["ended_at"]
    }
    for event in _build_event_stream(keypair):
        assert event.created_at in source_ts


@pytest.mark.asyncio
async def test_dogfood_bridge_to_mock_relay(keypair):
    """Full pipeline: fixture tree DB -> translate -> sign -> publish -> relay.

    Restarts the publisher mid-stream and replays from the top: the relay must
    end up with exactly one copy of every event (no duplicates, no gaps).
    """
    events = _build_event_stream(keypair)
    assert len(events) > 0

    async with MockRelay() as relay:
        config = CoreConfig(relay_url=relay.url)
        client = RelayClient(relay.url, keypair, config)
        await client.connect()
        try:
            # First publisher gets halfway, then "crashes".
            half = len(events) // 2
            publisher = Publisher(client, keypair)
            await publisher.publish_events(events[:half])
            assert len(relay.events) == half

            # Fresh publisher (restart): resume from the relay cursor, then
            # replay the full stream from the top.
            publisher2 = Publisher(client, keypair)
            resume_points = await publisher2.resume_from_relay()
            assert resume_points is not None
            assert str(KIND_NODE_LIFECYCLE) in resume_points

            await publisher2.idempotent_replay(events)

            # No duplicates, no gaps: relay holds exactly the expected stream.
            relay_ids = [e["id"] for e in relay.events]
            assert len(relay_ids) == len(set(relay_ids)), "duplicate events on relay"
            assert set(relay_ids) == {e.id for e in events}, "gaps in relayed stream"
        finally:
            await client.close()


@pytest.mark.asyncio
async def test_cli_invocation_produces_expected_events(keypair, tmp_path):
    """CLI entry point: invoke with fixture tree and mock relay, verify event stream.

    Acceptance test for deliverable 5: the CLI must wire the full pipeline and produce
    the same event stream as the component-level E2E test.
    """
    import shutil
    from unittest.mock import patch

    from lindenmayer.bridge.cli import _bridge_main

    # Set up temp directory structure matching what CLI expects:
    # tree_path/.fractal/main/.db
    fixture_db = FIXTURE_DB
    tree_path = tmp_path
    fractal_dir = tree_path / ".fractal" / "main"
    fractal_dir.mkdir(parents=True)
    temp_db = fractal_dir / ".db"
    shutil.copy(fixture_db, temp_db)

    expected_events = _build_event_stream(keypair)
    assert len(expected_events) > 0

    # Mock load_node_keypair to return the test keypair for all nodes
    # (ensures CLI generates the same events as the component test)
    def mock_load_node_keypair(node_name: str):
        return keypair if node_name else None

    async with MockRelay() as relay:
        config = CoreConfig(relay_url=relay.url)

        # Patch the identity module's load_node_keypair
        with patch("lindenmayer.bridge.identity.load_node_keypair", side_effect=mock_load_node_keypair):
            # Also patch the import inside _bridge_main
            with patch("lindenmayer.bridge.cli.load_node_keypair", side_effect=mock_load_node_keypair):
                # Invoke CLI's main bridge function directly (tests the wired pipeline)
                await _bridge_main(
                    tree_path=tree_path,
                    db_path=temp_db,
                    relay_url=relay.url,
                    config=config,
                    once=True,  # single-pass mode
                )

        # Verify the relay has exactly the expected stream
        relay_ids = sorted([e["id"] for e in relay.events])
        expected_ids = sorted([e.id for e in expected_events])
        assert relay_ids == expected_ids, "CLI produced unexpected event stream"
        assert len(relay_ids) == len(set(relay_ids)), "CLI produced duplicate events"
