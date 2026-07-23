"""An in-process NIP-01/29/42 mock relay for exercising RelayClient.

Owned by the relay leaf alongside tests/test_relay.py. Speaks just enough of
the wire protocol to drive the tests: EVENT -> OK, REQ -> stored EVENTs ->
EOSE (plus live fan-out on later publishes), CLOSE, and an optional
auth-required mode that challenges on connect and rejects EVENT/REQ with
``auth-required:``-prefixed OK/CLOSED messages until a valid signed kind-22242
AUTH event answers the challenge.
"""

from __future__ import annotations

import json
import secrets
from typing import Any

import websockets

from lindenmayer.core.event import Event, EventValidationError


def _matches(event_data: dict[str, Any], filt: dict[str, Any]) -> bool:
    if "ids" in filt and event_data["id"] not in filt["ids"]:
        return False
    if "authors" in filt and event_data["pubkey"] not in filt["authors"]:
        return False
    if "kinds" in filt and event_data["kind"] not in filt["kinds"]:
        return False
    for key, values in filt.items():
        if key.startswith("#") and len(key) == 2:
            tag_name = key[1]
            tag_values = {
                t[1] for t in event_data.get("tags", []) if len(t) > 1 and t[0] == tag_name
            }
            if not tag_values & set(values):
                return False
    return True


def _matches_any(event_data: dict[str, Any], filters: list[dict[str, Any]]) -> bool:
    return any(_matches(event_data, f) for f in filters)


class MockRelay:
    """A minimal in-process relay server for tests. One instance per test."""

    def __init__(self, *, require_auth: bool = False, reject_kinds: set[int] | None = None) -> None:
        self.require_auth = require_auth
        self.reject_kinds = reject_kinds or set()
        self.events: list[dict[str, Any]] = []
        self.url: str | None = None
        self._server: Any = None
        self._subs: dict[Any, dict[str, list[dict[str, Any]]]] = {}
        self._challenges: dict[Any, str] = {}
        self._authed: set[Any] = set()

    async def start(self) -> "MockRelay":
        self._server = await websockets.serve(self._handler, "localhost", 0)
        port = self._server.sockets[0].getsockname()[1]
        self.url = f"ws://localhost:{port}"
        return self

    async def stop(self) -> None:
        self._server.close()
        await self._server.wait_closed()

    async def __aenter__(self) -> "MockRelay":
        return await self.start()

    async def __aexit__(self, *exc_info: object) -> None:
        await self.stop()

    # -- connection handling ------------------------------------------------

    async def _handler(self, ws: Any) -> None:
        self._subs[ws] = {}
        if self.require_auth:
            challenge = secrets.token_hex(16)
            self._challenges[ws] = challenge
            await ws.send(json.dumps(["AUTH", challenge]))
        try:
            async for raw in ws:
                await self._dispatch(ws, json.loads(raw))
        finally:
            self._subs.pop(ws, None)
            self._challenges.pop(ws, None)
            self._authed.discard(ws)

    async def _dispatch(self, ws: Any, msg: list[Any]) -> None:
        msg_type = msg[0]
        if msg_type == "EVENT":
            await self._handle_event(ws, msg[1])
        elif msg_type == "REQ":
            await self._handle_req(ws, msg[1], msg[2:])
        elif msg_type == "CLOSE":
            self._subs[ws].pop(msg[1], None)
        elif msg_type == "AUTH":
            await self._handle_auth(ws, msg[1])

    # -- protocol handlers ----------------------------------------------------

    async def _handle_event(self, ws: Any, event_data: dict[str, Any]) -> None:
        event_id = event_data.get("id", "")
        if self.require_auth and ws not in self._authed:
            await ws.send(json.dumps(["OK", event_id, False, "auth-required: please authenticate"]))
            return
        if event_data.get("kind") in self.reject_kinds:
            await ws.send(json.dumps(["OK", event_id, False, "blocked: kind not allowed"]))
            return
        self.events.append(event_data)
        await ws.send(json.dumps(["OK", event_id, True, ""]))
        for conn, subs in self._subs.items():
            for sub_id, filters in subs.items():
                if _matches_any(event_data, filters):
                    await conn.send(json.dumps(["EVENT", sub_id, event_data]))

    async def _handle_req(self, ws: Any, sub_id: str, filters: list[dict[str, Any]]) -> None:
        if self.require_auth and ws not in self._authed:
            await ws.send(json.dumps(["CLOSED", sub_id, "auth-required: please authenticate"]))
            return
        self._subs[ws][sub_id] = filters
        for event_data in self.events:
            if _matches_any(event_data, filters):
                await ws.send(json.dumps(["EVENT", sub_id, event_data]))
        await ws.send(json.dumps(["EOSE", sub_id]))

    async def _handle_auth(self, ws: Any, event_data: dict[str, Any]) -> None:
        try:
            event = Event.from_dict(event_data)
        except EventValidationError:
            await ws.send(json.dumps(["OK", event_data.get("id", ""), False, "malformed auth event"]))
            return
        challenge = self._challenges.get(ws)
        ok = (
            event.verify()
            and event.kind == 22242
            and event.first_tag_value("challenge") == challenge
        )
        if ok:
            self._authed.add(ws)
        await ws.send(json.dumps(["OK", event.id, ok, "" if ok else "invalid auth event"]))
