from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from hashlib import sha256


@dataclass(frozen=True, slots=True)
class ReplanRequest:
    request_id: str
    problem_id: str
    order_id: str
    planned_release_at: datetime
    detected_at: datetime
    reason_code: str
    deviation_minutes: int
    consecutive_blocked_count: int
    source: str
    status: str
    source_reference_id: str | None = None
    requested_by: str | None = None
    decided_by: str | None = None
    decided_at: datetime | None = None
    decision_comment: str | None = None
    execution_started_at: datetime | None = None
    execution_completed_at: datetime | None = None
    solver_backend_id: str | None = None
    solver_status: str | None = None
    solver_message: str | None = None


def create_replan_request(
    *,
    problem_id: str,
    order_id: str,
    planned_release_at: datetime,
    detected_at: datetime,
    reason_code: str,
    deviation_minutes: int,
    consecutive_blocked_count: int,
    replan_required: bool,
    source: str = "ReleaseStability",
    source_reference_id: str | None = None,
    requested_by: str | None = None,
) -> ReplanRequest | None:
    if not replan_required:
        return None

    identity = "|".join(
        (
            problem_id,
            order_id,
            planned_release_at.isoformat(),
            reason_code,
            source,
            source_reference_id or "",
        )
    )
    request_id = f"RPL-{sha256(identity.encode('utf-8')).hexdigest()[:16]}"
    return ReplanRequest(
        request_id=request_id,
        problem_id=problem_id,
        order_id=order_id,
        planned_release_at=planned_release_at,
        detected_at=detected_at,
        reason_code=reason_code,
        deviation_minutes=deviation_minutes,
        consecutive_blocked_count=consecutive_blocked_count,
        source=source,
        status="PendingReview",
        source_reference_id=source_reference_id,
        requested_by=requested_by,
    )


def decide_replan_request(
    request: ReplanRequest,
    *,
    decision: str,
    decided_by: str,
    decided_at: datetime,
    comment: str | None = None,
) -> ReplanRequest:
    if request.status != "PendingReview":
        raise ValueError("Only PendingReview requests can be decided")
    if decision not in {"Approve", "Reject"}:
        raise ValueError(f"Unsupported replan decision: {decision}")

    normalized_comment = comment.strip() if comment else None
    if decision == "Reject" and not normalized_comment:
        raise ValueError("Reject decision requires a comment")

    return replace(
        request,
        status="Approved" if decision == "Approve" else "Rejected",
        decided_by=decided_by,
        decided_at=decided_at,
        decision_comment=normalized_comment,
    )


def start_replan_execution(
    request: ReplanRequest,
    *,
    started_at: datetime,
    solver_backend_id: str,
) -> ReplanRequest:
    if request.status != "Approved":
        raise ValueError("Only Approved requests can be executed")
    return replace(
        request,
        status="Running",
        execution_started_at=started_at,
        execution_completed_at=None,
        solver_backend_id=solver_backend_id,
        solver_status=None,
        solver_message=None,
    )


def finish_replan_execution(
    request: ReplanRequest,
    *,
    completed_at: datetime,
    solver_status: str,
    solver_message: str,
) -> ReplanRequest:
    if request.status != "Running":
        raise ValueError("Only Running requests can be finished")
    return replace(
        request,
        status=(
            "Completed"
            if solver_status in {"Optimal", "Feasible"}
            else "Failed"
        ),
        execution_completed_at=completed_at,
        solver_status=solver_status,
        solver_message=solver_message,
    )
