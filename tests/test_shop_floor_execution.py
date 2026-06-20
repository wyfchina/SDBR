from datetime import datetime, timezone

from sdbr.shop_floor_execution import (
    ExecutionEvent,
    build_authorized_execution_alerts,
    build_authorized_execution_status,
    default_exception_codes,
    summarize_execution_events,
    validate_execution_event,
)


def test_accepts_on_time_arrival_without_exception_code():
    event = ExecutionEvent(
        order_id="WO-1",
        event_type="ArrivedBuffer",
        event_at=datetime(2026, 6, 16, 7, 30, tzinfo=timezone.utc),
        target_start_at=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
    )

    result = validate_execution_event(event)

    assert result.accepted is True
    assert result.status == "Accepted"
    assert result.requires_exception_code is False
    assert result.requires_review is False


def test_rejects_late_arrival_without_exception_code():
    event = ExecutionEvent(
        order_id="WO-1",
        event_type="ArrivedBuffer",
        event_at=datetime(2026, 6, 16, 9, tzinfo=timezone.utc),
        target_start_at=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
    )

    result = validate_execution_event(event)

    assert result.accepted is False
    assert result.status == "Rejected"
    assert result.requires_exception_code is True
    assert result.message == "Late buffer arrival requires an exception code."


def test_accepts_late_arrival_with_exception_code_and_marks_review():
    event = ExecutionEvent(
        order_id="WO-1",
        event_type="ArrivedBuffer",
        event_at=datetime(2026, 6, 16, 9, tzinfo=timezone.utc),
        target_start_at=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
        exception_code="MATERIAL_SHORTAGE",
    )

    result = validate_execution_event(event)

    assert result.accepted is True
    assert result.status == "AcceptedWithException"
    assert result.requires_exception_code is False
    assert result.requires_review is True


def test_rejects_unknown_exception_code():
    event = ExecutionEvent(
        order_id="WO-1",
        event_type="ArrivedBuffer",
        event_at=datetime(2026, 6, 16, 9, tzinfo=timezone.utc),
        target_start_at=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
        exception_code="UNKNOWN_DELAY",
    )

    result = validate_execution_event(event)

    assert result.accepted is False
    assert result.status == "Rejected"
    assert result.message == "Unknown exception code."
    assert result.requires_review is False


def test_summarizes_process_topology_with_elapsed_minutes_and_rework_loops():
    events = [
        {
            "OrderID": "WO-1",
            "EventType": "ArrivedBuffer",
            "EventAt": "2026-06-16T08:00:00+00:00",
            "ExceptionCode": "MATERIAL_SHORTAGE",
            "RequiresReview": True,
        },
        {
            "OrderID": "WO-1",
            "EventType": "StartedOperation",
            "EventAt": "2026-06-16T08:30:00+00:00",
            "ExceptionCode": None,
            "RequiresReview": False,
        },
        {
            "OrderID": "WO-1",
            "EventType": "ArrivedBuffer",
            "EventAt": "2026-06-16T09:15:00+00:00",
            "ExceptionCode": "QUALITY_REWORK",
            "RequiresReview": True,
        },
    ]

    summary = summarize_execution_events(events)

    assert summary == {
        "TotalEvents": 3,
        "RequiresReviewCount": 2,
        "ExceptionCodeCounts": {
            "MATERIAL_SHORTAGE": 1,
            "QUALITY_REWORK": 1,
        },
        "ExceptionCategoryCounts": {
            "Supply": 1,
            "Quality": 1,
        },
        "TopExceptionCategories": [
            {
                "Rank": 1,
                "Category": "Quality",
                "Count": 1,
                "Percent": 50.0,
                "RecommendedAction": "Review quality gates and rework loops.",
            },
            {
                "Rank": 2,
                "Category": "Supply",
                "Count": 1,
                "Percent": 50.0,
                "RecommendedAction": "Expedite replenishment and review supplier reliability.",
            },
        ],
        "LateArrivalSummary": {
            "LateArrivalCount": 0,
            "AverageLateMinutes": 0.0,
            "MaxLateMinutes": 0.0,
        },
        "ReworkLoopCount": 1,
        "ProcessTransitions": [
            {
                "From": "ArrivedBuffer",
                "To": "StartedOperation",
                "Count": 1,
                "AverageElapsedMinutes": 30.0,
                "RequiresReviewCount": 1,
                "IsReworkLoop": False,
            },
            {
                "From": "StartedOperation",
                "To": "ArrivedBuffer",
                "Count": 1,
                "AverageElapsedMinutes": 45.0,
                "RequiresReviewCount": 1,
                "IsReworkLoop": True,
            },
        ],
    }


def test_default_exception_codes_classify_shop_floor_delays():
    codes = default_exception_codes()

    assert codes["MATERIAL_SHORTAGE"].display_name == "Material shortage"
    assert codes["MATERIAL_SHORTAGE"].category == "Supply"
    assert codes["EQUIPMENT_DOWN"].display_name == "Equipment down"
    assert codes["EQUIPMENT_DOWN"].category == "Equipment"


def test_summarizes_top_exception_categories_by_count_and_percent():
    events = [
        {
            "OrderID": "WO-1",
            "EventType": "ArrivedBuffer",
            "EventAt": "2026-06-16T08:00:00+00:00",
            "ExceptionCode": "MATERIAL_SHORTAGE",
            "RequiresReview": True,
        },
        {
            "OrderID": "WO-2",
            "EventType": "ArrivedBuffer",
            "EventAt": "2026-06-16T09:00:00+00:00",
            "ExceptionCode": "MATERIAL_SHORTAGE",
            "RequiresReview": True,
        },
        {
            "OrderID": "WO-3",
            "EventType": "ArrivedBuffer",
            "EventAt": "2026-06-16T10:00:00+00:00",
            "ExceptionCode": "EQUIPMENT_DOWN",
            "RequiresReview": True,
        },
    ]

    summary = summarize_execution_events(events)

    assert summary["TopExceptionCategories"] == [
        {
            "Rank": 1,
            "Category": "Supply",
            "Count": 2,
            "Percent": 66.67,
            "RecommendedAction": "Expedite replenishment and review supplier reliability.",
        },
        {
            "Rank": 2,
            "Category": "Equipment",
            "Count": 1,
            "Percent": 33.33,
            "RecommendedAction": "Review equipment downtime and maintenance coverage.",
        },
    ]


def test_summarizes_late_arrival_minutes_for_buffer_events():
    events = [
        {
            "OrderID": "WO-1",
            "EventType": "ArrivedBuffer",
            "EventAt": "2026-06-16T08:30:00+00:00",
            "TargetStartAt": "2026-06-16T08:00:00+00:00",
            "ExceptionCode": "MATERIAL_SHORTAGE",
            "RequiresReview": True,
        },
        {
            "OrderID": "WO-2",
            "EventType": "ArrivedBuffer",
            "EventAt": "2026-06-16T10:00:00+00:00",
            "TargetStartAt": "2026-06-16T09:00:00+00:00",
            "ExceptionCode": "EQUIPMENT_DOWN",
            "RequiresReview": True,
        },
        {
            "OrderID": "WO-3",
            "EventType": "StartedOperation",
            "EventAt": "2026-06-16T12:00:00+00:00",
            "TargetStartAt": "2026-06-16T08:00:00+00:00",
            "ExceptionCode": None,
            "RequiresReview": False,
        },
    ]

    summary = summarize_execution_events(events)

    assert summary["LateArrivalSummary"] == {
        "LateArrivalCount": 2,
        "AverageLateMinutes": 45.0,
        "MaxLateMinutes": 60.0,
    }


def test_builds_authorized_execution_status_from_dispatch_and_events():
    dispatch_packages = [
        {
            "AuthorizationID": "REL-1",
            "RequestID": "RPL-1",
            "OrderID": "WO-1",
            "DispatchStatus": "ReadyToIssue",
            "ReleasedBy": "planner-1",
            "ReleasedAt": "2026-06-20T06:05:00+00:00",
            "ScheduledStart": "2026-06-16T08:00:00+00:00",
            "ScheduledEnd": "2026-06-16T10:00:00+00:00",
            "SuggestedReleaseAt": "2026-06-20T06:00:00+00:00",
        },
        {
            "AuthorizationID": "REL-2",
            "RequestID": "RPL-2",
            "OrderID": "WO-2",
            "DispatchStatus": "ReadyToIssue",
            "ReleasedBy": "planner-1",
            "ReleasedAt": "2026-06-20T06:10:00+00:00",
            "ScheduledStart": "2026-06-16T09:00:00+00:00",
            "ScheduledEnd": "2026-06-16T11:00:00+00:00",
            "SuggestedReleaseAt": "2026-06-20T06:00:00+00:00",
        },
    ]
    events = [
        {
            "AuthorizationID": "REL-1",
            "OrderID": "WO-1",
            "EventType": "ArrivedBuffer",
            "EventAt": "2026-06-16T07:55:00+00:00",
            "TargetStartAt": "2026-06-16T08:00:00+00:00",
            "ExceptionCode": None,
            "Status": "Accepted",
            "RequiresReview": False,
        },
        {
            "AuthorizationID": "REL-1",
            "OrderID": "WO-1",
            "EventType": "StartedOperation",
            "EventAt": "2026-06-16T08:05:00+00:00",
            "TargetStartAt": "2026-06-16T08:00:00+00:00",
            "ExceptionCode": None,
            "Status": "Accepted",
            "RequiresReview": False,
        },
        {
            "AuthorizationID": "REL-2",
            "OrderID": "WO-2",
            "EventType": "ArrivedBuffer",
            "EventAt": "2026-06-16T09:30:00+00:00",
            "TargetStartAt": "2026-06-16T09:00:00+00:00",
            "ExceptionCode": "MATERIAL_SHORTAGE",
            "Status": "AcceptedWithException",
            "RequiresReview": True,
        },
    ]

    rows = build_authorized_execution_status(dispatch_packages, events)

    assert rows == [
        {
            "AuthorizationID": "REL-2",
            "RequestID": "RPL-2",
            "OrderID": "WO-2",
            "ScheduledStart": "2026-06-16T09:00:00+00:00",
            "ScheduledEnd": "2026-06-16T11:00:00+00:00",
            "ExecutionStatus": "ArrivedBuffer",
            "LastEventType": "ArrivedBuffer",
            "LastEventAt": "2026-06-16T09:30:00+00:00",
            "RequiresReview": True,
            "ExceptionCodes": ["MATERIAL_SHORTAGE"],
        },
        {
            "AuthorizationID": "REL-1",
            "RequestID": "RPL-1",
            "OrderID": "WO-1",
            "ScheduledStart": "2026-06-16T08:00:00+00:00",
            "ScheduledEnd": "2026-06-16T10:00:00+00:00",
            "ExecutionStatus": "InProcess",
            "LastEventType": "StartedOperation",
            "LastEventAt": "2026-06-16T08:05:00+00:00",
            "RequiresReview": False,
            "ExceptionCodes": [],
        },
    ]


def test_builds_authorized_execution_alerts_for_missed_start_and_exceptions():
    dispatch_packages = [
        {
            "AuthorizationID": "REL-1",
            "RequestID": "RPL-1",
            "OrderID": "WO-1",
            "ScheduledStart": "2026-06-16T08:00:00+00:00",
            "ScheduledEnd": "2026-06-16T10:00:00+00:00",
        },
        {
            "AuthorizationID": "REL-2",
            "RequestID": "RPL-2",
            "OrderID": "WO-2",
            "ScheduledStart": "2026-06-16T09:00:00+00:00",
            "ScheduledEnd": "2026-06-16T11:00:00+00:00",
        },
    ]
    events = [
        {
            "AuthorizationID": "REL-2",
            "OrderID": "WO-2",
            "EventType": "ArrivedBuffer",
            "EventAt": "2026-06-16T09:30:00+00:00",
            "TargetStartAt": "2026-06-16T09:00:00+00:00",
            "ExceptionCode": "MATERIAL_SHORTAGE",
            "Status": "AcceptedWithException",
            "RequiresReview": True,
        }
    ]

    alerts = build_authorized_execution_alerts(
        dispatch_packages=dispatch_packages,
        events=events,
        evaluated_at=datetime(2026, 6, 16, 9, 45, tzinfo=timezone.utc),
    )

    assert alerts == [
        {
            "AuthorizationID": "REL-1",
            "OrderID": "WO-1",
            "AlertType": "StartMissed",
            "Severity": "Critical",
            "Message": "Order WO-1 has not started by the scheduled start time.",
            "MinutesLate": 105,
            "ExceptionCodes": [],
        },
        {
            "AuthorizationID": "REL-2",
            "OrderID": "WO-2",
            "AlertType": "ExceptionReview",
            "Severity": "Warning",
            "Message": "Order WO-2 has execution exceptions requiring review.",
            "MinutesLate": 0,
            "ExceptionCodes": ["MATERIAL_SHORTAGE"],
        },
    ]
