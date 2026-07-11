from datetime import datetime, timezone

import pytest

from sdbr.planning_reservation_view import reservation_load_by_bucket
from sdbr.sdbr_market_control import (
    build_ccr_planned_load,
    build_mta_replenishment_load,
    build_mto_safe_date_summary,
    build_unified_buffer_priority,
    classify_ccr_load,
)


def test_ccr_planned_load_adds_unconverted_shared_reservations_once():
    # Acceptance evidence: BE-SDBR-008.
    result = build_ccr_planned_load(
        gantt_rows=[],
        resources=[{
            "ResourceID": "CCR-1",
            "Name": "Constraint",
            "IsConstraint": True,
            "DailyCapacityMinutes": {"2026-07-20": 480},
        }],
        orders=[],
        ddmrp_lines=[],
        horizon_start=datetime(2026, 7, 20, tzinfo=timezone.utc),
        capacity_reservations=[{
            "CapacityReservationID": "R-1",
            "ResourceID": "CCR-1",
            "WindowStartAt": "2026-07-20T08:00:00+00:00",
            "ReservedMinutes": 120,
            "DemandClass": "MTA",
            "Status": "ActivePlanReservation",
        }],
    )

    bucket = result["Buckets"][0]
    assert bucket["MtaLoadMinutes"] == 120
    assert bucket["ReservationLoadMinutes"] == 120
    assert bucket["TotalPlannedLoadMinutes"] == 120
    assert bucket["LoadPercent"] == 25.0


def test_ccr_planned_load_keeps_scheduled_load_unchanged_without_reservations():
    result = build_ccr_planned_load(
        gantt_rows=[],
        resources=[{
            "ResourceID": "CCR-1",
            "Name": "Constraint",
            "IsConstraint": True,
            "DailyCapacityMinutes": {"2026-07-20": 480},
        }],
        orders=[],
        ddmrp_lines=[],
        horizon_start=datetime(2026, 7, 20, tzinfo=timezone.utc),
    )

    bucket = result["Buckets"][0]
    assert bucket["ReservationLoadMinutes"] == 0
    assert bucket["MtoLoadMinutes"] == 0
    assert bucket["MtaLoadMinutes"] == 0
    assert bucket["TotalPlannedLoadMinutes"] == 0


def test_ccr_planned_load_ignores_valid_reservations_outside_visible_buckets():
    # Acceptance evidence: BE-SDBR-008 read-model boundary.
    reservations = [
        {
            "CapacityReservationID": "R-OTHER-RESOURCE",
            "ResourceID": "CCR-OTHER",
            "WindowStartAt": "2026-07-20T08:00:00+00:00",
            "ReservedMinutes": 60,
            "DemandClass": "MTO",
            "Status": "ActivePlanReservation",
        },
        {
            "CapacityReservationID": "R-OTHER-DATE",
            "ResourceID": "CCR-1",
            "WindowStartAt": "2026-07-21T08:00:00+00:00",
            "ReservedMinutes": 90,
            "DemandClass": "MTA",
            "Status": "ActivePlanReservation",
        },
    ]
    pure_projection = reservation_load_by_bucket(reservations)

    result = build_ccr_planned_load(
        gantt_rows=[],
        resources=[{
            "ResourceID": "CCR-1",
            "Name": "Constraint",
            "IsConstraint": True,
            "DailyCapacityMinutes": {"2026-07-20": 480},
        }],
        orders=[],
        ddmrp_lines=[],
        horizon_start=datetime(2026, 7, 20, tzinfo=timezone.utc),
        capacity_reservations=reservations,
    )

    assert pure_projection[("CCR-OTHER", "2026-07-20")]["ReservationLoadMinutes"] == 60
    assert pure_projection[("CCR-1", "2026-07-21")]["ReservationLoadMinutes"] == 90
    bucket = result["Buckets"][0]
    assert bucket["ReservationLoadMinutes"] == 0
    assert bucket["TotalPlannedLoadMinutes"] == 0


def test_ccr_planned_load_rejects_finite_scheduled_and_reservation_total_overflow():
    with pytest.raises(ValueError, match="TotalPlannedLoadMinutes.*aggregate overflow"):
        build_ccr_planned_load(
            gantt_rows=[{
                "ResourceID": "CCR-1",
                "Bars": [{
                    "OrderID": "WO-MTO-1",
                    "OperationID": "DRUM",
                    "Start": "2026-07-20T08:00:00+00:00",
                    "DurationMinutes": 1e308,
                }],
            }],
            resources=[{
                "ResourceID": "CCR-1",
                "Name": "Constraint",
                "IsConstraint": True,
                "DailyCapacityMinutes": {"2026-07-20": 1},
            }],
            orders=[{"OrderID": "WO-MTO-1", "DemandClass": "MTO"}],
            ddmrp_lines=[],
            horizon_start=datetime(2026, 7, 20, tzinfo=timezone.utc),
            capacity_reservations=[{
                "CapacityReservationID": "R-1",
                "ResourceID": "CCR-1",
                "WindowStartAt": "2026-07-20T10:00:00+00:00",
                "ReservedMinutes": 1e308,
                "DemandClass": "MTA",
                "Status": "ActivePlanReservation",
            }],
        )


def test_ccr_planned_load_rejects_finite_load_percent_overflow():
    with pytest.raises(ValueError, match="LoadPercent.*aggregate overflow"):
        build_ccr_planned_load(
            gantt_rows=[{
                "ResourceID": "CCR-1",
                "Bars": [{
                    "OrderID": "WO-MTO-1",
                    "OperationID": "DRUM",
                    "Start": "2026-07-20T08:00:00+00:00",
                    "DurationMinutes": 1e308,
                }],
            }],
            resources=[{
                "ResourceID": "CCR-1",
                "Name": "Constraint",
                "IsConstraint": True,
                "DailyCapacityMinutes": {"2026-07-20": 1},
            }],
            orders=[{"OrderID": "WO-MTO-1", "DemandClass": "MTO"}],
            ddmrp_lines=[],
            horizon_start=datetime(2026, 7, 20, tzinfo=timezone.utc),
        )


def test_ccr_planned_load_rejects_finite_summary_mto_aggregate_overflow():
    with pytest.raises(ValueError, match="Summary.MtoLoadMinutes.*aggregate overflow"):
        build_ccr_planned_load(
            gantt_rows=[
                {
                    "ResourceID": "CCR-1",
                    "Bars": [{
                        "OrderID": "WO-MTO-1",
                        "OperationID": "DRUM",
                        "Start": "2026-07-20T08:00:00+00:00",
                        "DurationMinutes": 1e308,
                    }],
                },
                {
                    "ResourceID": "CCR-2",
                    "Bars": [{
                        "OrderID": "WO-MTO-2",
                        "OperationID": "DRUM",
                        "Start": "2026-07-20T08:00:00+00:00",
                        "DurationMinutes": 1e308,
                    }],
                },
            ],
            resources=[
                {
                    "ResourceID": "CCR-1",
                    "Name": "Constraint 1",
                    "IsConstraint": True,
                    "DailyCapacityMinutes": {"2026-07-20": 10**308},
                },
                {
                    "ResourceID": "CCR-2",
                    "Name": "Constraint 2",
                    "IsConstraint": True,
                    "DailyCapacityMinutes": {"2026-07-20": 10**308},
                },
            ],
            orders=[
                {"OrderID": "WO-MTO-1", "DemandClass": "MTO"},
                {"OrderID": "WO-MTO-2", "DemandClass": "MTO"},
            ],
            ddmrp_lines=[],
            horizon_start=datetime(2026, 7, 20, tzinfo=timezone.utc),
        )


def test_ccr_planned_load_splits_mto_and_mta_load():
    result = build_ccr_planned_load(
        gantt_rows=[
            {
                "ResourceID": "CCR-1",
                "Bars": [
                    {
                        "OrderID": "WO-MTO-1",
                        "OperationID": "DRUM",
                        "Start": "2026-07-10T08:00:00+00:00",
                        "End": "2026-07-10T10:00:00+00:00",
                        "DurationMinutes": 120,
                        "BarType": "Processing",
                    },
                    {
                        "OrderID": "WO-MTA-1",
                        "OperationID": "DRUM",
                        "Start": "2026-07-10T10:00:00+00:00",
                        "End": "2026-07-10T11:00:00+00:00",
                        "DurationMinutes": 60,
                        "BarType": "Processing",
                    },
                ],
            }
        ],
        resources=[
            {
                "ResourceID": "CCR-1",
                "Name": "Constraint",
                "IsConstraint": True,
                "DailyCapacityMinutes": {"2026-07-10": 240},
            }
        ],
        orders=[
            {"OrderID": "WO-MTO-1", "DemandClass": "MTO"},
            {"OrderID": "WO-MTA-1", "DemandClass": "MTA"},
        ],
        ddmrp_lines=[],
        horizon_start=datetime(2026, 7, 10, 0, 0, tzinfo=timezone.utc),
    )

    bucket = result["Buckets"][0]
    assert bucket["ResourceID"] == "CCR-1"
    assert bucket["MtoLoadMinutes"] == 120
    assert bucket["MtaLoadMinutes"] == 60
    assert bucket["TotalPlannedLoadMinutes"] == 180
    assert bucket["LoadPercent"] == 75.0
    assert result["Summary"]["Status"] == "Protected"


def test_ccr_planned_load_marks_near_limit_and_overload():
    result = build_ccr_planned_load(
        gantt_rows=[
            {
                "ResourceID": "CCR-1",
                "Bars": [
                    {
                        "OrderID": "WO-MTO-1",
                        "OperationID": "DRUM",
                        "Start": "2026-07-10T08:00:00+00:00",
                        "End": "2026-07-10T12:30:00+00:00",
                        "DurationMinutes": 270,
                        "BarType": "Processing",
                    }
                ],
            }
        ],
        resources=[
            {
                "ResourceID": "CCR-1",
                "Name": "Constraint",
                "IsConstraint": True,
                "DailyCapacityMinutes": {"2026-07-10": 240},
            }
        ],
        orders=[{"OrderID": "WO-MTO-1", "DemandClass": "MTO"}],
        ddmrp_lines=[],
        horizon_start=datetime(2026, 7, 10, 0, 0, tzinfo=timezone.utc),
    )

    assert result["Buckets"][0]["Status"] == "Overloaded"
    assert result["Summary"]["Status"] == "Overloaded"
    assert result["Summary"]["MaxLoadPercent"] == 112.5


class TestSharedCcrLoadClassifier:
    def test_classifier_preserves_existing_threshold_boundaries(self):
        # Acceptance evidence: BE-SDBR-001, BE-SDBR-010.
        target = 80.0

        assert classify_ccr_load(
            load_percent=80.0,
            protective_capacity_target_percent=target,
        ) == "Protected"
        assert classify_ccr_load(
            load_percent=80.01,
            protective_capacity_target_percent=target,
        ) == "Watch"
        assert classify_ccr_load(
            load_percent=95.0,
            protective_capacity_target_percent=target,
        ) == "NearLimit"
        assert classify_ccr_load(
            load_percent=100.01,
            protective_capacity_target_percent=target,
        ) == "Overloaded"


def test_mto_safe_date_uses_first_protected_ccr_bucket_plus_half_buffer():
    planned_load = {
        "Buckets": [
            {
                "ResourceID": "CCR-1",
                "Date": "2026-07-10",
                "Status": "Overloaded",
                "LoadPercent": 112.5,
            },
            {
                "ResourceID": "CCR-1",
                "Date": "2026-07-11",
                "Status": "Protected",
                "LoadPercent": 70.0,
            },
        ]
    }

    summary = build_mto_safe_date_summary(
        ccr_planned_load=planned_load,
        time_buffer_minutes=480,
    )

    assert summary["Status"] == "Available"
    assert summary["EarliestSafeDate"] == "2026-07-11"
    assert summary["SafePromiseAt"] == "2026-07-11T04:00:00+00:00"
    assert summary["Rule"] == "FirstProtectedCcrBucketPlusHalfTimeBuffer"


def test_mto_safe_date_expires_when_evaluation_time_passes_safe_promise():
    planned_load = {
        "Buckets": [
            {
                "ResourceID": "CCR-1",
                "Date": "2026-07-11",
                "Status": "Protected",
                "LoadPercent": 70.0,
            },
        ]
    }

    summary = build_mto_safe_date_summary(
        ccr_planned_load=planned_load,
        time_buffer_minutes=480,
        evaluated_at=datetime(2026, 7, 11, 5, 0, tzinfo=timezone.utc),
    )

    assert summary["Status"] == "Expired"
    assert summary["EarliestSafeDate"] == "2026-07-11"
    assert summary["SafePromiseAt"] == "2026-07-11T04:00:00+00:00"
    assert "已过期" in summary["BusinessMeaning"]


def test_mta_replenishment_load_separates_mapped_and_unmapped_suggestions():
    result = build_mta_replenishment_load(
        ddmrp_lines=[
            {
                "ItemID": "FG-MTA",
                "LocationID": "MAIN",
                "PlanningStatus": "Red",
                "SuggestedReplenishmentQty": 20,
            },
            {
                "ItemID": "RM-UNMAPPED",
                "LocationID": "MAIN",
                "PlanningStatus": "Yellow",
                "SuggestedReplenishmentQty": 50,
            },
        ],
        orders=[
            {
                "OrderID": "WO-MTA-1",
                "ProductID": "FG-MTA",
                "DemandClass": "MTA",
                "Quantity": 20,
            }
        ],
    )

    assert result["MappedSuggestionCount"] == 1
    assert result["UnmappedSuggestionCount"] == 1
    assert result["Issues"][0]["Code"] == "MTA_REPLENISHMENT_EXECUTION_ORDER_MISSING"


def test_unified_buffer_priority_places_red_mto_and_mta_before_yellow():
    result = build_unified_buffer_priority(
        mto_candidates=[
            {
                "OrderID": "WO-MTO-YELLOW",
                "DemandClass": "MTO",
                "BufferZone": "Yellow",
                "BufferPenetrationPercent": 55,
                "SuggestedReleaseAt": "2026-07-10T08:00:00+00:00",
            }
        ],
        mta_lines=[
            {
                "ItemID": "FG-MTA",
                "LocationID": "MAIN",
                "PlanningStatus": "Red",
                "SuggestedReplenishmentQty": 20,
            }
        ],
    )

    rows = result["Rows"]
    assert rows[0]["DemandClass"] == "MTA"
    assert rows[0]["PriorityZone"] == "Red"
    assert rows[1]["DemandClass"] == "MTO"
    assert rows[1]["PriorityZone"] == "Yellow"
    assert result["Summary"]["RedCount"] == 1


def test_unified_buffer_priority_recomputes_mto_zone_from_schedule_timing():
    result = build_unified_buffer_priority(
        mto_candidates=[
            {
                "OrderID": "WO-MTO-LATE",
                "DemandClass": "MTO",
                "BufferZone": "Green",
                "SuggestedReleaseAt": "2026-07-10T08:00:00+00:00",
                "ScheduledStart": "2026-07-10T12:00:00+00:00",
            }
        ],
        mta_lines=[],
        evaluated_at=datetime(2026, 7, 10, 13, 0, tzinfo=timezone.utc),
    )

    assert result["Rows"][0]["PriorityZone"] == "Late"
    assert result["Rows"][0]["PriorityPenetrationPercent"] == 125.0
    assert result["Summary"]["RedCount"] == 1


def test_unified_buffer_priority_does_not_fallback_to_seed_zone_when_scheduled_start_exists():
    result = build_unified_buffer_priority(
        mto_candidates=[
            {
                "OrderID": "WO-MTO-LATE",
                "DemandClass": "MTO",
                "BufferZone": "Red",
                "BufferPenetrationPercent": 70,
                "SuggestedReleaseAt": "2026-07-10T08:00:00+00:00",
                "ScheduledStart": "2026-07-10T12:00:00+00:00",
            }
        ],
        mta_lines=[],
        evaluated_at=datetime(2026, 7, 10, 13, 0, tzinfo=timezone.utc),
    )

    assert result["Rows"][0]["PriorityZone"] == "Late"
    assert result["Rows"][0]["PriorityPenetrationPercent"] == 125.0
