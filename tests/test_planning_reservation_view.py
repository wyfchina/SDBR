"""Acceptance evidence for BE-SDBR-008 and BE-SDBR-009."""

import pytest

from sdbr.planning_reservation_view import (
    planning_allocated_qty_for_other_demands,
    reservation_load_by_bucket,
    uncommitted_supply_qty,
)


def test_active_reservations_count_but_converted_reservations_do_not():
    result = reservation_load_by_bucket([
        {
            "CapacityReservationID": "R-1",
            "ResourceID": "CCR-1",
            "WindowStartAt": "2026-07-20T08:00:00+00:00",
            "ReservedMinutes": 60,
            "DemandClass": "MTO",
            "Status": "ActivePlanReservation",
        },
        {
            "CapacityReservationID": "R-2",
            "ResourceID": "CCR-1",
            "WindowStartAt": "2026-07-20T10:00:00+00:00",
            "ReservedMinutes": 90,
            "DemandClass": "MTA",
            "Status": "ConvertedToScheduledOccupancy",
        },
    ])

    assert result[("CCR-1", "2026-07-20")]["MtoReservationMinutes"] == 60
    assert result[("CCR-1", "2026-07-20")]["MtaReservationMinutes"] == 0


def test_material_projection_excludes_current_demand_and_externalized_allocation():
    allocations = [
        {
            "ItemID": "RM-1",
            "LocationID": "MAIN",
            "DemandCommitmentID": "DC-A",
            "AllocatedQty": 5,
            "Status": "ActivePlanReservation",
        },
        {
            "ItemID": "RM-1",
            "LocationID": "MAIN",
            "DemandCommitmentID": "DC-B",
            "AllocatedQty": 7,
            "Status": "ActivePlanReservation",
        },
        {
            "ItemID": "RM-1",
            "LocationID": "MAIN",
            "DemandCommitmentID": "DC-C",
            "AllocatedQty": 11,
            "Status": "Externalized",
        },
    ]

    assert planning_allocated_qty_for_other_demands(
        allocations=allocations,
        item_id="RM-1",
        location_id="MAIN",
        current_demand_commitment_id="DC-A",
    ) == 7
    assert uncommitted_supply_qty(
        qualified_supply_qty=20,
        authority_allocated_qty=3,
        allocations=allocations,
        item_id="RM-1",
        location_id="MAIN",
        current_demand_commitment_id="DC-A",
    ) == 10


@pytest.mark.parametrize(
    ("reserved_minutes", "message"),
    [
        (float("nan"), "ReservedMinutes"),
        (-1, "ReservedMinutes"),
        pytest.param(10**10000, "ReservedMinutes", id="overflowing-integer"),
    ],
)
def test_capacity_projection_rejects_non_finite_or_negative_reserved_minutes(
    reserved_minutes: object, message: str
):
    with pytest.raises(ValueError, match=message):
        reservation_load_by_bucket([
            {
                "ResourceID": "CCR-1",
                "WindowStartAt": "2026-07-20T08:00:00+00:00",
                "ReservedMinutes": reserved_minutes,
                "DemandClass": "MTO",
                "Status": "ActivePlanReservation",
            }
        ])


@pytest.mark.parametrize(
    ("qualified_supply_qty", "authority_allocated_qty", "message"),
    [(float("inf"), 0, "qualified_supply_qty"), (10, -1, "authority_allocated_qty")],
)
def test_uncommitted_supply_rejects_non_finite_or_negative_quantities(
    qualified_supply_qty: float,
    authority_allocated_qty: float,
    message: str,
):
    with pytest.raises(ValueError, match=message):
        uncommitted_supply_qty(
            qualified_supply_qty=qualified_supply_qty,
            authority_allocated_qty=authority_allocated_qty,
            allocations=[],
            item_id="RM-1",
            location_id="MAIN",
            current_demand_commitment_id="DC-A",
        )


def test_material_projection_rejects_non_finite_active_allocation_quantity():
    with pytest.raises(ValueError, match="AllocatedQty"):
        planning_allocated_qty_for_other_demands(
            allocations=[{
                "ItemID": "RM-1",
                "LocationID": "MAIN",
                "DemandCommitmentID": "DC-B",
                "AllocatedQty": float("nan"),
                "Status": "ActivePlanReservation",
            }],
            item_id="RM-1",
            location_id="MAIN",
            current_demand_commitment_id="DC-A",
        )
