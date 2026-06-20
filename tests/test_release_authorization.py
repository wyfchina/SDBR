from datetime import datetime, timezone

import pytest

from sdbr.release_authorization import (
    build_release_stability_report,
    build_dispatch_package,
    create_release_authorization,
)


def test_creates_release_authorization_for_ready_candidate():
    candidate = {
        "OrderID": "WO-1",
        "ScheduledStart": "2026-06-16T08:00:00+00:00",
        "ScheduledEnd": "2026-06-16T10:00:00+00:00",
        "SuggestedReleaseAt": "2026-06-20T06:00:00+00:00",
        "RecommendedAction": "ReadyForRelease",
    }

    authorization = create_release_authorization(
        request_id="RPL-123",
        candidate=candidate,
        released_by="planner-1",
        released_at=datetime(2026, 6, 20, 6, 5, tzinfo=timezone.utc),
    )

    assert authorization.authorization_id == "REL-65f65e691742ee3f"
    assert authorization.request_id == "RPL-123"
    assert authorization.order_id == "WO-1"
    assert authorization.released_by == "planner-1"
    assert authorization.released_at.isoformat() == "2026-06-20T06:05:00+00:00"
    assert authorization.scheduled_start == "2026-06-16T08:00:00+00:00"
    assert authorization.scheduled_end == "2026-06-16T10:00:00+00:00"
    assert authorization.suggested_release_at == "2026-06-20T06:00:00+00:00"
    assert authorization.status == "Authorized"


def test_rejects_release_authorization_when_candidate_is_not_ready():
    with pytest.raises(ValueError, match="Only ReadyForRelease candidates can be authorized"):
        create_release_authorization(
            request_id="RPL-123",
            candidate={
                "OrderID": "WO-1",
                "RecommendedAction": "HoldForWip",
            },
            released_by="planner-1",
            released_at=datetime(2026, 6, 20, 6, 5, tzinfo=timezone.utc),
        )


def test_builds_dispatch_package_from_authorization():
    authorization = create_release_authorization(
        request_id="RPL-123",
        candidate={
            "OrderID": "WO-1",
            "ScheduledStart": "2026-06-16T08:00:00+00:00",
            "ScheduledEnd": "2026-06-16T10:00:00+00:00",
            "SuggestedReleaseAt": "2026-06-20T06:00:00+00:00",
            "RecommendedAction": "ReadyForRelease",
        },
        released_by="planner-1",
        released_at=datetime(2026, 6, 20, 6, 5, tzinfo=timezone.utc),
    )

    package = build_dispatch_package(authorization)

    assert package == {
        "AuthorizationID": "REL-65f65e691742ee3f",
        "RequestID": "RPL-123",
        "OrderID": "WO-1",
        "DispatchStatus": "ReadyToIssue",
        "ReleasedBy": "planner-1",
        "ReleasedAt": "2026-06-20T06:05:00+00:00",
        "ScheduledStart": "2026-06-16T08:00:00+00:00",
        "ScheduledEnd": "2026-06-16T10:00:00+00:00",
        "SuggestedReleaseAt": "2026-06-20T06:00:00+00:00",
    }


def test_builds_release_stability_report_from_authorizations():
    on_time = create_release_authorization(
        request_id="RPL-1",
        candidate={
            "OrderID": "WO-1",
            "SuggestedReleaseAt": "2026-06-20T06:00:00+00:00",
            "RecommendedAction": "ReadyForRelease",
        },
        released_by="planner-1",
        released_at=datetime(2026, 6, 20, 6, 20, tzinfo=timezone.utc),
    )
    late = create_release_authorization(
        request_id="RPL-2",
        candidate={
            "OrderID": "WO-2",
            "SuggestedReleaseAt": "2026-06-20T06:00:00+00:00",
            "RecommendedAction": "ReadyForRelease",
        },
        released_by="planner-1",
        released_at=datetime(2026, 6, 20, 9, 5, tzinfo=timezone.utc),
    )

    report = build_release_stability_report([on_time, late])

    assert report == [
        {
            "AuthorizationID": late.authorization_id,
            "RequestID": "RPL-2",
            "OrderID": "WO-2",
            "SuggestedReleaseAt": "2026-06-20T06:00:00+00:00",
            "ReleasedAt": "2026-06-20T09:05:00+00:00",
            "DeviationMinutes": 185,
            "AbsoluteDeviationMinutes": 185,
            "TimingStatus": "Late",
            "Severity": "Critical",
            "Action": "Replan",
            "ReplanRequired": True,
            "ReasonCode": "DeviationAtReplanThreshold",
        },
        {
            "AuthorizationID": on_time.authorization_id,
            "RequestID": "RPL-1",
            "OrderID": "WO-1",
            "SuggestedReleaseAt": "2026-06-20T06:00:00+00:00",
            "ReleasedAt": "2026-06-20T06:20:00+00:00",
            "DeviationMinutes": 20,
            "AbsoluteDeviationMinutes": 20,
            "TimingStatus": "Late",
            "Severity": "Normal",
            "Action": "Monitor",
            "ReplanRequired": False,
            "ReasonCode": "WithinTolerance",
        },
    ]
