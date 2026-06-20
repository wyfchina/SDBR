from datetime import datetime, timezone

import pytest

from sdbr.replanning import (
    create_replan_request,
    decide_replan_request,
    finish_replan_execution,
    start_replan_execution,
)


def _utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 6, 20, hour, minute, tzinfo=timezone.utc)


def test_creates_pending_replan_request_for_required_replan():
    request = create_replan_request(
        problem_id="PLAN-1",
        order_id="WO-1",
        planned_release_at=_utc(6),
        detected_at=_utc(8),
        reason_code="ConsecutiveGateBlocks",
        deviation_minutes=120,
        consecutive_blocked_count=3,
        replan_required=True,
    )

    assert request is not None
    assert request.request_id.startswith("RPL-")
    assert request.problem_id == "PLAN-1"
    assert request.order_id == "WO-1"
    assert request.status == "PendingReview"
    assert request.source == "ReleaseStability"
    assert request.reason_code == "ConsecutiveGateBlocks"


def test_replan_request_id_is_stable_across_repeated_detection_times():
    first = create_replan_request(
        problem_id="PLAN-1",
        order_id="WO-1",
        planned_release_at=_utc(6),
        detected_at=_utc(8),
        reason_code="ConsecutiveGateBlocks",
        deviation_minutes=120,
        consecutive_blocked_count=3,
        replan_required=True,
    )
    repeated = create_replan_request(
        problem_id="PLAN-1",
        order_id="WO-1",
        planned_release_at=_utc(6),
        detected_at=_utc(8, 30),
        reason_code="ConsecutiveGateBlocks",
        deviation_minutes=150,
        consecutive_blocked_count=4,
        replan_required=True,
    )

    assert first is not None
    assert repeated is not None
    assert repeated.request_id == first.request_id


def test_does_not_create_request_when_replan_is_not_required():
    request = create_replan_request(
        problem_id="PLAN-1",
        order_id="WO-1",
        planned_release_at=_utc(6),
        detected_at=_utc(6),
        reason_code="WithinTolerance",
        deviation_minutes=0,
        consecutive_blocked_count=0,
        replan_required=False,
    )

    assert request is None


def test_approves_pending_replan_request_with_audit_fields():
    request = _pending_request()

    approved = decide_replan_request(
        request,
        decision="Approve",
        decided_by="planner-1",
        decided_at=_utc(9),
        comment="Capacity plan reviewed.",
    )

    assert approved.status == "Approved"
    assert approved.decided_by == "planner-1"
    assert approved.decided_at == _utc(9)
    assert approved.decision_comment == "Capacity plan reviewed."
    assert request.status == "PendingReview"


def test_rejects_pending_replan_request_with_required_comment():
    rejected = decide_replan_request(
        _pending_request(),
        decision="Reject",
        decided_by="planner-1",
        decided_at=_utc(9),
        comment="Material arrival is already confirmed.",
    )

    assert rejected.status == "Rejected"
    assert rejected.decision_comment == "Material arrival is already confirmed."


def test_reject_decision_requires_comment():
    with pytest.raises(ValueError, match="Reject decision requires a comment"):
        decide_replan_request(
            _pending_request(),
            decision="Reject",
            decided_by="planner-1",
            decided_at=_utc(9),
        )


def test_decided_replan_request_cannot_be_decided_again():
    approved = decide_replan_request(
        _pending_request(),
        decision="Approve",
        decided_by="planner-1",
        decided_at=_utc(9),
    )

    with pytest.raises(ValueError, match="Only PendingReview requests can be decided"):
        decide_replan_request(
            approved,
            decision="Reject",
            decided_by="planner-2",
            decided_at=_utc(10),
            comment="Changed decision.",
        )


def test_starts_approved_replan_execution_with_gurobi():
    running = start_replan_execution(
        _approved_request(),
        started_at=_utc(10),
        solver_backend_id="gurobi",
    )

    assert running.status == "Running"
    assert running.execution_started_at == _utc(10)
    assert running.solver_backend_id == "gurobi"


def test_finishes_running_execution_as_completed_for_optimal_result():
    running = start_replan_execution(
        _approved_request(),
        started_at=_utc(10),
        solver_backend_id="gurobi",
    )

    completed = finish_replan_execution(
        running,
        completed_at=_utc(11),
        solver_status="Optimal",
        solver_message="Optimal schedule found.",
    )

    assert completed.status == "Completed"
    assert completed.execution_completed_at == _utc(11)
    assert completed.solver_status == "Optimal"
    assert completed.solver_message == "Optimal schedule found."


def test_finishes_running_execution_as_failed_for_infeasible_result():
    running = start_replan_execution(
        _approved_request(),
        started_at=_utc(10),
        solver_backend_id="gurobi",
    )

    failed = finish_replan_execution(
        running,
        completed_at=_utc(11),
        solver_status="Infeasible",
        solver_message="No feasible schedule.",
    )

    assert failed.status == "Failed"
    assert failed.solver_status == "Infeasible"


def test_cannot_start_execution_before_request_is_approved():
    with pytest.raises(ValueError, match="Only Approved requests can be executed"):
        start_replan_execution(
            _pending_request(),
            started_at=_utc(10),
            solver_backend_id="gurobi",
        )


def test_cannot_finish_execution_that_is_not_running():
    with pytest.raises(ValueError, match="Only Running requests can be finished"):
        finish_replan_execution(
            _approved_request(),
            completed_at=_utc(11),
            solver_status="Optimal",
            solver_message="Optimal schedule found.",
        )


def _pending_request():
    request = create_replan_request(
        problem_id="PLAN-1",
        order_id="WO-1",
        planned_release_at=_utc(6),
        detected_at=_utc(8),
        reason_code="ConsecutiveGateBlocks",
        deviation_minutes=120,
        consecutive_blocked_count=3,
        replan_required=True,
    )
    assert request is not None
    return request


def _approved_request():
    return decide_replan_request(
        _pending_request(),
        decision="Approve",
        decided_by="planner-1",
        decided_at=_utc(9),
    )
