from datetime import datetime, timezone

import pytest

from sdbr.operational_state import (
    create_operational_state_snapshot,
    evaluate_operational_state_freshness,
)
from sdbr.planner_view import InventoryBufferPolicy


def test_operational_state_snapshot_requires_timezone_aware_capture_time():
    with pytest.raises(ValueError, match="timezone-aware"):
        create_operational_state_snapshot(
            snapshot_id="OPS-1",
            captured_at=datetime(2026, 6, 16, 8),
            inventory_buffers=[],
            material_availability=[],
            wip_limits=[],
        )


def test_operational_state_snapshot_rejects_duplicate_inventory_buffer_keys():
    buffer = InventoryBufferPolicy(
        item_id="RM-STEEL",
        location_id="SUPPLIER",
        on_hand_qty=80,
        red_zone_qty=50,
        yellow_zone_qty=120,
        green_zone_qty=200,
    )

    with pytest.raises(ValueError, match="duplicate inventory buffers"):
        create_operational_state_snapshot(
            snapshot_id="OPS-1",
            captured_at=datetime(2026, 6, 16, 8, tzinfo=timezone.utc),
            inventory_buffers=[buffer, buffer],
            material_availability=[],
            wip_limits=[],
        )


@pytest.mark.parametrize(
    ("evaluated_at", "expected_status", "expected_acceptable"),
    [
        (datetime(2026, 6, 20, 7, 0, tzinfo=timezone.utc), "Fresh", True),
        (datetime(2026, 6, 20, 7, 1, tzinfo=timezone.utc), "Stale", False),
        (datetime(2026, 6, 20, 5, 59, tzinfo=timezone.utc), "Future", False),
    ],
)
def test_evaluates_operational_state_snapshot_freshness(
    evaluated_at: datetime,
    expected_status: str,
    expected_acceptable: bool,
):
    snapshot = create_operational_state_snapshot(
        snapshot_id="OPS-1",
        captured_at=datetime(2026, 6, 20, 6, 0, tzinfo=timezone.utc),
        inventory_buffers=[],
        material_availability=[],
        wip_limits=[],
    )

    result = evaluate_operational_state_freshness(
        snapshot=snapshot,
        evaluated_at=evaluated_at,
        max_age_minutes=60,
    )

    assert result.status == expected_status
    assert result.acceptable is expected_acceptable
