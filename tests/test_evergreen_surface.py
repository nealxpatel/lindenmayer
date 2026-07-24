"""Golden test for the context-surface generator, plus proof that its
model-policy block reads the live assignment rather than restating tiers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evergreen_helpers import BRANCH, build_fixture_events
from lindenmayer.core.config import CoreConfig
from lindenmayer.core.keys import Keypair
from lindenmayer.core.relay import RelayClient
from lindenmayer.evergreen.query import EvergreenQuery
from lindenmayer.evergreen.surface import generate_surface, read_model_policy, read_preamble
from relay_mock import MockRelay

FIXTURES = Path(__file__).parent / "fixtures" / "evergreen"


@pytest.fixture
def keypair() -> Keypair:
    return Keypair.generate()


@pytest.mark.asyncio
async def test_generate_surface_golden(keypair: Keypair):
    preamble = read_preamble(FIXTURES / "preamble.toml")
    model_policy = read_model_policy(FIXTURES / "node_a")
    # Sanity on the fixture inputs the golden below is pinned to.
    assert model_policy.default_model == "sonnet"
    assert model_policy.step_pins == {"REVIEW": "opus"}

    async with MockRelay() as relay:
        events = build_fixture_events(keypair)
        for event in events.values():
            relay.events.append(event.to_dict())
        config = CoreConfig(relay_url=relay.url)
        async with RelayClient(relay.url, keypair, config) as client:
            query = EvergreenQuery(client)
            surface = await generate_surface(
                query, branch=BRANCH, preamble=preamble, model_policy=model_policy
            )

    assert surface == EXPECTED_SURFACE


@pytest.mark.asyncio
async def test_model_policy_block_reflects_changed_live_assignment(tmp_path, keypair: Keypair):
    """Change the live assignment (config.json's model field) and assert the
    surface's model-policy block changes to match -- proving it reads live
    rather than restating a fixed tier table (NODE.md deliverable 2 acceptance)."""
    node_dir = tmp_path / "node_b"
    (node_dir / "steps").mkdir(parents=True)
    (node_dir / "config.json").write_text(json.dumps({"model": "sonnet"}))

    preamble = read_preamble(FIXTURES / "preamble.toml")

    async with MockRelay() as relay:
        config = CoreConfig(relay_url=relay.url)
        async with RelayClient(relay.url, keypair, config) as client:
            query = EvergreenQuery(client)

            policy_before = read_model_policy(node_dir)
            surface_before = await generate_surface(
                query, branch="main.demo2", preamble=preamble, model_policy=policy_before
            )
            assert "**node_b default:** sonnet" in surface_before
            assert "**node_b default:** opus" not in surface_before

            # Live re-assignment: the operator repoints this node to opus.
            (node_dir / "config.json").write_text(json.dumps({"model": "opus"}))

            policy_after = read_model_policy(node_dir)
            surface_after = await generate_surface(
                query, branch="main.demo2", preamble=preamble, model_policy=policy_after
            )
            assert "**node_b default:** opus" in surface_after
            assert "**node_b default:** sonnet" not in surface_after


EXPECTED_SURFACE = """\
# main.demo -- Evergreen Context

**Mission:** Build Lindenmayer -- a control plane for governing Fractal agent subgraphs through Buzz.
**Phase:** bootstrap
**Governance mode:** veto

## Non-negotiables

- Never patch or fork Fractal; integrate only through its extension surfaces.
- Aggregates flow up, details stay in the subgraph.
- No new storage systems: the signed event log is the history.

## Situational state (live, from the signed log)

- **Current state:** `completed` (run run-1, iter 3)
- **Spend:** $1.23 shadow cost of $25.00 cap
- **Subgraph:** 1 children (0 active, 1 completed, 0 exited, 0 stuck-flagged); subtree spend $1.23 shadow cost
- **Pending approval gates:** 1
  - `deploy` (deploy): ship to prod
- **Recent lifecycle:**
  - completed (run run-1)
  - started (run run-1)

## Model policy (live assignment)

- **node_a default:** sonnet
- **Step pins:**
  - REVIEW: opus

## Pointers

- docs/DESIGN.md
- tree/root/CONTEXT.md
"""
