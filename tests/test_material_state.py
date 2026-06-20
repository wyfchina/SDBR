from datetime import datetime, timezone

import pytest

from sdbr.material_state import (
    MaterialAvailabilityImportRow,
    WipLimitImportRow,
    import_material_availability_from_rows,
    import_wip_limits_from_rows,
)


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
