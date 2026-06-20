from datetime import datetime, timezone

from sdbr.master_data_validation import MaterialRequirement
from sdbr.planner_view import InventoryBufferPolicy
from sdbr.release_candidates import (
    MaterialAvailability,
    WipLimit,
    release_candidate_rows_from_schedule,
)


def test_builds_release_candidates_from_schedule_and_material_state():
    schedule = {
        "ReleaseRecommendations": [
            {
                "OrderID": "WO-1",
                "SuggestedReleaseDate": "2026-06-16T08:00:00+00:00",
            },
            {
                "OrderID": "WO-2",
                "SuggestedReleaseDate": "2026-06-16T10:00:00+00:00",
            },
        ],
        "GanttRows": [
            {
                "ResourceID": "WC-DRUM",
                "Bars": [
                    {
                        "OrderID": "WO-1",
                        "OperationID": "WO-1:CUT",
                        "Start": "2026-06-16T09:00:00+00:00",
                        "End": "2026-06-16T11:00:00+00:00",
                        "DurationMinutes": 120,
                    },
                    {
                        "OrderID": "WO-2",
                        "OperationID": "WO-2:CUT",
                        "Start": "2026-06-16T11:00:00+00:00",
                        "End": "2026-06-16T12:00:00+00:00",
                        "DurationMinutes": 60,
                    },
                ],
            }
        ],
    }

    rows = release_candidate_rows_from_schedule(
        schedule=schedule,
        evaluated_at=datetime(2026, 6, 16, 9, 0, tzinfo=timezone.utc),
        inventory_buffers=[
            InventoryBufferPolicy(
                item_id="RM-STEEL",
                location_id="SUPPLIER",
                on_hand_qty=55,
                red_zone_qty=50,
                yellow_zone_qty=120,
                green_zone_qty=200,
            )
        ],
        material_requirements=[
            MaterialRequirement(
                order_id="WO-1",
                item_id="RM-STEEL",
                location_id="SUPPLIER",
                required_qty=10,
            )
        ],
        wip_limits=[],
    )

    assert rows == [
        {
            "OrderID": "WO-1",
            "ScheduledStart": "2026-06-16T09:00:00+00:00",
            "ScheduledEnd": "2026-06-16T11:00:00+00:00",
            "SuggestedReleaseAt": "2026-06-16T08:00:00+00:00",
            "EvaluatedAt": "2026-06-16T09:00:00+00:00",
            "RopeStatus": "Ready",
            "MinutesUntilRelease": 0,
            "MaterialStatus": "Blocked",
            "InventoryRisks": [
                {
                    "OrderID": "WO-1",
                    "ItemID": "RM-STEEL",
                    "LocationID": "SUPPLIER",
                    "RequiredQty": 10,
                    "OnHandQty": 55,
                    "ProjectedOnHandQty": 45,
                    "RedZoneQty": 50,
                    "Message": (
                        "Releasing order WO-1 would project RM-STEEL at "
                        "SUPPLIER below the red zone."
                    ),
                }
            ],
            "WipStatus": "Clear",
            "WipRisks": [],
            "RecommendedAction": "ExpediteMaterial",
        },
        {
            "OrderID": "WO-2",
            "ScheduledStart": "2026-06-16T11:00:00+00:00",
            "ScheduledEnd": "2026-06-16T12:00:00+00:00",
            "SuggestedReleaseAt": "2026-06-16T10:00:00+00:00",
            "EvaluatedAt": "2026-06-16T09:00:00+00:00",
            "RopeStatus": "Early",
            "MinutesUntilRelease": 60,
            "MaterialStatus": "Clear",
            "InventoryRisks": [],
            "WipStatus": "Clear",
            "WipRisks": [],
            "RecommendedAction": "HoldUntilRope",
        },
    ]


def test_blocks_release_candidate_when_wip_limit_would_be_exceeded():
    schedule = {
        "ReleaseRecommendations": [
            {
                "OrderID": "WO-1",
                "SuggestedReleaseDate": "2026-06-16T08:00:00+00:00",
            }
        ],
        "GanttRows": [
            {
                "ResourceID": "WC-DRUM",
                "Bars": [
                    {
                        "OrderID": "WO-1",
                        "OperationID": "WO-1:CUT",
                        "Start": "2026-06-16T09:00:00+00:00",
                        "End": "2026-06-16T11:00:00+00:00",
                        "DurationMinutes": 120,
                    }
                ],
            }
        ],
    }

    rows = release_candidate_rows_from_schedule(
        schedule=schedule,
        evaluated_at=datetime(2026, 6, 16, 9, 0, tzinfo=timezone.utc),
        inventory_buffers=[],
        material_requirements=[],
        wip_limits=[
            WipLimit(
                scope_id="DRUM-FEED",
                current_wip_count=5,
                max_wip_count=5,
            )
        ],
    )

    assert rows[0]["WipStatus"] == "Blocked"
    assert rows[0]["WipRisks"] == [
        {
            "ScopeID": "DRUM-FEED",
            "CurrentWipCount": 5,
            "MaxWipCount": 5,
            "ProjectedWipCount": 6,
            "OrderWipIncrement": 1,
            "Message": (
                "Releasing order WO-1 would project WIP in DRUM-FEED "
                "above the configured limit."
            ),
        }
    ]
    assert rows[0]["RecommendedAction"] == "HoldForWip"


def test_waits_for_inbound_material_when_it_arrives_before_scheduled_start():
    schedule = {
        "ReleaseRecommendations": [
            {
                "OrderID": "WO-1",
                "SuggestedReleaseDate": "2026-06-16T08:00:00+00:00",
            }
        ],
        "GanttRows": [
            {
                "ResourceID": "WC-DRUM",
                "Bars": [
                    {
                        "OrderID": "WO-1",
                        "OperationID": "WO-1:CUT",
                        "Start": "2026-06-16T10:00:00+00:00",
                        "End": "2026-06-16T12:00:00+00:00",
                        "DurationMinutes": 120,
                    }
                ],
            }
        ],
    }

    rows = release_candidate_rows_from_schedule(
        schedule=schedule,
        evaluated_at=datetime(2026, 6, 16, 8, 0, tzinfo=timezone.utc),
        inventory_buffers=[
            InventoryBufferPolicy(
                item_id="RM-STEEL",
                location_id="SUPPLIER",
                on_hand_qty=55,
                red_zone_qty=50,
                yellow_zone_qty=120,
                green_zone_qty=200,
            )
        ],
        material_requirements=[
            MaterialRequirement(
                order_id="WO-1",
                item_id="RM-STEEL",
                location_id="SUPPLIER",
                required_qty=10,
            )
        ],
        material_availability=[
            MaterialAvailability(
                item_id="RM-STEEL",
                location_id="SUPPLIER",
                allocated_qty=5,
                inbound_qty=15,
                inbound_available_at=datetime(2026, 6, 16, 9, 30, tzinfo=timezone.utc),
            )
        ],
    )

    assert rows[0]["MaterialStatus"] == "PendingInbound"
    assert rows[0]["InventoryRisks"] == [
        {
            "OrderID": "WO-1",
            "ItemID": "RM-STEEL",
            "LocationID": "SUPPLIER",
            "RiskType": "InboundPending",
            "RequiredQty": 10,
            "OnHandQty": 55,
            "AllocatedQty": 5,
            "AvailableQty": 50,
            "InboundQty": 15,
            "InboundAvailableAt": "2026-06-16T09:30:00+00:00",
            "ProjectedAvailableQty": 40,
            "ProjectedWithInboundQty": 55,
            "RedZoneQty": 50,
            "Message": (
                "Releasing order WO-1 requires waiting for inbound RM-STEEL "
                "at SUPPLIER before scheduled start."
            ),
        }
    ]
    assert rows[0]["RecommendedAction"] == "WaitForInbound"


def test_blocks_release_when_inbound_material_arrives_after_scheduled_start():
    schedule = {
        "ReleaseRecommendations": [
            {
                "OrderID": "WO-1",
                "SuggestedReleaseDate": "2026-06-16T08:00:00+00:00",
            }
        ],
        "GanttRows": [
            {
                "ResourceID": "WC-DRUM",
                "Bars": [
                    {
                        "OrderID": "WO-1",
                        "OperationID": "WO-1:CUT",
                        "Start": "2026-06-16T10:00:00+00:00",
                        "End": "2026-06-16T12:00:00+00:00",
                        "DurationMinutes": 120,
                    }
                ],
            }
        ],
    }

    rows = release_candidate_rows_from_schedule(
        schedule=schedule,
        evaluated_at=datetime(2026, 6, 16, 8, 0, tzinfo=timezone.utc),
        inventory_buffers=[
            InventoryBufferPolicy(
                item_id="RM-STEEL",
                location_id="SUPPLIER",
                on_hand_qty=55,
                red_zone_qty=50,
                yellow_zone_qty=120,
                green_zone_qty=200,
            )
        ],
        material_requirements=[
            MaterialRequirement(
                order_id="WO-1",
                item_id="RM-STEEL",
                location_id="SUPPLIER",
                required_qty=10,
            )
        ],
        material_availability=[
            MaterialAvailability(
                item_id="RM-STEEL",
                location_id="SUPPLIER",
                allocated_qty=5,
                inbound_qty=15,
                inbound_available_at=datetime(2026, 6, 16, 10, 30, tzinfo=timezone.utc),
            )
        ],
    )

    assert rows[0]["MaterialStatus"] == "Blocked"
    assert rows[0]["InventoryRisks"][0]["RiskType"] == "InboundLate"
    assert rows[0]["InventoryRisks"][0]["InboundAvailableAt"] == "2026-06-16T10:30:00+00:00"
    assert rows[0]["InventoryRisks"][0]["ScheduledStart"] == "2026-06-16T10:00:00+00:00"
    assert rows[0]["RecommendedAction"] == "ExpediteMaterial"
