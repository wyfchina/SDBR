from datetime import datetime, timezone

import pytest

from sdbr.material_state import (
    MaterialAvailabilityImportRow,
    WipLimitImportRow,
    import_material_availability_from_rows,
    import_wip_limits_from_rows,
)
from sdbr.light_mrp import evaluate_light_mrp
from sdbr.master_data_validation import MaterialRequirement
from sdbr.planner_view import InventoryBufferPolicy
from sdbr.release_candidates import MaterialAvailability


def test_import_material_availability_maps_and_sorts_rows():
    rows = [
        MaterialAvailabilityImportRow(
            item_id="WIP-KIT",
            location_id="LINE",
            allocated_qty=2,
        ),
        MaterialAvailabilityImportRow(
            item_id="RM-STEEL",
            location_id="SUPPLIER",
            allocated_qty=5,
            inbound_qty=15,
            inbound_available_at=datetime(2026, 6, 16, 7, 30, tzinfo=timezone.utc),
        ),
    ]

    availability = import_material_availability_from_rows(rows)

    assert [item.item_id for item in availability] == ["RM-STEEL", "WIP-KIT"]
    assert availability[0].location_id == "SUPPLIER"
    assert availability[0].allocated_qty == 5
    assert availability[0].inbound_qty == 15
    assert availability[0].inbound_available_at == datetime(
        2026, 6, 16, 7, 30, tzinfo=timezone.utc
    )


def test_import_material_availability_rejects_negative_quantities():
    with pytest.raises(ValueError, match="negative allocated quantity"):
        import_material_availability_from_rows(
            [
                MaterialAvailabilityImportRow(
                    item_id="RM-STEEL",
                    location_id="SUPPLIER",
                    allocated_qty=-1,
                )
            ]
        )


def test_import_wip_limits_maps_and_sorts_rows():
    rows = [
        WipLimitImportRow(
            scope_id="LINE",
            current_wip_count=2,
            max_wip_count=8,
        ),
        WipLimitImportRow(
            scope_id="DRUM-FEED",
            current_wip_count=5,
            max_wip_count=6,
            order_wip_increment=2,
        ),
    ]

    limits = import_wip_limits_from_rows(rows)

    assert [limit.scope_id for limit in limits] == ["DRUM-FEED", "LINE"]
    assert limits[0].current_wip_count == 5
    assert limits[0].max_wip_count == 6
    assert limits[0].order_wip_increment == 2


def test_import_wip_limits_rejects_current_wip_above_maximum():
    with pytest.raises(ValueError, match="current WIP above maximum WIP"):
        import_wip_limits_from_rows(
            [
                WipLimitImportRow(
                    scope_id="DRUM-FEED",
                    current_wip_count=7,
                    max_wip_count=6,
                )
            ]
        )


def test_be_data_012_light_mrp_nets_allocated_and_inbound_within_window():
    # BE-DATA-012
    result = evaluate_light_mrp(
        material_requirements=[
            MaterialRequirement("WO-READY", "RM-STEEL", "MAIN", 10),
            MaterialRequirement("WO-INBOUND", "RM-COPPER", "MAIN", 12),
            MaterialRequirement("WO-SHORT", "RM-ALLOY", "MAIN", 20),
            MaterialRequirement("WO-MISSING", "RM-UNKNOWN", "MAIN", 1),
        ],
        inventory_buffers=[
            InventoryBufferPolicy("RM-STEEL", "MAIN", 20, 5, 10, 20),
            InventoryBufferPolicy("RM-COPPER", "MAIN", 5, 2, 5, 10),
            InventoryBufferPolicy("RM-ALLOY", "MAIN", 8, 2, 5, 10),
        ],
        material_availability=[
            MaterialAvailability("RM-STEEL", "MAIN", allocated_qty=3),
            MaterialAvailability(
                "RM-COPPER",
                "MAIN",
                allocated_qty=1,
                inbound_qty=10,
                inbound_available_at=datetime(
                    2026, 6, 21, 10, tzinfo=timezone.utc
                ),
            ),
            MaterialAvailability("RM-ALLOY", "MAIN", inbound_qty=4),
        ],
        evaluated_at=datetime(2026, 6, 21, 8, tzinfo=timezone.utc),
        material_check_window_minutes=180,
    )

    statuses = {line["OrderID"]: line for line in result["Lines"]}
    assert result["EvaluationMode"] == "LightMRPV1"
    assert statuses["WO-READY"]["Status"] == "Available"
    assert statuses["WO-INBOUND"]["Status"] == "CoveredByInbound"
    assert statuses["WO-INBOUND"]["ReasonCode"] == "INBOUND_WITHIN_WINDOW"
    assert statuses["WO-SHORT"]["Status"] == "Shortage"
    assert statuses["WO-SHORT"]["ReasonCode"] == "MATERIAL_SHORTAGE"
    assert statuses["WO-MISSING"]["Status"] == "MissingInventory"
    assert result["Summary"]["ReadyForPlanning"] is False
