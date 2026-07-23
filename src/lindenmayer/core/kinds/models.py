"""Typed models for Lindenmayer's eight custom kinds.

Wire shapes follow docs/research/relay-integration/event-kinds.md §2
exactly; the portable per-kind specs live in docs/kinds/. Privacy is a
wire-format property here: run accounting is one rolled-up event per run
(no per-step model exists), and nothing in this API takes a per-worker
identity — ephemeral workers author no events.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator

from lindenmayer.core.event import Event
from lindenmayer.core.kinds import constants
from lindenmayer.core.kinds.base import KindModel, KindValidationError

__all__ = [
    "NodeLifecycle",
    "NodeStatePointer",
    "RunAccounting",
    "SubgraphDigest",
    "ApprovalRequest",
    "ApprovalVerdict",
    "TemplateVersion",
    "TemplatePointer",
]

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _check_hex64(value: str, what: str) -> str:
    if not _HEX64.fullmatch(value):
        raise ValueError(f"{what} must be 64-char lowercase hex, got {value!r}")
    return value


def _check_iso8601(value: str, what: str) -> str:
    try:
        datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{what} must be an ISO 8601 timestamp: {exc}") from exc
    return value


class NodeLifecycle(KindModel):
    """Kind 42010 — one append-only event per node status transition."""

    KIND = constants.KIND_NODE_LIFECYCLE

    branch: str = Field(min_length=1)
    status: str = Field(min_length=1)
    run: str = Field(min_length=1)
    reason: str = ""
    parent_pubkey: str | None = None
    prev_event_id: str | None = None

    @field_validator("parent_pubkey")
    @classmethod
    def _v_parent(cls, v: str | None) -> str | None:
        return None if v is None else _check_hex64(v, "parent_pubkey")

    @field_validator("prev_event_id")
    @classmethod
    def _v_prev(cls, v: str | None) -> str | None:
        return None if v is None else _check_hex64(v, "prev_event_id")

    def event_tags(self) -> list[list[str]]:
        tags = [
            ["branch", self.branch],
            ["status", self.status],
            ["run", self.run],
        ]
        if self.parent_pubkey is not None:
            tags.append(["p", self.parent_pubkey])
        if self.prev_event_id is not None:
            tags.append(["e", self.prev_event_id])
        return tags

    def event_content(self) -> str:
        return self._dump_content({"reason": self.reason})

    @classmethod
    def _from_wire(cls, event: Event) -> dict[str, Any]:
        content = cls._content_object(event)
        return {
            "branch": cls._require_tag(event, "branch"),
            "status": cls._require_tag(event, "status"),
            "run": cls._require_tag(event, "run"),
            "parent_pubkey": event.first_tag_value("p"),
            "prev_event_id": event.first_tag_value("e"),
            "reason": content.get("reason", ""),
        }


class NodeStatePointer(KindModel):
    """Kind 38110 — addressable latest-state snapshot, ``d`` = branch name."""

    KIND = constants.KIND_NODE_STATE_POINTER

    branch: str = Field(min_length=1)  # the addressable `d` key
    status: str = Field(min_length=1)
    run: str = Field(min_length=1)
    iter: str = Field(min_length=1)
    cost_shadow_usd: float = Field(ge=0)
    cost_cap_usd: float = Field(ge=0)
    last_lifecycle_event: str

    @field_validator("last_lifecycle_event")
    @classmethod
    def _v_last(cls, v: str) -> str:
        return _check_hex64(v, "last_lifecycle_event")

    def event_tags(self) -> list[list[str]]:
        return [
            ["d", self.branch],
            ["status", self.status],
            ["run", self.run],
            ["iter", self.iter],
        ]

    def event_content(self) -> str:
        return self._dump_content(
            {
                "cost_shadow_usd": self.cost_shadow_usd,
                "cost_cap_usd": self.cost_cap_usd,
                "last_lifecycle_event": self.last_lifecycle_event,
            }
        )

    @classmethod
    def _from_wire(cls, event: Event) -> dict[str, Any]:
        content = cls._content_object(event)
        return {
            "branch": cls._require_tag(event, "d"),
            "status": cls._require_tag(event, "status"),
            "run": cls._require_tag(event, "run"),
            "iter": cls._require_tag(event, "iter"),
            "cost_shadow_usd": content.get("cost_shadow_usd"),
            "cost_cap_usd": content.get("cost_cap_usd"),
            "last_lifecycle_event": content.get("last_lifecycle_event"),
        }


class RunAccounting(KindModel):
    """Kind 42020 — one rolled-up accounting event per completed run.

    Deliberately run-grained: no per-step fields exist anywhere in this
    API (aggregates flow up, details stay in the subgraph). Costs are
    shadow cost, never real spend.
    """

    KIND = constants.KIND_RUN_ACCOUNTING

    branch: str = Field(min_length=1)
    run: str = Field(min_length=1)
    iter_count: int = Field(ge=0)
    cost_shadow_usd: float = Field(ge=0)
    duration_s: float = Field(ge=0)
    exit_status: Literal["completed", "exited", "killed"]
    template: str | None = None  # template version event id, when template-spawned

    @field_validator("template")
    @classmethod
    def _v_template(cls, v: str | None) -> str | None:
        return None if v is None else _check_hex64(v, "template")

    def event_tags(self) -> list[list[str]]:
        tags = [["branch", self.branch], ["run", self.run]]
        if self.template is not None:
            tags.append(["template", self.template])
        return tags

    def event_content(self) -> str:
        return self._dump_content(
            {
                "iter_count": self.iter_count,
                "cost_shadow_usd": self.cost_shadow_usd,
                "duration_s": self.duration_s,
                "exit_status": self.exit_status,
            }
        )

    @classmethod
    def _from_wire(cls, event: Event) -> dict[str, Any]:
        content = cls._content_object(event)
        return {
            "branch": cls._require_tag(event, "branch"),
            "run": cls._require_tag(event, "run"),
            "template": event.first_tag_value("template"),
            "iter_count": content.get("iter_count"),
            "cost_shadow_usd": content.get("cost_shadow_usd"),
            "duration_s": content.get("duration_s"),
            "exit_status": content.get("exit_status"),
        }


class SubgraphDigest(KindModel):
    """Kind 42030 — periodic aggregate a persistent node publishes about
    its own subtree. No per-child breakdown, by design."""

    KIND = constants.KIND_SUBGRAPH_DIGEST

    branch: str = Field(min_length=1)
    period_start: str
    period_end: str
    child_count: int = Field(ge=0)
    active: int = Field(ge=0)
    exited: int = Field(ge=0)
    completed: int = Field(ge=0)
    stuck_flagged: int = Field(ge=0)
    subtree_cost_shadow_usd: float = Field(ge=0)

    @field_validator("period_start")
    @classmethod
    def _v_start(cls, v: str) -> str:
        return _check_iso8601(v, "period_start")

    @field_validator("period_end")
    @classmethod
    def _v_end(cls, v: str) -> str:
        return _check_iso8601(v, "period_end")

    def event_tags(self) -> list[list[str]]:
        return [
            ["branch", self.branch],
            ["period_start", self.period_start],
            ["period_end", self.period_end],
        ]

    def event_content(self) -> str:
        return self._dump_content(
            {
                "child_count": self.child_count,
                "active": self.active,
                "exited": self.exited,
                "completed": self.completed,
                "stuck_flagged": self.stuck_flagged,
                "subtree_cost_shadow_usd": self.subtree_cost_shadow_usd,
            }
        )

    @classmethod
    def _from_wire(cls, event: Event) -> dict[str, Any]:
        content = cls._content_object(event)
        return {
            "branch": cls._require_tag(event, "branch"),
            "period_start": cls._require_tag(event, "period_start"),
            "period_end": cls._require_tag(event, "period_end"),
            "child_count": content.get("child_count"),
            "active": content.get("active"),
            "exited": content.get("exited"),
            "completed": content.get("completed"),
            "stuck_flagged": content.get("stuck_flagged"),
            "subtree_cost_shadow_usd": content.get("subtree_cost_shadow_usd"),
        }


class ApprovalRequest(KindModel):
    """Kind 42040 — a ``requires_approval`` step asking its approver."""

    KIND = constants.KIND_APPROVAL_REQUEST

    branch: str = Field(min_length=1)
    run: str = Field(min_length=1)
    iter: str = Field(min_length=1)
    step: str = Field(min_length=1)
    approver_pubkey: str
    step_name: str = Field(min_length=1)
    summary: str

    @field_validator("approver_pubkey")
    @classmethod
    def _v_approver(cls, v: str) -> str:
        return _check_hex64(v, "approver_pubkey")

    def event_tags(self) -> list[list[str]]:
        return [
            ["branch", self.branch],
            ["run", self.run],
            ["iter", self.iter],
            ["step", self.step],
            ["p", self.approver_pubkey],
        ]

    def event_content(self) -> str:
        return self._dump_content({"step_name": self.step_name, "summary": self.summary})

    @classmethod
    def _from_wire(cls, event: Event) -> dict[str, Any]:
        content = cls._content_object(event)
        return {
            "branch": cls._require_tag(event, "branch"),
            "run": cls._require_tag(event, "run"),
            "iter": cls._require_tag(event, "iter"),
            "step": cls._require_tag(event, "step"),
            "approver_pubkey": cls._require_tag(event, "p"),
            "step_name": content.get("step_name"),
            "summary": content.get("summary"),
        }


class ApprovalVerdict(KindModel):
    """Kind 42041 — answers a request by ``e``-tagging it; append-only so
    reject→revise→approve chains stay threaded."""

    KIND = constants.KIND_APPROVAL_VERDICT

    request_id: str
    verdict: Literal["approve", "reject"]
    rationale: str

    @field_validator("request_id")
    @classmethod
    def _v_request(cls, v: str) -> str:
        return _check_hex64(v, "request_id")

    def event_tags(self) -> list[list[str]]:
        return [["e", self.request_id], ["verdict", self.verdict]]

    def event_content(self) -> str:
        return self._dump_content({"rationale": self.rationale})

    @classmethod
    def _from_wire(cls, event: Event) -> dict[str, Any]:
        content = cls._content_object(event)
        return {
            "request_id": cls._require_tag(event, "e"),
            "verdict": cls._require_tag(event, "verdict"),
            "rationale": content.get("rationale"),
        }


class TemplateVersion(KindModel):
    """Kind 42050 — one immutable event per registered template version."""

    KIND = constants.KIND_TEMPLATE_VERSION

    template_name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    summary: str
    inherits: str | None = None  # parent template version event id
    git_ref: str | None = None

    @field_validator("inherits")
    @classmethod
    def _v_inherits(cls, v: str | None) -> str | None:
        return None if v is None else _check_hex64(v, "inherits")

    def event_tags(self) -> list[list[str]]:
        tags = [["template_name", self.template_name], ["version", self.version]]
        if self.inherits is not None:
            # NIP-10 style marked e-tag: ["e", <id>, <relay-url>, <marker>]
            tags.append(["e", self.inherits, "", "inherit"])
        if self.git_ref is not None:
            tags.append(["git_ref", self.git_ref])
        return tags

    def event_content(self) -> str:
        return self._dump_content({"summary": self.summary})

    @classmethod
    def _from_wire(cls, event: Event) -> dict[str, Any]:
        content = cls._content_object(event)
        inherits = None
        for values in event.tag_values("e"):
            if len(values) >= 3 and values[2] == "inherit":
                inherits = values[0]
                break
        return {
            "template_name": cls._require_tag(event, "template_name"),
            "version": cls._require_tag(event, "version"),
            "inherits": inherits,
            "git_ref": event.first_tag_value("git_ref"),
            "summary": content.get("summary"),
        }


class TemplatePointer(KindModel):
    """Kind 38150 — addressable pointer to the current template version,
    ``d`` = template name. Pure indirection: content is empty."""

    KIND = constants.KIND_TEMPLATE_POINTER

    template_name: str = Field(min_length=1)  # the addressable `d` key
    version_event_id: str

    @field_validator("version_event_id")
    @classmethod
    def _v_version(cls, v: str) -> str:
        return _check_hex64(v, "version_event_id")

    def event_tags(self) -> list[list[str]]:
        return [["d", self.template_name], ["e", self.version_event_id]]

    def event_content(self) -> str:
        return ""

    @classmethod
    def _from_wire(cls, event: Event) -> dict[str, Any]:
        # Spec: content is empty or "{}" — anything else is malformed.
        if event.content not in ("", "{}"):
            raise KindValidationError(
                f"kind {cls.KIND} (TemplatePointer) content must be empty or '{{}}', "
                f"got {event.content!r}"
            )
        return {
            "template_name": cls._require_tag(event, "d"),
            "version_event_id": cls._require_tag(event, "e"),
        }
