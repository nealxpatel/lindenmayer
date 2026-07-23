"""RelayClient tests against the in-process mock relay (tests/relay_mock.py).

Covers the minimum NIP-01 + NIP-29 + NIP-42 contract: publish/OK, query until
EOSE, live subscribe, NIP-42 auth (including retry-after-auth), dropping
invalid-signature events, ``h``-tag group scoping, and fail-loud private-group
gating without/with the operator attestation.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from lindenmayer.core.config import CapabilityAttestation, CoreConfig, CAP_PRIVATE_READ_GATING
from lindenmayer.core.event import Event
from lindenmayer.core.keys import Keypair
from lindenmayer.core.relay import PrivateCapabilityError, RelayClient, RelayError, RelayRejection

from relay_mock import MockRelay

pytestmark = pytest.mark.asyncio


def make_config(relay_url: str, *, private_attested: bool = False) -> CoreConfig:
    attestations = (
        [
            CapabilityAttestation(
                capability=CAP_PRIVATE_READ_GATING,
                attested_by="test-operator",
                attested_at=1_700_000_000,
            )
        ]
        if private_attested
        else []
    )
    return CoreConfig(relay_url=relay_url, capability_attestations=attestations)


def make_signed_event(kp: Keypair, *, kind: int = 1, content: str = "hi", tags=()) -> Event:
    event = Event.build(pubkey=kp.public_key_hex, kind=kind, tags=list(tags), content=content)
    return kp.sign_event(event)


# -- publish / OK ------------------------------------------------------------


async def test_publish_ok_round_trip():
    async with MockRelay() as mock:
        kp = Keypair.generate()
        config = make_config(mock.url)
        async with RelayClient(mock.url, kp, config) as client:
            event = make_signed_event(kp)
            await client.publish(event)
        assert mock.events[0]["id"] == event.id


async def test_publish_rejection_raises():
    async with MockRelay(reject_kinds={9999}) as mock:
        kp = Keypair.generate()
        config = make_config(mock.url)
        async with RelayClient(mock.url, kp, config) as client:
            event = make_signed_event(kp, kind=9999)
            with pytest.raises(RelayRejection):
                await client.publish(event)


async def test_publish_unsigned_event_refused():
    async with MockRelay() as mock:
        kp = Keypair.generate()
        config = make_config(mock.url)
        async with RelayClient(mock.url, kp, config) as client:
            unsigned = Event.build(pubkey=kp.public_key_hex, kind=1, content="x")
            with pytest.raises(RelayError):
                await client.publish(unsigned)


# -- query until EOSE ---------------------------------------------------------


async def test_query_collects_until_eose():
    async with MockRelay() as mock:
        kp = Keypair.generate()
        config = make_config(mock.url)
        async with RelayClient(mock.url, kp, config) as publisher:
            e1 = make_signed_event(kp, content="one")
            e2 = make_signed_event(kp, content="two")
            await publisher.publish(e1)
            await publisher.publish(e2)

        async with RelayClient(mock.url, kp, config) as client:
            results = await client.query([{"kinds": [1]}])
        assert {e.id for e in results} == {e1.id, e2.id}


# -- live subscribe -----------------------------------------------------------


async def test_subscribe_yields_live_events():
    async with MockRelay() as mock:
        kp = Keypair.generate()
        config = make_config(mock.url)
        async with RelayClient(mock.url, kp, config) as subscriber, RelayClient(
            mock.url, kp, config
        ) as publisher:
            received: list[Event] = []

            async def collect():
                async for event in subscriber.subscribe([{"kinds": [1]}]):
                    received.append(event)
                    if len(received) == 1:
                        return

            task = asyncio.create_task(collect())
            await asyncio.sleep(0.05)  # let the REQ land before publishing
            live_event = make_signed_event(kp, content="live")
            await publisher.publish(live_event)
            await asyncio.wait_for(task, timeout=5)

        assert len(received) == 1
        assert received[0].id == live_event.id


# -- NIP-42 auth ---------------------------------------------------------------


async def test_auth_flow_permits_publish_after_challenge():
    async with MockRelay(require_auth=True) as mock:
        kp = Keypair.generate()
        config = make_config(mock.url)
        async with RelayClient(mock.url, kp, config) as client:
            event = make_signed_event(kp)
            await client.publish(event)  # rejected auth-required, retried after auth
        assert client._authed
        assert mock.events[0]["id"] == event.id


async def test_auth_flow_permits_query_after_challenge():
    async with MockRelay(require_auth=True) as mock:
        kp = Keypair.generate()
        config = make_config(mock.url)
        async with RelayClient(mock.url, kp, config) as publisher:
            event = make_signed_event(kp)
            await publisher.publish(event)

        async with RelayClient(mock.url, kp, config) as client:
            results = await client.query([{"kinds": [1]}])
        assert {e.id for e in results} == {event.id}


# -- invalid signature dropped -------------------------------------------------


async def test_invalid_signature_event_dropped():
    async with MockRelay() as mock:
        kp = Keypair.generate()
        config = make_config(mock.url)

        good = make_signed_event(kp, content="good")
        bad_sig = replace(good, sig="00" * 64)  # well-formed but invalid signature
        mock.events.append(bad_sig.to_dict())
        mock.events.append(good.to_dict())

        async with RelayClient(mock.url, kp, config) as client:
            results = await client.query([{"kinds": [1]}])
            assert {e.id for e in results} == {good.id}
            assert client.dropped_invalid == 1


# -- h-tag group scoping --------------------------------------------------------


async def test_group_scoping_applied_to_publish_and_query():
    async with MockRelay() as mock:
        kp = Keypair.generate()
        config = make_config(mock.url)
        async with RelayClient(mock.url, kp, config) as client:
            scoped = make_signed_event(kp, tags=[["h", "group-a"]])
            unscoped = make_signed_event(kp, content="unscoped")
            await client.publish(scoped, group="group-a")
            await client.publish(unscoped)

            group_results = await client.query([{"kinds": [1]}], group="group-a")
            all_results = await client.query([{"kinds": [1]}])

        assert {e.id for e in group_results} == {scoped.id}
        assert {e.id for e in all_results} == {scoped.id, unscoped.id}


async def test_group_scoped_publish_requires_matching_h_tag():
    async with MockRelay() as mock:
        kp = Keypair.generate()
        config = make_config(mock.url)
        async with RelayClient(mock.url, kp, config) as client:
            event = make_signed_event(kp)  # no h tag
            with pytest.raises(RelayError):
                await client.publish(event, group="group-a")


# -- private-group read gating --------------------------------------------------


async def test_private_gating_refused_without_attestation():
    async with MockRelay() as mock:
        kp = Keypair.generate()
        config = make_config(mock.url, private_attested=False)
        async with RelayClient(mock.url, kp, config) as client:
            with pytest.raises(PrivateCapabilityError):
                await client.query([{"kinds": [1]}], group="secret-group", private=True)
            with pytest.raises(PrivateCapabilityError):
                client.require_private("secret-group")


async def test_private_gating_succeeds_with_attestation():
    async with MockRelay() as mock:
        kp = Keypair.generate()
        config = make_config(mock.url, private_attested=True)
        async with RelayClient(mock.url, kp, config) as client:
            # Should not raise -- the attestation is present.
            results = await client.query(
                [{"kinds": [1]}], group=client.require_private("secret-group"), private=True
            )
        assert results == []
