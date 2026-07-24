"""Read-only query surface over the signed log for the nine evergreen kinds.

``EvergreenQuery`` wraps a ``core.relay.RelayClient`` -- no new client, no
local index (DESIGN.md §6.2, relay-as-context): every method issues a fresh
relay ``query`` and reconstructs its answer from the returned events. Every
event is verified (NIP-01 id + signature, via ``Event.verify()``) before it
is parsed into a record; a tampered or unsigned event is silently dropped,
never surfaced as data (§6.5) -- this mirrors core's own
``verify.filter_attested`` posture (drop, don't raise) rather than the
registry reader's raise-on-failure style, since a read-plane dashboard
should degrade by omission, not crash on one bad event. A structurally
malformed (but validly signed) event is dropped the same way.

Nine kinds: the eight in ``core.kinds.constants`` plus 42060 (session
compaction), which core has not yet allocated a constant for -- see
``KIND_COMPACTION`` below.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Generic, TypeVar

from lindenmayer.core.event import Event
from lindenmayer.core.kinds import constants
from lindenmayer.core.kinds.base import KindModel, KindValidationError
from lindenmayer.core.kinds.models import (
    ApprovalRequest,
    NodeLifecycle,
    NodeStatePointer,
    RunAccounting,
    SubgraphDigest,
    TemplatePointer,
    TemplateVersion,
)
from lindenmayer.core.verify import ApprovalCounts, count_approvals

__all__ = [
    "KIND_COMPACTION",
    "Compaction",
    "EvergreenQuery",
    "QueryError",
    "Record",
]

# Kind 42060 (session compaction) is ratified by DESIGN.md §5.2 and
# wiki/event_kind_conventions.md, but core has not yet allocated a constant
# for it in lindenmayer.core.kinds.constants (docs/research/evergreen/
# README.md, "What remains open": the block/buzz collision check is core's
# to run before docs/kinds/42060-*.md lands). Evergreen only ever reads this
# kind -- the bridge's transcript adapter is the sole emitter (boundary
# note, tree/evergreen/NODE.md) -- so a local literal is used here rather
# than waiting on, or editing, core's module.
KIND_COMPACTION = 42060


class QueryError(Exception):
    """A query against the signed log failed outright (relay/transport error
    or a referenced event was not found) -- never raised for a merely
    untrusted event, which is dropped instead (see module docstring)."""


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Record(Generic[T]):
    """A verified kind-model instance plus the event metadata the model
    itself doesn't carry (id, author, timestamp) -- deliverable 2 needs
    these to resolve pointers and order history."""

    model: T
    event_id: str
    pubkey: str
    created_at: int


@dataclass(frozen=True, slots=True)
class Compaction:
    """Kind 42060 -- a session-compaction digest (metrics + summary hash
    only; never the summary text -- §6.1). Tag/content shape follows
    DESIGN.md §5.2 and wiki/event_kind_conventions.md. No ``core.kinds``
    model exists for this kind yet, so it's hand-parsed rather than going
    through ``KindModel``."""

    branch: str
    run: str
    iter: str
    step: str
    session: str
    summary_of: str | None
    detection: str
    pre_tokens: int | None
    post_tokens: int | None
    duration_ms: int | None
    summary_hash: str | None
    event_id: str
    pubkey: str
    created_at: int


def _parse_compaction(event: Event) -> Compaction:
    if event.kind != KIND_COMPACTION:
        raise KindValidationError(f"expected kind {KIND_COMPACTION}, got {event.kind}")

    def _require(name: str) -> str:
        value = event.first_tag_value(name)
        if value is None:
            raise KindValidationError(f"kind {KIND_COMPACTION} missing required tag '{name}'")
        return value

    summary_of = None
    for values in event.tag_values("e"):
        if len(values) >= 3 and values[2] == "summary-of":
            summary_of = values[0]
            break

    detection = _require("detection")
    if detection not in ("harness-marker", "usage-discontinuity"):
        raise KindValidationError(f"kind {KIND_COMPACTION} invalid detection tag: {detection!r}")

    try:
        content = json.loads(event.content) if event.content else {}
    except json.JSONDecodeError as exc:
        raise KindValidationError(
            f"kind {KIND_COMPACTION} content is not valid JSON: {exc}"
        ) from exc
    if not isinstance(content, dict):
        raise KindValidationError(f"kind {KIND_COMPACTION} content must be a JSON object")

    return Compaction(
        branch=_require("branch"),
        run=_require("run"),
        iter=_require("iter"),
        step=_require("step"),
        session=_require("session"),
        summary_of=summary_of,
        detection=detection,
        pre_tokens=content.get("pre_tokens"),
        post_tokens=content.get("post_tokens"),
        duration_ms=content.get("duration_ms"),
        summary_hash=content.get("summary_hash"),
        event_id=event.id,
        pubkey=event.pubkey,
        created_at=event.created_at,
    )


def _tag_matches(event: Event, tag_name: str, tag_value: str | None) -> bool:
    """Does ``event`` carry ``[tag_name, tag_value]``? True when no constraint."""
    if tag_value is None:
        return True
    return any(values and values[0] == tag_value for values in event.tag_values(tag_name))


def _to_records(
    events: list[Event],
    model_cls: type[KindModel],
    *,
    tag_name: str | None = None,
    tag_value: str | None = None,
) -> list[Record]:
    """Verify, apply the client-side tag constraint, then parse each event;
    drop (don't raise on) any failure. See ``_filter`` on why the tag
    constraint is enforced here rather than trusted to the relay."""
    out: list[Record] = []
    for event in events:
        if not event.verify():
            continue
        if tag_name is not None and not _tag_matches(event, tag_name, tag_value):
            continue
        try:
            model = model_cls.from_event(event)
        except KindValidationError:
            continue
        out.append(Record(model=model, event_id=event.id, pubkey=event.pubkey, created_at=event.created_at))
    return out


def _latest_addressable(events: list[Event], model_cls: type[KindModel], d_value: str) -> Record | None:
    """NIP-01 addressable collapse: keep only the latest verified, parseable
    event by (created_at, id). The ``d``-tag match is re-checked client-side
    for the same reason every other tag constraint is (``_filter``), even
    though ``#d`` *is* a NIP-01-valid filter -- relay enforcement is an
    optimization, never an assumption (DESIGN.md §6 principle 5).

    If several distinct authors share the same ``d``-tag (unusual -- normally
    one keypair per branch/template), this still picks a single global latest;
    scope with ``author=`` to disambiguate.
    """
    verified = [e for e in events if e.verify() and _tag_matches(e, "d", d_value)]
    if not verified:
        return None
    latest = max(verified, key=lambda e: (e.created_at, e.id))
    try:
        model = model_cls.from_event(latest)
    except KindValidationError:
        return None
    return Record(model=model, event_id=latest.id, pubkey=latest.pubkey, created_at=latest.created_at)


# NIP-01 defines tag filters as ``#<single-letter>`` only (``#e``, ``#p``,
# ``#d``, ...). A multi-character key like ``#branch`` or ``#template_name``
# is NOT part of the spec: a compliant relay simply ignores it and returns
# every event matching the remaining terms. Verified against this tree's own
# dev relay -- a ``{"kinds":[42010],"#branch":["main.evergreen"]}`` query and
# a bare ``{"kinds":[42010]}`` query returned the identical 12 events,
# spanning twelve *different* branches.
#
# Sending such a key is therefore harmless but never load-bearing: it may let
# a permissive relay narrow the result set, but correctness may not depend on
# it. Every multi-character tag constraint is re-applied client-side in
# ``_to_records`` -- which also keeps this consistent with §6 principle 5
# (relay enforcement is an optimization, never an assumption) and with §6.1:
# a surface labeled for one branch must never carry another subgraph's rows
# because a relay declined to filter.
_NIP01_SINGLE_LETTER_TAG = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")


def _filter(kind: int, *, author: str | None, tag_name: str | None = None, tag_value: str | None = None) -> dict:
    f: dict = {"kinds": [kind]}
    if author is not None:
        f["authors"] = [author]
    if tag_name is not None and tag_value is not None and tag_name in _NIP01_SINGLE_LETTER_TAG:
        f[f"#{tag_name}"] = [tag_value]
    return f


class EvergreenQuery:
    """Typed read surface over the nine evergreen kinds.

    Every method takes an optional ``author`` (pubkey) to scope the query to
    one signing key; omitted, it queries across all authors the relay knows
    about. No caching, no local state: each call is a fresh
    ``relay_client.query(...)`` round trip.
    """

    def __init__(self, relay_client) -> None:
        self._relay = relay_client

    # -- 42010: node lifecycle ---------------------------------------------

    async def node_lifecycle(
        self, *, branch: str | None = None, author: str | None = None
    ) -> list[Record[NodeLifecycle]]:
        f = _filter(constants.KIND_NODE_LIFECYCLE, author=author, tag_name="branch", tag_value=branch)
        events = await self._relay.query([f])
        return _to_records(events, NodeLifecycle, tag_name="branch", tag_value=branch)

    # -- 38110: node state pointer (addressable) ----------------------------

    async def node_state_pointer(
        self, branch: str, *, author: str | None = None
    ) -> Record[NodeStatePointer] | None:
        f = _filter(constants.KIND_NODE_STATE_POINTER, author=author, tag_name="d", tag_value=branch)
        events = await self._relay.query([f])
        return _latest_addressable(events, NodeStatePointer, branch)

    # -- 42020: run accounting ----------------------------------------------

    async def run_accounting(
        self, *, branch: str | None = None, author: str | None = None
    ) -> list[Record[RunAccounting]]:
        f = _filter(constants.KIND_RUN_ACCOUNTING, author=author, tag_name="branch", tag_value=branch)
        events = await self._relay.query([f])
        return _to_records(events, RunAccounting, tag_name="branch", tag_value=branch)

    # -- 42030: subgraph digest ----------------------------------------------

    async def subgraph_digest(
        self, *, branch: str | None = None, author: str | None = None
    ) -> list[Record[SubgraphDigest]]:
        f = _filter(constants.KIND_SUBGRAPH_DIGEST, author=author, tag_name="branch", tag_value=branch)
        events = await self._relay.query([f])
        return _to_records(events, SubgraphDigest, tag_name="branch", tag_value=branch)

    # -- 42040/42041: approvals ----------------------------------------------

    async def approval_requests(
        self, *, branch: str | None = None, author: str | None = None
    ) -> list[Record[ApprovalRequest]]:
        f = _filter(constants.KIND_APPROVAL_REQUEST, author=author, tag_name="branch", tag_value=branch)
        events = await self._relay.query([f])
        return _to_records(events, ApprovalRequest, tag_name="branch", tag_value=branch)

    async def approval_status(self, request_event_id: str) -> ApprovalCounts:
        """Tally kind 42041 verdicts answering the kind-42040 request
        ``request_event_id``. Delegates counting to core's
        ``count_approvals`` entirely -- approval-counting logic is not
        reimplemented here."""
        request_events = await self._relay.query(
            [{"kinds": [constants.KIND_APPROVAL_REQUEST], "ids": [request_event_id]}]
        )
        request = next((e for e in request_events if e.id == request_event_id and e.verify()), None)
        if request is None:
            raise QueryError(
                f"approval request {request_event_id} not found or failed verification"
            )
        verdict_events = await self._relay.query(
            [{"kinds": [constants.KIND_APPROVAL_VERDICT], "#e": [request_event_id]}]
        )
        return count_approvals(request, verdict_events)

    async def pending_approvals(
        self, *, branch: str | None = None, author: str | None = None
    ) -> list[Record[ApprovalRequest]]:
        """Approval requests with no verdict of either polarity yet.

        One extra relay round trip per request (no local index -- §6.2), which
        is fine for a read-plane dashboard's request volume.
        """
        requests = await self.approval_requests(branch=branch, author=author)
        pending: list[Record[ApprovalRequest]] = []
        for record in requests:
            counts = await self.approval_status(record.event_id)
            if counts.approve_count == 0 and counts.reject_count == 0:
                pending.append(record)
        return pending

    # -- 42050/38150: templates ----------------------------------------------

    async def template_versions(
        self, *, template_name: str | None = None, author: str | None = None
    ) -> list[Record[TemplateVersion]]:
        f = _filter(
            constants.KIND_TEMPLATE_VERSION, author=author, tag_name="template_name", tag_value=template_name
        )
        events = await self._relay.query([f])
        return _to_records(events, TemplateVersion, tag_name="template_name", tag_value=template_name)

    async def template_version_by_id(self, event_id: str) -> Record[TemplateVersion] | None:
        """Resolve a single kind-42050 event id (e.g. from a kind-42020
        ``template`` tag) to its parsed version record -- the join step
        for template-version -> instance linkage (deliverable 3)."""
        events = await self._relay.query([{"kinds": [constants.KIND_TEMPLATE_VERSION], "ids": [event_id]}])
        records = _to_records([e for e in events if e.id == event_id], TemplateVersion)
        return records[0] if records else None

    async def template_pointer(
        self, template_name: str, *, author: str | None = None
    ) -> Record[TemplatePointer] | None:
        f = _filter(constants.KIND_TEMPLATE_POINTER, author=author, tag_name="d", tag_value=template_name)
        events = await self._relay.query([f])
        return _latest_addressable(events, TemplatePointer, template_name)

    # -- 42060: session compaction (read-side only; bridge emits) -----------

    async def compactions(
        self, *, branch: str | None = None, author: str | None = None
    ) -> list[Compaction]:
        f = _filter(KIND_COMPACTION, author=author, tag_name="branch", tag_value=branch)
        events = await self._relay.query([f])
        out: list[Compaction] = []
        for event in events:
            if not event.verify():
                continue
            try:
                out.append(_parse_compaction(event))
            except KindValidationError:
                continue
        return out
