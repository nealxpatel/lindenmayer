"""Tests for Lindenmayer custom event kinds.

Validates:
- Round-trip conversion (model -> Event -> model)
- Rejection of invalid inputs (wrong kind, missing tags, malformed content)
- Addressable kinds carry 'd' tag
- All worked examples from docs validate
"""

import json
import pytest

from lindenmayer.core.event import Event
from lindenmayer.core.kinds.constants import (
    KIND_NODE_LIFECYCLE,
    KIND_NODE_STATE_POINTER,
    KIND_RUN_ACCOUNTING,
    KIND_SUBGRAPH_DIGEST,
    KIND_APPROVAL_REQUEST,
    KIND_APPROVAL_VERDICT,
    KIND_TEMPLATE_VERSION,
    KIND_TEMPLATE_POINTER,
)
from lindenmayer.core.kinds.models import (
    NodeLifecycle,
    NodeStatePointer,
    RunAccounting,
    SubgraphDigest,
    ApprovalRequest,
    ApprovalVerdict,
    TemplateVersion,
    TemplatePointer,
)
from lindenmayer.core.kinds.registry import KIND_REGISTRY, parse_event
from lindenmayer.core.kinds.base import KindValidationError


# Test fixtures for common values
EXAMPLE_PUBKEY = "3f0ff4ce8fa9b8006d754e26e73b8562711f264efc45ec4a751ba735d6221513"
EXAMPLE_PARENT_PUBKEY = "0e4702b8331d23cf835aeb1d1e0640403b1812709ab10eb1250f688cc6ce183f"
EXAMPLE_CREATED_AT = 1721761200


class TestNodeLifecycle:
    """Tests for kind 42010 — Node Lifecycle."""

    def test_round_trip(self):
        """Valid model -> Event -> model conversion."""
        nl = NodeLifecycle(
            branch="main.core.kinds",
            status="active",
            run="run-001",
            reason="Initial startup",
            parent_pubkey=EXAMPLE_PARENT_PUBKEY,
            prev_event_id=None,
        )
        event = nl.to_event(pubkey=EXAMPLE_PUBKEY, created_at=EXAMPLE_CREATED_AT)
        parsed = NodeLifecycle.from_event(event)

        assert parsed.branch == nl.branch
        assert parsed.status == nl.status
        assert parsed.run == nl.run
        assert parsed.reason == nl.reason
        assert parsed.parent_pubkey == nl.parent_pubkey
        assert parsed.prev_event_id == nl.prev_event_id

    def test_wrong_kind(self):
        """Rejects event with wrong kind number."""
        event = Event.build(
            pubkey=EXAMPLE_PUBKEY,
            kind=42020,  # Wrong kind
            tags=[["branch", "test"], ["status", "active"], ["run", "r1"]],
            content='{"reason":""}',
            created_at=EXAMPLE_CREATED_AT,
        )
        with pytest.raises(KindValidationError, match="kind 42020"):
            NodeLifecycle.from_event(event)

    def test_missing_required_tag_branch(self):
        """Rejects event missing required 'branch' tag."""
        event = Event.build(
            pubkey=EXAMPLE_PUBKEY,
            kind=KIND_NODE_LIFECYCLE,
            tags=[["status", "active"], ["run", "r1"]],  # Missing branch
            content='{"reason":""}',
            created_at=EXAMPLE_CREATED_AT,
        )
        with pytest.raises(KindValidationError, match="branch"):
            NodeLifecycle.from_event(event)

    def test_missing_required_tag_status(self):
        """Rejects event missing required 'status' tag."""
        event = Event.build(
            pubkey=EXAMPLE_PUBKEY,
            kind=KIND_NODE_LIFECYCLE,
            tags=[["branch", "test"], ["run", "r1"]],  # Missing status
            content='{"reason":""}',
            created_at=EXAMPLE_CREATED_AT,
        )
        with pytest.raises(KindValidationError, match="status"):
            NodeLifecycle.from_event(event)

    def test_missing_required_tag_run(self):
        """Rejects event missing required 'run' tag."""
        event = Event.build(
            pubkey=EXAMPLE_PUBKEY,
            kind=KIND_NODE_LIFECYCLE,
            tags=[["branch", "test"], ["status", "active"]],  # Missing run
            content='{"reason":""}',
            created_at=EXAMPLE_CREATED_AT,
        )
        with pytest.raises(KindValidationError, match="run"):
            NodeLifecycle.from_event(event)

    def test_malformed_parent_pubkey(self):
        """Rejects event with malformed parent pubkey."""
        with pytest.raises(ValueError, match="parent_pubkey"):
            NodeLifecycle(
                branch="test",
                status="active",
                run="r1",
                reason="",
                parent_pubkey="not-hex",
                prev_event_id=None,
            )

    def test_malformed_prev_event_id(self):
        """Rejects event with malformed prev_event_id."""
        with pytest.raises(ValueError, match="prev_event_id"):
            NodeLifecycle(
                branch="test",
                status="active",
                run="r1",
                reason="",
                parent_pubkey=None,
                prev_event_id="not-hex",
            )

    def test_optional_parent_and_prev(self):
        """Accepts event with optional parent and prev omitted."""
        nl = NodeLifecycle(
            branch="test",
            status="completed",
            run="r1",
            reason="Done",
            parent_pubkey=None,
            prev_event_id=None,
        )
        event = nl.to_event(pubkey=EXAMPLE_PUBKEY, created_at=EXAMPLE_CREATED_AT)
        # Should have only branch, status, run tags
        tag_names = {tag[0] for tag in event.tags}
        assert tag_names == {"branch", "status", "run"}

    def test_worked_example_from_docs(self):
        """Validate worked example from 42010-node-lifecycle.md."""
        example_json = {
            "kind": 42010,
            "tags": [
                ["branch", "main.core.kinds"],
                ["status", "active"],
                ["run", "run-001"],
                ["p", "0e4702b8331d23cf835aeb1d1e0640403b1812709ab10eb1250f688cc6ce183f"],
                ["e", "abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234"],
            ],
            "content": '{"reason":"Initial startup"}',
            "created_at": 1721761200,
            "pubkey": "3f0ff4ce8fa9b8006d754e26e73b8562711f264efc45ec4a751ba735d6221513",
            "id": "a" * 64,
            "sig": None,
        }
        event = Event.from_dict(example_json)
        parsed = NodeLifecycle.from_event(event)
        assert parsed.branch == "main.core.kinds"
        assert parsed.status == "active"


class TestNodeStatePointer:
    """Tests for kind 38110 — Node State Pointer."""

    def test_round_trip(self):
        """Valid model -> Event -> model conversion."""
        nsp = NodeStatePointer(
            branch="main.core.kinds",
            status="active",
            run="run-001",
            iter="1",
            cost_shadow_usd=0.15,
            cost_cap_usd=2.5,
            last_lifecycle_event="a" * 64,
        )
        event = nsp.to_event(pubkey=EXAMPLE_PUBKEY, created_at=EXAMPLE_CREATED_AT)
        parsed = NodeStatePointer.from_event(event)

        assert parsed.branch == nsp.branch
        assert parsed.status == nsp.status
        assert parsed.run == nsp.run
        assert parsed.iter == nsp.iter
        assert parsed.cost_shadow_usd == nsp.cost_shadow_usd
        assert parsed.cost_cap_usd == nsp.cost_cap_usd
        assert parsed.last_lifecycle_event == nsp.last_lifecycle_event

    def test_addressable_carries_d_tag(self):
        """Addressable kind must carry 'd' tag (equals branch)."""
        nsp = NodeStatePointer(
            branch="test-branch",
            status="active",
            run="r1",
            iter="1",
            cost_shadow_usd=0.0,
            cost_cap_usd=1.0,
            last_lifecycle_event="a" * 64,
        )
        event = nsp.to_event(pubkey=EXAMPLE_PUBKEY, created_at=EXAMPLE_CREATED_AT)
        d_tags = [tag[1] for tag in event.tags if tag[0] == "d"]
        assert len(d_tags) == 1
        assert d_tags[0] == "test-branch"

    def test_missing_required_tag_d(self):
        """Rejects event missing 'd' tag."""
        event = Event.build(
            pubkey=EXAMPLE_PUBKEY,
            kind=KIND_NODE_STATE_POINTER,
            tags=[["status", "active"], ["run", "r1"], ["iter", "1"]],
            content='{"cost_shadow_usd":0,"cost_cap_usd":1,"last_lifecycle_event":"' + "a" * 64 + '"}',
            created_at=EXAMPLE_CREATED_AT,
        )
        with pytest.raises(KindValidationError, match="d"):
            NodeStatePointer.from_event(event)

    def test_malformed_last_lifecycle_event(self):
        """Rejects malformed last_lifecycle_event."""
        with pytest.raises(ValueError, match="last_lifecycle_event"):
            NodeStatePointer(
                branch="test",
                status="active",
                run="r1",
                iter="1",
                cost_shadow_usd=0.0,
                cost_cap_usd=1.0,
                last_lifecycle_event="not-hex",
            )

    def test_worked_example_from_docs(self):
        """Validate worked example from 38110-node-state-pointer.md."""
        example_json = {
            "kind": 38110,
            "tags": [
                ["d", "main.core.kinds"],
                ["status", "active"],
                ["run", "run-001"],
                ["iter", "1"],
            ],
            "content": '{"cost_shadow_usd":0.15,"cost_cap_usd":2.5,"last_lifecycle_event":"' + "a" * 64 + '"}',
            "created_at": 1721761201,
            "pubkey": "3f0ff4ce8fa9b8006d754e26e73b8562711f264efc45ec4a751ba735d6221513",
            "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "sig": None,
        }
        event = Event.from_dict(example_json)
        parsed = NodeStatePointer.from_event(event)
        assert parsed.branch == "main.core.kinds"
        assert parsed.status == "active"
        assert parsed.cost_shadow_usd == 0.15


class TestRunAccounting:
    """Tests for kind 42020 — Run Accounting."""

    def test_round_trip(self):
        """Valid model -> Event -> model conversion."""
        ra = RunAccounting(
            branch="main.core.kinds",
            run="run-001",
            iter_count=5,
            cost_shadow_usd=0.42,
            duration_s=123.45,
            exit_status="completed",
            template=None,
        )
        event = ra.to_event(pubkey=EXAMPLE_PUBKEY, created_at=EXAMPLE_CREATED_AT)
        parsed = RunAccounting.from_event(event)

        assert parsed.branch == ra.branch
        assert parsed.run == ra.run
        assert parsed.iter_count == ra.iter_count
        assert parsed.cost_shadow_usd == ra.cost_shadow_usd
        assert parsed.duration_s == ra.duration_s
        assert parsed.exit_status == ra.exit_status
        assert parsed.template == ra.template

    def test_exit_status_invalid(self):
        """Rejects invalid exit_status."""
        with pytest.raises(ValueError):
            RunAccounting(
                branch="test",
                run="r1",
                iter_count=1,
                cost_shadow_usd=0.0,
                duration_s=1.0,
                exit_status="invalid",
                template=None,
            )

    def test_template_field_optional(self):
        """Template field is optional."""
        ra_none = RunAccounting(
            branch="test",
            run="r1",
            iter_count=1,
            cost_shadow_usd=0.0,
            duration_s=1.0,
            exit_status="completed",
            template=None,
        )
        event = ra_none.to_event(pubkey=EXAMPLE_PUBKEY, created_at=EXAMPLE_CREATED_AT)
        # Event should not have template tag
        template_tags = [tag for tag in event.tags if tag[0] == "template"]
        assert len(template_tags) == 0

    def test_worked_example_from_docs(self):
        """Validate worked example from 42020-run-accounting.md."""
        example_json = {
            "kind": 42020,
            "tags": [
                ["branch", "main.core.kinds"],
                ["run", "run-001"],
                ["template", "a" * 64],
            ],
            "content": '{"iter_count":5,"cost_shadow_usd":0.42,"duration_s":123.45,"exit_status":"completed"}',
            "created_at": 1721761202,
            "pubkey": "3f0ff4ce8fa9b8006d754e26e73b8562711f264efc45ec4a751ba735d6221513",
            "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "sig": None,
        }
        event = Event.from_dict(example_json)
        parsed = RunAccounting.from_event(event)
        assert parsed.iter_count == 5
        assert parsed.cost_shadow_usd == 0.42


class TestSubgraphDigest:
    """Tests for kind 42030 — Subgraph Digest."""

    def test_round_trip(self):
        """Valid model -> Event -> model conversion."""
        sg = SubgraphDigest(
            branch="main.core.kinds",
            period_start="2026-07-23T00:00:00Z",
            period_end="2026-07-23T01:00:00Z",
            child_count=2,
            active=1,
            exited=1,
            completed=0,
            stuck_flagged=0,
            subtree_cost_shadow_usd=1.23,
        )
        event = sg.to_event(pubkey=EXAMPLE_PUBKEY, created_at=EXAMPLE_CREATED_AT)
        parsed = SubgraphDigest.from_event(event)

        assert parsed.branch == sg.branch
        assert parsed.period_start == sg.period_start
        assert parsed.period_end == sg.period_end
        assert parsed.child_count == sg.child_count
        assert parsed.subtree_cost_shadow_usd == sg.subtree_cost_shadow_usd

    def test_invalid_iso8601_period_start(self):
        """Rejects invalid ISO 8601 period_start."""
        with pytest.raises(ValueError, match="period_start"):
            SubgraphDigest(
                branch="test",
                period_start="not-a-timestamp",
                period_end="2026-07-23T01:00:00Z",
                child_count=0,
                active=0,
                exited=0,
                completed=0,
                stuck_flagged=0,
                subtree_cost_shadow_usd=0.0,
            )

    def test_worked_example_from_docs(self):
        """Validate worked example from 42030-subgraph-digest.md."""
        example_json = {
            "kind": 42030,
            "tags": [
                ["branch", "main.core.kinds"],
                ["period_start", "2026-07-23T00:00:00Z"],
                ["period_end", "2026-07-23T01:00:00Z"],
            ],
            "content": '{"child_count":2,"active":1,"exited":1,"completed":0,"stuck_flagged":0,"subtree_cost_shadow_usd":1.23}',
            "created_at": 1721761203,
            "pubkey": "3f0ff4ce8fa9b8006d754e26e73b8562711f264efc45ec4a751ba735d6221513",
            "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "sig": None,
        }
        event = Event.from_dict(example_json)
        parsed = SubgraphDigest.from_event(event)
        assert parsed.child_count == 2
        assert parsed.active == 1


class TestApprovalRequest:
    """Tests for kind 42040 — Approval Request."""

    def test_round_trip(self):
        """Valid model -> Event -> model conversion."""
        ar = ApprovalRequest(
            branch="main.core.kinds",
            run="run-001",
            iter="2",
            step="03-REVIEW",
            approver_pubkey=EXAMPLE_PARENT_PUBKEY,
            step_name="REVIEW",
            summary="Code review required before proceeding",
        )
        event = ar.to_event(pubkey=EXAMPLE_PUBKEY, created_at=EXAMPLE_CREATED_AT)
        parsed = ApprovalRequest.from_event(event)

        assert parsed.branch == ar.branch
        assert parsed.run == ar.run
        assert parsed.iter == ar.iter
        assert parsed.step == ar.step
        assert parsed.approver_pubkey == ar.approver_pubkey
        assert parsed.step_name == ar.step_name
        assert parsed.summary == ar.summary

    def test_malformed_approver_pubkey(self):
        """Rejects malformed approver_pubkey."""
        with pytest.raises(ValueError, match="approver_pubkey"):
            ApprovalRequest(
                branch="test",
                run="r1",
                iter="1",
                step="01",
                approver_pubkey="not-hex",
                step_name="TEST",
                summary="",
            )

    def test_worked_example_from_docs(self):
        """Validate worked example from 42040-approval-request.md."""
        example_json = {
            "kind": 42040,
            "tags": [
                ["branch", "main.core.kinds"],
                ["run", "run-001"],
                ["iter", "2"],
                ["step", "03-REVIEW"],
                ["p", "0e4702b8331d23cf835aeb1d1e0640403b1812709ab10eb1250f688cc6ce183f"],
            ],
            "content": '{"step_name":"REVIEW","summary":"Code review required before proceeding with deployment"}',
            "created_at": 1721761204,
            "pubkey": "3f0ff4ce8fa9b8006d754e26e73b8562711f264efc45ec4a751ba735d6221513",
            "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "sig": None,
        }
        event = Event.from_dict(example_json)
        parsed = ApprovalRequest.from_event(event)
        assert parsed.step_name == "REVIEW"


class TestApprovalVerdict:
    """Tests for kind 42041 — Approval Verdict."""

    def test_round_trip(self):
        """Valid model -> Event -> model conversion."""
        av = ApprovalVerdict(
            request_id="b" * 64,
            verdict="approve",
            rationale="Changes look good",
        )
        event = av.to_event(pubkey=EXAMPLE_PUBKEY, created_at=EXAMPLE_CREATED_AT)
        parsed = ApprovalVerdict.from_event(event)

        assert parsed.request_id == av.request_id
        assert parsed.verdict == av.verdict
        assert parsed.rationale == av.rationale

    def test_verdict_values(self):
        """Only 'approve' and 'reject' are valid verdicts."""
        # approve should work
        av_ok = ApprovalVerdict(
            request_id="a" * 64,
            verdict="approve",
            rationale="",
        )
        assert av_ok.verdict == "approve"

        # reject should work
        av_ok2 = ApprovalVerdict(
            request_id="a" * 64,
            verdict="reject",
            rationale="",
        )
        assert av_ok2.verdict == "reject"

        # invalid should fail
        with pytest.raises(ValueError):
            ApprovalVerdict(
                request_id="a" * 64,
                verdict="maybe",
                rationale="",
            )

    def test_worked_example_from_docs(self):
        """Validate worked example from 42041-approval-verdict.md."""
        example_json = {
            "kind": 42041,
            "tags": [
                ["e", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"],
                ["verdict", "approve"],
            ],
            "content": '{"rationale":"Changes look good, approved for deployment"}',
            "created_at": 1721761205,
            "pubkey": "0e4702b8331d23cf835aeb1d1e0640403b1812709ab10eb1250f688cc6ce183f",
            "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "sig": None,
        }
        event = Event.from_dict(example_json)
        parsed = ApprovalVerdict.from_event(event)
        assert parsed.verdict == "approve"


class TestTemplateVersion:
    """Tests for kind 42050 — Template Version."""

    def test_round_trip(self):
        """Valid model -> Event -> model conversion."""
        tv = TemplateVersion(
            template_name="default-node",
            version="1.0.0",
            summary="Initial release",
            inherits=None,
            git_ref="main@abc123d",
        )
        event = tv.to_event(pubkey=EXAMPLE_PUBKEY, created_at=EXAMPLE_CREATED_AT)
        parsed = TemplateVersion.from_event(event)

        assert parsed.template_name == tv.template_name
        assert parsed.version == tv.version
        assert parsed.summary == tv.summary
        assert parsed.inherits == tv.inherits
        assert parsed.git_ref == tv.git_ref

    def test_with_inheritance(self):
        """Template version can have inherits field."""
        tv = TemplateVersion(
            template_name="specialized-node",
            version="1.0.0",
            summary="Specialization of default-node",
            inherits="a" * 64,
            git_ref=None,
        )
        event = tv.to_event(pubkey=EXAMPLE_PUBKEY, created_at=EXAMPLE_CREATED_AT)
        parsed = TemplateVersion.from_event(event)

        assert parsed.inherits == "a" * 64
        # Should have e tag with inherit marker (4-element tag: ["e", id, relay, marker])
        e_tags = [tag for tag in event.tags if tag[0] == "e" and len(tag) >= 4 and tag[3] == "inherit"]
        assert len(e_tags) == 1
        assert e_tags[0][1] == "a" * 64

    def test_worked_example_from_docs(self):
        """Validate worked example from 42050-template-version.md."""
        example_json = {
            "kind": 42050,
            "tags": [
                ["template_name", "default-node"],
                ["version", "1.0.0"],
                ["git_ref", "main@abc123d"],
            ],
            "content": '{"summary":"Initial release of default node template"}',
            "created_at": 1721761206,
            "pubkey": "3f0ff4ce8fa9b8006d754e26e73b8562711f264efc45ec4a751ba735d6221513",
            "id": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
            "sig": None,
        }
        event = Event.from_dict(example_json)
        parsed = TemplateVersion.from_event(event)
        assert parsed.template_name == "default-node"
        assert parsed.version == "1.0.0"


class TestTemplatePointer:
    """Tests for kind 38150 — Template Pointer."""

    def test_round_trip(self):
        """Valid model -> Event -> model conversion."""
        tp = TemplatePointer(
            template_name="default-node",
            version_event_id="cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
        )
        event = tp.to_event(pubkey=EXAMPLE_PUBKEY, created_at=EXAMPLE_CREATED_AT)
        parsed = TemplatePointer.from_event(event)

        assert parsed.template_name == tp.template_name
        assert parsed.version_event_id == tp.version_event_id

    def test_addressable_carries_d_tag(self):
        """Addressable kind must carry 'd' tag (equals template_name)."""
        tp = TemplatePointer(
            template_name="my-template",
            version_event_id="a" * 64,
        )
        event = tp.to_event(pubkey=EXAMPLE_PUBKEY, created_at=EXAMPLE_CREATED_AT)
        d_tags = [tag[1] for tag in event.tags if tag[0] == "d"]
        assert len(d_tags) == 1
        assert d_tags[0] == "my-template"

    def test_content_must_be_empty(self):
        """Content must be empty or '{}'."""
        # Empty should work
        event_empty = Event.build(
            pubkey=EXAMPLE_PUBKEY,
            kind=KIND_TEMPLATE_POINTER,
            tags=[["d", "test"], ["e", "a" * 64]],
            content="",
            created_at=EXAMPLE_CREATED_AT,
        )
        parsed = TemplatePointer.from_event(event_empty)
        assert parsed is not None

        # '{}' should work
        event_obj = Event.build(
            pubkey=EXAMPLE_PUBKEY,
            kind=KIND_TEMPLATE_POINTER,
            tags=[["d", "test"], ["e", "a" * 64]],
            content="{}",
            created_at=EXAMPLE_CREATED_AT,
        )
        parsed = TemplatePointer.from_event(event_obj)
        assert parsed is not None

        # Non-empty should fail
        event_bad = Event.build(
            pubkey=EXAMPLE_PUBKEY,
            kind=KIND_TEMPLATE_POINTER,
            tags=[["d", "test"], ["e", "a" * 64]],
            content='{"data":"bad"}',
            created_at=EXAMPLE_CREATED_AT,
        )
        with pytest.raises(KindValidationError, match="content must be empty"):
            TemplatePointer.from_event(event_bad)

    def test_worked_example_from_docs(self):
        """Validate worked example from 38150-template-pointer.md."""
        example_json = {
            "kind": 38150,
            "tags": [
                ["d", "default-node"],
                ["e", "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"],
            ],
            "content": "",
            "created_at": 1721761207,
            "pubkey": "3f0ff4ce8fa9b8006d754e26e73b8562711f264efc45ec4a751ba735d6221513",
            "id": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
            "sig": None,
        }
        event = Event.from_dict(example_json)
        parsed = TemplatePointer.from_event(event)
        assert parsed.template_name == "default-node"


class TestRegistry:
    """Tests for the kind registry and parse_event dispatcher."""

    def test_all_kinds_registered(self):
        """All eight kinds are in the registry."""
        expected_kinds = {
            KIND_NODE_LIFECYCLE,
            KIND_NODE_STATE_POINTER,
            KIND_RUN_ACCOUNTING,
            KIND_SUBGRAPH_DIGEST,
            KIND_APPROVAL_REQUEST,
            KIND_APPROVAL_VERDICT,
            KIND_TEMPLATE_VERSION,
            KIND_TEMPLATE_POINTER,
        }
        assert set(KIND_REGISTRY.keys()) == expected_kinds

    def test_parse_event_node_lifecycle(self):
        """parse_event correctly dispatches kind 42010."""
        event = Event.build(
            pubkey=EXAMPLE_PUBKEY,
            kind=KIND_NODE_LIFECYCLE,
            tags=[["branch", "test"], ["status", "active"], ["run", "r1"]],
            content='{"reason":""}',
            created_at=EXAMPLE_CREATED_AT,
        )
        parsed = parse_event(event)
        assert isinstance(parsed, NodeLifecycle)
        assert parsed.branch == "test"

    def test_parse_event_unknown_kind(self):
        """parse_event raises for unknown kind."""
        event = Event.build(
            pubkey=EXAMPLE_PUBKEY,
            kind=999,  # Unknown kind
            tags=[],
            content="",
            created_at=EXAMPLE_CREATED_AT,
        )
        with pytest.raises(ValueError, match="not a Lindenmayer kind"):
            parse_event(event)

    def test_parse_event_wrong_kind_number(self):
        """parse_event raises if event kind doesn't match expected kind."""
        # Build an event that looks like 42010 but has wrong kind number
        event = Event.build(
            pubkey=EXAMPLE_PUBKEY,
            kind=42020,  # Wrong kind
            tags=[["branch", "test"], ["status", "active"], ["run", "r1"]],
            content='{"reason":""}',
            created_at=EXAMPLE_CREATED_AT,
        )
        # Force it to try parsing as 42010
        with pytest.raises(KindValidationError, match="kind 42020"):
            NodeLifecycle.from_event(event)
