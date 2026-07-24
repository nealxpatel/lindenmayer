"""Tests for EvergreenQuery against a mock relay, per fixture in evergreen_helpers."""

from __future__ import annotations

import pytest

from evergreen_helpers import BRANCH, RUN, TEMPLATE_NAME, build_fixture_events, tamper
from lindenmayer.core.config import CoreConfig
from lindenmayer.core.keys import Keypair
from lindenmayer.core.relay import RelayClient
from lindenmayer.evergreen.query import EvergreenQuery, QueryError
from relay_mock import MockRelay


@pytest.fixture
def keypair() -> Keypair:
    return Keypair.generate()


@pytest.fixture
async def query_with_events(keypair: Keypair):
    """A (EvergreenQuery, fixture events dict) pair against a live MockRelay,
    with all nine kinds' fixture events already published."""
    async with MockRelay() as relay:
        events = build_fixture_events(keypair)
        for event in events.values():
            relay.events.append(event.to_dict())
        config = CoreConfig(relay_url=relay.url)
        async with RelayClient(relay.url, keypair, config) as client:
            yield EvergreenQuery(client), events


@pytest.mark.asyncio
async def test_node_lifecycle(query_with_events):
    query, events = query_with_events
    records = await query.node_lifecycle(branch=BRANCH)
    assert {r.event_id for r in records} == {
        events["lifecycle_started"].id,
        events["lifecycle_completed"].id,
    }
    statuses = {r.model.status for r in records}
    assert statuses == {"started", "completed"}


@pytest.mark.asyncio
async def test_node_lifecycle_scoped_to_other_branch_is_empty(query_with_events):
    query, _events = query_with_events
    records = await query.node_lifecycle(branch="main.someone_else")
    assert records == []


@pytest.mark.asyncio
async def test_node_state_pointer_latest(query_with_events):
    query, events = query_with_events
    record = await query.node_state_pointer(BRANCH)
    assert record is not None
    assert record.event_id == events["state_pointer"].id
    assert record.model.status == "completed"
    assert record.model.cost_shadow_usd == 1.23


@pytest.mark.asyncio
async def test_node_state_pointer_addressable_latest_wins(keypair: Keypair):
    """Two pointer events for the same branch/d-tag: the newer created_at wins."""
    from lindenmayer.core.event import Event

    async with MockRelay() as relay:
        older = keypair.sign_event(
            Event.build(
                pubkey=keypair.public_key_hex,
                kind=38110,
                tags=[["d", "main.x"], ["status", "active"], ["run", "r"], ["iter", "1"]],
                content='{"cost_shadow_usd":0.1,"cost_cap_usd":5.0,"last_lifecycle_event":"' + "0" * 64 + '"}',
                created_at=100,
            )
        )
        newer = keypair.sign_event(
            Event.build(
                pubkey=keypair.public_key_hex,
                kind=38110,
                tags=[["d", "main.x"], ["status", "completed"], ["run", "r"], ["iter", "2"]],
                content='{"cost_shadow_usd":0.2,"cost_cap_usd":5.0,"last_lifecycle_event":"' + "1" * 64 + '"}',
                created_at=200,
            )
        )
        relay.events.append(older.to_dict())
        relay.events.append(newer.to_dict())
        config = CoreConfig(relay_url=relay.url)
        async with RelayClient(relay.url, keypair, config) as client:
            query = EvergreenQuery(client)
            record = await query.node_state_pointer("main.x")
            assert record is not None
            assert record.event_id == newer.id
            assert record.model.status == "completed"


@pytest.mark.asyncio
async def test_run_accounting(query_with_events):
    query, events = query_with_events
    records = await query.run_accounting(branch=BRANCH)
    assert len(records) == 1
    assert records[0].event_id == events["run_accounting"].id
    assert records[0].model.run == RUN
    assert records[0].model.cost_shadow_usd == 1.23


@pytest.mark.asyncio
async def test_subgraph_digest(query_with_events):
    query, events = query_with_events
    records = await query.subgraph_digest(branch=BRANCH)
    assert len(records) == 1
    assert records[0].event_id == events["subgraph_digest"].id
    assert records[0].model.completed == 1


@pytest.mark.asyncio
async def test_approval_requests(query_with_events):
    query, events = query_with_events
    records = await query.approval_requests(branch=BRANCH)
    assert {r.event_id for r in records} == {
        events["approval_request_resolved"].id,
        events["approval_request_pending"].id,
    }


@pytest.mark.asyncio
async def test_approval_status_resolved(query_with_events):
    query, events = query_with_events
    counts = await query.approval_status(events["approval_request_resolved"].id)
    assert counts.approve_count == 1
    assert counts.reject_count == 0


@pytest.mark.asyncio
async def test_approval_status_missing_request_raises(query_with_events):
    query, _events = query_with_events
    with pytest.raises(QueryError):
        await query.approval_status("0" * 64)


@pytest.mark.asyncio
async def test_pending_approvals(query_with_events):
    query, events = query_with_events
    pending = await query.pending_approvals(branch=BRANCH)
    assert len(pending) == 1
    assert pending[0].event_id == events["approval_request_pending"].id


@pytest.mark.asyncio
async def test_template_versions(query_with_events):
    query, events = query_with_events
    records = await query.template_versions(template_name=TEMPLATE_NAME)
    assert len(records) == 1
    assert records[0].event_id == events["template_version"].id
    assert records[0].model.version == "2"


@pytest.mark.asyncio
async def test_template_pointer(query_with_events):
    query, events = query_with_events
    record = await query.template_pointer(TEMPLATE_NAME)
    assert record is not None
    assert record.model.version_event_id == events["template_version"].id


@pytest.mark.asyncio
async def test_compactions(query_with_events):
    query, events = query_with_events
    records = await query.compactions(branch=BRANCH)
    assert len(records) == 1
    comp = records[0]
    assert comp.event_id == events["compaction"].id
    assert comp.summary_of == events["lifecycle_started"].id
    assert comp.detection == "harness-marker"
    assert comp.pre_tokens == 50000
    assert comp.post_tokens == 8000
    # summary text is never carried -- only metrics and a hash (§6.1)
    assert comp.summary_hash == "deadbeef" * 8


# -- tampered-event rejection (deliverable 1 acceptance) --------------------


@pytest.mark.asyncio
async def test_tampered_event_dropped_by_relay_layer(keypair: Keypair):
    """A tampered event fails Event.verify() at the relay client's own
    ingestion boundary (core.relay.RelayClient._handle_event) and is never
    delivered to a query() caller at all -- the query surface sees nothing,
    not an error."""
    async with MockRelay() as relay:
        events = build_fixture_events(keypair)
        good = events["lifecycle_started"]
        bad = tamper(events["lifecycle_completed"])
        assert not bad.verify()  # sanity: the tamper actually broke verification
        relay.events.append(good.to_dict())
        relay.events.append(bad.to_dict())
        config = CoreConfig(relay_url=relay.url)
        async with RelayClient(relay.url, keypair, config) as client:
            query = EvergreenQuery(client)
            records = await query.node_lifecycle(branch=BRANCH)
            assert {r.event_id for r in records} == {good.id}


# -- relay-ignores-the-filter regression (NIP-01 single-letter tag filters) --


@pytest.mark.asyncio
async def test_multi_char_tag_constraint_enforced_client_side(keypair: Keypair):
    """A branch-scoped query must not leak another branch's events.

    NIP-01 defines tag filters as ``#<single-letter>`` only, so a real relay
    IGNORES ``#branch`` and returns every event matching the remaining terms
    (verified against this tree's dev relay: a #branch-filtered 42010 query
    and a bare one returned the identical 12 events across 12 branches).
    MockRelay reproduces that behavior faithfully, so this asserts the
    client-side constraint in EvergreenQuery is what actually scopes the
    result -- a §6.1 concern, not just a correctness one: a surface labeled
    for one branch must never carry another subgraph's rows.
    """
    from lindenmayer.core.event import Event

    async with MockRelay() as relay:
        mine = keypair.sign_event(
            Event.build(
                pubkey=keypair.public_key_hex,
                kind=42010,
                tags=[["branch", "main.mine"], ["status", "started"], ["run", "r1"]],
                content='{"reason":""}',
                created_at=100,
            )
        )
        theirs = keypair.sign_event(
            Event.build(
                pubkey=keypair.public_key_hex,
                kind=42010,
                tags=[["branch", "main.theirs"], ["status", "started"], ["run", "r2"]],
                content='{"reason":""}',
                created_at=101,
            )
        )
        relay.events.append(mine.to_dict())
        relay.events.append(theirs.to_dict())

        config = CoreConfig(relay_url=relay.url)
        async with RelayClient(relay.url, keypair, config) as client:
            # Precondition: the relay really does ignore the #branch filter,
            # so this test is exercising the client-side path, not a mock that
            # happens to filter for us.
            raw = await client.query([{"kinds": [42010], "#branch": ["main.mine"]}])
            assert len(raw) == 2, "mock relay should ignore the non-NIP-01 #branch filter"

            query = EvergreenQuery(client)
            records = await query.node_lifecycle(branch="main.mine")
            assert {r.event_id for r in records} == {mine.id}


@pytest.mark.asyncio
async def test_addressable_pointer_d_tag_enforced_client_side(keypair: Keypair):
    """Same guarantee for addressable kinds: even though ``#d`` IS a valid
    NIP-01 filter, relay enforcement is an optimization, never an assumption
    (§6 principle 5), so the ``d`` match is re-checked client-side."""
    from lindenmayer.core.event import Event
    from lindenmayer.evergreen.query import _latest_addressable
    from lindenmayer.core.kinds.models import NodeStatePointer

    def pointer(branch: str, created_at: int) -> Event:
        return keypair.sign_event(
            Event.build(
                pubkey=keypair.public_key_hex,
                kind=38110,
                tags=[["d", branch], ["status", "active"], ["run", "r"], ["iter", "1"]],
                content='{"cost_shadow_usd":0.1,"cost_cap_usd":5.0,"last_lifecycle_event":"'
                + "0" * 64
                + '"}',
                created_at=created_at,
            )
        )

    mine = pointer("main.mine", 100)
    theirs = pointer("main.theirs", 999)  # newer -- would win without the d check

    record = _latest_addressable([mine, theirs], NodeStatePointer, "main.mine")
    assert record is not None
    assert record.event_id == mine.id


@pytest.mark.asyncio
async def test_tampered_event_dropped_by_query_layer_too(keypair: Keypair):
    """Belt-and-suspenders: EvergreenQuery's own _to_records re-verifies
    every event and would drop a tampered one even if it somehow reached
    the query layer (e.g. a relay that doesn't verify on ingest)."""
    from lindenmayer.evergreen.query import _to_records
    from lindenmayer.core.kinds.models import NodeLifecycle

    events = build_fixture_events(keypair)
    good = events["lifecycle_started"]
    bad = tamper(events["lifecycle_completed"])
    records = _to_records([good, bad], NodeLifecycle)
    assert {r.event_id for r in records} == {good.id}
