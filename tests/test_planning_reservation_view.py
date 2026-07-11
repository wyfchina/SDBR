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
            "MaterialAllocationID": "MA-1",
            "ItemID": "RM-1",
            "LocationID": "MAIN",
            "DemandCommitmentID": "DC-A",
            "AllocatedQty": 5,
            "Status": "ActivePlanReservation",
        },
        {
            "MaterialAllocationID": "MA-2",
            "ItemID": "RM-1",
            "LocationID": "MAIN",
            "DemandCommitmentID": "DC-B",
            "AllocatedQty": 7,
            "Status": "ActivePlanReservation",
        },
        {
            "MaterialAllocationID": "MA-3",
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


def test_capacity_projection_counts_identical_ledger_rows_once():
    # Acceptance evidence: BE-SDBR-008.
    reservation = {
        "CapacityReservationID": "R-1",
        "ResourceID": "CCR-1",
        "WindowStartAt": "2026-07-20T08:00:00+00:00",
        "ReservedMinutes": 60,
        "DemandClass": "MTO",
        "Status": "ActivePlanReservation",
    }

    result = reservation_load_by_bucket([reservation, dict(reservation)])

    assert result[("CCR-1", "2026-07-20")]["MtoReservationMinutes"] == 60
    assert result[("CCR-1", "2026-07-20")]["ReservationLoadMinutes"] == 60


def test_capacity_projection_rejects_conflicting_active_and_converted_ledger_rows():
    reservation = {
        "CapacityReservationID": "R-1",
        "ResourceID": "CCR-1",
        "WindowStartAt": "2026-07-20T08:00:00+00:00",
        "ReservedMinutes": 60,
        "DemandClass": "MTO",
        "Status": "ActivePlanReservation",
    }

    with pytest.raises(ValueError, match="CapacityReservationID.*different content"):
        reservation_load_by_bucket([
            reservation,
            {**reservation, "Status": "ConvertedToScheduledOccupancy"},
        ])


def test_material_projection_counts_identical_ledger_rows_once():
    # Acceptance evidence: BE-SDBR-009.
    allocation = {
        "MaterialAllocationID": "MA-1",
        "ItemID": "RM-1",
        "LocationID": "MAIN",
        "DemandCommitmentID": "DC-B",
        "AllocatedQty": 7,
        "Status": "ActivePlanReservation",
    }

    result = planning_allocated_qty_for_other_demands(
        allocations=[allocation, dict(allocation)],
        item_id="RM-1",
        location_id="MAIN",
        current_demand_commitment_id="DC-A",
    )

    assert result == 7


def test_material_projection_rejects_conflicting_ledger_rows():
    allocation = {
        "MaterialAllocationID": "MA-1",
        "ItemID": "RM-1",
        "LocationID": "MAIN",
        "DemandCommitmentID": "DC-B",
        "AllocatedQty": 7,
        "Status": "ActivePlanReservation",
    }

    with pytest.raises(ValueError, match="MaterialAllocationID.*different content"):
        planning_allocated_qty_for_other_demands(
            allocations=[allocation, {**allocation, "Status": "Externalized"}],
            item_id="RM-1",
            location_id="MAIN",
            current_demand_commitment_id="DC-A",
        )


@pytest.mark.parametrize(
    ("function", "rows", "message"),
    [
        (
            reservation_load_by_bucket,
            [{
                "ResourceID": "CCR-1",
                "WindowStartAt": "2026-07-20T08:00:00+00:00",
                "ReservedMinutes": 60,
                "DemandClass": "MTO",
                "Status": "ActivePlanReservation",
            }],
            "CapacityReservationID",
        ),
        (
            planning_allocated_qty_for_other_demands,
            [{
                "ItemID": "RM-1",
                "LocationID": "MAIN",
                "DemandCommitmentID": "DC-B",
                "AllocatedQty": 7,
                "Status": "ActivePlanReservation",
            }],
            "MaterialAllocationID",
        ),
    ],
)
def test_projection_requires_ledger_identity(
    function: object, rows: list[dict[str, object]], message: str
):
    with pytest.raises(ValueError, match=message):
        if function is reservation_load_by_bucket:
            function(rows)
        else:
            function(
                allocations=rows,
                item_id="RM-1",
                location_id="MAIN",
                current_demand_commitment_id="DC-A",
            )


@pytest.mark.parametrize("demand_class", ["MTO", "mta"])
def test_capacity_projection_accepts_mto_and_mta_demand_classes(demand_class: str):
    result = reservation_load_by_bucket([{
        "CapacityReservationID": "R-1",
        "ResourceID": "CCR-1",
        "WindowStartAt": "2026-07-20T08:00:00+00:00",
        "ReservedMinutes": 60,
        "DemandClass": demand_class,
        "Status": "ActivePlanReservation",
    }])

    bucket = result[("CCR-1", "2026-07-20")]
    assert bucket["MtaReservationMinutes" if demand_class.lower() == "mta" else "MtoReservationMinutes"] == 60


@pytest.mark.parametrize("demand_class", [None, "DependentDemand", "MTS"])
def test_capacity_projection_rejects_missing_or_unsupported_demand_classes(
    demand_class: object,
):
    reservation = {
        "CapacityReservationID": "R-1",
        "ResourceID": "CCR-1",
        "WindowStartAt": "2026-07-20T08:00:00+00:00",
        "ReservedMinutes": 60,
        "Status": "ActivePlanReservation",
    }
    if demand_class is not None:
        reservation["DemandClass"] = demand_class

    with pytest.raises(ValueError, match="DemandClass"):
        reservation_load_by_bucket([reservation])


def test_capacity_projection_rejects_naive_window_start_at():
    with pytest.raises(ValueError, match="timezone-aware"):
        reservation_load_by_bucket([{
            "CapacityReservationID": "R-1",
            "ResourceID": "CCR-1",
            "WindowStartAt": "2026-07-20T08:00:00",
            "ReservedMinutes": 60,
            "DemandClass": "MTO",
            "Status": "ActivePlanReservation",
        }])


@pytest.mark.parametrize(
    ("window_start_at", "expected_day"),
    [
        ("2026-07-20T00:30:00+14:00", "2026-07-20"),
        ("2026-07-20T23:30:00-11:00", "2026-07-20"),
    ],
)
def test_capacity_projection_buckets_using_window_start_own_offset_local_day(
    window_start_at: str, expected_day: str
):
    result = reservation_load_by_bucket([{
        "CapacityReservationID": "R-1",
        "ResourceID": "CCR-1",
        "WindowStartAt": window_start_at,
        "ReservedMinutes": 60,
        "DemandClass": "MTO",
        "Status": "ActivePlanReservation",
    }])

    assert result[("CCR-1", expected_day)]["MtoReservationMinutes"] == 60


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
                "CapacityReservationID": "R-1",
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
                "MaterialAllocationID": "MA-1",
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
