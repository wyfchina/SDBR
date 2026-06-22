from datetime import datetime, timezone

from sdbr.dispatch_priority import build_mes_dispatch_priority_queue
from sdbr.release_authorization import ReleaseAuthorization


def test_mes_dispatch_priority_allows_red_zone_queue_jump_with_constraint_confirmation():
    # BE-INT-005 / BE-REL-011 / BE-EXEC-001
    planning_run = _planning_run()
    master_data = _master_data()
    authorizations = [
        _authorization("AUTH-A", "WO-A"),
        _authorization("AUTH-B", "WO-B"),
    ]
    release_workbench = {
        "OperationalStateSnapshotID": "OPS-LATEST",
        "ReleasePolicyVersionID": "POLICY-1",
        "Candidates": [
            _candidate("WO-A", "Green", 10),
            _candidate("WO-B", "Red", 90),
        ],
    }

    queue = build_mes_dispatch_priority_queue(
        planning_run=planning_run,
        master_data_version=master_data,
        release_workbench=release_workbench,
        authorizations=authorizations,
        execution_events=[],
        evaluated_at=datetime(2026, 6, 16, 9, tzinfo=timezone.utc),
    )

    resource_queue = queue["Resources"][0]["Queue"]
    assert [row["OrderID"] for row in resource_queue] == ["WO-B", "WO-A"]
    assert resource_queue[0]["ConflictResult"] == "SuggestQueueJump"
    assert resource_queue[0]["ConflictResultLabelZh"] == "建议插队"
    assert resource_queue[0]["RequiresPlannerConfirmation"] is True
    assert resource_queue[0]["PlannerConfirmationReasons"] == [
        "ConstraintResourceSetupOrIdleRisk",
        "RedZoneCanOverrideSetupLossOnlyAfterPlannerConfirmation",
    ]
    assert queue["Summary"]["QueueJumpSuggestionCount"] == 1
    assert queue["Summary"]["PlannerConfirmationCount"] == 1
    assert queue["DispatchPolicy"]["ReleaseIsHardGate"] is True


def test_mes_dispatch_priority_keeps_unreleased_or_blocked_orders_as_warnings():
    planning_run = _planning_run(include_third_order=True)
    master_data = _master_data(include_third_order=True)
    release_workbench = {
        "OperationalStateSnapshotID": "OPS-LATEST",
        "Candidates": [
            _candidate("WO-A", "Green", 10),
            _candidate("WO-B", "Red", 90, action="HoldForWip", blocking_code="WIP_LIMIT_EXCEEDED"),
            _candidate("WO-C", "Yellow", 65),
        ],
    }

    queue = build_mes_dispatch_priority_queue(
        planning_run=planning_run,
        master_data_version=master_data,
        release_workbench=release_workbench,
        authorizations=[_authorization("AUTH-A", "WO-A"), _authorization("AUTH-B", "WO-B")],
        execution_events=[],
        evaluated_at=datetime(2026, 6, 16, 9, tzinfo=timezone.utc),
    )

    resource = queue["Resources"][0]
    assert [row["OrderID"] for row in resource["Queue"]] == ["WO-A"]
    warnings = {row["OrderID"]: row for row in resource["CandidateWarnings"]}
    assert warnings["WO-B"]["LatestGateStatus"] == "LatestOperationalStateBlocked"
    assert warnings["WO-B"]["LatestGateBlockingReasons"][0]["Code"] == "WIP_LIMIT_EXCEEDED"
    assert warnings["WO-C"]["LatestGateStatus"] == "ReleaseNotAuthorized"
    assert queue["Summary"]["CandidateWarningCount"] == 2


def test_mes_dispatch_priority_recommends_replan_after_repeated_queue_jumps():
    queue = build_mes_dispatch_priority_queue(
        planning_run=_planning_run(),
        master_data_version=_master_data(),
        release_workbench={
            "Candidates": [
                _candidate("WO-A", "Green", 10),
                _candidate("WO-B", "Red", 90),
            ],
        },
        authorizations=[
            _authorization("AUTH-A", "WO-A"),
            _authorization("AUTH-B", "WO-B"),
        ],
        execution_events=[
            {
                "EventType": "DispatchAccepted",
                "OrderID": "WO-X1",
                "ResourceID": "WC-DRUM",
                "EventAt": "2026-06-16T08:10:00+00:00",
                "DispatchConflictResult": "SuggestQueueJump",
            },
            {
                "EventType": "DispatchAccepted",
                "OrderID": "WO-X2",
                "ResourceID": "WC-DRUM",
                "EventAt": "2026-06-16T08:20:00+00:00",
                "DispatchConflictResult": "SuggestQueueJump",
            },
            {
                "EventType": "DispatchAccepted",
                "OrderID": "WO-X3",
                "ResourceID": "WC-DRUM",
                "EventAt": "2026-06-16T08:30:00+00:00",
                "DispatchConflictResult": "SuggestQueueJump",
            },
        ],
        evaluated_at=datetime(2026, 6, 16, 9, tzinfo=timezone.utc),
    )

    first = queue["Resources"][0]["Queue"][0]
    assert first["OrderID"] == "WO-B"
    assert first["ConflictResult"] == "NeedsReplan"
    assert first["ConflictResultLabelZh"] == "需要重排"
    assert queue["Summary"]["ReplanSuggestionCount"] == 1


def _planning_run(*, include_third_order: bool = False) -> dict[str, object]:
    bars = [
        {
            "OrderID": "WO-A",
            "OperationID": "OP-A",
            "Start": "2026-06-16T08:00:00+00:00",
            "End": "2026-06-16T09:00:00+00:00",
            "DurationMinutes": 60,
        },
        {
            "OrderID": "WO-B",
            "OperationID": "OP-B",
            "Start": "2026-06-16T09:00:00+00:00",
            "End": "2026-06-16T10:00:00+00:00",
            "DurationMinutes": 60,
        },
    ]
    if include_third_order:
        bars.append(
            {
                "OrderID": "WO-C",
                "OperationID": "OP-C",
                "Start": "2026-06-16T10:00:00+00:00",
                "End": "2026-06-16T11:00:00+00:00",
                "DurationMinutes": 60,
            }
        )
    return {
        "RunID": "RUN-DISPATCH",
        "Schedule": {
            "GanttRows": [
                {
                    "ResourceID": "WC-DRUM",
                    "Bars": bars,
                }
            ]
        },
    }


def _master_data(*, include_third_order: bool = False) -> dict[str, object]:
    orders = [
        {"OrderID": "WO-A", "DueDate": "2026-06-18T08:00:00+00:00"},
        {"OrderID": "WO-B", "DueDate": "2026-06-18T09:00:00+00:00"},
    ]
    if include_third_order:
        orders.append({"OrderID": "WO-C", "DueDate": "2026-06-18T10:00:00+00:00"})
    return {
        "Resources": [
            {"ResourceID": "WC-DRUM", "Name": "Constraint Drum", "IsConstraint": True}
        ],
        "Orders": orders,
    }


def _authorization(authorization_id: str, order_id: str) -> ReleaseAuthorization:
    starts = {
        "WO-A": "2026-06-16T08:00:00+00:00",
        "WO-B": "2026-06-16T09:00:00+00:00",
    }
    ends = {
        "WO-A": "2026-06-16T09:00:00+00:00",
        "WO-B": "2026-06-16T10:00:00+00:00",
    }
    return ReleaseAuthorization(
        authorization_id=authorization_id,
        request_id="RUN-DISPATCH",
        order_id=order_id,
        released_by="planner",
        released_at=datetime(2026, 6, 16, 7, tzinfo=timezone.utc),
        scheduled_start=starts[order_id],
        scheduled_end=ends[order_id],
        suggested_release_at="2026-06-16T07:00:00+00:00",
        status="Authorized",
    )


def _candidate(
    order_id: str,
    zone: str,
    penetration: float,
    *,
    action: str = "ReadyForRelease",
    blocking_code: str | None = None,
) -> dict[str, object]:
    return {
        "OrderID": order_id,
        "RecommendedAction": action,
        "BufferZone": zone,
        "BufferPenetrationPercent": penetration,
        "BlockingReasons": (
            [{"Code": blocking_code, "Category": "WIP", "Details": {}}]
            if blocking_code
            else []
        ),
    }
