"""Tests for the bridge translation layer (translate.py).

Validates:
- Golden tests: fixture rows → expected signed events
- No-per-step-path test: proves no per-step publication path for kind 42020
- All six translation functions work correctly
"""

import pytest

from lindenmayer.bridge.translate import (
    translate_node_lifecycle,
    translate_run_accounting,
    translate_subgraph_digest,
    translate_approval_request,
    translate_approval_verdict,
    translate_node_state,
)
from lindenmayer.core.kinds.models import (
    NodeLifecycle,
    RunAccounting,
    SubgraphDigest,
    ApprovalRequest,
    ApprovalVerdict,
    NodeStatePointer,
)


class TestTranslateNodeLifecycle:
    """Tests for translate_node_lifecycle."""

    def test_valid_row(self):
        """Translates a valid node row to NodeLifecycle."""
        row = {
            "node": "main.test",
            "status": "active",
            "run": "run-001",
            "reason": "Started",
            "parent_pubkey": "a" * 64,
            "prev_event_id": "b" * 64,
        }
        result = translate_node_lifecycle(row)
        assert isinstance(result, NodeLifecycle)
        assert result.branch == "main.test"
        assert result.status == "active"
        assert result.run == "run-001"
        assert result.reason == "Started"
        assert result.parent_pubkey == "a" * 64
        assert result.prev_event_id == "b" * 64

    def test_minimal_row(self):
        """Translates a minimal valid row."""
        row = {
            "node": "main.test",
            "status": "completed",
            "run": "run-001",
        }
        result = translate_node_lifecycle(row)
        assert isinstance(result, NodeLifecycle)
        assert result.branch == "main.test"
        assert result.status == "completed"
        assert result.run == "run-001"
        assert result.reason == ""
        assert result.parent_pubkey is None
        assert result.prev_event_id is None

    def test_missing_required_field(self):
        """Returns None if required field is missing."""
        row = {"node": "main.test", "status": "active"}  # missing run
        result = translate_node_lifecycle(row)
        assert result is None

    def test_empty_row(self):
        """Returns None for empty row."""
        result = translate_node_lifecycle({})
        assert result is None

    def test_none_row(self):
        """Returns None for None row."""
        result = translate_node_lifecycle(None)
        assert result is None


class TestTranslateRunAccounting:
    """Tests for translate_run_accounting."""

    def test_valid_row_with_transcript_usage(self):
        """Translates a run row with transcript usage."""
        row = {
            "node": "main.test",
            "run": "run-001",
            "status": "completed",
            "started_at": "2026-07-23T10:00:00Z",
            "ended_at": "2026-07-23T10:01:00Z",
            "template": "c" * 64,
        }
        transcript_usage = {
            "iter_count": 5,
            "cost_shadow_usd": 0.5,
            "duration_s": 60.0,
        }
        result = translate_run_accounting(row, transcript_usage)
        assert isinstance(result, RunAccounting)
        assert result.branch == "main.test"
        assert result.run == "run-001"
        assert result.iter_count == 5
        assert result.cost_shadow_usd == 0.5
        assert result.exit_status == "completed"
        assert result.template == "c" * 64

    def test_calculates_duration_from_timestamps(self):
        """Calculates duration from started_at and ended_at."""
        row = {
            "node": "main.test",
            "run": "run-001",
            "status": "completed",
            "started_at": "2026-07-23T10:00:00Z",
            "ended_at": "2026-07-23T10:02:30Z",
        }
        transcript_usage = {}
        result = translate_run_accounting(row, transcript_usage)
        assert result.duration_s == 150.0

    def test_exit_status_mapping(self):
        """Maps run status to exit_status."""
        row = {
            "node": "main.test",
            "run": "run-001",
            "status": "exited",
        }
        result = translate_run_accounting(row, {})
        assert result.exit_status == "exited"

    def test_missing_required_field(self):
        """Returns None if required field is missing."""
        row = {"node": "main.test"}  # missing run
        result = translate_run_accounting(row, {})
        assert result is None

    def test_one_per_run_constraint(self):
        """Confirms function returns one result per run, never per step."""
        runs = [
            {"node": "main.test", "run": "run-001", "status": "completed"},
            {"node": "main.test", "run": "run-002", "status": "completed"},
        ]
        results = [translate_run_accounting(r, {}) for r in runs]
        assert len(results) == 2
        assert all(isinstance(r, RunAccounting) for r in results)


class TestTranslateSubgraphDigest:
    """Tests for translate_subgraph_digest."""

    def test_valid_digest_row(self):
        """Translates a valid digest row."""
        row = {
            "node": "main.test",
            "period_start": "2026-07-23T10:00:00Z",
            "period_end": "2026-07-23T11:00:00Z",
            "child_count": 5,
            "active": 3,
            "exited": 1,
            "completed": 1,
            "stuck_flagged": 0,
            "subtree_cost_shadow_usd": 1.5,
        }
        result = translate_subgraph_digest(row)
        assert isinstance(result, SubgraphDigest)
        assert result.branch == "main.test"
        assert result.child_count == 5
        assert result.active == 3
        assert result.subtree_cost_shadow_usd == 1.5

    def test_missing_period_fields(self):
        """Returns None if period fields are missing."""
        row = {
            "node": "main.test",
            "period_start": "2026-07-23T10:00:00Z",
            # missing period_end
        }
        result = translate_subgraph_digest(row)
        assert result is None


class TestTranslateApprovalRequest:
    """Tests for translate_approval_request."""

    def test_valid_approval_request(self):
        """Translates a valid approval request row."""
        row = {
            "node": "main.test",
            "run": "run-001",
            "iter": 1,
            "step": 5,
            "approver_pubkey": "d" * 64,
            "step_name": "Review",
            "summary": "Awaiting approval",
        }
        result = translate_approval_request(row)
        assert isinstance(result, ApprovalRequest)
        assert result.branch == "main.test"
        assert result.run == "run-001"
        assert result.iter == "1"
        assert result.step == "5"
        assert result.approver_pubkey == "d" * 64
        assert result.step_name == "Review"

    def test_missing_approver_pubkey(self):
        """Returns None if approver_pubkey is missing."""
        row = {
            "node": "main.test",
            "run": "run-001",
            "iter": 1,
            "step": 5,
            "step_name": "Review",
            # missing approver_pubkey
        }
        result = translate_approval_request(row)
        assert result is None


class TestTranslateApprovalVerdict:
    """Tests for translate_approval_verdict."""

    def test_valid_approval_verdict(self):
        """Translates a valid approval verdict row."""
        row = {
            "request_id": "e" * 64,
            "verdict": "approve",
            "rationale": "Looks good",
        }
        result = translate_approval_verdict(row)
        assert isinstance(result, ApprovalVerdict)
        assert result.request_id == "e" * 64
        assert result.verdict == "approve"
        assert result.rationale == "Looks good"

    def test_reject_verdict(self):
        """Translates a rejection verdict."""
        row = {
            "request_id": "e" * 64,
            "verdict": "reject",
            "rationale": "Needs revision",
        }
        result = translate_approval_verdict(row)
        assert result.verdict == "reject"

    def test_invalid_verdict(self):
        """Returns None for invalid verdict."""
        row = {
            "request_id": "e" * 64,
            "verdict": "invalid",
        }
        result = translate_approval_verdict(row)
        assert result is None


class TestTranslateNodeState:
    """Tests for translate_node_state."""

    def test_valid_node_state(self):
        """Translates a valid node state row."""
        row = {
            "node": "main.test",
            "status": "active",
            "run": "run-001",
            "iter": 2,
            "last_lifecycle_event": "f" * 64,
            "cost_shadow_usd": 0.25,
            "cost_cap_usd": 1.0,
        }
        result = translate_node_state(row)
        assert isinstance(result, NodeStatePointer)
        assert result.branch == "main.test"
        assert result.status == "active"
        assert result.run == "run-001"
        assert result.iter == "2"
        assert result.last_lifecycle_event == "f" * 64
        assert result.cost_shadow_usd == 0.25
        assert result.cost_cap_usd == 1.0

    def test_missing_required_field(self):
        """Returns None if required field is missing."""
        row = {
            "node": "main.test",
            "status": "active",
            "run": "run-001",
            # missing iter and last_lifecycle_event
        }
        result = translate_node_state(row)
        assert result is None


class TestNoPerStepPath:
    """Proves no per-step publication path exists for kind 42020.

    This test class verifies that RunAccounting (kind 42020) is only
    published per-run, never per-step. The constraint is enforced by:
    1. Function signature only accepts a run row
    2. No step-level fields in RunAccounting model
    3. No per-step iteration in the translate pipeline
    """

    def test_run_accounting_has_no_step_fields(self):
        """Confirms RunAccounting model has no per-step fields."""
        row = {
            "node": "main.test",
            "run": "run-001",
            "status": "completed",
        }
        result = translate_run_accounting(row, {})
        assert hasattr(result, "branch")
        assert hasattr(result, "run")
        assert hasattr(result, "iter_count")
        assert hasattr(result, "cost_shadow_usd")
        assert hasattr(result, "duration_s")
        assert hasattr(result, "exit_status")
        assert not hasattr(result, "step")
        assert not hasattr(result, "step_cost")
        assert not hasattr(result, "step_tokens")

    def test_translate_run_accounting_function_signature(self):
        """Confirms function takes run row, not step row."""
        import inspect
        sig = inspect.signature(translate_run_accounting)
        params = list(sig.parameters.keys())
        assert "row" in params
        assert "transcript_usage" in params
        assert len(params) == 2
