from datetime import datetime, timezone

from sdbr.sdbr_market_control import (
    build_ccr_planned_load,
    build_mta_replenishment_load,
    build_mto_safe_date_summary,
    build_unified_buffer_priority,
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
