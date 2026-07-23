"""The security boundary: attestation validation, approval counting, revocation.

Every consumer verifies from the signed log alone (DESIGN.md §6.5). Relay
enforcement — group membership, private-read gating, event deletion — is an
optimization, never an assumption: a plain relay may serve stale, revoked,
or hostile events, and these helpers are the reader-side bound on trusting
them.

Attestation follows NIP-OA (restated in docs/kinds/nip-oa-attestation.md):
an optional ``auth`` tag by which an owner key authorizes the agent key that
authored the event. Verification here never consults a wall clock —
``created_at`` clauses constrain the event's self-declared timestamp, which
the agent controls, so wall-clock freshness is a caller concern by design.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import Enum, unique
from typing import Iterable, Literal, NamedTuple

import lindenmayer.core.keys as _keys
from lindenmayer.core.event import Event
from lindenmayer.core.kinds.constants import KIND_APPROVAL_VERDICT

__all__ = [
    "ApprovalCounts",
    "AttestationLabel",
    "AttestationOutcome",
    "AttestationResult",
    "AttestationState",
    "attestation_state",
    "count_approvals",
    "filter_attested",
    "is_approved",
    "validate_attestation",
]

AUTH_TAG_NAME = "auth"
_AUTH_DOMAIN = "nostr:agent-auth:"

# Strict per-clause grammar: canonical decimals only. ``fullmatch`` with an
# explicit digit class rejects unicode digits, leading zeros, signs, and
# whitespace that ``str.isdigit()``-based parsing would let through.
_CLAUSE_RE = re.compile(r"(kind=|created_at<|created_at>)(0|[1-9][0-9]*)")

_KIND_MAX = 65535
_CREATED_AT_MAX = 4294967295


def _is_hex(value: str, length: int) -> bool:
    if len(value) != length or value != value.lower():
        return False
    try:
        bytes.fromhex(value)
    except ValueError:
        return False
    return True


# -- attestation validation ------------------------------------------------


@unique
class AttestationOutcome(Enum):
    """Tri-state result of NIP-OA auth-tag validation."""

    VALID = "valid"
    ABSENT = "absent"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class AttestationResult:
    """Outcome plus the machine-readable ``reason`` when INVALID.

    ``owner_pubkey`` and ``conditions`` are populated only for VALID —
    an invalid tag's claims are not facts and are deliberately withheld.
    """

    outcome: AttestationOutcome
    owner_pubkey: str | None = None
    conditions: str | None = None
    reason: str | None = None


def _parse_conditions(conditions: str) -> list[tuple[str, int]] | None:
    """Parse a NIP-OA conditions string strictly; None on any violation.

    The empty string is valid (no clauses). The raw string is what the
    owner signed — callers must never reorder, dedupe, or normalize it.
    """
    if conditions == "":
        return []
    clauses: list[tuple[str, int]] = []
    for segment in conditions.split("&"):
        match = _CLAUSE_RE.fullmatch(segment)
        if match is None:
            return None
        op, number = match.group(1), int(match.group(2))
        limit = _KIND_MAX if op == "kind=" else _CREATED_AT_MAX
        if number > limit:
            return None
        clauses.append((op, number))
    return clauses


def _clause_satisfied(event: Event, op: str, number: int) -> bool:
    if op == "kind=":
        return event.kind == number
    if op == "created_at<":
        return event.created_at < number
    return event.created_at > number


def validate_attestation(event: Event) -> AttestationResult:
    """Validate the NIP-OA ``auth`` tag on ``event`` from the signed log alone.

    Order matters: the event's own NIP-01 validity comes first (a valid auth
    tag on an invalid event establishes nothing), then tag shape, then the
    owner signature over ``sha256("nostr:agent-auth:" + event.pubkey + ":"
    + conditions)``, then every clause evaluated against the event (AND).
    """
    _invalid = lambda reason: AttestationResult(  # noqa: E731 — local shorthand
        outcome=AttestationOutcome.INVALID, reason=reason
    )
    if not event.verify():
        return _invalid("invalid_event")
    auth_tags = [tag for tag in event.tags if tag and tag[0] == AUTH_TAG_NAME]
    if not auth_tags:
        return AttestationResult(outcome=AttestationOutcome.ABSENT)
    if len(auth_tags) > 1:
        return _invalid("duplicate_auth_tag")
    tag = auth_tags[0]
    if len(tag) != 4:
        return _invalid("malformed_tag")
    owner_pubkey, conditions, sig_hex = tag[1], tag[2], tag[3]
    if not _is_hex(owner_pubkey, 64):
        return _invalid("invalid_owner_pubkey")
    if not _is_hex(sig_hex, 128):
        return _invalid("invalid_sig_encoding")
    if owner_pubkey == event.pubkey:
        return _invalid("self_attestation")
    clauses = _parse_conditions(conditions)
    if clauses is None:
        return _invalid("invalid_conditions")
    preimage = f"{_AUTH_DOMAIN}{event.pubkey}:{conditions}".encode("utf-8")
    message = hashlib.sha256(preimage).digest()
    if not _keys.schnorr_verify(owner_pubkey, message, bytes.fromhex(sig_hex)):
        return _invalid("invalid_owner_signature")
    for op, number in clauses:
        if not _clause_satisfied(event, op, number):
            return _invalid("condition_unsatisfied")
    return AttestationResult(
        outcome=AttestationOutcome.VALID,
        owner_pubkey=owner_pubkey,
        conditions=conditions,
    )


# -- approval counting -----------------------------------------------------


class ApprovalCounts(NamedTuple):
    """Verdict tally for one approval request (kind 42040)."""

    approve_count: int
    reject_count: int
    per_approver: dict[str, Literal["approve", "reject"]]


def _verdict_value(event: Event) -> str | None:
    """The single ``verdict`` tag value, or None if absent or ambiguous.

    The kind-42041 schema (docs/kinds/) carries the verdict in exactly one
    ``verdict`` tag; an event with zero or several is not a valid verdict.
    """
    values = [vals[0] for vals in event.tag_values("verdict") if vals]
    return values[0] if len(values) == 1 else None


def count_approvals(request: Event, events: Iterable[Event]) -> ApprovalCounts:
    """Count signed verdicts (kind 42041) answering ``request``.

    A candidate must verify under NIP-01, ``e``-tag the request id, and carry
    a ``verdict`` tag of exactly ``approve`` or ``reject`` — anything else is
    excluded, not counted either way. Per approver (``event.pubkey``) the
    latest verdict wins, ordered by ``created_at`` descending with ascending
    id as the tiebreak, so reject→revise→approve chains resolve to the final
    word deterministically on every reader.
    """
    latest: dict[str, Event] = {}
    for event in events:
        if event.kind != KIND_APPROVAL_VERDICT:
            continue
        verdict = _verdict_value(event)
        if verdict not in ("approve", "reject"):
            continue
        if not any(vals and vals[0] == request.id for vals in event.tag_values("e")):
            continue
        if not event.verify():
            continue
        current = latest.get(event.pubkey)
        if (
            current is None
            or event.created_at > current.created_at
            or (event.created_at == current.created_at and event.id < current.id)
        ):
            latest[event.pubkey] = event
    per_approver: dict[str, Literal["approve", "reject"]] = {
        pubkey: "approve" if _verdict_value(event) == "approve" else "reject"
        for pubkey, event in latest.items()
    }
    approves = sum(1 for v in per_approver.values() if v == "approve")
    return ApprovalCounts(
        approve_count=approves,
        reject_count=len(per_approver) - approves,
        per_approver=per_approver,
    )


def is_approved(
    request: Event,
    events: Iterable[Event],
    threshold: int,
    required_approvers: Iterable[str] | None = None,
) -> bool:
    """Does ``request`` have >= ``threshold`` standing approvals?

    With ``required_approvers``, only verdicts from that set count — a
    merge-gate caller names its reviewers; everyone else is advisory. This
    helper only counts the signed log: *enforcing* the gate (refusing a
    merge) is a bridge/process concern layered above these events.
    """
    counts = count_approvals(request, events)
    per_approver = counts.per_approver
    if required_approvers is not None:
        allowed = set(required_approvers)
        per_approver = {k: v for k, v in per_approver.items() if k in allowed}
    return sum(1 for v in per_approver.values() if v == "approve") >= threshold


# -- revocation filtering and extraction labeling --------------------------


@unique
class AttestationState(Enum):
    """Trust label for a stored event row (extraction pipeline, DESIGN.md §4)."""

    ATTESTED = "attested"
    UNATTESTED = "unattested"
    REVOKED = "revoked"
    INVALID_ATTESTATION = "invalid_attestation"
    INVALID_EVENT = "invalid_event"


@dataclass(frozen=True, slots=True)
class AttestationLabel:
    """An ``AttestationState`` plus its provenance details.

    ``reason`` carries the ``validate_attestation`` reason verbatim for
    INVALID_ATTESTATION rows; ``owner_pubkey`` is set only when the auth
    tag validated (including REVOKED-by-owner rows, where the owner is
    exactly the fact that matters).
    """

    state: AttestationState
    owner_pubkey: str | None = None
    reason: str | None = None


def attestation_state(
    event: Event,
    revoked_owners: frozenset[str] | set[str] = frozenset(),
    revoked_agents: frozenset[str] | set[str] = frozenset(),
) -> AttestationLabel:
    """Label ``event`` for read-time trust decisions and corpus extraction.

    Agent revocation deliberately applies even to events with no auth tag:
    the reader-side trust bound bounds the *key*, not just the attestation
    claim — a banned agent key does not regain neutrality by omitting its
    provenance tag. Owner revocation, by contrast, can only apply where an
    owner is validly claimed.
    """
    if not event.verify():
        return AttestationLabel(state=AttestationState.INVALID_EVENT, reason="invalid_event")
    result = validate_attestation(event)
    if result.outcome is AttestationOutcome.ABSENT:
        if event.pubkey in revoked_agents:
            return AttestationLabel(state=AttestationState.REVOKED)
        return AttestationLabel(state=AttestationState.UNATTESTED)
    if result.outcome is AttestationOutcome.VALID:
        if result.owner_pubkey in revoked_owners or event.pubkey in revoked_agents:
            return AttestationLabel(
                state=AttestationState.REVOKED, owner_pubkey=result.owner_pubkey
            )
        return AttestationLabel(
            state=AttestationState.ATTESTED, owner_pubkey=result.owner_pubkey
        )
    return AttestationLabel(state=AttestationState.INVALID_ATTESTATION, reason=result.reason)


def filter_attested(
    events: Iterable[Event],
    revoked_owners: frozenset[str] | set[str] = frozenset(),
    revoked_agents: frozenset[str] | set[str] = frozenset(),
) -> list[Event]:
    """Keep events a reader may trust: ATTESTED or UNATTESTED, in order.

    Drops INVALID_EVENT, INVALID_ATTESTATION, and REVOKED rows.

    Revocation latency caveat (degradation.md): a plain relay still serves
    revoked or stale events after the fact — revocation propagates only as
    fast as readers refresh their revocation sets and re-filter. This
    function is that reader-side bound, not relay enforcement; deployments
    needing hard deletion must verify that capability separately
    (``CoreConfig`` capability attestations) rather than assume it.
    """
    keep = (AttestationState.ATTESTED, AttestationState.UNATTESTED)
    return [
        event
        for event in events
        if attestation_state(event, revoked_owners, revoked_agents).state in keep
    ]
