"""verify.py — attestation chains, approval counting, revocation filtering.

Attestation cases run against the NIP-OA published test vectors (valid
vector, signed event example, and all six invalid vectors), then exercise
the conditions grammar and the wall-clock-free expiry semantics. Approval
cases cover threshold edges, latest-verdict-wins, and malformed-verdict
exclusion.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from lindenmayer.core.event import Event
from lindenmayer.core.keys import Keypair
from lindenmayer.core.kinds.constants import KIND_APPROVAL_REQUEST, KIND_APPROVAL_VERDICT
from lindenmayer.core.verify import (
    AttestationOutcome,
    AttestationState,
    attestation_state,
    count_approvals,
    filter_attested,
    is_approved,
    validate_attestation,
)

VECTORS = Path(__file__).parent / "vectors"

# NIP-OA "Test Vectors" section.
OWNER_SECRET = bytes.fromhex(
    "0000000000000000000000000000000000000000000000000000000000000001"
)
OWNER_PUBKEY = "79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"
AGENT_SECRET = bytes.fromhex(
    "0000000000000000000000000000000000000000000000000000000000000002"
)
AGENT_PUBKEY = "c6047f9441ed7d6d3045406e95c07cd85c778e4b8cef3ca7abac09b95c709ee5"
VECTOR_CONDITIONS = "kind=1&created_at<1713957000"
VECTOR_PREIMAGE_SHA256 = "08cdecd55af4c28d3801fd69615dcf5cc04fab3bc134b38a840bf157197069a6"
VECTOR_AUTH_SIG = (
    "8b7df2575caf0a108374f8471722b233c53f9ff827a8b0f91861966c3b9dd5cb"
    "2e189eae9f49d72187674c2f5bd244145e10ff86c9f257ffe65a1ee5f108b369"
)

OWNER = Keypair(OWNER_SECRET)
AGENT = Keypair(AGENT_SECRET)


def auth_sig_for(conditions: str, agent_pubkey: str = AGENT_PUBKEY) -> str:
    preimage = f"nostr:agent-auth:{agent_pubkey}:{conditions}".encode()
    return OWNER.sign(hashlib.sha256(preimage).digest()).hex()


def attested_event(
    conditions: str,
    *,
    kind: int = 1,
    created_at: int = 1713956400,
    extra_tags: list[list[str]] | None = None,
    auth_tag: list[str] | None = None,
) -> Event:
    """An agent-authored, agent-signed event carrying an owner auth tag."""
    tag = auth_tag if auth_tag is not None else [
        "auth", OWNER_PUBKEY, conditions, auth_sig_for(conditions)
    ]
    tags = [tag] + (extra_tags or [])
    event = Event.build(
        pubkey=AGENT_PUBKEY, kind=kind, tags=tags, content="x", created_at=created_at
    )
    return AGENT.sign_event(event)


# -- published vectors -----------------------------------------------------


class TestPublishedVectors:
    def test_keypairs_match_vector_pubkeys(self):
        assert OWNER.public_key_hex == OWNER_PUBKEY
        assert AGENT.public_key_hex == AGENT_PUBKEY

    def test_preimage_sha256_matches(self):
        preimage = f"nostr:agent-auth:{AGENT_PUBKEY}:{VECTOR_CONDITIONS}".encode()
        assert hashlib.sha256(preimage).hexdigest() == VECTOR_PREIMAGE_SHA256

    def test_published_auth_sig_verifies(self):
        event = attested_event(
            VECTOR_CONDITIONS,
            auth_tag=["auth", OWNER_PUBKEY, VECTOR_CONDITIONS, VECTOR_AUTH_SIG],
        )
        result = validate_attestation(event)
        assert result.outcome is AttestationOutcome.VALID
        assert result.owner_pubkey == OWNER_PUBKEY
        assert result.conditions == VECTOR_CONDITIONS

    def test_signed_event_example_end_to_end(self):
        event = Event.from_dict(
            json.loads((VECTORS / "nip_oa_signed_event.json").read_text())
        )
        result = validate_attestation(event)
        assert result.outcome is AttestationOutcome.VALID
        assert result.owner_pubkey == OWNER_PUBKEY


class TestInvalidVectors:
    """The six NIP-OA "Invalid Test Vectors" — each MUST be rejected."""

    def test_two_auth_tags(self):
        tag = ["auth", OWNER_PUBKEY, VECTOR_CONDITIONS, auth_sig_for(VECTOR_CONDITIONS)]
        event = attested_event(VECTOR_CONDITIONS, extra_tags=[list(tag)])
        result = validate_attestation(event)
        assert result.outcome is AttestationOutcome.INVALID
        assert result.reason == "duplicate_auth_tag"

    @pytest.mark.parametrize(
        "tag",
        [
            ["auth", OWNER_PUBKEY, "kind=1"],  # three elements
            ["auth", OWNER_PUBKEY, "kind=1", "ab" * 64, "extra"],  # five
        ],
    )
    def test_wrong_element_count(self, tag):
        result = validate_attestation(attested_event("", auth_tag=tag))
        assert result.outcome is AttestationOutcome.INVALID
        assert result.reason == "malformed_tag"

    def test_trailing_delimiter(self):
        result = validate_attestation(attested_event("kind=1&"))
        assert result.outcome is AttestationOutcome.INVALID
        assert result.reason == "invalid_conditions"

    def test_leading_zero(self):
        result = validate_attestation(attested_event("kind=01"))
        assert result.outcome is AttestationOutcome.INVALID
        assert result.reason == "invalid_conditions"

    def test_self_attestation(self):
        # Owner pubkey equal to event.pubkey — sign the preimage with the
        # agent key so only the self-attestation check can reject it.
        preimage = f"nostr:agent-auth:{AGENT_PUBKEY}:".encode()
        sig = AGENT.sign(hashlib.sha256(preimage).digest()).hex()
        event = attested_event("", auth_tag=["auth", AGENT_PUBKEY, "", sig])
        result = validate_attestation(event)
        assert result.outcome is AttestationOutcome.INVALID
        assert result.reason == "self_attestation"

    def test_valid_tag_on_invalid_event(self):
        event = attested_event(VECTOR_CONDITIONS)
        tampered = replace(event, content="tampered")  # id no longer matches
        result = validate_attestation(tampered)
        assert result.outcome is AttestationOutcome.INVALID
        assert result.reason == "invalid_event"


# -- conditions grammar and evaluation -------------------------------------


class TestConditions:
    def test_empty_conditions_valid(self):
        result = validate_attestation(attested_event(""))
        assert result.outcome is AttestationOutcome.VALID

    def test_absent_tag_is_absent(self):
        event = Event.build(pubkey=AGENT_PUBKEY, kind=1, content="x", created_at=1)
        result = validate_attestation(AGENT.sign_event(event))
        assert result.outcome is AttestationOutcome.ABSENT

    @pytest.mark.parametrize(
        "conditions",
        [
            "&kind=1",  # leading delimiter
            "kind=1&&created_at<5",  # double delimiter
            "kind =1",  # whitespace
            "kind=1 ",  # trailing whitespace
            "KIND=1",  # case-sensitive
            "kind=+1",  # sign
            "kind=１",  # unicode fullwidth digit — str.isdigit() accepts it
            "kind=65536",  # kind out of range
            "created_at<4294967296",  # created_at out of range
            "expires_at<5",  # unsupported clause
        ],
    )
    def test_bad_grammar_rejected(self, conditions):
        result = validate_attestation(attested_event(conditions))
        assert result.outcome is AttestationOutcome.INVALID
        assert result.reason == "invalid_conditions"

    def test_range_boundaries_accepted(self):
        result = validate_attestation(
            attested_event("kind=65535&created_at<4294967295", kind=65535)
        )
        assert result.outcome is AttestationOutcome.VALID

    def test_kind_mismatch_unsatisfied(self):
        result = validate_attestation(attested_event("kind=2"))
        assert result.outcome is AttestationOutcome.INVALID
        assert result.reason == "condition_unsatisfied"

    def test_expired_window_no_wall_clock(self):
        # The event's own created_at violates its auth tag's created_at<
        # bound: rejected purely from the signed data, never the verifier
        # clock. An agent backdating created_at would satisfy the bound —
        # that residual risk is NIP-OA's documented posture, not a bug.
        result = validate_attestation(
            attested_event("created_at<1713957000", created_at=1713957100)
        )
        assert result.outcome is AttestationOutcome.INVALID
        assert result.reason == "condition_unsatisfied"

    def test_created_at_lower_bound(self):
        assert (
            validate_attestation(
                attested_event("created_at>100", created_at=101)
            ).outcome
            is AttestationOutcome.VALID
        )
        result = validate_attestation(attested_event("created_at>100", created_at=100))
        assert result.reason == "condition_unsatisfied"

    def test_wrong_owner_signature(self):
        # Signature by a third key over the right preimage.
        stranger = Keypair(bytes.fromhex("11" * 32))
        preimage = f"nostr:agent-auth:{AGENT_PUBKEY}:".encode()
        sig = stranger.sign(hashlib.sha256(preimage).digest()).hex()
        event = attested_event("", auth_tag=["auth", OWNER_PUBKEY, "", sig])
        result = validate_attestation(event)
        assert result.reason == "invalid_owner_signature"

    def test_conditions_not_normalized(self):
        # Same clauses, different order: each is its own signed string.
        conditions = "created_at<1713957000&kind=1"
        assert validate_attestation(attested_event(conditions)).outcome is (
            AttestationOutcome.VALID
        )
        # Reusing that sig with the reordered string must fail.
        event = attested_event(
            "",
            auth_tag=["auth", OWNER_PUBKEY, VECTOR_CONDITIONS, auth_sig_for(conditions)],
        )
        assert validate_attestation(event).reason == "invalid_owner_signature"


# -- attestation_state / filter_attested -----------------------------------


class TestAttestationState:
    def test_attested(self):
        label = attestation_state(attested_event(""))
        assert label.state is AttestationState.ATTESTED
        assert label.owner_pubkey == OWNER_PUBKEY

    def test_unattested(self):
        event = AGENT.sign_event(
            Event.build(pubkey=AGENT_PUBKEY, kind=1, content="x", created_at=1)
        )
        assert attestation_state(event).state is AttestationState.UNATTESTED

    def test_revoked_owner(self):
        label = attestation_state(attested_event(""), revoked_owners={OWNER_PUBKEY})
        assert label.state is AttestationState.REVOKED
        assert label.owner_pubkey == OWNER_PUBKEY

    def test_revoked_agent_with_attestation(self):
        label = attestation_state(attested_event(""), revoked_agents={AGENT_PUBKEY})
        assert label.state is AttestationState.REVOKED

    def test_revoked_agent_without_attestation(self):
        # The extension: agent-key revocation applies even with no auth tag.
        event = AGENT.sign_event(
            Event.build(pubkey=AGENT_PUBKEY, kind=1, content="x", created_at=1)
        )
        label = attestation_state(event, revoked_agents={AGENT_PUBKEY})
        assert label.state is AttestationState.REVOKED

    def test_invalid_attestation_carries_reason(self):
        label = attestation_state(attested_event("kind=01"))
        assert label.state is AttestationState.INVALID_ATTESTATION
        assert label.reason == "invalid_conditions"

    def test_invalid_event(self):
        tampered = replace(attested_event(""), content="tampered")
        assert attestation_state(tampered).state is AttestationState.INVALID_EVENT

    def test_filter_attested_keeps_order(self):
        attested = attested_event("")
        unattested = AGENT.sign_event(
            Event.build(pubkey=AGENT_PUBKEY, kind=1, content="x", created_at=1)
        )
        attested_later = attested_event("", created_at=2)
        tampered = replace(attested_event("", created_at=3), content="t")
        invalid = attested_event("kind=01")
        kept = filter_attested(
            [attested, tampered, unattested, invalid, attested_later],
            revoked_owners=frozenset(),
            revoked_agents=frozenset(),
        )
        assert kept == [attested, unattested, attested_later]
        kept = filter_attested(
            [attested, unattested], revoked_agents=frozenset({AGENT_PUBKEY})
        )
        assert kept == []


# -- approval counting -----------------------------------------------------


APPROVERS = [Keypair(bytes.fromhex(f"{i:02x}" * 32)) for i in (3, 4, 5)]


def make_request() -> Event:
    requester = APPROVERS[0]
    event = Event.build(
        pubkey=requester.public_key_hex,
        kind=KIND_APPROVAL_REQUEST,
        tags=[["p", APPROVERS[1].public_key_hex]],
        content="approve step 7?",
        created_at=1000,
    )
    return requester.sign_event(event)


def make_verdict(
    approver: Keypair,
    request: Event,
    verdict: str,
    *,
    created_at: int = 2000,
    request_id: str | None = None,
    kind: int = KIND_APPROVAL_VERDICT,
    tags: list[list[str]] | None = None,
) -> Event:
    if tags is None:
        tags = [["e", request_id or request.id], ["verdict", verdict]]
    event = Event.build(
        pubkey=approver.public_key_hex,
        kind=kind,
        tags=tags,
        content="",
        created_at=created_at,
    )
    return approver.sign_event(event)


class TestApprovals:
    def test_counts_and_threshold(self):
        request = make_request()
        events = [
            make_verdict(APPROVERS[0], request, "approve"),
            make_verdict(APPROVERS[1], request, "approve"),
            make_verdict(APPROVERS[2], request, "reject"),
        ]
        counts = count_approvals(request, events)
        assert counts.approve_count == 2
        assert counts.reject_count == 1
        assert is_approved(request, events, threshold=2)
        assert not is_approved(request, events, threshold=3)

    def test_latest_verdict_wins_per_approver(self):
        request = make_request()
        events = [
            make_verdict(APPROVERS[0], request, "approve", created_at=2000),
            make_verdict(APPROVERS[0], request, "reject", created_at=3000),
        ]
        counts = count_approvals(request, events)
        assert counts.per_approver == {APPROVERS[0].public_key_hex: "reject"}
        # Order of the input iterable must not matter.
        counts = count_approvals(request, list(reversed(events)))
        assert counts.per_approver == {APPROVERS[0].public_key_hex: "reject"}

    def test_same_created_at_lowest_id_wins(self):
        request = make_request()
        a = make_verdict(APPROVERS[0], request, "approve", created_at=2000)
        b = make_verdict(
            APPROVERS[0],
            request,
            "reject",
            created_at=2000,
            tags=[["e", request.id], ["verdict", "reject"], ["note", "tiebreak"]],
        )
        winner, loser = (a, b) if a.id < b.id else (b, a)
        expected = "approve" if winner is a else "reject"
        for ordering in ([a, b], [b, a]):
            counts = count_approvals(request, ordering)
            assert counts.per_approver[APPROVERS[0].public_key_hex] == expected

    def test_excluded_candidates(self):
        request = make_request()
        valid = make_verdict(APPROVERS[0], request, "approve")
        wrong_kind = make_verdict(APPROVERS[1], request, "approve", kind=1)
        other_request = make_verdict(
            APPROVERS[1], request, "approve", request_id="ab" * 32
        )
        bad_sig = replace(
            make_verdict(APPROVERS[1], request, "approve"), sig="cd" * 64
        )
        garbage_verdict = make_verdict(
            APPROVERS[1],
            request,
            "maybe",
            tags=[["e", request.id], ["verdict", "maybe"]],
        )
        content_only = APPROVERS[1].sign_event(
            Event.build(
                pubkey=APPROVERS[1].public_key_hex,
                kind=KIND_APPROVAL_VERDICT,
                tags=[["e", request.id]],
                content="approve",  # schema carries the verdict in a tag, not content
                created_at=2000,
            )
        )
        duplicate_tags = make_verdict(
            APPROVERS[1],
            request,
            "approve",
            tags=[["e", request.id], ["verdict", "approve"], ["verdict", "reject"]],
        )
        counts = count_approvals(
            request,
            [
                valid,
                wrong_kind,
                other_request,
                bad_sig,
                garbage_verdict,
                content_only,
                duplicate_tags,
            ],
        )
        assert counts.per_approver == {APPROVERS[0].public_key_hex: "approve"}
        assert counts.approve_count == 1
        assert counts.reject_count == 0

    def test_required_approvers_filter(self):
        request = make_request()
        events = [
            make_verdict(APPROVERS[0], request, "approve"),
            make_verdict(APPROVERS[1], request, "approve"),
        ]
        required = [APPROVERS[1].public_key_hex]
        assert is_approved(request, events, threshold=1, required_approvers=required)
        assert not is_approved(
            request, events, threshold=2, required_approvers=required
        )
        # Outsider approvals alone never satisfy a required-set gate.
        assert not is_approved(
            request,
            [make_verdict(APPROVERS[2], request, "approve")],
            threshold=1,
            required_approvers=required,
        )
