"""Minimum-contract Nostr relay client: NIP-01 + NIP-29 + NIP-42, nothing more.

Per the relay-integration research aggregate
(``docs/research/relay-integration/README.md``, recommendation 1) and
DESIGN.md §6.5, this client assumes only NIP-01 (wire protocol), NIP-29
(group scoping via the ``h`` tag), and NIP-42 (auth challenge/response). NIP-34,
Blossom, and Buzz custom-relay behaviors are additive capabilities layered
elsewhere; this module never special-cases them.

Security posture: every inbound event is verified (``Event.verify()``) before
it reaches a caller — an invalid signature is dropped and counted, never
delivered as data. Relay-side enforcement (including NIP-29 private-group read
gating) is an optimization, never an assumption (DESIGN.md §6 principle 5):
this client refuses to treat a channel as private-readable unless the
deployment operator has explicitly attested
``CAP_PRIVATE_READ_GATING`` in :class:`~lindenmayer.core.config.CoreConfig`.

Reconnection is a bounded best-effort convenience, not a durability guarantee:
on an unexpected disconnect the client retries a few times with exponential
backoff and reissues ``REQ`` for live ``subscribe()`` calls, but there is no
persistent queue — events published or delivered by the relay during the gap
are not replayed or buffered. Callers that need gap-free delivery must
reconcile via ``query()`` after a reconnect.
"""

from __future__ import annotations

import asyncio
import contextlib
import itertools
import json
import logging
from typing import Any, AsyncIterator

import websockets

from lindenmayer.core.config import CAP_PRIVATE_READ_GATING, CoreConfig
from lindenmayer.core.event import Event, EventValidationError
from lindenmayer.core.keys import Keypair

__all__ = [
    "PrivateCapabilityError",
    "RelayClient",
    "RelayError",
    "RelayRejection",
]

logger = logging.getLogger(__name__)

# NIP-42: kind of the client's authentication event.
_AUTH_EVENT_KIND = 22242

_AUTH_REQUIRED_PREFIX = "auth-required:"


class RelayError(Exception):
    """Base error for relay client failures."""


class RelayRejection(RelayError):
    """The relay rejected a published or auth event via ``OK ... false``."""

    def __init__(self, event_id: str, message: str) -> None:
        self.event_id = event_id
        self.message = message
        super().__init__(f"relay rejected event {event_id}: {message}")


class PrivateCapabilityError(RelayError):
    """Private-group semantics were requested without an operator attestation.

    NIP-29's ``private`` read gating is spec-permissive, not a protocol
    guarantee: a relay may store the flag without enforcing it. Treating a
    channel as private-readable on that basis alone would silently degrade
    the platform's aggregates-up privacy default into a client-side courtesy
    (relay-integration research aggregate, finding 4). This client refuses
    instead: the deployment operator must attest
    ``CAP_PRIVATE_READ_GATING`` in ``CoreConfig`` before any private-group
    call succeeds. Absence of an attestation is a hard "no", never inferred
    from "the relay speaks NIP-29".
    """


class _Eose:
    """Sentinel pushed onto a subscription queue when the relay sends EOSE."""


_EOSE = _Eose()


class _Closed:
    """Sentinel pushed onto a subscription queue when the relay sends CLOSED."""

    __slots__ = ("message",)

    def __init__(self, message: str) -> None:
        self.message = message


class RelayClient:
    """An asyncio client for a single Nostr relay.

    One instance per connection. Not thread-safe; intended for use from a
    single asyncio event loop.
    """

    def __init__(
        self,
        relay_url: str,
        keypair: Keypair,
        config: CoreConfig,
        *,
        op_timeout: float = 10.0,
        max_reconnect_attempts: int = 5,
    ) -> None:
        self._url = relay_url
        self._keypair = keypair
        self._config = config
        self._op_timeout = op_timeout
        self._max_reconnect_attempts = max_reconnect_attempts

        self._ws: Any = None
        self._run_task: asyncio.Task[None] | None = None
        self._closed = True

        self._sub_id_counter = itertools.count(1)
        self._sub_queues: dict[str, "asyncio.Queue[Event | _Eose | _Closed]"] = {}
        # Only long-lived subscribe() subs are tracked here, for resubscribe
        # on reconnect -- query() is a one-shot REQ/EOSE/CLOSE round trip
        # that isn't worth resuming after a drop.
        self._live_sub_filters: dict[str, list[dict[str, Any]]] = {}
        self._pending_ok: dict[str, "asyncio.Future[tuple[bool, str]]"] = {}

        self._authed = False
        self._auth_lock = asyncio.Lock()
        self._pending_challenge: str | None = None
        self._auth_waiters: list["asyncio.Future[str]"] = []

        #: Count of inbound events dropped for failing ``Event.verify()``.
        self.dropped_invalid = 0

    # -- lifecycle -----------------------------------------------------

    async def connect(self) -> None:
        self._ws = await websockets.connect(self._url)
        self._closed = False
        self._run_task = asyncio.create_task(self._run())

    async def close(self) -> None:
        self._closed = True
        if self._run_task is not None:
            self._run_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._run_task
            self._run_task = None
        if self._ws is not None:
            await self._ws.close()
            self._ws = None

    async def __aenter__(self) -> "RelayClient":
        await self.connect()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    # -- publish ---------------------------------------------------------

    async def publish(
        self, event: Event, *, group: str | None = None, private: bool = False
    ) -> None:
        """Publish a signed event and wait for the relay's ``OK``.

        Raises :class:`RelayRejection` on ``OK ... false`` -- rejection is
        never swallowed. If ``group`` is given, the event must already carry
        a matching ``["h", group]`` tag (this client publishes events it is
        given; it does not rewrite a signed event's tags, since that would
        invalidate its id and signature). If ``private`` is true, publishing
        is refused unless the deployment attests ``CAP_PRIVATE_READ_GATING``.
        """
        if private:
            self._require_private_capability()
        if group is not None and event.first_tag_value("h") != group:
            raise RelayError(
                f"event must carry an ['h', {group!r}] tag for group-scoped "
                "publish; build it with that tag before signing"
            )
        if event.sig is None:
            raise RelayError("cannot publish an unsigned event")
        await self._publish_signed(event)

    async def _publish_signed(self, event: Event, *, _retried: bool = False) -> None:
        fut: "asyncio.Future[tuple[bool, str]]" = asyncio.get_running_loop().create_future()
        self._pending_ok[event.id] = fut
        try:
            await self._send(["EVENT", event.to_dict()])
            ok, message = await asyncio.wait_for(fut, timeout=self._op_timeout)
        finally:
            self._pending_ok.pop(event.id, None)
        if not ok:
            if not _retried and message.startswith(_AUTH_REQUIRED_PREFIX):
                await self._authenticate()
                await self._publish_signed(event, _retried=True)
                return
            raise RelayRejection(event.id, message)

    # -- query / subscribe -------------------------------------------------

    async def query(
        self,
        filters: list[dict[str, Any]],
        *,
        group: str | None = None,
        private: bool = False,
    ) -> list[Event]:
        """``REQ`` the given filters, collect verified events until ``EOSE``,
        then ``CLOSE``. Invalid-signature events are dropped, not returned."""
        if private:
            self._require_private_capability()
        return await self._query_scoped(self._scope_filters(filters, group))

    async def _query_scoped(
        self, filters: list[dict[str, Any]], *, _retried: bool = False
    ) -> list[Event]:
        sub_id = self._next_sub_id()
        queue: "asyncio.Queue[Event | _Eose | _Closed]" = asyncio.Queue()
        self._sub_queues[sub_id] = queue
        events: list[Event] = []
        try:
            await self._send(["REQ", sub_id, *filters])
            while True:
                item = await asyncio.wait_for(queue.get(), timeout=self._op_timeout)
                if isinstance(item, _Eose):
                    break
                if isinstance(item, _Closed):
                    if not _retried and item.message.startswith(_AUTH_REQUIRED_PREFIX):
                        await self._authenticate()
                        return await self._query_scoped(filters, _retried=True)
                    raise RelayError(f"subscription closed: {item.message}")
                events.append(item)
        finally:
            self._sub_queues.pop(sub_id, None)
            with contextlib.suppress(RelayError):
                await self._send(["CLOSE", sub_id])
        return events

    async def subscribe(
        self,
        filters: list[dict[str, Any]],
        *,
        group: str | None = None,
        private: bool = False,
    ) -> AsyncIterator[Event]:
        """``REQ`` the given filters and yield verified events indefinitely
        (including post-``EOSE`` live fan-out) until the generator is closed.

        Resubscribes automatically on reconnect. Invalid-signature events are
        dropped, never yielded.
        """
        if private:
            self._require_private_capability()
        scoped = self._scope_filters(filters, group)
        sub_id = self._next_sub_id()
        queue: "asyncio.Queue[Event | _Eose | _Closed]" = asyncio.Queue()
        self._sub_queues[sub_id] = queue
        self._live_sub_filters[sub_id] = scoped
        try:
            await self._send(["REQ", sub_id, *scoped])
            while True:
                item = await queue.get()
                if isinstance(item, _Eose):
                    continue
                if isinstance(item, _Closed):
                    if item.message.startswith(_AUTH_REQUIRED_PREFIX):
                        await self._authenticate()
                        await self._send(["REQ", sub_id, *scoped])
                        continue
                    raise RelayError(f"subscription closed: {item.message}")
                yield item
        finally:
            self._sub_queues.pop(sub_id, None)
            self._live_sub_filters.pop(sub_id, None)
            with contextlib.suppress(RelayError):
                await self._send(["CLOSE", sub_id])

    @staticmethod
    def _scope_filters(
        filters: list[dict[str, Any]], group: str | None
    ) -> list[dict[str, Any]]:
        """NIP-29 group scoping: add ``#h: [group]`` to each filter."""
        if group is None:
            return filters
        return [{**f, "#h": [group]} for f in filters]

    # -- private-group gating ---------------------------------------------

    def require_private(self, group: str) -> str:
        """Assert the deployment attests relay-side private read gating.

        Returns ``group`` unchanged so it composes at call sites, e.g.
        ``client.query(filters, group=client.require_private(group))``.
        Raises :class:`PrivateCapabilityError` without the attestation.
        """
        self._require_private_capability()
        return group

    def _require_private_capability(self) -> None:
        if not self._config.has_capability(CAP_PRIVATE_READ_GATING):
            raise PrivateCapabilityError(
                "private-group semantics require the deployment to attest "
                f"{CAP_PRIVATE_READ_GATING!r} in CoreConfig.capability_attestations "
                "-- NIP-29 compliance alone does not guarantee relay-side read "
                "enforcement (docs/research/relay-integration/README.md, finding 4)"
            )

    # -- NIP-42 authentication ---------------------------------------------

    async def _authenticate(self) -> None:
        async with self._auth_lock:
            if self._authed:
                return
            challenge = self._pending_challenge
            if challenge is None:
                fut: "asyncio.Future[str]" = asyncio.get_running_loop().create_future()
                self._auth_waiters.append(fut)
                challenge = await asyncio.wait_for(fut, timeout=self._op_timeout)
            auth_event = Event.build(
                pubkey=self._keypair.public_key_hex,
                kind=_AUTH_EVENT_KIND,
                tags=[["relay", self._url], ["challenge", challenge]],
            )
            signed = self._keypair.sign_event(auth_event)
            fut_ok: "asyncio.Future[tuple[bool, str]]" = (
                asyncio.get_running_loop().create_future()
            )
            self._pending_ok[signed.id] = fut_ok
            try:
                await self._send(["AUTH", signed.to_dict()])
                ok, message = await asyncio.wait_for(fut_ok, timeout=self._op_timeout)
            finally:
                self._pending_ok.pop(signed.id, None)
            if not ok:
                raise RelayRejection(signed.id, message or "authentication rejected")
            self._authed = True
            self._pending_challenge = None

    # -- wire I/O ------------------------------------------------------------

    async def _send(self, message: list[Any]) -> None:
        if self._ws is None:
            raise RelayError("not connected")
        await self._ws.send(json.dumps(message, ensure_ascii=False, separators=(",", ":")))

    def _next_sub_id(self) -> str:
        return f"ln-{next(self._sub_id_counter)}"

    async def _run(self) -> None:
        while not self._closed:
            try:
                assert self._ws is not None
                async for raw in self._ws:
                    await self._handle_message(raw)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # connection dropped or protocol error
                if self._closed:
                    return
                logger.warning("relay connection lost: %s", exc)
            if self._closed:
                return
            try:
                await self._reconnect()
            except RelayError as exc:
                self._closed = True
                self._fail_pending(exc)
                return

    async def _reconnect(self) -> None:
        last_exc: Exception | None = None
        for attempt in range(self._max_reconnect_attempts):
            if attempt:
                await asyncio.sleep(min(2**attempt, 30))
            try:
                self._ws = await websockets.connect(self._url)
            except OSError as exc:
                last_exc = exc
                continue
            self._authed = False
            self._pending_challenge = None
            for sub_id, filters in list(self._live_sub_filters.items()):
                await self._send(["REQ", sub_id, *filters])
            return
        raise RelayError(f"failed to reconnect to {self._url} after "
                         f"{self._max_reconnect_attempts} attempts: {last_exc}")

    def _fail_pending(self, exc: Exception) -> None:
        """Unblock every in-flight caller after giving up on reconnection.

        There is no persistent queue: callers awaiting an OK or iterating a
        subscription at the moment reconnection is abandoned get this error
        rather than hanging forever.
        """
        for fut in list(self._pending_ok.values()):
            if not fut.done():
                fut.set_exception(exc)
        self._pending_ok.clear()
        for fut in list(self._auth_waiters):
            if not fut.done():
                fut.set_exception(exc)
        self._auth_waiters.clear()
        for queue in self._sub_queues.values():
            queue.put_nowait(_Closed(str(exc)))

    async def _handle_message(self, raw: str | bytes) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("dropping malformed relay frame")
            return
        if not isinstance(msg, list) or not msg:
            return
        msg_type = msg[0]
        if msg_type == "EVENT" and len(msg) >= 3:
            await self._handle_event(msg[1], msg[2])
        elif msg_type == "EOSE" and len(msg) >= 2:
            queue = self._sub_queues.get(msg[1])
            if queue is not None:
                await queue.put(_EOSE)
        elif msg_type == "OK" and len(msg) >= 3:
            event_id, ok = msg[1], msg[2]
            message = msg[3] if len(msg) > 3 else ""
            fut = self._pending_ok.get(event_id)
            if fut is not None and not fut.done():
                fut.set_result((bool(ok), message))
        elif msg_type == "CLOSED" and len(msg) >= 2:
            message = msg[2] if len(msg) > 2 else ""
            queue = self._sub_queues.get(msg[1])
            if queue is not None:
                await queue.put(_Closed(message))
        elif msg_type == "NOTICE":
            logger.info("relay notice: %s", msg[1] if len(msg) > 1 else "")
        elif msg_type == "AUTH" and len(msg) >= 2:
            self._on_auth_challenge(msg[1])

    async def _handle_event(self, sub_id: str, event_data: Any) -> None:
        try:
            event = Event.from_dict(event_data)
        except EventValidationError:
            self.dropped_invalid += 1
            return
        if not event.verify():
            self.dropped_invalid += 1
            return
        queue = self._sub_queues.get(sub_id)
        if queue is not None:
            await queue.put(event)

    def _on_auth_challenge(self, challenge: str) -> None:
        self._pending_challenge = challenge
        for fut in self._auth_waiters:
            if not fut.done():
                fut.set_result(challenge)
        self._auth_waiters.clear()
